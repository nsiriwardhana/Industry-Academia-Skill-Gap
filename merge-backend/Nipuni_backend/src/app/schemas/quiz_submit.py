"""
Quiz submission schemas.
"""

from pydantic import BaseModel, Field
from typing import List


class AnswerItem(BaseModel):
    """Single quiz answer."""
    question_id: int
    selected_option: str = Field(..., pattern="^[A-D]$", description="Selected option: A, B, C, or D")


class QuizSubmitRequest(BaseModel):
    """Request schema for quiz submission."""
    answers: List[AnswerItem]
