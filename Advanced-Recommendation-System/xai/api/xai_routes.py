"""
XAI FastAPI Routes.

Provides endpoints for explainable AI features:
- GET /explain/missing-skill: Explain why a skill is recommended
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import pandas as pd
from pathlib import Path

from xai.services.xai_explainer import XAIExplainer

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/explain", tags=["XAI"])

# Global state (loaded on startup)
explainer: Optional[XAIExplainer] = None
dataset: Optional[pd.DataFrame] = None


class SkillExplanation(BaseModel):
    """Response model for skill explanation."""
    candidate_id: str
    role_key: str
    skill: str
    final_score: float
    top_factors: list
    explanation_text: str


def initialize_xai_service():
    """
    Initialize XAI service on startup.
    
    Should be called from main app startup event.
    """
    global explainer, dataset
    
    model_path = "xai/output/xai_surrogate.pkl"
    dataset_path = "xai/output/xai_missing_skill_dataset.csv"
    
    # Check if model exists
    if not Path(model_path).exists():
        logger.warning(f"XAI model not found: {model_path}")
        logger.warning("XAI endpoints will not be available")
        logger.warning("Run: python -m xai.scripts.build_xai_dataset && python -m xai.scripts.train_xai_surrogate")
        return
    
    # Check if dataset exists
    if not Path(dataset_path).exists():
        logger.warning(f"XAI dataset not found: {dataset_path}")
        logger.warning("XAI endpoints will not be available")
        logger.warning("Run: python -m xai.scripts.build_xai_dataset")
        return
    
    try:
        logger.info("Loading XAI explainer...")
        explainer = XAIExplainer(model_path=model_path)
        
        logger.info("Loading XAI dataset...")
        dataset = pd.read_csv(dataset_path)
        
        # Initialize SHAP with background samples
        X, _, _ = explainer._prepare_features(dataset)
        background = X[:100]  # Use first 100 samples
        explainer.initialize_shap(background)
        
        logger.info(f"XAI service initialized (dataset: {len(dataset)} rows)")
        
    except Exception as e:
        logger.error(f"Failed to initialize XAI service: {e}")
        explainer = None
        dataset = None


@router.get("/missing-skill", response_model=SkillExplanation)
async def explain_missing_skill(
    candidate_id: str = Query(..., description="Candidate identifier"),
    role_key: str = Query(..., description="Role identifier"),
    skill: str = Query(..., description="Skill name")
):
    """
    Explain why a specific skill is recommended for a candidate-role pair.
    
    Returns:
        - skill: Skill name
        - final_score: Ranking score (0-1)
        - top_factors: Top SHAP contributors with human-readable meanings
        - explanation_text: Natural language explanation
    
    Example:
        GET /explain/missing-skill?candidate_id=person_0&role_key=role_0&skill=Python
    """
    # Check if service is initialized
    if explainer is None or dataset is None:
        raise HTTPException(
            status_code=503,
            detail="XAI service not available. Please train the surrogate model first."
        )
    
    try:
        # Generate explanation
        explanation = explainer.explain_skill(
            candidate_id=candidate_id,
            role_key=role_key,
            skill=skill,
            df=dataset
        )
        
        # Check for errors
        if 'error' in explanation:
            raise HTTPException(
                status_code=404,
                detail=explanation['error']
            )
        
        return SkillExplanation(**explanation)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Explanation generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.get("/health")
async def xai_health():
    """Check if XAI service is available."""
    return {
        "service": "XAI",
        "status": "available" if (explainer and dataset) else "unavailable",
        "model_loaded": explainer is not None,
        "dataset_loaded": dataset is not None,
        "dataset_size": len(dataset) if dataset is not None else 0
    }
