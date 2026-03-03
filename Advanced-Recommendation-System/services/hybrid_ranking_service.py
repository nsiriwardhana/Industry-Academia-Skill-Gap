"""
Hybrid Skill Gap Ranking Service.

Implements HYBRID MULTIPLICATIVE formula where GNN is used as a learnability factor:
    final_score = gap × importance_norm × learn

Where:
- gap = 1 - P_has (missing magnitude, 0-1)
- importance_norm = importance / max_importance for this role (0-1)
- learn = P_gnn from trained GNN model (0-1)

This differs from the additive GNN ranking in gnn_ranking_service.py which uses:
    0.3×(1-P_has_norm) + 0.4×importance_norm + 0.3×P_gnn_norm

The multiplicative approach emphasizes skills that are:
1. Missing (high gap)
2. Important for the role (high importance)
3. Learnable by the candidate (high P_gnn)

If any component is low, the final score drops significantly.
"""
import logging
from typing import Dict, List, Tuple
from collections import defaultdict
import numpy as np
from services.gnn_inference_service import gnn_service
from services.skill_confidence_service import SkillConfidenceService
from services.role_importance_service import RoleImportanceService
from services.category_service import CategoryService

logger = logging.getLogger(__name__)


class HybridRankingService:
    """
    Service for ranking missing skills using hybrid multiplicative formula.
    Combines symbolic reasoning (gap, importance) with GNN learnability.
    """
    
    @staticmethod
    def rank_missing_skills_hybrid(
        session,
        candidate_id: str,
        role_key: str,
        top_k: int = 25,
        p_has_threshold: float = 0.6
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Rank missing skills using hybrid multiplicative formula.
        
        Algorithm:
        1. Get role required skills with importance scores
        2. Normalize importance: importance_norm = importance / max_importance(role)
        3. Get candidate skill confidence (P_has)
        4. Filter to missing skills (P_has < threshold)
        5. Get P_gnn for all skills from GNN
        6. For each missing skill s:
           gap = 1 - P_has(candidate, s)
           final_score = gap × importance_norm × P_gnn
        7. Rank by final_score desc, return top_k
        8. Aggregate by category for XAI
        
        Args:
            session: Neo4j session
            candidate_id: Candidate identifier
            role_key: Role identifier
            top_k: Number of top skills to return (default: 25)
            p_has_threshold: Threshold for considering skill as "missing" (default: 0.6)
            
        Returns:
            Tuple of (ranked_skills, category_summary, metadata):
            - ranked_skills: List of dicts with skill, scores, and reasons
            - category_summary: List of dicts with category-level gap scores
            - metadata: Dict with computation statistics
        """
        logger.info(f"Hybrid ranking: candidate={candidate_id}, role={role_key}")
        
        # Check if GNN service is ready
        if not gnn_service.is_ready():
            raise RuntimeError("GNN model not loaded. Service not ready.")
        
        # Step 1: Get role required skills with importance scores
        role_importance_dict, total_jobs, role_name = RoleImportanceService.compute_role_importance(
            session, role_key
        )
        
        if not role_importance_dict:
            logger.warning(f"No skills found for role {role_key}")
            return [], [], {"warning": "Role has no required skills"}
        
        logger.info(f"Role '{role_name}' has {len(role_importance_dict)} required skills")
        
        # Step 2: Normalize importance per role (importance_norm = importance / max_importance)
        importance_values = [data['importance'] for data in role_importance_dict.values()]
        max_importance = max(importance_values) if importance_values else 1.0
        
        if max_importance < 1e-9:
            logger.warning(f"Max importance is zero for role {role_key}, using 1.0")
            max_importance = 1.0
        
        logger.info(f"Max importance for role: {max_importance:.4f}")
        
        # Step 3: Get candidate skill confidence (P_has)
        candidate_confidence = SkillConfidenceService.compute_confidence(session, candidate_id)
        logger.info(f"Candidate has confidence scores for {len(candidate_confidence)} skills")
        
        # Step 4 & 5: Get P_gnn for all skills from GNN
        # Note: use_fallback=True enables hybrid ranking for new candidates
        try:
            gnn_probs = gnn_service.predict_skill_probs(candidate_id, use_fallback=True)
            logger.info(f"GNN predicted probabilities for {len(gnn_probs)} skills")
        except ValueError as e:
            # This should not happen with use_fallback=True, but handle defensively
            logger.error(f"Candidate {candidate_id} not found in GNN graph: {e}")
            raise ValueError(
                f"Candidate {candidate_id} not in training data and fallback failed. "
                f"Use symbolic ranking method instead."
            ) from e
        
        # Step 6: Filter to missing skills and compute final scores
        candidate_skills = []
        
        for skill_name, importance_data in role_importance_dict.items():
            # Get P_has (default to 0 if not in candidate profile)
            p_has = candidate_confidence.get(skill_name, {}).get('confidence', 0.0)
            
            # Filter: Only consider "missing" skills
            if p_has >= p_has_threshold:
                continue
            
            # Get importance_norm
            importance = importance_data.get('importance', 0.0)
            importance_norm = importance / max_importance
            
            # Get P_gnn (default to 0 if not predicted)
            p_gnn = gnn_probs.get(skill_name, 0.0)
            
            # Compute gap
            gap = 1.0 - p_has
            
            # HYBRID MULTIPLICATIVE FORMULA
            final_score = gap * importance_norm * p_gnn
            
            # Get category (will now come from role_importance_dict)
            category = importance_data.get('category', 'Uncategorized')
            
            # Generate reason (include fallback info if applicable)
            is_new_candidate = candidate_id not in gnn_service.candidate_id_to_idx
            reason = HybridRankingService._generate_reason(
                gap, importance_norm, p_gnn, final_score, is_new_candidate
            )
            
            candidate_skills.append({
                'skill': skill_name,
                'category': category,
                'final_score': final_score,
                'gap': gap,
                'importance': importance,
                'importance_norm': importance_norm,
                'P_gnn': p_gnn,
                'P_has': p_has,
                'reason': reason
            })
        
        if not candidate_skills:
            logger.warning(f"No missing skills found for candidate {candidate_id} in role {role_key}")
            return [], [], {
                "warning": "No missing skills",
                "role_name": role_name,
                "total_required_skills": len(role_importance_dict),
                "p_has_threshold": p_has_threshold
            }
        
        # Step 7: Rank by final_score descending
        candidate_skills.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Take top_k
        top_skills = candidate_skills[:top_k]
        
        logger.info(f"Ranked {len(candidate_skills)} missing skills, returning top {len(top_skills)}")
        
        # Step 8: Aggregate by category for XAI
        category_summary = HybridRankingService._aggregate_by_category(top_skills)
        
        # Build metadata
        metadata = {
            "role_name": role_name,
            "total_required_skills": len(role_importance_dict),
            "total_missing_skills": len(candidate_skills),
            "returned_skills": len(top_skills),
            "p_has_threshold": p_has_threshold,
            "max_importance": max_importance,
            "formula": "gap × importance_norm × P_gnn",
            "ranking_method": "hybrid_multiplicative"
        }
        
        return top_skills, category_summary, metadata
    
    @staticmethod
    def _generate_reason(gap: float, importance_norm: float, p_gnn: float, final_score: float, is_new_candidate: bool = False) -> str:
        """
        Generate human-readable reason for skill ranking.
        
        Args:
            gap: Missing magnitude (0-1)
            importance_norm: Normalized importance (0-1)
            p_gnn: GNN learnability score (0-1)
            final_score: Final ranking score
            is_new_candidate: If True, P_gnn is average fallback (not personalized)
            
        Returns:
            Human-readable reason string
        """
        # Add fallback indicator
        fallback_note = " (avg baseline)" if is_new_candidate else ""
        
        # Classify each component
        gap_label = "high" if gap > 0.7 else "medium" if gap > 0.4 else "low"
        importance_label = "critical" if importance_norm > 0.7 else "important" if importance_norm > 0.4 else "moderate"
        learn_label = "high" if p_gnn > 0.6 else "medium" if p_gnn > 0.3 else "low"
        
        # Build reason
        parts = []
        
        if gap > 0.7:
            parts.append(f"{gap_label} skill gap ({gap:.0%} missing)")
        
        if importance_norm > 0.5:
            parts.append(f"{importance_label} for role")
        
        if p_gnn > 0.5:
            parts.append(f"{learn_label} learning potential{fallback_note}")
        elif p_gnn < 0.3:
            parts.append(f"{learn_label} learnability{fallback_note} (may be challenging)")
        
        if not parts:
            parts.append(f"Gap: {gap:.0%}, Importance: {importance_norm:.0%}, Learnability: {p_gnn:.0%}{fallback_note}")
        
        return "; ".join(parts)
    
    @staticmethod
    def _aggregate_by_category(skills: List[Dict]) -> List[Dict]:
        """
        Aggregate skills by category for XAI summary.
        
        Args:
            skills: List of skill dicts with 'category' and 'final_score'
            
        Returns:
            List of category summaries sorted by gap_score descending
        """
        category_data = defaultdict(lambda: {
            'gap_score': 0.0,
            'missing_skills_count': 0,
            'skills': []
        })
        
        for skill in skills:
            cat = skill['category']
            category_data[cat]['gap_score'] += skill['final_score']
            category_data[cat]['missing_skills_count'] += 1
            category_data[cat]['skills'].append(skill['skill'])
        
        # Build summary list
        summary = []
        for category, data in category_data.items():
            # Take top 3 skills in this category
            top_skills = data['skills'][:3]
            
            summary.append({
                'category': category,
                'gap_score': round(data['gap_score'], 4),
                'missing_skills_count': data['missing_skills_count'],
                'top_skills': top_skills
            })
        
        # Sort by gap_score descending
        summary.sort(key=lambda x: x['gap_score'], reverse=True)
        
        return summary
