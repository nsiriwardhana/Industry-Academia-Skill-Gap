from .schemas import (
    RoleBasic,
    SkillImportance,
    RoleSkillProfile,
    SkillConfidence,
    CandidateSkillProfile,
    SkillDeficit,
    SkillGapResponse,
    CourseRecommendation,
    CourseRecommendationResponse,
    ProjectRelevance,
    ProjectRelevanceResponse,
    # NEW: Category-aware models
    CategorySkillImportance,
    RoleCategoryProfile,
    RoleCategoryProfileResponse,
    CategoryGap,
    CategoryGain,
    SkillDeficitEnhanced,
    SkillGapResponseEnhanced,
    CourseRecommendationEnhanced,
    CourseRecommendationResponseEnhanced,
    # NEW: GNN-based models
    GNNSkillPrediction,
    GNNCategorySummary,
    GNNMissingSkillsResponse,
    # NEW: Hybrid multiplicative models
    HybridSkillPrediction,
    HybridCategorySummary,
    HybridMissingSkillsResponse,
)

__all__ = [
    "RoleBasic",
    "SkillImportance",
    "RoleSkillProfile",
    "SkillConfidence",
    "CandidateSkillProfile",
    "SkillDeficit",
    "SkillGapResponse",
    "CourseRecommendation",
    "CourseRecommendationResponse",
    "ProjectRelevance",
    "ProjectRelevanceResponse",
    # NEW: Category-aware models
    "CategorySkillImportance",
    "RoleCategoryProfile",
    "RoleCategoryProfileResponse",
    "CategoryGap",
    "CategoryGain",
    "SkillDeficitEnhanced",
    "SkillGapResponseEnhanced",
    "CourseRecommendationEnhanced",
    "CourseRecommendationResponseEnhanced",
    # NEW: GNN-based models
    "GNNSkillPrediction",
    "GNNCategorySummary",
    "GNNMissingSkillsResponse",
    # NEW: Hybrid multiplicative models
    "HybridSkillPrediction",
    "HybridCategorySummary",
    "HybridMissingSkillsResponse",
]


