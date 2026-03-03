"""
XAI (Explainable AI) service for skill score explanations.
TEMPORARY placeholder - needs reimplementation for flat skill structure.
"""

import logging
from typing import Dict
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_skill_explanation(
    db: Session, 
    student_id: str, 
    skill_name: str,
    skill_type: str = "flat"
) -> Dict:
    """
    Placeholder: Get explanation of skill score calculation.
    
    TODO: Reimplement for flat skill structure using SkillEvidence.
    """
    return {
        "error": "XAI service not yet reimplemented for flat skills",
        "skill_name": skill_name,
        "message": "This feature will be available after XAI service update"
    }


def get_all_skills_summary(db: Session, student_id: str) -> Dict:
    """
    Placeholder: Get summary of all skills with explanations.
    
    TODO: Reimplement for flat skill structure.
    """
    return {
        "error": "XAI service not yet reimplemented for flat schools",
        "student_id": student_id,
        "message": "This feature will be available after XAI service update",
        "skills": []
    }
