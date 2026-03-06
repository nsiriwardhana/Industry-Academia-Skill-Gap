from pydantic import BaseModel
from typing import Optional


class TranscriptCourseOut(BaseModel):
    id: int
    student_id: str
    course_code: str
    course_name: Optional[str] = None
    grade: str
    year_taken: Optional[int] = None
    credits: Optional[float] = None
    academic_year: Optional[int] = None
    
    class Config:
        from_attributes = True
