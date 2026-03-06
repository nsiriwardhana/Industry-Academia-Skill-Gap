"""
Quiz schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class QuizPlanRequest(BaseModel):
    """Request schema for creating a quiz plan."""
    selected_skills: Optional[List[str]] = Field(
        None,
        description="Optional list of specific parent skills to include (max 5)"
    )


class QuizPlanOut(BaseModel):
    """Response schema for quiz plan."""
    id: int
    student_id: str
    skill_type: str
    skills_json: str
    questions_per_skill: int
    difficulty_mix_json: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class QuizGenerateRequest(BaseModel):
    """Request schema for quiz generation."""
    model: Optional[str] = Field(
        "llama3.1:8b",
        description="Ollama model to use for generation"
    )


class QuizQuestionOut(BaseModel):
    """Response schema for quiz question (without answer)."""
    question_id: int
    skill_name: str
    difficulty: str
    question_text: str
    options: Dict[str, str]  # {A: "...", B: "...", C: "...", D: "..."}


class QuizGenerateResponse(BaseModel):
    """Response schema for quiz generation."""
    attempt_id: int
    questions: List[QuizQuestionOut]


class QuizAnswerInput(BaseModel):
    """Schema for a single quiz answer."""
    question_id: int
    selected_option: str = Field(..., pattern="^[A-D]$", description="Selected option: A, B, C, or D")


class QuizSubmitRequest(BaseModel):
    """Request schema for quiz submission."""
    answers: List[QuizAnswerInput]


class SkillScoreDetail(BaseModel):
    """Per-skill scoring detail."""
    skill_name: str
    correct: int
    total: int
    verified_score: float
    verified_level: str


class PortfolioEntry(BaseModel):
    """Portfolio entry with claimed, verified, and final scores."""
    skill_name: str
    claimed_score: float
    verified_score: float
    final_score: float
    final_level: str


class QuizSubmitResponse(BaseModel):
    """Response schema for quiz submission."""
    attempt_id: int
    overall_verified_score: float
    total_correct: int
    total_questions: int
    per_skill: List[SkillScoreDetail]
    portfolio: List[PortfolioEntry]
