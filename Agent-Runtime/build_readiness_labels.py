"""
Build Readiness Labels for GNN Training

Generates training labels by computing skill gap index and readiness scores
for all candidate-role pairs in Neo4j using the existing advanced skill gap engine.

Author: ML Data Engineer
Date: 2025-12-29
"""

import os
import sys
import csv
import logging
import time
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from database import Neo4jConnection
from agents.gap_analyzer import GapAnalyzerTool
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, RECOMMENDATION_API_BASE_URL

# Configure logging with UTF-8 encoding to support Unicode characters
import sys

# Set console encoding to UTF-8 for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('build_readiness_labels.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ReadinessLabelBuilder:
    """
    Builds readiness labels for all candidate-role pairs in Neo4j.
    """
    
    def __init__(self):
        """Initialize the label builder."""
        self.gap_analyzer = GapAnalyzerTool()
        self.processed_count = 0
        self.failed_count = 0
        self.failed_candidates = []
        self.labels = []
        self.stats_by_role = defaultdict(list)
        
    def fetch_candidate_role_pairs(self) -> List[Tuple[str, str]]:
        """
        Fetch all candidate-role pairs from Neo4j.
        
        Returns:
            List of (candidate_id, role_key) tuples
        """
        logger.info("Fetching candidate-role pairs from Neo4j...")
        
        query = """
        MATCH (p:Person)-[:TARGETS_ROLE]->(r:Role)
        WHERE p.candidate_id IS NOT NULL AND r.role_key IS NOT NULL
        RETURN p.candidate_id AS candidate_id, r.role_key AS role_key
        ORDER BY p.candidate_id, r.role_key
        """
        
        try:
            with Neo4jConnection.get_session() as session:
                result = session.run(query)
                pairs = [(record["candidate_id"], record["role_key"]) for record in result]
            
            logger.info(f"[OK] Found {len(pairs)} candidate-role pairs")
            return pairs
            
        except Exception as e:
            logger.error(f"[FAIL] Failed to fetch candidate-role pairs: {e}")
            raise
    
    def compute_label_for_pair(
        self, 
        candidate_id: str, 
        role_key: str
    ) -> Optional[Dict]:
        """
        Compute readiness label for a single candidate-role pair.
        
        Args:
            candidate_id: Candidate identifier
            role_key: Target role key
            
        Returns:
            Dictionary with label data or None if failed
        """
        try:
            logger.info(f"Processing: {candidate_id} -> {role_key}")
            
            # Use existing gap analyzer to get deficits
            gap_result = self.gap_analyzer.analyze_gap(
                candidate_id=candidate_id,
                role_key=role_key,
                top_k=100  # Get all deficits for accurate calculation
            )
            
            if "error" in gap_result:
                logger.warning(f"  ⚠ Gap analysis error: {gap_result['error']}")
                return None
            
            deficits = gap_result.get("skill_gap_top", [])
            
            if not deficits:
                logger.warning(f"  ⚠ No deficits found (perfect match or no role skills)")
                # Perfect match scenario
                return {
                    "candidate_id": candidate_id,
                    "role_key": role_key,
                    "skill_gap_index": 0.0,
                    "readiness": 1.0,
                    "total_deficit": 0.0,
                    "total_importance": 0.0,
                    "num_deficits": 0,
                    "matched_required_skills": 0,
                    "role_skill_coverage": 1.0
                }
            
            # Compute aggregates
            total_deficit = sum(d.deficit for d in deficits)
            total_importance = sum(d.importance for d in deficits)
            
            # Compute skill gap index and readiness
            if total_importance > 0:
                skill_gap_index = total_deficit / total_importance
            else:
                skill_gap_index = 0.0
            
            readiness = 1.0 - skill_gap_index
            
            # Clamp to [0, 1]
            skill_gap_index = max(0.0, min(1.0, skill_gap_index))
            readiness = max(0.0, min(1.0, readiness))
            
            # Additional metrics
            num_deficits = len(deficits)
            
            # Estimate matched skills (skills with p_has > 0)
            matched_skills = sum(1 for d in deficits if d.p_has > 0.1)
            
            # Estimate coverage (proportion of skills with good match)
            role_skill_coverage = matched_skills / num_deficits if num_deficits > 0 else 0.0
            
            label_data = {
                "candidate_id": candidate_id,
                "role_key": role_key,
                "skill_gap_index": round(skill_gap_index, 6),
                "readiness": round(readiness, 6),
                "total_deficit": round(total_deficit, 6),
                "total_importance": round(total_importance, 6),
                "num_deficits": num_deficits,
                "matched_required_skills": matched_skills,
                "role_skill_coverage": round(role_skill_coverage, 6)
            }
            
            logger.info(
                f"  [OK] Computed: skill_gap={skill_gap_index:.4f}, "
                f"readiness={readiness:.4f}, deficits={num_deficits}"
            )
            
            return label_data
            
        except Exception as e:
            logger.error(f"  [FAIL] Failed to compute label: {e}", exc_info=True)
            return None
    
    def write_label_to_neo4j(self, label_data: Dict) -> bool:
        """
        Write readiness label to Neo4j as a separate node.
        
        Creates:
            (:ReadinessLabel {candidate_id, role_key, readiness, skill_gap_index, ...})
            (Person)-[:HAS_LABEL]->(ReadinessLabel)
        
        Args:
            label_data: Dictionary with label information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            MATCH (p:Person {candidate_id: $candidate_id})
            MATCH (r:Role {role_key: $role_key})
            
            // Delete existing label if any (including all its relationships)
            OPTIONAL MATCH (p)-[:HAS_LABEL]->(old:ReadinessLabel)
            WHERE old.candidate_id = $candidate_id AND old.role_key = $role_key
            DETACH DELETE old
            
            // Create new label node
            CREATE (label:ReadinessLabel {
                candidate_id: $candidate_id,
                role_key: $role_key,
                skill_gap_index: $skill_gap_index,
                readiness: $readiness,
                total_deficit: $total_deficit,
                total_importance: $total_importance,
                num_deficits: $num_deficits,
                matched_required_skills: $matched_required_skills,
                role_skill_coverage: $role_skill_coverage,
                created_at: datetime(),
                label_version: 'v1.0'
            })
            
            // Create relationships
            CREATE (p)-[:HAS_LABEL]->(label)
            CREATE (label)-[:FOR_ROLE]->(r)
            
            RETURN label.readiness AS readiness
            """
            
            with Neo4jConnection.get_session() as session:
                result = session.run(query, **label_data)
                record = result.single()
                
                if record:
                    logger.debug(f"  [OK] Wrote label to Neo4j: readiness={record['readiness']:.4f}")
                    return True
                else:
                    logger.warning(f"  ⚠ No record returned (candidate or role not found)")
                    return False
                    
        except Exception as e:
            logger.error(f"  [FAIL] Failed to write label to Neo4j: {e}")
            return False
    
    def save_to_csv(self, output_file: str = "readiness_labels.csv"):
        """
        Save all labels to CSV file.
        
        Args:
            output_file: Output CSV filename
        """
        logger.info(f"Saving {len(self.labels)} labels to {output_file}...")
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'candidate_id', 'role_key', 'skill_gap_index', 'readiness',
                    'total_deficit', 'total_importance', 'num_deficits',
                    'matched_required_skills', 'role_skill_coverage'
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for label in self.labels:
                    writer.writerow(label)
            
            logger.info(f"[OK] CSV saved successfully")
            
        except Exception as e:
            logger.error(f"[FAIL] Failed to save CSV: {e}")
            raise
    
    def compute_statistics(self):
        """Compute and log summary statistics."""
        logger.info("\n" + "="*80)
        logger.info("SUMMARY STATISTICS")
        logger.info("="*80)
        
        logger.info(f"Total pairs processed: {self.processed_count}")
        logger.info(f"Successfully computed: {len(self.labels)}")
        logger.info(f"Failed: {self.failed_count}")
        
        if self.failed_candidates:
            logger.info(f"\nFailed candidates:")
            for cand_id, role_key, reason in self.failed_candidates[:10]:
                logger.info(f"  - {cand_id} -> {role_key}: {reason}")
            if len(self.failed_candidates) > 10:
                logger.info(f"  ... and {len(self.failed_candidates) - 10} more")
        
        if self.labels:
            # Overall statistics
            all_readiness = [label["readiness"] for label in self.labels]
            all_skill_gap = [label["skill_gap_index"] for label in self.labels]
            
            logger.info(f"\nOverall Metrics:")
            logger.info(f"  Mean Readiness: {sum(all_readiness) / len(all_readiness):.4f}")
            logger.info(f"  Min Readiness: {min(all_readiness):.4f}")
            logger.info(f"  Max Readiness: {max(all_readiness):.4f}")
            logger.info(f"  Mean Skill Gap Index: {sum(all_skill_gap) / len(all_skill_gap):.4f}")
            
            # Per-role statistics
            logger.info(f"\nPer-Role Statistics:")
            for role_key, readiness_scores in self.stats_by_role.items():
                mean_readiness = sum(readiness_scores) / len(readiness_scores)
                logger.info(
                    f"  {role_key}: "
                    f"n={len(readiness_scores)}, "
                    f"mean_readiness={mean_readiness:.4f}"
                )
        
        logger.info("="*80 + "\n")
    
    def build(
        self, 
        output_csv: str = "readiness_labels.csv",
        rate_limit_delay: float = 0.1,
        write_to_neo4j: bool = True
    ):
        """
        Main build process: fetch pairs, compute labels, save to CSV and Neo4j.
        
        Args:
            output_csv: Output CSV filename
            rate_limit_delay: Delay between API calls (seconds)
            write_to_neo4j: Whether to write labels back to Neo4j
        """
        start_time = time.time()
        
        logger.info("="*80)
        logger.info("READINESS LABEL BUILDER - Starting")
        logger.info("="*80)
        logger.info(f"Neo4j URI: {NEO4J_URI}")
        logger.info(f"Recommendation API: {RECOMMENDATION_API_BASE_URL}")
        logger.info(f"Output CSV: {output_csv}")
        logger.info(f"Write to Neo4j: {write_to_neo4j}")
        logger.info(f"Rate limit delay: {rate_limit_delay}s")
        logger.info("="*80 + "\n")
        
        # Check API health
        if not self.gap_analyzer.check_api_health():
            logger.error("[FAIL] Recommendation API is not available!")
            logger.error(f"   Check if service is running at {RECOMMENDATION_API_BASE_URL}")
            sys.exit(1)
        
        logger.info("[OK] Recommendation API is healthy\n")
        
        # Fetch candidate-role pairs
        pairs = self.fetch_candidate_role_pairs()
        
        if not pairs:
            logger.warning("No candidate-role pairs found. Exiting.")
            return
        
        # Process each pair
        logger.info(f"\nProcessing {len(pairs)} candidate-role pairs...\n")
        
        for i, (candidate_id, role_key) in enumerate(pairs, 1):
            logger.info(f"[{i}/{len(pairs)}] Processing: {candidate_id} -> {role_key}")
            
            self.processed_count += 1
            
            # Compute label
            label_data = self.compute_label_for_pair(candidate_id, role_key)
            
            if label_data is None:
                self.failed_count += 1
                self.failed_candidates.append((candidate_id, role_key, "Computation failed"))
                continue
            
            # Store label
            self.labels.append(label_data)
            self.stats_by_role[role_key].append(label_data["readiness"])
            
            # Write to Neo4j
            if write_to_neo4j:
                success = self.write_label_to_neo4j(label_data)
                if not success:
                    logger.warning(f"  ⚠ Failed to write to Neo4j (label still saved to CSV)")
            
            # Rate limiting
            if rate_limit_delay > 0:
                time.sleep(rate_limit_delay)
            
            # Progress update every 10 items
            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(pairs)} ({i/len(pairs)*100:.1f}%)\n")
        
        # Save to CSV
        logger.info("\n")
        self.save_to_csv(output_csv)
        
        # Compute and display statistics
        self.compute_statistics()
        
        # Final summary
        elapsed_time = time.time() - start_time
        logger.info(f"[OK] Process completed in {elapsed_time:.2f} seconds")
        logger.info(f"[OK] Output saved to: {output_csv}")
        
        if write_to_neo4j:
            logger.info(f"[OK] Labels written to Neo4j as ReadinessLabel nodes")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build readiness labels for GNN training"
    )
    parser.add_argument(
        "--output",
        default="readiness_labels.csv",
        help="Output CSV filename (default: readiness_labels.csv)"
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.1,
        help="Delay between API calls in seconds (default: 0.1)"
    )
    parser.add_argument(
        "--no-neo4j",
        action="store_true",
        help="Skip writing labels back to Neo4j"
    )
    
    args = parser.parse_args()
    
    try:
        builder = ReadinessLabelBuilder()
        builder.build(
            output_csv=args.output,
            rate_limit_delay=args.rate_limit,
            write_to_neo4j=not args.no_neo4j
        )
        
    except KeyboardInterrupt:
        logger.info("\n\n[INTERRUPTED] Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n[FAIL] Process failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
