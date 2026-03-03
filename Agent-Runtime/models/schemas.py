"""
Pydantic models for Agent Runtime API.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Input Models (Extracted Data from CV)
# ============================================================================

class SkillsCategorized(BaseModel):
    """Categorized skills structure from combined_resumes.json."""
    programming_languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    database: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)


class ProjectData(BaseModel):
    """Project details from combined_resumes.json."""
    project_name: str = Field(..., description="Project name")
    project_description: Optional[str] = Field(None, description="Project description")
    duration: Optional[str] = Field(None, description="Duration (e.g., 'Jan 2024 – Mar 2024')")
    complexity: Optional[str] = Field(None, description="Complexity level: High, Medium, Low")
    technologies_used: List[str] = Field(default_factory=list, description="Technologies used")


class WorkExperienceData(BaseModel):
    """Work experience details from combined_resumes.json."""
    role: str = Field(..., description="Job title/role")
    company: str = Field(..., description="Company name")
    duration: Optional[str] = Field(None, description="Duration (e.g., 'Jan 2020 – Dec 2022')")
    duration_months: Optional[int] = Field(None, description="Duration in months")
    used_skills: List[str] = Field(default_factory=list, description="Skills used in this role")


class EducationData(BaseModel):
    """Education details from combined_resumes.json."""
    degree: str = Field(..., description="Degree title")
    university: str = Field(..., description="University name")


class ExtractedData(BaseModel):
    """
    Complete extracted data from CV (matches combined_resumes.json structure).
    """
    candidate_id: str = Field(..., description="Unique candidate identifier")
    candidate_name: str = Field(..., description="Full name")
    mobile_number: Optional[str] = Field(None, description="Mobile number")
    email: Optional[str] = Field(None, description="Email address")
    current_role: Optional[str] = Field(None, description="Current role")
    target_role: Optional[str] = Field(None, description="Target role")
    current_employment: Optional[str] = Field(None, description="Current employer")
    
    education: Optional[EducationData] = Field(None, description="Education details")
    
    skills: List[SkillsCategorized] = Field(default_factory=list, description="Categorized skills")
    work_experiences: List[WorkExperienceData] = Field(default_factory=list, description="Work experience history")
    projects_and_technologies_involved: List[ProjectData] = Field(default_factory=list, description="Projects")
    certificates_or_qualifications: List[str] = Field(default_factory=list, description="Certifications (string array)")
    
    all_skills: Optional[List[str]] = Field(None, description="Flattened list of all skills")
    num_skills: Optional[int] = Field(None, description="Total number of skills")
    experience_months: Optional[int] = Field(None, description="Total experience in months")
    experience_level: Optional[str] = Field(None, description="Experience level")
    num_projects: Optional[int] = Field(None, description="Number of projects")
    evaluation_score: Optional[float] = Field(None, description="Evaluation score")
    skill_score: Optional[float] = Field(None, description="Skill score")
    date_uploaded: Optional[str] = Field(None, description="Upload date")
    status: Optional[str] = Field(None, description="Status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "CAND_ML_2024_001",
                "candidate_name": "Sarah Chen",
                "mobile_number": "+94 77 123 4567",
                "email": "sarah.chen@email.com",
                "current_role": "Machine Learning Engineer",
                "target_role": "Senior ML Engineer",
                "current_employment": "AI Solutions Ltd",
                "education": {
                    "degree": "BSc (Hons) in Computer Science & Engineering",
                    "university": "University of Colombo"
                },
                "skills": [{
                    "programming_languages": ["Python", "Java"],
                    "frameworks": ["TensorFlow", "PyTorch"],
                    "technologies": ["Docker", "AWS"],
                    "technical_skills": ["Machine Learning"],
                    "database": ["PostgreSQL"],
                    "soft_skills": ["Communication"]
                }],
                "projects_and_technologies_involved": [
                    {
                        "project_name": "Sentiment Analysis",
                        "project_description": "NLP pipeline",
                        "duration": "Jan 2024 – Mar 2024",
                        "complexity": "High",
                        "technologies_used": ["Python", "TensorFlow"]
                    }
                ],
                "certificates_or_qualifications": [
                    "AWS Certified ML: Amazon",
                    "TensorFlow Developer: Google"
                ],
                "all_skills": ["AWS", "Docker", "Python", "TensorFlow"],
                "num_skills": 4,
                "experience_months": 36,
                "experience_level": "Mid-Level"
            }
        }


# ============================================================================
# Agent Request/Response Models
# ============================================================================

class AgentRunRequest(BaseModel):
    """Request model for agent runtime."""
    role_key: str = Field(..., description="Target role key for gap analysis")
    cv_data: ExtractedData = Field(..., description="CV data from combined_resumes.json format")
    top_k: int = Field(25, ge=1, le=100, description="Number of top deficits to return")


class SkillConfidenceResult(BaseModel):
    """Skill confidence result."""
    skill_name: str
    confidence: float
    evidence_count: int
    evidence_sources: List[str]


class SkillDeficitResult(BaseModel):
    """Skill deficit result."""
    skill_name: str
    p_has: float
    importance: float
    deficit: float
    tf: int
    df: int
    idf: float
    
    # GNN Hybrid fields (optional - only present when using hybrid ranking)
    P_gnn: Optional[float] = Field(None, description="GNN learning potential prediction (0-1)")
    final_score: Optional[float] = Field(None, description="Hybrid score: gap × importance_norm × P_gnn")
    gap: Optional[float] = Field(None, description="Skill gap magnitude (1 - P_has)")
    importance_norm: Optional[float] = Field(None, description="Normalized importance score")
    reason: Optional[str] = Field(None, description="Human-readable explanation with learning potential")
    category: Optional[str] = Field(None, description="Skill category")
    ranking_method: Optional[str] = Field(None, description="Ranking method used: symbolic, hybrid, or additive_gnn")
    
    @property
    def match_strength(self) -> float:
        """Alias for p_has (for XAI compatibility)."""
        return self.p_has


class AgentRunResponse(BaseModel):
    """Complete agent runtime response."""
    candidate_id: str = Field(..., description="Candidate identifier")
    role_key: str = Field(..., description="Target role")
    
    # Status
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Status message")
    
    # Normalization results
    normalized_skills_count: int = Field(..., description="Number of skills normalized")
    
    # Graph write results
    nodes_created: int = Field(..., description="Nodes created in Neo4j")
    relationships_created: int = Field(..., description="Relationships created")
    
    # Gap analysis results
    skill_confidence_top: List[SkillConfidenceResult] = Field(
        default_factory=list,
        description="Top skills by confidence"
    )
    skill_gap_top: List[SkillDeficitResult] = Field(
        default_factory=list,
        description="Top skill deficits"
    )
    readiness_score: Optional[float] = Field(
        None,
        description="Overall readiness for role (1 - avg_deficit)"
    )
    
    # Project relevance score
    project_relevance_score: Optional[float] = Field(
        None,
        description="Project relevance score for target role (0-1)"
    )
    
    relevant_projects: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of relevant projects with scores"
    )
    
    # Explainability (optional)
    xai: Optional[Any] = Field(
        None,
        description="Explainable AI results (skill-level + SHAP-level)"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    neo4j_connected: bool = Field(..., description="Neo4j connection status")
    recommendation_api_available: Optional[bool] = Field(
        None,
        description="Recommendation API availability"
    )


# ============================================================================
# Internal Agent Models
# ============================================================================

class NormalizedSkill(BaseModel):
    """Normalized skill after alias resolution."""
    original_name: str
    canonical_name: str
    category: str = "unknown"


class GraphWriteResult(BaseModel):
    """Result from KG writer."""
    success: bool
    nodes_created: int
    relationships_created: int
    candidate_id: str
    message: str
