from pydantic import BaseModel
from datetime import datetime


class ClaimedSkillOut(BaseModel):
    id: int
    student_id: str
    skill_name: str
    claimed_score: float
    claimed_level: str
    confidence: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class SkillEvidenceOut(BaseModel):
    id: int
    student_id: str
    skill_name: str
    course_code: str
    map_weight: float
    credits: float
    grade: str
    grade_norm: float
    academic_year: int | None = None
    recency: float
    evidence_weight: float
    contribution: float
    
    class Config:
        from_attributes = True


class ParentSkillOut(BaseModel):
    id: int
    student_id: str
    parent_skill: str
    parent_score: float
    parent_level: str
    confidence: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class ParentSkillEvidenceOut(BaseModel):
    id: int
    student_id: str
    parent_skill: str
    child_skill: str
    course_code: str
    contribution: float
    evidence_weight: float
    recency: float
    grade: str
    credits: float
    map_weight: float
    
    class Config:
        from_attributes = True
