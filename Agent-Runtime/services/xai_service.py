"""
Runtime Explainable AI (EXAI) Service

Provides skill-level and model-level explanations for skill gap predictions.
"""
import logging
import json
from typing import Dict, List, Optional, Any
import requests
import joblib
import numpy as np
import pandas as pd

from config import RECOMMENDATION_API_BASE_URL

logger = logging.getLogger(__name__)


# Feature name mappings for better interpretability
FEATURE_DISPLAY_NAMES = {
    "role_key": "Target Role",
    "experience_level": "Experience Level",
    "experience_months": "Total Experience (Months)",
    "num_skills": "Number of Skills",
    "num_projects": "Number of Projects",
    "num_work_experiences": "Work Experience Count",
    "avg_mastery_confidence": "Average Skill Mastery",
    "role_skill_coverage": "Role-Skill Match Coverage",
    "role_project_relevance": "Project Relevance Score",
    "institution_name": "Educational Institution"
}

# Feature descriptions explaining what they mean
FEATURE_DESCRIPTIONS = {
    "role_key": "The target role being evaluated against",
    "experience_level": "Career level: Junior, Mid-level, or Senior",
    "experience_months": "Total months of professional work experience",
    "num_skills": "Total number of skills listed in CV",
    "num_projects": "Number of projects completed",
    "num_work_experiences": "Number of different positions held",
    "avg_mastery_confidence": "Average confidence score across all skills (0-1)",
    "role_skill_coverage": "Percentage of role-required skills that candidate has",
    "role_project_relevance": "How relevant candidate's projects are to target role",
    "institution_name": "Name of educational institution attended"
}

# Impact interpretations (positive = increases gap, negative = decreases gap)
def get_feature_interpretation(feature_name: str, impact: float, is_positive: bool) -> str:
    """
    Get human-readable interpretation of feature impact.
    
    Args:
        feature_name: Name of the feature
        impact: SHAP impact value
        is_positive: True if impact increases gap (bad), False if decreases gap (good)
    
    Returns:
        Human-readable interpretation
    """
    interpretations = {
        "experience_months": {
            "positive": "Less experience than typically required for this role",
            "negative": "Good experience level for this role"
        },
        "avg_mastery_confidence": {
            "positive": "Lower skill proficiency levels overall",
            "negative": "Strong skill proficiency helps reduce gap"
        },
        "role_skill_coverage": {
            "positive": "Missing many key skills required for the role",
            "negative": "Good coverage of role-required skills"
        },
        "num_skills": {
            "positive": "Limited skill diversity",
            "negative": "Diverse skill set helps"
        },
        "num_projects": {
            "positive": "Fewer projects than expected",
            "negative": "Good project portfolio demonstrates capability"
        },
        "role_project_relevance": {
            "positive": "Projects not closely aligned with role requirements",
            "negative": "Relevant project experience is valuable"
        },
        "num_work_experiences": {
            "positive": "Limited work history breadth",
            "negative": "Diverse work experience is beneficial"
        },
        "experience_level": {
            "positive": "Experience level may not match role expectations",
            "negative": "Experience level aligns well with role"
        },
        "institution_name": {
            "positive": "Educational background may be a factor",
            "negative": "Educational background is strong"
        }
    }
    
    key = "positive" if is_positive else "negative"
    return interpretations.get(feature_name, {}).get(key, 
        f"{'Increases' if is_positive else 'Decreases'} skill gap"
    )


