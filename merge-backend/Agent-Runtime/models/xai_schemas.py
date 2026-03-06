"""
Pydantic models for Explainable AI (XAI) endpoints.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field


class SkillContribution(BaseModel):
    """Skill-level contribution to skill gap."""
    skill_name: str = Field(..., description="Skill name")
    deficit: float = Field(..., description="Deficit score")
    importance: float = Field(..., description="Importance score")
    match_strength: float = Field(..., description="Match strength (0-1)")
    contribution_percent: float = Field(..., description="Contribution to total gap (%)")


class SkillExplainResponse(BaseModel):
    """Response for skill-level explainability."""
    candidate_id: str = Field(..., description="Candidate ID")
    role_key: str = Field(..., description="Role key")
    top_contributors: List[SkillContribution] = Field(..., description="Top skill contributors")
    total_deficit: float = Field(..., description="Sum of all deficits")
    
    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "CAND_ML_2024_001",
                "role_key": "ai_ml_engineer",
                "top_contributors": [
                    {
                        "skill_name": "TensorFlow",
                        "deficit": 12.45,
                        "importance": 0.85,
                        "match_strength": 0.0,
                        "contribution_percent": 18.5
                    },
                    {
                        "skill_name": "PyTorch",
                        "deficit": 10.32,
                        "importance": 0.82,
                        "match_strength": 0.0,
                        "contribution_percent": 15.3
                    }
                ],
                "total_deficit": 67.3
            }
        }


class FriendlyFeatureImpact(BaseModel):
    """User-friendly feature impact with plain English explanations."""
    feature: str = Field(..., description="Human-readable feature name (e.g., 'Target role: AI/ML Engineer')")
    value: Optional[Union[float, str, int]] = Field(None, description="Original feature value (numeric or categorical)")
    impact: float = Field(..., description="SHAP value - positive increases gap, negative reduces gap")
    message: str = Field(..., description="Plain English explanation of this factor's contribution")


class FriendlyPredictExplainResponse(BaseModel):
    """User-friendly model explainability response."""
    enabled: bool = Field(..., description="Whether SHAP explanation is available")
    reason: Optional[str] = Field(None, description="Reason if disabled")
    candidate_id: Optional[str] = Field(None, description="Candidate ID")
    role_key: Optional[str] = Field(None, description="Role key")
    predicted_skill_gap_index: Optional[float] = Field(None, description="Predicted skill gap (0-1, higher = more gap)")
    predicted_readiness: Optional[float] = Field(None, description="Predicted readiness (0-1, higher = better)")
    top_increasing_factors: Optional[List[FriendlyFeatureImpact]] = Field(None, description="Top factors increasing the gap")
    top_reducing_factors: Optional[List[FriendlyFeatureImpact]] = Field(None, description="Top factors reducing the gap")
    summary_text: Optional[str] = Field(None, description="Brief summary of main reasons for the gap")
    base_value: Optional[float] = Field(None, description="Base prediction before feature adjustments")
    notes: Optional[List[str]] = Field(None, description="Additional notes about the prediction")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "candidate_id": "CAND_ML_2024_001",
                "role_key": "ai_ml_engineer",
                "predicted_skill_gap_index": 0.456,
                "predicted_readiness": 0.544,
                "top_increasing_factors": [
                    {
                        "feature": "Role-Skill Match Coverage",
                        "value": 0.12,
                        "impact": 0.08,
                        "message": "You have limited coverage of the skills required for this role."
                    },
                    {
                        "feature": "Project Relevance Score",
                        "value": 0.25,
                        "impact": 0.06,
                        "message": "Your projects are not strongly aligned with the target role requirements."
                    }
                ],
                "top_reducing_factors": [
                    {
                        "feature": "Number of Projects",
                        "value": 5.0,
                        "impact": -0.05,
                        "message": "Your project portfolio demonstrates practical capability."
                    },
                    {
                        "feature": "Average Skill Mastery",
                        "value": 0.78,
                        "impact": -0.04,
                        "message": "Your strong skill proficiency helps reduce the skill gap."
                    }
                ],
                "summary_text": "Main gap contributors: role-skill match coverage. Key strengths: number of projects.",
                "base_value": 0.50,
                "notes": [
                    "Graph-based readiness is the authoritative score; ML is an estimate and may be blended/overridden."
                ]
            }
        }


# Legacy schema for backward compatibility
class FeatureImpact(BaseModel):
    """Feature impact from SHAP (legacy format)."""
    feature: str = Field(..., description="Human-readable feature name")
    feature_key: str = Field(..., description="Technical feature key")
    impact: float = Field(..., description="SHAP value (impact on prediction)")
    description: str = Field(..., description="What this feature represents")
    interpretation: str = Field(..., description="Plain English interpretation of the impact")


class PredictExplainResponse(BaseModel):
    """Response for model-level explainability."""
    enabled: bool = Field(..., description="Whether SHAP is enabled")
    reason: Optional[str] = Field(None, description="Reason if disabled")
    candidate_id: Optional[str] = Field(None, description="Candidate ID")
    role_key: Optional[str] = Field(None, description="Role key")
    skill_gap_prediction: Optional[float] = Field(None, description="Predicted skill gap index")
    readiness_prediction: Optional[float] = Field(None, description="Predicted readiness (1 - gap)")
    top_positive_contributors: Optional[List[FeatureImpact]] = Field(None, description="Features increasing gap")
    top_negative_contributors: Optional[List[FeatureImpact]] = Field(None, description="Features decreasing gap")
    base_value: Optional[float] = Field(None, description="Base prediction value")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "candidate_id": "CAND_ML_2024_001",
                "role_key": "ai_ml_engineer",
                "skill_gap_prediction": 0.4523,
                "readiness_prediction": 0.5477,
                "top_positive_contributors": [
                    {"feature": "experience_months", "impact": -0.15},
                    {"feature": "num_projects", "impact": -0.08}
                ],
                "top_negative_contributors": [
                    {"feature": "experience_level_Fresher", "impact": 0.12},
                    {"feature": "num_skills", "impact": 0.05}
                ],
                "base_value": 0.50
            }
        }


class XAIResponse(BaseModel):
    """Combined XAI response for /agent/run."""
    skill_level: Optional[SkillExplainResponse] = Field(None, description="Skill-level explainability")
    shap_level: Optional[FriendlyPredictExplainResponse] = Field(None, description="Model-level explainability with friendly messages")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill_level": {
                    "candidate_id": "CAND_ML_2024_001",
                    "role_key": "ai_ml_engineer",
                    "top_contributors": [
                        {
                            "skill_name": "TensorFlow",
                            "deficit": 12.45,
                            "importance": 0.85,
                            "match_strength": 0.0,
                            "contribution_percent": 18.5
                        }
                    ],
                    "total_deficit": 67.3
                },
                "shap_level": {
                    "enabled": True,
                    "candidate_id": "CAND_ML_2024_001",
                    "role_key": "ai_ml_engineer",
                    "skill_gap_prediction": 0.4523,
                    "readiness_prediction": 0.5477,
                    "top_positive_contributors": [
                        {"feature": "experience_months", "impact": -0.15}
                    ],
                    "top_negative_contributors": [
                        {"feature": "experience_level_Fresher", "impact": 0.12}
                    ],
                    "base_value": 0.50
                }
            }
        }
