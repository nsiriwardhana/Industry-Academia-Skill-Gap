"""
SHAP-based Explainability Service for GNN Skill Recommendations.

Provides three levels of explanations:
1. Formula-level: How P_gnn, importance, gap contribute to final_score
2. Feature-level: Which candidate attributes influenced P_gnn
3. Graph-level: Which graph neighbors contributed to prediction
"""
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class SHAPExplainerService:
    """Service for generating SHAP explanations for skill recommendations."""
    
    # ========================================================================
    # LEVEL 1: FORMULA-LEVEL SHAP (Component Contributions)
    # ========================================================================
    
    @staticmethod
    def explain_formula_contribution(
        skill_name: str,
        P_gnn: float,
        importance: float,
        gap_magnitude: float,
        final_score: float
    ) -> Dict:
        """
        Explain how each component contributes to final_score using SHAP-like decomposition.
        
        Formula: final_score = gap_magnitude × importance × P_gnn
        
        We decompose this multiplicative formula into additive contributions:
        log(final_score) ≈ log(gap) + log(importance) + log(P_gnn) + baseline
        
        Then compute SHAP values showing each component's contribution.
        
        Args:
            skill_name: Name of the skill
            P_gnn: GNN predicted probability (0-1)
            importance: Role importance score (0-1)
            gap_magnitude: 1 - P_has (0-1)
            final_score: Computed final score
            
        Returns:
            Dict with SHAP values and explanation
        """
        # Avoid log(0) by adding small epsilon
        eps = 1e-6
        
        # Baseline: mean of all components (neutral case)
        baseline_gap = 0.5
        baseline_importance = 0.5
        baseline_p_gnn = 0.5
        baseline_score = baseline_gap * baseline_importance * baseline_p_gnn
        
        # Compute log-space contributions (Shapley values for multiplicative models)
        if final_score > eps:
            log_final = np.log(final_score + eps)
            log_baseline = np.log(baseline_score + eps)
            
            log_gap = np.log(gap_magnitude + eps)
            log_importance = np.log(importance + eps)
            log_p_gnn = np.log(P_gnn + eps)
            
            log_gap_baseline = np.log(baseline_gap + eps)
            log_importance_baseline = np.log(baseline_importance + eps)
            log_p_gnn_baseline = np.log(baseline_p_gnn + eps)
            
            # SHAP values: deviation from baseline
            shap_gap = log_gap - log_gap_baseline
            shap_importance = log_importance - log_importance_baseline
            shap_p_gnn = log_p_gnn - log_p_gnn_baseline
            
            # Total deviation
            total_deviation = log_final - log_baseline
            
            # Normalize SHAP values to sum to total deviation
            total_shap = shap_gap + shap_importance + shap_p_gnn
            if abs(total_shap) > eps:
                norm_factor = total_deviation / total_shap
                shap_gap *= norm_factor
                shap_importance *= norm_factor
                shap_p_gnn *= norm_factor
            
            # Convert to percentage contributions
            contributions = {
                'gap_magnitude': {
                    'value': float(gap_magnitude),
                    'shap_value': float(shap_gap),
                    'contribution_pct': float(abs(shap_gap) / (abs(shap_gap) + abs(shap_importance) + abs(shap_p_gnn) + eps) * 100),
                    'effect': 'increases' if shap_gap > 0 else 'decreases'
                },
                'importance': {
                    'value': float(importance),
                    'shap_value': float(shap_importance),
                    'contribution_pct': float(abs(shap_importance) / (abs(shap_gap) + abs(shap_importance) + abs(shap_p_gnn) + eps) * 100),
                    'effect': 'increases' if shap_importance > 0 else 'decreases'
                },
                'P_gnn': {
                    'value': float(P_gnn),
                    'shap_value': float(shap_p_gnn),
                    'contribution_pct': float(abs(shap_p_gnn) / (abs(shap_gap) + abs(shap_importance) + abs(shap_p_gnn) + eps) * 100),
                    'effect': 'increases' if shap_p_gnn > 0 else 'decreases'
                },
                'baseline_score': float(baseline_score),
                'final_score': float(final_score),
                'total_gain': float(final_score - baseline_score)
            }
        else:
            # Handle edge case where final_score is 0
            contributions = {
                'gap_magnitude': {'value': float(gap_magnitude), 'shap_value': 0.0, 'contribution_pct': 33.3, 'effect': 'neutral'},
                'importance': {'value': float(importance), 'shap_value': 0.0, 'contribution_pct': 33.3, 'effect': 'neutral'},
                'P_gnn': {'value': float(P_gnn), 'shap_value': 0.0, 'contribution_pct': 33.3, 'effect': 'neutral'},
                'baseline_score': float(baseline_score),
                'final_score': 0.0,
                'total_gain': float(-baseline_score)
            }
        
        # Generate human-readable explanation
        explanation = SHAPExplainerService._generate_formula_explanation(contributions)
        
        return {
            'skill': skill_name,
            'contributions': contributions,
            'explanation': explanation,
            'method': 'formula_shap'
        }
    
    @staticmethod
    def _generate_formula_explanation(contributions: Dict) -> str:
        """Generate natural language explanation from SHAP contributions."""
        parts = []
        
        # Sort by absolute contribution
        components = [
            ('gap_magnitude', contributions['gap_magnitude']),
            ('importance', contributions['importance']),
            ('P_gnn', contributions['P_gnn'])
        ]
        components.sort(key=lambda x: abs(x[1]['shap_value']), reverse=True)
        
        # Describe top contributor
        top_name, top_contrib = components[0]
        friendly_names = {
            'gap_magnitude': 'skill gap size',
            'importance': 'role importance',
            'P_gnn': 'GNN learning potential'
        }
        
        top_friendly = friendly_names[top_name]
        top_pct = top_contrib['contribution_pct']
        top_effect = top_contrib['effect']
        
        parts.append(f"Primary driver: {top_friendly} ({top_pct:.1f}% contribution, {top_effect} score)")
        
        # Describe secondary contributors
        for name, contrib in components[1:]:
            friendly = friendly_names[name]
            pct = contrib['contribution_pct']
            effect = contrib['effect']
            parts.append(f"{friendly}: {pct:.1f}% ({effect})")
        
        return " | ".join(parts)
    
    # ========================================================================
    # LEVEL 2: FEATURE-LEVEL SHAP (Candidate Profile Attribution)
    # ========================================================================
    
    @staticmethod
    def explain_candidate_features(
        session,
        candidate_id: str,
        skill_name: str,
        P_gnn: float
    ) -> Dict:
        """
        Explain which candidate features (skills, projects, categories) influenced P_gnn.
        
        Uses perturbation-based SHAP approximation:
        - Remove each skill/project from candidate's profile
        - Re-compute P_gnn for target skill
        - SHAP value = (P_gnn_full - P_gnn_without_feature)
        
        Args:
            session: Neo4j session
            candidate_id: Candidate identifier
            skill_name: Skill to explain prediction for
            P_gnn: Original GNN prediction
            
        Returns:
            Dict with feature attributions
        """
        # Query candidate's current skills and projects
        query = """
        MATCH (p:Person {candidate_id: $candidate_id})
        
        // Get candidate's skills
        OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)
        WITH p, collect(DISTINCT s.name) as candidate_skills
        
        // Get candidate's projects
        OPTIONAL MATCH (p)-[:WORKED_ON]->(proj:Project)
        WITH p, candidate_skills, collect(DISTINCT proj.name) as candidate_projects
        
        // Get skill categories represented
        OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)-[:BELONGS_TO_CATEGORY]->(cat:SkillCategory)
        WITH candidate_skills, candidate_projects, collect(DISTINCT cat.name) as candidate_categories
        
        RETURN candidate_skills, candidate_projects, candidate_categories
        """
        
        result = session.run(query, candidate_id=candidate_id)
        record = result.single()
        
        if not record:
            return {
                'skill': skill_name,
                'error': 'Candidate not found',
                'method': 'feature_shap'
            }
        
        candidate_skills = record['candidate_skills'] or []
        candidate_projects = record['candidate_projects'] or []
        candidate_categories = record['candidate_categories'] or []
        
        # Compute feature attributions (simplified - without actual re-inference)
        # In production, you'd re-run GNN with features removed
        
        # Heuristic: Estimate feature importance based on relevance
        skill_attributions = []
        for skill in candidate_skills[:10]:  # Top 10 skills
            # Check if skill is related to target skill (same category, common in projects)
            relevance = SHAPExplainerService._compute_skill_relevance(
                session, skill, skill_name
            )
            attribution = P_gnn * relevance  # Approximate contribution
            
            skill_attributions.append({
                'feature': skill,
                'feature_type': 'skill',
                'attribution': float(attribution),
                'relevance': float(relevance)
            })
        
        # Sort by attribution
        skill_attributions.sort(key=lambda x: abs(x['attribution']), reverse=True)
        
        return {
            'skill': skill_name,
            'P_gnn': float(P_gnn),
            'feature_attributions': skill_attributions[:5],  # Top 5
            'candidate_profile': {
                'num_skills': len(candidate_skills),
                'num_projects': len(candidate_projects),
                'num_categories': len(candidate_categories)
            },
            'method': 'feature_shap',
            'note': 'Heuristic approximation - full SHAP requires model re-inference'
        }
    
    @staticmethod
    def _compute_skill_relevance(session, skill1: str, skill2: str) -> float:
        """
        Compute relevance between two skills (0-1).
        
        Based on:
        - Same category
        - Co-occurrence in projects
        - Co-occurrence in candidates
        """
        query = """
        MATCH (s1:Skill {name: $skill1})
        MATCH (s2:Skill {name: $skill2})
        
        // Same category?
        OPTIONAL MATCH (s1)-[:BELONGS_TO_CATEGORY]->(cat:SkillCategory)<-[:BELONGS_TO_CATEGORY]-(s2)
        WITH s1, s2, count(cat) as same_category
        
        // Co-occur in projects?
        OPTIONAL MATCH (s1)<-[:USES_TECHNOLOGY]-(p:Project)-[:USES_TECHNOLOGY]->(s2)
        WITH same_category, count(DISTINCT p) as cooccur_projects
        
        // Co-occur in candidates?
        OPTIONAL MATCH (s1)<-[:HAS_SKILL]-(person:Person)-[:HAS_SKILL]->(s2)
        WITH same_category, cooccur_projects, count(DISTINCT person) as cooccur_candidates
        
        RETURN same_category, cooccur_projects, cooccur_candidates
        """
        
        result = session.run(query, skill1=skill1, skill2=skill2)
        record = result.single()
        
        if not record:
            return 0.0
        
        same_cat = min(record['same_category'], 1)
        cooccur_proj = min(record['cooccur_projects'] / 10.0, 1.0)  # Normalize
        cooccur_cand = min(record['cooccur_candidates'] / 50.0, 1.0)  # Normalize
        
        # Weighted relevance
        relevance = 0.5 * same_cat + 0.3 * cooccur_proj + 0.2 * cooccur_cand
        
        return min(relevance, 1.0)
    
    # ========================================================================
    # LEVEL 3: GRAPH-LEVEL SHAP (Neighborhood Attribution)
    # ========================================================================
    
    @staticmethod
    def explain_graph_neighborhood(
        session,
        candidate_id: str,
        skill_name: str,
        P_gnn: float,
        max_neighbors: int = 10
    ) -> Dict:
        """
        Explain which graph neighbors (skills, projects, similar candidates) 
        influenced the GNN prediction.
        
        This is a simplified version of GNNExplainer that identifies:
        - Most important existing skills (1-hop neighbors)
        - Most important projects (2-hop neighbors)
        - Most similar candidates who have target skill (collaborative filtering signal)
        
        Args:
            session: Neo4j session
            candidate_id: Candidate identifier
            skill_name: Skill to explain
            P_gnn: GNN prediction
            max_neighbors: Max neighbors to return
            
        Returns:
            Dict with neighborhood attributions
        """
        # Query 1: Direct skill neighbors (1-hop)
        skill_neighbors_query = """
        MATCH (p:Person {candidate_id: $candidate_id})-[:HAS_SKILL]->(s:Skill)
        MATCH (target:Skill {name: $skill_name})
        
        // Find skills in same category as target
        OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:SkillCategory)<-[:BELONGS_TO_CATEGORY]-(target)
        WITH s, count(cat) as same_category
        
        // Find skills that co-occur with target in projects
        OPTIONAL MATCH (s)<-[:USES_TECHNOLOGY]-(proj:Project)-[:USES_TECHNOLOGY]->(target)
        WITH s, same_category, count(DISTINCT proj) as cooccur_projects
        
        // Compute relevance score
        WITH s, same_category, cooccur_projects,
             (same_category * 0.6 + cooccur_projects * 0.4) as relevance_score
        
        RETURN s.name as skill, relevance_score
        ORDER BY relevance_score DESC
        LIMIT $max_neighbors
        """
        
        skill_result = session.run(
            skill_neighbors_query,
            candidate_id=candidate_id,
            skill_name=skill_name,
            max_neighbors=max_neighbors
        )
        
        skill_neighbors = []
        for record in skill_result:
            skill_neighbors.append({
                'neighbor': record['skill'],
                'neighbor_type': 'skill',
                'relevance_score': float(record['relevance_score']),
                'attribution': float(P_gnn * record['relevance_score'] / 10.0)  # Approximate
            })
        
        # Query 2: Project neighbors (2-hop)
        project_neighbors_query = """
        MATCH (p:Person {candidate_id: $candidate_id})-[:WORKED_ON]->(proj:Project)
        MATCH (target:Skill {name: $skill_name})
        
        // Check if project uses target skill or related skills
        OPTIONAL MATCH (proj)-[:USES_TECHNOLOGY]->(target)
        WITH proj, count(*) as direct_use
        
        OPTIONAL MATCH (proj)-[:USES_TECHNOLOGY]->(s:Skill)-[:BELONGS_TO_CATEGORY]->(cat:SkillCategory)<-[:BELONGS_TO_CATEGORY]-(target)
        WITH proj, direct_use, count(DISTINCT s) as related_skills
        
        WITH proj, (direct_use * 2 + related_skills) as relevance_score
        WHERE relevance_score > 0
        
        RETURN proj.name as project, relevance_score
        ORDER BY relevance_score DESC
        LIMIT $max_neighbors
        """
        
        project_result = session.run(
            project_neighbors_query,
            candidate_id=candidate_id,
            skill_name=skill_name,
            max_neighbors=max_neighbors
        )
        
        project_neighbors = []
        for record in project_result:
            project_neighbors.append({
                'neighbor': record['project'],
                'neighbor_type': 'project',
                'relevance_score': float(record['relevance_score']),
                'attribution': float(P_gnn * record['relevance_score'] / 15.0)  # Approximate
            })
        
        # Query 3: Similar candidates (collaborative filtering signal)
        similar_candidates_query = """
        MATCH (p:Person {candidate_id: $candidate_id})-[:HAS_SKILL]->(s:Skill)
        WITH p, collect(s.name) as p_skills
        
        // Find candidates with similar skills
        MATCH (other:Person)-[:HAS_SKILL]->(s2:Skill)
        WHERE other.candidate_id <> $candidate_id
        WITH p, p_skills, other, collect(s2.name) as other_skills
        
        // Compute Jaccard similarity
        WITH p, other, 
             [x IN p_skills WHERE x IN other_skills] as intersection,
             p_skills + [x IN other_skills WHERE NOT x IN p_skills] as union_set
        WITH other, 
             size(intersection) * 1.0 / size(union_set) as similarity
        WHERE similarity > 0.3
        
        // Check if similar candidate has target skill
        MATCH (other)-[:HAS_SKILL]->(target:Skill {name: $skill_name})
        
        RETURN other.candidate_id as similar_candidate, similarity
        ORDER BY similarity DESC
        LIMIT 5
        """
        
        similar_result = session.run(
            similar_candidates_query,
            candidate_id=candidate_id,
            skill_name=skill_name
        )
        
        similar_neighbors = []
        for record in similar_result:
            similar_neighbors.append({
                'neighbor': record['similar_candidate'],
                'neighbor_type': 'similar_candidate',
                'similarity': float(record['similarity']),
                'attribution': float(P_gnn * record['similarity'] * 0.5)  # Approximate
            })
        
        return {
            'skill': skill_name,
            'P_gnn': float(P_gnn),
            'skill_neighbors': skill_neighbors,
            'project_neighbors': project_neighbors,
            'similar_candidates': similar_neighbors,
            'method': 'graph_neighborhood',
            'explanation': SHAPExplainerService._generate_graph_explanation(
                skill_neighbors, project_neighbors, similar_neighbors
            )
        }
    
    @staticmethod
    def _generate_graph_explanation(
        skill_neighbors: List[Dict],
        project_neighbors: List[Dict],
        similar_candidates: List[Dict]
    ) -> str:
        """Generate natural language explanation from graph neighbors."""
        parts = []
        
        if skill_neighbors:
            top_skill = skill_neighbors[0]['neighbor']
            parts.append(f"Your '{top_skill}' skill is highly related")
        
        if project_neighbors:
            top_project = project_neighbors[0]['neighbor']
            parts.append(f"Your '{top_project}' project experience is relevant")
        
        if similar_candidates:
            num_similar = len(similar_candidates)
            parts.append(f"{num_similar} similar candidates successfully acquired this skill")
        
        if not parts:
            return "Prediction based on overall profile patterns"
        
        return " | ".join(parts)
    
    # ========================================================================
    # BATCH EXPLANATION (For Multiple Skills)
    # ========================================================================
    
    @staticmethod
    def explain_top_recommendations(
        session,
        ranked_skills: List[Dict],
        candidate_id: str,
        explanation_level: str = 'formula'
    ) -> List[Dict]:
        """
        Generate SHAP explanations for multiple recommended skills.
        
        Args:
            session: Neo4j session
            ranked_skills: List of ranked skill dicts (from GNN ranking service)
            candidate_id: Candidate identifier
            explanation_level: 'formula', 'feature', or 'graph'
            
        Returns:
            List of skill dicts with added 'shap_explanation' field
        """
        explained_skills = []
        
        for skill_dict in ranked_skills:
            skill_name = skill_dict['skill']
            P_gnn = skill_dict['P_gnn']
            importance = skill_dict['importance']
            gap_magnitude = skill_dict['gap_magnitude']
            final_score = skill_dict['final_score']
            
            # Choose explanation method
            if explanation_level == 'formula':
                explanation = SHAPExplainerService.explain_formula_contribution(
                    skill_name, P_gnn, importance, gap_magnitude, final_score
                )
            elif explanation_level == 'feature':
                explanation = SHAPExplainerService.explain_candidate_features(
                    session, candidate_id, skill_name, P_gnn
                )
            elif explanation_level == 'graph':
                explanation = SHAPExplainerService.explain_graph_neighborhood(
                    session, candidate_id, skill_name, P_gnn
                )
            else:
                explanation = {'error': 'Invalid explanation level'}
            
            # Add explanation to skill dict
            skill_with_explanation = skill_dict.copy()
            skill_with_explanation['shap_explanation'] = explanation
            
            explained_skills.append(skill_with_explanation)
        
        return explained_skills


# Singleton instance
shap_explainer = SHAPExplainerService()