class XAIService:
    """
    Explainable AI service for skill gap analysis.
    
    Provides two levels of explainability:
    1. Skill-level: Contribution of each skill deficit
    2. SHAP-level: Feature importance from ML model
    """
    
    def __init__(self, model_path: str = "ml_models/skillgap_pipeline.joblib"):
        """
        Initialize XAI service.
        
        Args:
            model_path: Path to trained model pipeline
        """
        self.model_path = model_path
        self.model = None
        self.explainer = None
        self.model_loaded = False
        
        # Try to load model at initialization
        self._load_model()
    
    def _load_model(self) -> bool:
        """
        Load the trained model pipeline and create SHAP explainer.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import shap
            
            logger.info(f"Loading model from {self.model_path}...")
            self.model = joblib.load(self.model_path)
            
            # Extract the final estimator from pipeline
            if hasattr(self.model, 'named_steps'):
                # It's a Pipeline
                estimator = self.model.steps[-1][1]
            else:
                estimator = self.model
            
            # Create TreeExplainer (works for tree-based models)
            logger.info("Creating SHAP TreeExplainer...")
            self.explainer = shap.TreeExplainer(estimator)
            
            self.model_loaded = True
            logger.info("✓ Model and explainer loaded successfully")
            return True
            
        except ImportError:
            logger.warning("SHAP library not installed. Install with: pip install shap")
            return False
        except FileNotFoundError:
            logger.warning(f"Model file not found: {self.model_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def compute_skill_level_explanation(
        self,
        deficits: List[Dict],
        top_n: int = 10
    ) -> List[Dict]:
        """
        Compute skill-level contributions.
        
        Args:
            deficits: List of skill deficits from gap analysis
            top_n: Number of top contributors to return
            
        Returns:
            List of skill contributions with percentages
        """
        if not deficits:
            return []
        
        # Calculate total deficit sum
        total_deficit = sum(d.get("deficit", 0) for d in deficits)
        
        if total_deficit == 0:
            return []
        
        # Compute contribution percentages
        contributions = []
        for d in deficits[:top_n]:
            contribution_percent = (d.get("deficit", 0) / total_deficit) * 100
            contributions.append({
                "skill_name": d.get("skill_name", "Unknown"),
                "deficit": round(d.get("deficit", 0), 4),
                "importance": round(d.get("importance", 0), 4),
                "match_strength": round(d.get("p_has", 0), 4),
                "contribution_percent": round(contribution_percent, 2)
            })
        
        return contributions
    
    def build_feature_row(
        self,
        session,
        candidate_id: str,
        role_key: str
    ) -> Optional[pd.DataFrame]:
        """
        Build feature row for model prediction from Neo4j data.
        
        Args:
            session: Neo4j session
            candidate_id: Candidate ID
            role_key: Role key
            
        Returns:
            DataFrame with single row of features, or None if failed
        """
        try:
            # Query Neo4j for candidate data
            query = """
            MATCH (p:Person {candidate_id: $candidate_id})
            OPTIONAL MATCH (p)-[:STUDIED_AT]->(edu:Education)
            OPTIONAL MATCH (p)-[:WORKED_AT]->(we:WorkExperience)
            OPTIONAL MATCH (p)-[:WORKED_ON]->(proj:Project)
            OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)
            
            WITH p, edu,
                 count(DISTINCT we) as num_work_exp,
                 count(DISTINCT proj) as num_proj,
                 count(DISTINCT s) as num_skills
            
            RETURN 
                p.experience_level as experience_level,
                p.experience_months as experience_months,
                num_skills,
                num_proj,
                num_work_exp,
                edu.institution_name as institution_name
            """
            
            result = session.run(query, candidate_id=candidate_id)
            record = result.single()
            
            if not record:
                logger.error(f"Candidate {candidate_id} not found in Neo4j")
                return None
            
            # Extract basic features
            experience_level = record.get("experience_level") or "Fresher"
            experience_months = record.get("experience_months")
            num_skills = record.get("num_skills") or 0
            num_projects = record.get("num_proj") or 0
            num_work_experiences = record.get("num_work_exp") or 0
            institution_name = record.get("institution_name") or "Unknown"
            
            # Derive experience_months if missing
            if experience_months is None:
                if experience_level == "Fresher":
                    experience_months = 0
                elif experience_level == "Junior":
                    experience_months = 12
                elif experience_level == "Mid":
                    experience_months = 36
                else:
                    experience_months = 0
            
            # Get avg_mastery_confidence from skill-confidence API
            avg_mastery = self._get_avg_mastery(candidate_id)
            
            # Get role_skill_coverage and role_project_relevance
            role_coverage = self._get_role_skill_coverage(session, candidate_id, role_key)
            project_relevance = self._get_project_relevance(session, candidate_id, role_key)
            
            # Build feature dictionary
            features = {
                "role_key": role_key,
                "experience_level": experience_level,
                "experience_months": experience_months,
                "num_skills": num_skills,
                "num_projects": num_projects,
                "num_work_experiences": num_work_experiences,
                "avg_mastery_confidence": avg_mastery,
                "role_skill_coverage": role_coverage,
                "role_project_relevance": project_relevance,
                "institution_name": institution_name
            }
            
            # Create DataFrame
            df = pd.DataFrame([features])
            
            logger.info(f"Built feature row: {features}")
            return df
            
        except Exception as e:
            logger.error(f"Error building feature row: {e}")
            return None
    
    def _get_avg_mastery(self, candidate_id: str) -> float:
        """Get average mastery confidence from skill-confidence API."""
        try:
            url = f"{RECOMMENDATION_API_BASE_URL}/candidates/{candidate_id}/skill-confidence"
            response = requests.get(url, params={"top_n": 100}, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                skills = data.get("skills", [])
                if skills:
                    avg = sum(s.get("confidence_score", 0) for s in skills) / len(skills)
                    return round(avg, 4)
            
            return 0.50  # Default
        except Exception as e:
            logger.warning(f"Failed to get mastery confidence: {e}")
            return 0.50
    
    def _get_role_skill_coverage(self, session, candidate_id: str, role_key: str) -> float:
        """
        Compute role skill coverage: fraction of top role skills matched.
        
        Uses graded matching: exact (1.0), cluster (0.7), similarity (0.4-0.6)
        """
        try:
            query = """
            MATCH (r:Role {key: $role_key})-[imp:REQUIRES_SKILL]->(rs:Skill)
            WITH rs, imp.importance as importance
            ORDER BY importance DESC
            LIMIT 20
            
            MATCH (p:Person {candidate_id: $candidate_id})
            OPTIONAL MATCH (p)-[:HAS_SKILL]->(cs:Skill)
            WHERE rs = cs
            
            WITH rs, cs, importance,
                 CASE 
                   WHEN cs IS NOT NULL THEN 1.0
                   ELSE 0.0
                 END as match_score
            
            RETURN avg(match_score) as coverage
            """
            
            result = session.run(query, candidate_id=candidate_id, role_key=role_key)
            record = result.single()
            
            if record and record.get("coverage") is not None:
                return round(record["coverage"], 4)
            
            return 0.0
        except Exception as e:
            logger.warning(f"Failed to compute role_skill_coverage: {e}")
            return 0.0
    
    def _get_project_relevance(self, session, candidate_id: str, role_key: str) -> float:
        """
        Compute project relevance: fraction of project skills matching role.
        """
        try:
            query = """
            MATCH (p:Person {candidate_id: $candidate_id})-[:WORKED_ON]->(proj:Project)
            MATCH (proj)-[:USES_TECHNOLOGY]->(ps:Skill)
            
            MATCH (r:Role {key: $role_key})-[:REQUIRES_SKILL]->(rs:Skill)
            
            WITH ps, rs,
                 CASE WHEN ps = rs THEN 1.0 ELSE 0.0 END as match
            
            RETURN avg(match) as relevance
            """
            
            result = session.run(query, candidate_id=candidate_id, role_key=role_key)
            record = result.single()
            
            if record and record.get("relevance") is not None:
                return round(record["relevance"], 4)
            
            return 0.0
        except Exception as e:
            logger.warning(f"Failed to compute project_relevance: {e}")
            return 0.0
    
    def _get_transformed_feature_names(self) -> List[str]:
        """
        Extract proper feature names from preprocessing pipeline.
        
        Returns:
            List of feature names after transformation
        """
        try:
            if hasattr(self.model, 'named_steps'):
                # Get preprocessing step (should be ColumnTransformer)
                preprocessor = None
                for step_name, step in self.model.steps[:-1]:
                    if hasattr(step, 'get_feature_names_out'):
                        preprocessor = step
                        break
                
                if preprocessor:
                    return preprocessor.get_feature_names_out().tolist()
            
            # Fallback: use original feature names
            return list(FEATURE_DISPLAY_NAMES.keys())
        except Exception as e:
            logger.warning(f"Could not extract feature names: {e}")
            return list(FEATURE_DISPLAY_NAMES.keys())
    
    def _create_friendly_name(self, encoded_name: str, feature_value: Any = None) -> str:
        """
        Convert encoded feature name to friendly display name.
        
        Examples:
            cat__role_key_ai_ml_engineer -> "Target role: AI/ML Engineer"
            cat__experience_level_Fresher -> "Experience level: Fresher"
            num__role_skill_coverage -> "Role skill coverage"
            
        Args:
            encoded_name: Encoded feature name from pipeline
            feature_value: Original feature value if available
            
        Returns:
            Human-friendly name
        """
        # Handle pipeline prefixes (cat__, num__, remainder__)
        if '__' in encoded_name:
            parts = encoded_name.split('__', 1)
            prefix = parts[0]  # cat, num, remainder
            feature_part = parts[1] if len(parts) > 1 else encoded_name
            
            # For categorical features with values (role_key_ai_ml_engineer)
            if prefix == 'cat':
                # Find the base feature name
                for base_name in FEATURE_DISPLAY_NAMES.keys():
                    if feature_part.startswith(base_name + '_'):
                        # Extract the value part
                        value_part = feature_part[len(base_name) + 1:]
                        value_display = value_part.replace('_', ' ').title()
                        
                        base_display = FEATURE_DISPLAY_NAMES.get(base_name, base_name)
                        return f"{base_display}: {value_display}"
                
                # If no match, clean up the feature part
                return feature_part.replace('_', ' ').title()
            
            # For numeric features (num__role_skill_coverage)
            elif prefix == 'num':
                return FEATURE_DISPLAY_NAMES.get(feature_part, feature_part.replace('_', ' ').title())
            
            # Other prefixes
            else:
                return FEATURE_DISPLAY_NAMES.get(feature_part, feature_part.replace('_', ' ').title())
        
        # No prefix - use direct mapping
        return FEATURE_DISPLAY_NAMES.get(encoded_name, encoded_name.replace('_', ' ').title())
    
    def _generate_explanation_message(
        self,
        feature_name: str,
        feature_key: str,
        impact: float,
        feature_value: Any = None
    ) -> str:
        """
        Generate user-friendly explanation sentence for a SHAP impact.
        
        Args:
            feature_name: Friendly display name
            feature_key: Base feature key
            impact: SHAP impact value (positive = increases gap, negative = reduces gap)
            feature_value: Original feature value
            
        Returns:
            Plain English explanation
        """
        is_positive = impact > 0  # Positive = increases gap (bad for candidate)
        
        # Role-specific explanations
        if 'role_key' in feature_key.lower() or 'role' in feature_name.lower():
            if is_positive:
                return "This role typically requires more skills, increasing your skill gap."
            else:
                return "Your background is well-aligned with this role type."
        
        # Skill coverage
        if 'coverage' in feature_key.lower():
            if is_positive:
                return "You have limited coverage of the skills required for this role."
            else:
                return "You have good coverage of the role's required skills."
        
        # Project relevance
        if 'project' in feature_key.lower() and 'relevance' in feature_key.lower():
            if is_positive:
                return "Your projects are not strongly aligned with the target role requirements."
            else:
                return "Your projects demonstrate relevant experience for this role."
        
        # Experience months
        if 'experience_months' in feature_key.lower():
            if is_positive:
                return "You have less professional experience than typically expected for this role."
            else:
                return "Your experience level is appropriate for this role."
        
        # Experience level
        if 'experience_level' in feature_key.lower():
            if is_positive:
                return "Your seniority level may not fully match the role's requirements."
            else:
                return "Your seniority level aligns well with the role expectations."
        
        # Skill mastery
        if 'mastery' in feature_key.lower() or 'confidence' in feature_key.lower():
            if is_positive:
                return "Your overall skill proficiency levels are lower than ideal for this role."
            else:
                return "Your strong skill proficiency helps reduce the skill gap."
        
        # Number of skills
        if 'num_skills' in feature_key.lower():
            if is_positive:
                return "Having more diverse skills would strengthen your candidacy."
            else:
                return "Your diverse skill set is beneficial for this role."
        
        # Number of projects
        if 'num_projects' in feature_key.lower():
            if is_positive:
                return "More project experience would strengthen your profile."
            else:
                return "Your project portfolio demonstrates practical capability."
        
        # Work experiences
        if 'work_experience' in feature_key.lower():
            if is_positive:
                return "More varied work experience would be beneficial."
            else:
                return "Your diverse work history is an asset."
        
        # Institution
        if 'institution' in feature_key.lower():
            if is_positive:
                return "Educational background is a contributing factor to the gap."
            else:
                return "Your educational background is strong."
        
        # Generic fallback
        if is_positive:
            return f"{feature_name} is contributing to an increased skill gap."
        else:
            return f"{feature_name} helps reduce the skill gap."
    
    def compute_shap_explanation(
        self,
        feature_row: pd.DataFrame,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Compute SHAP values and generate user-friendly explanations.
        
        Args:
            feature_row: Single-row DataFrame with features
            top_k: Number of top positive/negative contributors (default 5)
            
        Returns:
            Dictionary with prediction and friendly SHAP explanations
        """
        if not self.model_loaded:
            return {
                "enabled": False,
                "reason": "Model not loaded (file missing or SHAP not installed)"
            }
        
        try:
            import shap
            import time
            
            start_time = time.time()
            logger.info(f"Starting SHAP computation for {len(feature_row.columns)} features...")
            
            # Make prediction
            skill_gap_pred = self.model.predict(feature_row)[0]
            readiness_pred = 1.0 - skill_gap_pred
            logger.info(f"Prediction complete: gap={skill_gap_pred:.4f}, readiness={readiness_pred:.4f}")
            
            # Transform features through pipeline
            if hasattr(self.model, 'named_steps'):
                # Get preprocessing step
                preprocessor_steps = [step for name, step in self.model.steps[:-1]]
                X_transformed = feature_row.copy()
                
                transform_start = time.time()
                for transformer in preprocessor_steps:
                    X_transformed = transformer.transform(X_transformed)
                logger.info(f"Feature transformation took {time.time() - transform_start:.2f}s")
                
                # Get proper feature names from preprocessor
                transformed_feature_names = self._get_transformed_feature_names()
            else:
                X_transformed = feature_row
                transformed_feature_names = feature_row.columns.tolist()
            
            logger.info(f"Transformed features: {X_transformed.shape[1]} dimensions")
            
            # Compute SHAP values
            shap_start = time.time()
            shap_values = self.explainer.shap_values(X_transformed)
            logger.info(f"SHAP computation took {time.time() - shap_start:.2f}s")
            
            # Handle multi-output models
            if isinstance(shap_values, list):
                shap_values = shap_values[0]
            
            # Ensure we have the right number of feature names
            if len(transformed_feature_names) != shap_values.shape[1]:
                logger.warning(f"Feature count mismatch: {len(transformed_feature_names)} names vs {shap_values.shape[1]} SHAP values")
                # Fallback to generic names
                transformed_feature_names = [f"feature_{i}" for i in range(shap_values.shape[1])]
            
            # Create feature-impact pairs with friendly names and values
            impacts = []
            original_values = feature_row.iloc[0].to_dict()
            
            for i, encoded_name in enumerate(transformed_feature_names):
                shap_impact = float(shap_values[0, i])
                
                # Skip very small impacts
                if abs(shap_impact) < 0.001:
                    continue
                
                # Extract base feature name and create friendly display
                friendly_name = self._create_friendly_name(encoded_name)
                
                # Try to find the base feature key
                base_key = encoded_name
                if '__' in encoded_name:
                    parts = encoded_name.split('__', 1)
                    if len(parts) > 1:
                        # For cat__role_key_ai_ml_engineer, extract "role_key"
                        feature_part = parts[1]
                        for orig_key in FEATURE_DISPLAY_NAMES.keys():
                            if feature_part.startswith(orig_key):
                                base_key = orig_key
                                break
                
                # Get original value if available
                feature_val = original_values.get(base_key, None)
                
                # Generate user-friendly explanation
                explanation_msg = self._generate_explanation_message(
                    friendly_name, base_key, shap_impact, feature_val
                )
                
                impacts.append({
                    "feature": friendly_name,
                    "value": feature_val,
                    "impact": shap_impact,
                    "message": explanation_msg
                })
            
            # Sort by absolute impact
            impacts.sort(key=lambda x: abs(x["impact"]), reverse=True)
            
            logger.info(f"Generated {len(impacts)} feature impacts")
            
            # Split into increasing (positive) and reducing (negative) factors
            increasing_factors = [x for x in impacts if x["impact"] > 0][:top_k]
            reducing_factors = [x for x in impacts if x["impact"] < 0][:top_k]
            
            logger.info(f"Total computation time: {time.time() - start_time:.2f}s")
            
            # Generate summary text
            summary_parts = []
            if increasing_factors:
                top_increasing = increasing_factors[0]["feature"]
                summary_parts.append(f"Main gap contributors: {top_increasing.lower()}")
            
            if reducing_factors:
                top_reducing = reducing_factors[0]["feature"]
                summary_parts.append(f"Key strengths: {top_reducing.lower()}")
            
            summary_text = ". ".join(summary_parts) + "." if summary_parts else "Balanced profile with multiple factors."
            
            return {
                "enabled": True,
                "predicted_skill_gap_index": round(skill_gap_pred, 4),
                "predicted_readiness": round(readiness_pred, 4),
                "top_increasing_factors": increasing_factors,
                "top_reducing_factors": reducing_factors,
                "summary_text": summary_text,
                "base_value": float(self.explainer.expected_value) if hasattr(self.explainer, 'expected_value') else 0.5,
                "notes": [
                    "Graph-based readiness is the authoritative score; ML is an estimate and may be blended/overridden."
                ]
            }
            
        except Exception as e:
            logger.error(f"SHAP computation failed: {e}", exc_info=True)
            return {
                "enabled": False,
                "reason": f"SHAP computation error: {str(e)}"
            }


# Singleton instance
_xai_service = None

def get_xai_service(model_path: str = "ml_models/skillgap_pipeline.joblib") -> XAIService:
    """Get or create XAI service singleton."""
    global _xai_service
    if _xai_service is None:
        _xai_service = XAIService(model_path)
    return _xai_service
