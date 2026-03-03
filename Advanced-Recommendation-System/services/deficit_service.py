"""
Deficit Engine - Skill Gap Ranking with Graded Matching.

Computes deficit(skill) = importance(role, skill) × (1 - match_strength(skill))

NEW: Uses graded matching instead of binary (0/1) confidence:
- Exact match: 1.0 → deficit = 0
- Cluster match: 0.7 → deficit = importance × 0.3
- Similarity match: 0.4-0.6 → deficit = importance × 0.4-0.6
- No match: 0.0 → deficit = importance × 1.0

This reduces false negatives (e.g., candidate has "Python3" but job needs "Python").
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class DeficitService:
    """
    Computes skill deficits by combining importance and graded match strength.
    
    Higher deficit = important skill that candidate lacks (or only partially has).
    """
    
    @staticmethod
    def compute_deficits(
        candidate_confidence: Dict[str, Dict],
        role_importance: Dict[str, Dict],
        top_k: int = 25
    ) -> List[Dict]:
        """
        Compute deficit scores and return top-K.
        
        DEPRECATED: This method uses OLD binary confidence.
        Use compute_deficits_with_graded_matching() for better accuracy.
        
        Args:
            candidate_confidence: Dict mapping skill_name to confidence data
            role_importance: Dict mapping skill_name to importance data
            top_k: Number of top deficits to return
            
        Returns:
            List of top-K deficit dictionaries sorted by deficit descending
        """
        logger.info(f"Computing skill deficits (top_k={top_k})")
        
        deficits = []
        
        for skill_name, importance_data in role_importance.items():
            # Get candidate confidence (default 0 if skill not in profile)
            conf_data = candidate_confidence.get(skill_name, {"confidence": 0.0})
            p_has = conf_data["confidence"]
            
            # Extract importance data
            tf = importance_data["tf"]
            df = importance_data["df"]
            idf = importance_data["idf"]
            importance = importance_data["importance"]
            
            # Compute deficit = importance × (1 - p_has)
            deficit = importance * (1 - p_has)
            
            deficits.append({
                "skill_name": skill_name,
                "p_has": p_has,
                "tf": tf,
                "df": df,
                "idf": idf,
                "importance": importance,
                "deficit": deficit,
            })
        
        # Sort by deficit descending and return top-K
        deficits.sort(key=lambda x: x["deficit"], reverse=True)
        top_deficits = deficits[:top_k]
        
        logger.info(f"Identified {len(top_deficits)} top deficits")
        return top_deficits
    
    @staticmethod
    def compute_deficits_with_graded_matching(
        session,
        candidate_id: str,
        role_importance: Dict[str, Dict],
        top_k: int = 25
    ) -> List[Dict]:
        """
        Compute deficit scores using GRADED skill matching (research-grade).
        
        Key improvements over binary matching:
        1. Recognizes similar skills (Python3 → Python)
        2. Uses skill clusters (supervised learning, machine learning)
        3. Leverages graph similarity edges
        4. Provides richer signal for GNN training
        
        Args:
            session: Neo4j session for skill matching queries
            candidate_id: Candidate identifier
            role_importance: Dict mapping skill_name to importance data
            top_k: Number of top deficits to return
            
        Returns:
            List of top-K deficit dictionaries with match_strength field:
            [
                {
                    "skill_name": "TensorFlow",
                    "match_strength": 0.6,    # NEW: graded match
                    "tf": 38,
                    "df": 3,
                    "idf": 1.609,
                    "importance": 61.14,
                    "deficit": 24.456         # importance × (1 - 0.6)
                },
                ...
            ]
        """
        from .skill_matching import compute_graded_matches
        
        logger.info(f"Computing deficits with GRADED matching (top_k={top_k})")
        
        # Get all required skills for this role
        required_skill_names = list(role_importance.keys())
        
        # Compute graded match strengths (3 Neo4j queries total)
        match_strengths = compute_graded_matches(session, candidate_id, required_skill_names)
        
        # Compute deficits
        deficits = []
        
        for skill_name, importance_data in role_importance.items():
            # Get match strength (0.0 to 1.0)
            match_strength = match_strengths.get(skill_name, 0.0)
            
            # Extract importance data
            tf = importance_data["tf"]
            df = importance_data["df"]
            idf = importance_data["idf"]
            importance = importance_data["importance"]
            
            # NEW FORMULA: deficit = importance × (1 - match_strength)
            # Examples:
            # - Exact match (1.0): deficit = 0
            # - Cluster match (0.7): deficit = importance × 0.3
            # - No match (0.0): deficit = importance × 1.0
            deficit = importance * (1 - match_strength)
            
            deficits.append({
                "skill_name": skill_name,
                "match_strength": match_strength,  # NEW: instead of binary p_has
                "tf": tf,
                "df": df,
                "idf": idf,
                "importance": importance,
                "deficit": deficit,
            })
        
        # Sort by deficit descending and return top-K
        deficits.sort(key=lambda x: x["deficit"], reverse=True)
        top_deficits = deficits[:top_k]
        
        # Log matching statistics
        exact_matches = sum(1 for d in deficits if d["match_strength"] == 1.0)
        partial_matches = sum(1 for d in deficits if 0.0 < d["match_strength"] < 1.0)
        no_matches = sum(1 for d in deficits if d["match_strength"] == 0.0)
        
        logger.info(
            f"Identified {len(top_deficits)} top deficits. "
            f"Match distribution: {exact_matches} exact, {partial_matches} partial, {no_matches} gaps"
        )
        
        return top_deficits
