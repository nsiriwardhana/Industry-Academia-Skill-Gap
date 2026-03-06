"""
XAI Dataset Builder Service.

Constructs explanation dataset by querying system components:
- Gathers candidate-role-skill triples
- Computes features: P_has, importance, P_gnn, category coverage, etc.
- Computes label: final_score = (1 - P_has) × importance × P_gnn
"""
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import pandas as pd
import numpy as np
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.neo4j_connection import Neo4jConnection
from services.gnn_inference_service import gnn_service
from services.skill_confidence_service import SkillConfidenceService
from services.role_importance_service import RoleImportanceService

logger = logging.getLogger(__name__)


class XAIDatasetBuilder:
    """Builds explanation dataset for missing skill ranking XAI."""
    
    def __init__(self):
        """Initialize dataset builder."""
        self.neo4j = Neo4jConnection()
        logger.info("XAI Dataset Builder initialized")
    
    def build_dataset(
        self,
        candidate_role_pairs: List[Tuple[str, str]],
        output_path: str = "xai/output/xai_missing_skill_dataset.csv"
    ) -> pd.DataFrame:
        """
        Build explanation dataset from candidate-role pairs.
        
        For each pair, creates rows for all role-required skills with:
        - Features: P_has, importance, P_gnn, category_coverage, etc.
        - Label: final_score = (1 - P_has) × importance × P_gnn
        
        Args:
            candidate_role_pairs: List of (candidate_id, role_key) tuples
            output_path: Path to save CSV
            
        Returns:
            DataFrame with explanation dataset
        """
        logger.info(f"Building XAI dataset for {len(candidate_role_pairs)} candidate-role pairs")
        
        rows = []
        failed_pairs = []
        
        with self.neo4j.get_session() as session:
            for candidate_id, role_key in tqdm(candidate_role_pairs, desc="Building dataset"):
                try:
                    pair_rows = self._build_rows_for_pair(session, candidate_id, role_key)
                    rows.extend(pair_rows)
                except Exception as e:
                    logger.warning(f"Failed to process {candidate_id}/{role_key}: {e}")
                    failed_pairs.append((candidate_id, role_key, str(e)))
        
        df = pd.DataFrame(rows)
        
        logger.info(f"Built dataset: {len(df)} rows from {len(candidate_role_pairs)} pairs")
        logger.info(f"Failed pairs: {len(failed_pairs)}")
        logger.info(f"Columns: {list(df.columns)}")
        
        # Save to CSV
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_file, index=False)
        logger.info(f"Saved dataset to {output_file}")
        
        return df
    
    def _build_rows_for_pair(
        self,
        session,
        candidate_id: str,
        role_key: str
    ) -> List[Dict]:
        """
        Build dataset rows for one candidate-role pair.
        
        Creates one row per role-required skill.
        """
        rows = []
        
        # Step 1: Get role skills and importance
        role_importance_dict, _, role_name = RoleImportanceService.compute_role_importance(
            session, role_key
        )
        
        if not role_importance_dict:
            logger.warning(f"No skills found for role {role_key}")
            return rows
        
        # Step 2: Get candidate skill confidence (P_has)
        candidate_confidence = SkillConfidenceService.compute_confidence(session, candidate_id)
        
        # Step 3: Get GNN predictions (P_gnn) for all skills
        try:
            gnn_probs = gnn_service.predict_skill_probs(candidate_id)
        except ValueError:
            logger.warning(f"Candidate {candidate_id} not in GNN graph")
            return rows
        
        # Step 4: Get candidate profile for feature engineering
        candidate_profile = self._get_candidate_profile(session, candidate_id)
        
        # Step 5: Get skill categories
        skill_categories = self._get_skill_categories(session, list(role_importance_dict.keys()))
        
        # Step 6: For each role-required skill, create row
        for skill_name, importance_data in role_importance_dict.items():
            # Get components
            p_has = candidate_confidence.get(skill_name, {}).get('confidence', 0.0)
            importance = importance_data.get('importance', 0.0)
            p_gnn = gnn_probs.get(skill_name, 0.0)
            
            # Compute label: final_score
            gap_magnitude = 1.0 - p_has
            final_score = gap_magnitude * importance * p_gnn
            
            # Get category
            category = skill_categories.get(skill_name, 'Uncategorized')
            
            # Compute additional features
            category_coverage = self._compute_category_coverage(
                candidate_profile['skills'], 
                category, 
                skill_categories
            )
            
            project_support = self._compute_project_support(
                candidate_profile['projects'],
                category,
                session
            )
            
            neighbor_overlap = self._compute_neighbor_overlap(
                candidate_profile['skills'],
                skill_name,
                session
            )
            
            skill_popularity = self._compute_skill_popularity(skill_name, session)
            
            # Create row
            row = {
                # Identifiers
                'candidate_id': candidate_id,
                'role_key': role_key,
                'role_name': role_name,
                'skill': skill_name,
                
                # Core features (formula components)
                'P_has': p_has,
                'importance': importance,
                'P_gnn': p_gnn,
                'gap_magnitude': gap_magnitude,
                
                # Additional features
                'category': category,
                'category_coverage': category_coverage,
                'project_support': project_support,
                'neighbor_overlap': neighbor_overlap,
                'skill_popularity': skill_popularity,
                
                # Candidate profile stats
                'num_candidate_skills': len(candidate_profile['skills']),
                'num_candidate_projects': len(candidate_profile['projects']),
                'num_candidate_categories': len(set(skill_categories.get(s, 'Uncategorized') 
                                                     for s in candidate_profile['skills'])),
                
                # Label
                'final_score': final_score
            }
            
            rows.append(row)
        
        return rows
    
    def _get_candidate_profile(self, session, candidate_id: str) -> Dict:
        """Get candidate's skills and projects."""
        query = """
        MATCH (p:Person {candidate_id: $candidate_id})
        
        OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)
        WITH p, collect(DISTINCT s.name) as skills
        
        OPTIONAL MATCH (p)-[:WORKED_ON]->(proj:Project)
        WITH skills, collect(DISTINCT proj.name) as projects
        
        RETURN skills, projects
        """
        
        result = session.run(query, candidate_id=candidate_id)
        record = result.single()
        
        if not record:
            return {'skills': [], 'projects': []}
        
        return {
            'skills': record['skills'] or [],
            'projects': record['projects'] or []
        }
    
    def _get_skill_categories(self, session, skill_names: List[str]) -> Dict[str, str]:
        """Get categories for skills."""
        if not skill_names:
            return {}
        
        query = """
        UNWIND $skill_names as skill_name
        MATCH (s:Skill {name: skill_name})
        OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:SkillCategory)
        RETURN s.name as skill, cat.name as category
        """
        
        result = session.run(query, skill_names=skill_names)
        return {record['skill']: record['category'] or 'Uncategorized' for record in result}
    
    def _compute_category_coverage(
        self,
        candidate_skills: List[str],
        target_category: str,
        all_skill_categories: Dict[str, str]
    ) -> float:
        """
        Compute fraction of candidate skills in target category.
        
        Returns: 0-1 indicating coverage
        """
        if not candidate_skills:
            return 0.0
        
        category_skills = [s for s in candidate_skills 
                          if all_skill_categories.get(s) == target_category]
        
        return len(category_skills) / len(candidate_skills)
    
    def _compute_project_support(
        self,
        candidate_projects: List[str],
        target_category: str,
        session
    ) -> int:
        """
        Count candidate projects using skills in target category.
        """
        if not candidate_projects:
            return 0
        
        query = """
        UNWIND $project_names as proj_name
        MATCH (proj:Project {name: proj_name})
        MATCH (proj)-[:USES_TECHNOLOGY]->(s:Skill)-[:BELONGS_TO_CATEGORY]->(cat:SkillCategory {name: $category})
        RETURN count(DISTINCT proj) as count
        """
        
        result = session.run(query, project_names=candidate_projects, category=target_category)
        record = result.single()
        return record['count'] if record else 0
    
    def _compute_neighbor_overlap(
        self,
        candidate_skills: List[str],
        target_skill: str,
        session
    ) -> float:
        """
        Compute how many candidate skills co-occur with target skill.
        
        Returns: 0-1 normalized overlap score
        """
        if not candidate_skills:
            return 0.0
        
        query = """
        MATCH (target:Skill {name: $target_skill})
        UNWIND $candidate_skills as cand_skill
        MATCH (s:Skill {name: cand_skill})
        
        // Co-occurrence in projects
        OPTIONAL MATCH (target)<-[:USES_TECHNOLOGY]-(p:Project)-[:USES_TECHNOLOGY]->(s)
        WITH s, count(DISTINCT p) as proj_cooccur
        
        // Co-occurrence in candidates
        OPTIONAL MATCH (target)<-[:HAS_SKILL]-(person:Person)-[:HAS_SKILL]->(s)
        WITH s, proj_cooccur, count(DISTINCT person) as person_cooccur
        
        WITH s, proj_cooccur + person_cooccur as total_cooccur
        WHERE total_cooccur > 0
        
        RETURN count(s) as overlapping_skills
        """
        
        result = session.run(
            query, 
            target_skill=target_skill, 
            candidate_skills=candidate_skills
        )
        record = result.single()
        overlapping = record['overlapping_skills'] if record else 0
        
        return min(overlapping / len(candidate_skills), 1.0)
    
    def _compute_skill_popularity(self, skill_name: str, session) -> int:
        """
        Compute global popularity of skill (person + job mentions).
        """
        query = """
        MATCH (s:Skill {name: $skill_name})
        
        // Count persons with this skill
        OPTIONAL MATCH (s)<-[:HAS_SKILL]-(p:Person)
        WITH s, count(DISTINCT p) as person_count
        
        // Count roles requiring this skill
        OPTIONAL MATCH (s)<-[:REQUIRES_SKILL]-(r:Role)
        WITH person_count, count(DISTINCT r) as role_count
        
        RETURN person_count + role_count as popularity
        """
        
        result = session.run(query, skill_name=skill_name)
        record = result.single()
        return record['popularity'] if record else 0
    
    def close(self):
        """Close Neo4j connection."""
        self.neo4j.close()
