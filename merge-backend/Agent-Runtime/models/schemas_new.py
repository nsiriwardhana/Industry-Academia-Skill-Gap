"""
UPDATED Pydantic models matching KG Person node structure exactly.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Input Models - Match KG Structure Exactly
# ============================================================================

class EducationData(BaseModel):
    """Education details matching KG Education node."""
    degree: str = Field(..., description="Degree title")
    university: str = Field(..., description="University/Institution name")


class ProjectData(BaseModel):
    """Project details matching KG Project node."""
    project_name: str = Field(..., description="Project name")
    project_description: Optional[str] = Field(None, description="Project description")
    technologies_used: List[str] = Field(default_factory=list, description="Technologies/skills used in project")
    duration: Optional[str] = Field(None, description="Duration")
    complexity: Optional[str] = Field(None, description="Complexity: High/Medium/Low")


class ExtractedData(BaseModel):
    """
    CV data matching KG Person node structure EXACTLY.
    This is what Graph-Builder creates, so we accept the same format.
    """
    # Core Identity (REQUIRED)
    candidate_id: str = Field(..., description="Unique candidate ID (CAND_XXXXXXXX)")
    candidate_name: str = Field(..., description="Full name")
    
    # Contact Info
    mobile_number: Optional[str] = Field(None, description="Phone number")
    email: Optional[str] = Field(None, description="Email address")
    
    # Roles & Employment
    current_role: Optional[str] = Field(None, description="Current job title")
    target_role: Optional[str] = Field(None, description="Desired role (NOT used for TARGETS_ROLE relationship)")
    current_employment: Optional[str] = Field(None, description="Current employer/company")
    
    # Experience
    experience_months: Optional[int] = Field(None, description="Total months of experience")
    experience_level: Optional[str] = Field(None, description="Fresher/Junior/Mid-Level/Senior/Expert")
    
    # Skills (PRIMARY SOURCE)
    all_skills: List[str] = Field(default_factory=list, description="Flat list of all skill names")
    num_skills: Optional[int] = Field(None, description="Count of skills")
    
    # Projects (SECONDARY SKILL SOURCE)
    projects_and_technologies_involved: List[ProjectData] = Field(
        default_factory=list,
        description="Projects with technologies_used for skill extraction"
    )
    num_projects: Optional[int] = Field(None, description="Count of projects")
    
    # Certifications
    certificates_or_qualifications: List[str] = Field(
        default_factory=list,
        description="List of certification strings (e.g., 'AWS ML Specialist: Amazon')"
    )
    
    # Education
    education: Optional[EducationData] = Field(None, description="Education details")
    
    # Scores (optional, from resume evaluation)
    evaluation_score: Optional[float] = Field(None, description="Overall evaluation score")
    skill_score: Optional[float] = Field(None, description="Skill assessment score")
    
    # Metadata
    date_uploaded: Optional[str] = Field(None, description="Upload timestamp")
    status: Optional[str] = Field(None, description="Processing status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "CAND_ABC12345",
                "candidate_name": "John Doe",
                "mobile_number": "+1 (555) 123-4567",
                "email": "john.doe@example.com",
                "current_role": "Software Engineer",
                "target_role": "Senior Data Scientist",
                "current_employment": "Tech Corp Inc",
                "experience_months": 48,
                "experience_level": "Mid-Level",
                "all_skills": ["Python", "TensorFlow", "Docker", "PostgreSQL", "AWS"],
                "num_skills": 5,
                "projects_and_technologies_involved": [
                    {
                        "project_name": "ML Pipeline Automation",
                        "project_description": "Automated ML model training pipeline",
                        "technologies_used": ["Python", "Airflow", "Docker"],
                        "duration": "3 months",
                        "complexity": "High"
                    }
                ],
                "num_projects": 1,
                "certificates_or_qualifications": [
                    "AWS Certified Solutions Architect: Amazon Web Services",
                    "TensorFlow Developer Certificate: Google"
                ],
                "education": {
                    "degree": "BSc Computer Science",
                    "university": "State University"
                },
                "evaluation_score": 85.5,
                "skill_score": 78.0
            }
        }


# ============================================================================
# Agent Response Models
# ============================================================================

class SkillConfidenceResult(BaseModel):
    """Single skill with confidence score."""
    skill_name: str
    confidence_score: float
    evidence_sources: List[str] = Field(default_factory=list)


class SkillDeficitResult(BaseModel):
    """Single missing/deficit skill."""
    skill_name: str
    demand: int = Field(..., description="Number of jobs requiring this skill")
    deficit_score: float = Field(..., description="Calculated deficit score")


class AgentRunResponse(BaseModel):
    """Complete agent pipeline response."""
    candidate_id: str
    status: str = Field(..., description="success/failed")
    message: Optional[str] = Field(None, description="Error message if failed")
    
    # Pipeline Stats
    normalized_skills_count: Optional[int] = None
    nodes_created: Optional[int] = None
    relationships_created: Optional[int] = None
    
    # Gap Analysis Results
    top_skills: Optional[List[SkillConfidenceResult]] = None
    top_deficits: Optional[List[SkillDeficitResult]] = None
    readiness_score: Optional[float] = None
    
    # Metadata
    role_key: Optional[str] = None
    processing_time_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    neo4j_connected: bool
    gap_analyzer_url: str
