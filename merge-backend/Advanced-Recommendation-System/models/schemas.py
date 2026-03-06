"""
Pydantic models for request/response validation.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Role Models
# ============================================================================

class RoleBasic(BaseModel):
    """Basic role information."""
    role_key: str = Field(..., description="Unique identifier for the role")
    name: str = Field(..., description="Human-readable role name")
    job_count: int = Field(..., description="Number of jobs in this role")


# ============================================================================
# Skill Models
# ============================================================================

class SkillImportance(BaseModel):
    """TF-IDF importance of a skill within a role."""
    skill_name: str = Field(..., description="Name of the skill")
    tf: int = Field(..., description="Term Frequency: jobs in role requiring skill")
    df: int = Field(..., description="Document Frequency: roles requiring skill")
    idf: float = Field(..., description="Inverse Document Frequency: log(R/df)")
    importance: float = Field(..., description="TF-IDF score: TF × IDF")
    percentage: float = Field(..., description="Percentage of jobs requiring skill")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill_name": "Python",
                "tf": 45,
                "df": 8,
                "idf": 0.845,
                "importance": 38.025,
                "percentage": 90.0
            }
        }


class RoleSkillProfile(BaseModel):
    """Complete TF-IDF profile for a role."""
    role_key: str = Field(..., description="Role identifier")
    role_name: str = Field(..., description="Role name")
    total_jobs: int = Field(..., description="Total jobs in this role")
    total_roles: int = Field(..., description="Total roles in system (for IDF)")
    skills: List[SkillImportance] = Field(..., description="Ranked skill importance")


class SkillConfidence(BaseModel):
    """Evidence-weighted confidence for a skill."""
    skill_name: str = Field(..., description="Name of the skill")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score [0,1]")
    evidence_sources: List[str] = Field(..., description="Sources of evidence")
    evidence_count: int = Field(..., description="Number of evidence instances")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill_name": "Python",
                "confidence": 0.95,
                "evidence_sources": ["HAS_SKILL", "USED_SKILL", "USES_TECHNOLOGY"],
                "evidence_count": 5
            }
        }


class CandidateSkillProfile(BaseModel):
    """Complete skill confidence profile for a candidate."""
    candidate_id: str = Field(..., description="Candidate identifier")
    skills: List[SkillConfidence] = Field(..., description="Ranked skill confidence")


# ============================================================================
# Skill Gap Models
# ============================================================================

class SkillDeficit(BaseModel):
    """
    Deficit score for a skill gap with GRADED matching.
    
    NEW (Research-Grade Enhancement):
    p_has is now "match_strength" - a graded score [0.0, 1.0]:
    - 1.0: Exact match (candidate has this skill)
    - 0.7: Cluster match (candidate has similar skill in same cluster)
    - 0.4-0.6: Similarity match (candidate has related skill via graph edge)
    - 0.0: No match
    
    This improves accuracy by recognizing skill relationships beyond exact names.
    """
    skill_name: str = Field(..., description="Name of the skill")
    p_has: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Graded match strength (1.0=exact, 0.7=cluster, 0.4-0.6=similar, 0.0=none)"
    )
    tf: int = Field(..., description="Term Frequency in role")
    df: int = Field(..., description="Document Frequency across roles")
    idf: float = Field(..., description="Inverse Document Frequency")
    importance: float = Field(..., description="TF-IDF importance score")
    deficit: float = Field(..., description="Deficit score: importance × (1 - match_strength)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill_name": "TensorFlow",
                "p_has": 0.6,
                "tf": 30,
                "df": 5,
                "idf": 1.386,
                "importance": 41.58,
                "deficit": 16.632
            }
        }


class SkillGapResponse(BaseModel):
    """Complete skill gap analysis."""
    candidate_id: str = Field(..., description="Candidate identifier")
    role_key: str = Field(..., description="Role identifier")
    role_name: str = Field(..., description="Role name")
    total_jobs: int = Field(..., description="Total jobs in role")
    total_roles: int = Field(..., description="Total roles in system")
    deficits: List[SkillDeficit] = Field(..., description="Top-K skill deficits")


# ============================================================================
# Course Recommendation Models
# ============================================================================

class JobGapSkillDeficit(BaseModel):
    """Simplified skill deficit for job gap analysis (without TF-IDF fields)."""
    skill_name: str = Field(..., description="Name of the skill")
    deficit: float = Field(..., ge=0.0, description="Skill deficit score")
    importance: float = Field(..., ge=0.0, le=1.0, description="Skill importance")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Candidate confidence in skill")
    match_strength: Optional[float] = Field(None, ge=0.0, le=1.0, description="Match strength")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill_name": "Python",
                "deficit": 0.8,
                "importance": 0.9,
                "confidence": 0.1,
                "match_strength": 0.1
            }
        }


class CourseRecommendation(BaseModel):
    """Course recommendation with gain score."""
    course_id: str = Field(..., description="Unique course identifier")
    title: Optional[str] = Field(None, description="Course title")
    provider: Optional[str] = Field(None, description="Course provider")
    url: Optional[str] = Field(None, description="Course URL")
    imageUrl: Optional[str] = Field(None, description="Course image URL")
    avg_rating: Optional[float] = Field(None, description="Average rating (0-5)")
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    covered_deficit_skills: List[str] = Field(..., description="Deficit skills taught")
    gain_score: float = Field(..., description="Expected deficit reduction score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "course_id": "coursera-ml-001",
                "title": "Machine Learning Specialization",
                "provider": "Coursera",
                "url": "https://www.coursera.org/specializations/machine-learning",
                "avg_rating": 4.8,
                "difficulty": "intermediate",
                "covered_deficit_skills": ["TensorFlow", "PyTorch", "Neural Networks"],
                "gain_score": 85.5
            }
        }


class CourseRecommendationResponse(BaseModel):
    """Complete course recommendation response."""
    candidate_id: str = Field(..., description="Candidate identifier")
    role_key: str = Field(..., description="Role identifier")
    role_name: str = Field(..., description="Role name")
    top_k_deficits_considered: int = Field(..., description="Number of deficits considered")
    recommendations: List[CourseRecommendation] = Field(..., description="Top-N courses")


# ============================================================================
# Project Relevance Models
# ============================================================================

class ProjectRelevance(BaseModel):
    """Single project relevance score."""
    project_name: str = Field(..., description="Project name")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance to role (0-1)")
    matched_role_skills: List[str] = Field(..., description="Skills that match role requirements")
    project_skills: List[str] = Field(..., description="All skills used in project")
    num_matched: int = Field(..., description="Number of matched skills")
    num_project_skills: int = Field(..., description="Total project skills")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_name": "AI Chatbot System",
                "relevance_score": 0.75,
                "matched_role_skills": ["Python", "TensorFlow", "NLP", "FastAPI"],
                "project_skills": ["Python", "TensorFlow", "NLP", "FastAPI", "Docker", "PostgreSQL"],
                "num_matched": 4,
                "num_project_skills": 6
            }
        }


class ProjectRelevanceResponse(BaseModel):
    """Project-role relevance analysis response."""
    candidate_id: str = Field(..., description="Candidate identifier")


# ============================================================================
# GNN-Based Skill Gap Models (NEW)
# ============================================================================

class GNNSkillPrediction(BaseModel):
    """Single skill prediction from GNN with all scoring components."""
    skill: str = Field(..., description="Skill name")
    category: str = Field(..., description="Skill category")
    final_score: float = Field(..., description="Final ranking score: (1-P_has) * importance * P_gnn")
    P_gnn: float = Field(..., ge=0.0, le=1.0, description="GNN predicted probability")
    P_has: float = Field(..., ge=0.0, le=1.0, description="Current skill confidence")
    importance: float = Field(..., description="Role importance score (TF-IDF)")
    gap_magnitude: float = Field(..., ge=0.0, le=1.0, description="Gap magnitude: 1 - P_has")
    reason: str = Field(..., description="Human-readable reason for ranking")
    shap_explanation: Optional[dict] = Field(None, description="SHAP explanation (if requested)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill": "RAG",
                "category": "LLM & Generative AI",
                "final_score": 0.0842,
                "P_gnn": 0.72,
                "P_has": 0.18,
                "importance": 0.82,
                "gap_magnitude": 0.82,
                "reason": "Large skill gap; critical for role; GNN predicts high learning potential"
            }
        }


class GNNCategorySummary(BaseModel):
    """Category-level aggregation for XAI."""
    category: str = Field(..., description="Skill category name")
    gap_score: float = Field(..., description="Sum of final scores in this category")
    missing_skills_count: int = Field(..., description="Number of missing skills in category")
    top_skills: List[str] = Field(..., description="Top 3 skills in this category")
    
    class Config:
        json_schema_extra = {
            "example": {
                "category": "LLM & Generative AI",
                "gap_score": 0.31,
                "missing_skills_count": 4,
                "top_skills": ["RAG", "Prompt Engineering", "LangChain"]
            }
        }


class GNNMissingSkillsResponse(BaseModel):
    """Response for GNN-based missing skill ranking endpoint."""
    candidate_id: str = Field(..., description="Candidate identifier")
    role_key: str = Field(..., description="Role identifier")
    role_name: str = Field(..., description="Role name")
    top_missing_skills: List[GNNSkillPrediction] = Field(..., description="Top-K missing skills ranked by final_score")
    category_summary: List[GNNCategorySummary] = Field(..., description="Category-level gap analysis")
    metadata: dict = Field(..., description="Computation metadata and statistics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "C12345",
                "role_key": "ai_ml_engineer",
                "role_name": "AI/ML Engineer",
                "top_missing_skills": [
                    {
                        "skill": "RAG",
                        "category": "LLM & Generative AI",
                        "final_score": 0.0842,
                        "P_gnn": 0.72,
                        "P_has": 0.18,
                        "importance": 0.82,
                        "gap_magnitude": 0.82,
                        "reason": "Large skill gap; critical for role; GNN predicts high learning potential"
                    }
                ],
                "category_summary": [
                    {
                        "category": "LLM & Generative AI",
                        "gap_score": 0.31,
                        "missing_skills_count": 4,
                        "top_skills": ["RAG", "Prompt Engineering", "LangChain"]
                    }
                ],
                "metadata": {
                    "total_required_skills": 42,
                    "total_missing_skills": 28,
                    "returned_skills": 20,
                    "p_has_threshold": 0.6
                }
            }
        }


class ProjectRelevanceResponse(BaseModel):
    """Project-role relevance analysis response."""
    candidate_id: str = Field(..., description="Candidate identifier")
    role_key: str = Field(..., description="Role identifier")
    role_name: Optional[str] = Field(None, description="Role name")
    projects: List[ProjectRelevance] = Field(..., description="Projects sorted by relevance")
    candidate_project_score: float = Field(
        ..., 
        ge=0, 
        le=1, 
        description="Overall project relevance (avg of top 3 or max)"
    )
    total_projects: int = Field(..., description="Total number of candidate projects")
    error: Optional[str] = Field(None, description="Error message if any")


# ============================================================================
# Hybrid Skill Gap Models (Multiplicative Formula)
# ============================================================================

class HybridSkillPrediction(BaseModel):
    """
    Single skill prediction using HYBRID MULTIPLICATIVE formula.
    
    Formula: final_score = gap × importance_norm × P_gnn
    
    Where:
    - gap = 1 - P_has (missing magnitude)
    - importance_norm = importance / max_importance(role) [normalized per role]
    - P_gnn = GNN learnability score [0-1]
    
    This differs from additive GNN ranking by emphasizing skills that are
    simultaneously missing, important, AND learnable.
    """
    skill: str = Field(..., description="Skill name")
    category: str = Field(..., description="Skill category")
    final_score: float = Field(..., description="Final ranking score: gap × importance_norm × P_gnn")
    gap: float = Field(..., ge=0.0, le=1.0, description="Gap magnitude: 1 - P_has")
    importance_norm: float = Field(..., ge=0.0, le=1.0, description="Normalized importance (0-1)")
    P_gnn: float = Field(..., ge=0.0, le=1.0, description="GNN learnability score")
    P_has: float = Field(..., ge=0.0, le=1.0, description="Current skill confidence")
    importance: float = Field(..., description="Raw TF-IDF importance score")
    reason: str = Field(..., description="Human-readable reason for ranking")
    
    class Config:
        json_schema_extra = {
            "example": {
                "skill": "RAG",
                "category": "LLM & Generative AI",
                "final_score": 0.456,
                "gap": 0.82,
                "importance_norm": 0.95,
                "P_gnn": 0.72,
                "P_has": 0.18,
                "importance": 38.5,
                "reason": "high skill gap (82% missing); critical for role; high learning potential"
            }
        }


class HybridCategorySummary(BaseModel):
    """Category-level aggregation for hybrid ranking."""
    category: str = Field(..., description="Skill category name")
    gap_score: float = Field(..., description="Sum of final scores in this category")
    missing_skills_count: int = Field(..., description="Number of missing skills in category")
    top_skills: List[str] = Field(..., description="Top 3 skills in this category")
    
    class Config:
        json_schema_extra = {
            "example": {
                "category": "LLM & Generative AI",
                "gap_score": 1.24,
                "missing_skills_count": 4,
                "top_skills": ["RAG", "Prompt Engineering", "LangChain"]
            }
        }


class HybridMissingSkillsResponse(BaseModel):
    """Response for hybrid multiplicative skill ranking endpoint."""
    candidate_id: str = Field(..., description="Candidate identifier")
    role_key: str = Field(..., description="Role identifier")
    role_name: str = Field(..., description="Role name")
    top_missing_skills: List[HybridSkillPrediction] = Field(
        ..., 
        description="Top-K missing skills ranked by final_score (gap × importance_norm × P_gnn)"
    )
    category_summary: List[HybridCategorySummary] = Field(
        ..., 
        description="Category-level gap analysis"
    )
    metadata: dict = Field(..., description="Computation metadata and statistics")
    
    class Config:
        json_schema_extra = {
            "example": {
                "candidate_id": "C12345",
                "role_key": "ai_ml_engineer",
                "role_name": "AI/ML Engineer",
                "top_missing_skills": [
                    {
                        "skill": "RAG",
                        "category": "LLM & Generative AI",
                        "final_score": 0.456,
                        "gap": 0.82,
                        "importance_norm": 0.95,
                        "P_gnn": 0.72,
                        "P_has": 0.18,
                        "importance": 38.5,
                        "reason": "high skill gap (82% missing); critical for role; high learning potential"
                    }
                ],
                "category_summary": [
                    {
                        "category": "LLM & Generative AI",
                        "gap_score": 1.24,
                        "missing_skills_count": 4,
                        "top_skills": ["RAG", "Prompt Engineering", "LangChain"]
                    }
                ],
                "metadata": {
                    "total_required_skills": 42,
                    "total_missing_skills": 28,
                    "returned_skills": 25,
                    "p_has_threshold": 0.6,
                    "max_importance": 42.5,
                    "formula": "gap × importance_norm × P_gnn",
                    "ranking_method": "hybrid_multiplicative"
                }
            }
        }


# ============================================================================
# Category-Aware Models (NEW)
# ============================================================================

class CategorySkillImportance(BaseModel):
    """Single skill importance within a category."""
    skill: str = Field(..., description="Skill name")
    importance: float = Field(..., description="TF-IDF importance score")


class RoleCategoryProfile(BaseModel):
    """Aggregated category profile for a role."""
    category: str = Field(..., description="Category name")
    importance_sum: float = Field(..., description="Sum of importance for all skills in category")
    num_role_skills: int = Field(..., description="Number of role skills in this category")
    top_skills: List[CategorySkillImportance] = Field(
        ..., 
        description="Top skills in category by importance"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "category": "MLOps / DevOps",
                "importance_sum": 45.8,
                "num_role_skills": 12,
                "top_skills": [
                    {"skill": "Docker", "importance": 12.5},
                    {"skill": "Kubernetes", "importance": 10.2}
                ]
            }
        }


class RoleCategoryProfileResponse(BaseModel):
    """Complete category profile for a role."""
    role_key: str = Field(..., description="Role identifier")
    role_name: str = Field(..., description="Role name")
    total_jobs: int = Field(..., description="Total jobs in role")
    categories: List[RoleCategoryProfile] = Field(..., description="Categories sorted by importance")
    category_coverage: float = Field(
        ..., 
        description="Percentage of role skills mapped to categories"
    )


class CategoryGap(BaseModel):
    """Category-level skill gap."""
    category: str = Field(..., description="Category name")
    gap_score: float = Field(..., description="importance_sum × (1 - coverage)")
    importance_sum: float = Field(..., description="Total importance of role skills in category")
    coverage: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Coverage: avg match_strength of role skills in category"
    )
    missing_count: int = Field(..., description="Number of missing/weak skills in category")
    top_missing_skills: List[dict] = Field(..., description="Top missing skills with deficits")
    
    class Config:
        json_schema_extra = {
            "example": {
                "category": "LLM & Generative AI",
                "gap_score": 25.4,
                "importance_sum": 42.3,
                "coverage": 0.40,
                "missing_count": 5,
                "top_missing_skills": [
                    {"skill": "RAG", "deficit": 8.5, "importance": 10.2}
                ]
            }
        }


class CategoryGain(BaseModel):
    """Category coverage improvement from course."""
    category: str = Field(..., description="Category name")
    gain: float = Field(..., description="Improvement in category coverage")


# ============================================================================
# Enhanced Response Models (Backward Compatible)
# ============================================================================

class SkillDeficitEnhanced(SkillDeficit):
    """Enhanced skill deficit with category (OPTIONAL field for backward compatibility)."""
    category: Optional[str] = Field(None, description="Skill category (if mapped)")


class SkillGapResponseEnhanced(BaseModel):
    """Enhanced skill gap analysis with category-aware grouping."""
    candidate_id: str = Field(..., description="Candidate identifier")
    role_key: str = Field(..., description="Role identifier")
    role_name: str = Field(..., description="Role name")
    total_jobs: int = Field(..., description="Total jobs in role")
    total_roles: int = Field(..., description="Total roles in system")
    deficits: List[SkillDeficitEnhanced] = Field(..., description="Top-K skill deficits")
    
    # NEW: Category-aware fields (optional for backward compatibility)
    category_gaps: Optional[List[CategoryGap]] = Field(
        None, 
        description="Category-level gaps sorted by gap_score"
    )
    category_mapping_stats: Optional[dict] = Field(
        None,
        description="Statistics on category mapping coverage"
    )


class CourseRecommendationEnhanced(CourseRecommendation):
    """Enhanced course recommendation with category gains (OPTIONAL field)."""
    category_gain: Optional[List[CategoryGain]] = Field(
        None,
        description="Category coverage improvements from this course"
    )


class CourseRecommendationResponseEnhanced(BaseModel):
    """Enhanced course recommendation response with category awareness."""
    candidate_id: str = Field(..., description="Candidate identifier")
    role_key: str = Field(..., description="Role identifier")
    role_name: str = Field(..., description="Role name")
    top_k_deficits_considered: int = Field(..., description="Number of deficits considered")
    recommendations: List[CourseRecommendationEnhanced] = Field(..., description="Top-N courses")
