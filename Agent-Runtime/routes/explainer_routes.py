"""
Explainer API Routes

Provides endpoints for AI-powered skill gap explanations using fine-tuned Qwen model.
Replaces external Colab/ngrok dependency.
"""
import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Lazy import to avoid PyTorch DLL loading issues at import time
_explainer_service_module = None

def _get_explainer_service_lazy():
    """Lazy import and get explainer service."""
    global _explainer_service_module
    if _explainer_service_module is None:
        from services.ai_explainer_service import get_explainer_service
        _explainer_service_module = get_explainer_service
    return _explainer_service_module()

# Create router
router = APIRouter(prefix="/explainer", tags=["AI Explainer"])


# Request/Response Models
class MissingSkillDetail(BaseModel):
    """Detail about a missing skill."""
    skill: str
    importance: float
    deficit: float


class RelevantProject(BaseModel):
    """Detail about a relevant project."""
    name: str
    relevance: float
    matched_skills: List[str]
    total_skills: int
    complexity: Optional[str] = None


class ExplainerInput(BaseModel):
    """Input data for explanation generation."""
    target_name: str
    target_key: str
    readiness: float
    skill_gap_index: float
    matched_skills: List[str]
    num_matched: int
    missing_skills: List[MissingSkillDetail]
    num_missing: int
    total_role_skills: int
    project_relevance_score: float
    relevant_projects: List[RelevantProject]
    total_projects: int


class ExplainerRequest(BaseModel):
    """Request for explanation generation."""
    id: Optional[str] = None
    mode: str = Field(..., pattern="^(role_gap|job_gap)$")
    input: ExplainerInput
    metadata: Optional[Dict[str, Any]] = None


class ExplainerResponse(BaseModel):
    """Response containing generated explanation."""
    explanation_text: str
    generation_time: float
    model: str


@router.post("/explain", response_model=ExplainerResponse)
async def generate_explanation(request: ExplainerRequest) -> ExplainerResponse:
    """
    Generate AI explanation for skill gap analysis.
    
    Args:
        request: ExplainerRequest containing gap analysis data
    
    Returns:
        ExplainerResponse with generated explanation
    
    Raises:
        HTTPException: If explanation generation fails
    """
    try:
        logger.info(f"📝 Generating explanation for {request.input.target_name} ({request.mode})")
        
        # Get explainer service (lazy import)
        explainer = _get_explainer_service_lazy()
        
        # Prepare input data
        input_data = {
            "mode": request.mode,
            "target_name": request.input.target_name,
            "target_key": request.input.target_key,
            "readiness": request.input.readiness,
            "skill_gap_index": request.input.skill_gap_index,
            "matched_skills": request.input.matched_skills,
            "num_matched": request.input.num_matched,
            "missing_skills": [skill.dict() for skill in request.input.missing_skills],
            "num_missing": request.input.num_missing,
            "total_role_skills": request.input.total_role_skills,
            "project_relevance_score": request.input.project_relevance_score,
            "relevant_projects": [proj.dict() for proj in request.input.relevant_projects],
            "total_projects": request.input.total_projects
        }
        
        # Generate explanation
        result = explainer.generate_explanation(input_data)
        
        logger.info(f"✅ Explanation generated successfully in {result['generation_time']:.2f}s")
        
        return ExplainerResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Failed to generate explanation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate explanation: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Check explainer service health.
    
    Returns:
        Health status information
    """
    try:
        explainer = _get_explainer_service_lazy()
        
        return {
            "status": "healthy",
            "service": "AI Explainer",
            "model_loaded": explainer.model is not None,
            "device": explainer.device,
            "model_path": explainer.model_path
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "AI Explainer",
            "error": str(e)
        }


@router.get("/info")
async def get_info() -> Dict[str, Any]:
    """
    Get explainer service information.
    
    Returns:
        Service information including model details
    """
    try:
        explainer = _get_explainer_service_lazy()
        
        return {
            "service": "AI Explainer",
            "description": "Fine-tuned Qwen model for skill gap explanations",
            "model": "Qwen2.5-3B-Instruct with LoRA adapter",
            "model_path": explainer.model_path,
            "device": explainer.device,
            "status": "ready" if explainer.model is not None else "not_loaded",
            "capabilities": [
                "Role gap analysis explanation",
                "Job gap analysis explanation",
                "Skill-level insights",
                "Project relevance analysis",
                "Actionable recommendations"
            ]
        }
    except Exception as e:
        logger.error(f"❌ Failed to get info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get service info: {str(e)}"
        )
