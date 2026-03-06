"""
ML-Based Job Recommendation Service

Enhanced job recommendation using machine learning models, verified skills,
skill levels, and skill gap analysis.

Updated for flat skill structure.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.skill import SkillProfileClaimed
from app.models.student_skill_portfolio import StudentSkillPortfolio
import logging
import pickle
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
JOB_FEATURES_FILE = DATA_DIR / "job_parent_skill_features.csv"
ROLE_MODEL_FILE = MODELS_DIR / "role_model.pkl"
FEATURE_COLUMNS_FILE = MODELS_DIR / "feature_columns.json"

# Cache
_job_features_cache = None
_ml_model_cache = None
_feature_columns_cache = None


def load_ml_model() -> Optional[any]:
    """
    Load the pre-trained ML model for job role prediction.
    
    Returns:
        Trained model object or None if not available
    """
    global _ml_model_cache
    
    if _ml_model_cache is not None:
        return _ml_model_cache
    
    if not ROLE_MODEL_FILE.exists():
        logger.warning(
            f"ML model not found at {ROLE_MODEL_FILE}. "
            "Using cosine similarity fallback. "
            "Recommendations will still work but may be less accurate."
        )
        return None
    
    try:
        with open(ROLE_MODEL_FILE, 'rb') as f:
            _ml_model_cache = pickle.load(f)
        logger.info(f"ML model loaded successfully from {ROLE_MODEL_FILE}")
        return _ml_model_cache
    except Exception as e:
        logger.error(f"Failed to load ML model: {e}")
        return None


def load_feature_columns() -> Optional[List[str]]:
    """
    Load feature column names used for ML model.
    
    Returns:
        List of feature column names or None
    """
    global _feature_columns_cache
    
    if _feature_columns_cache is not None:
        return _feature_columns_cache
    
    if not FEATURE_COLUMNS_FILE.exists():
        logger.warning(f"Feature columns file not found at {FEATURE_COLUMNS_FILE}")
        return None
    
    try:
        import json
        with open(FEATURE_COLUMNS_FILE, 'r') as f:
            _feature_columns_cache = json.load(f)
        logger.info(f"Feature columns loaded: {len(_feature_columns_cache)} features")
        return _feature_columns_cache
    except Exception as e:
        logger.error(f"Failed to load feature columns: {e}")
        return None


def load_jobs_feature_table() -> pd.DataFrame:
    """
    Load job parent skill features from CSV.
    
    Returns:
        DataFrame with job skill requirements
    """
    global _job_features_cache
    
    if _job_features_cache is not None:
        return _job_features_cache
    
    if not JOB_FEATURES_FILE.exists():
        raise FileNotFoundError(
            f"Job features file not found: {JOB_FEATURES_FILE}\n"
            f"Run: python scripts/build_job_parent_features.py"
        )
    
    logger.info(f"Loading job features from {JOB_FEATURES_FILE}")
    df = pd.read_csv(JOB_FEATURES_FILE)
    _job_features_cache = df
    logger.info(f"Loaded {len(df):,} jobs with {len(df.columns)} columns")
    return df


def get_student_skill_profile(
    db: Session,
    student_id: str,
    prefer_verified: bool = True
) -> Tuple[Dict[str, float], Dict[str, str]]:
    """
    Get student's skill scores and levels (flat skill structure).
    
    Prioritizes portfolio (tested) skills over claimed skills.
    
    Args:
        db: Database session
        student_id: Student identifier
        prefer_verified: If True, use portfolio (verified) skills when available
        
    Returns:
        Tuple of (skill_scores dict, skill_levels dict)
    """
    skill_scores = {}
    skill_levels = {}
    verified_count = 0
    claimed_count = 0
    
    # Get verified skills from portfolio (tested via quiz)
    portfolio_skills = db.query(StudentSkillPortfolio).filter(
        StudentSkillPortfolio.student_id == student_id
    ).all()
    
    if portfolio_skills and prefer_verified:
        logger.info(f"Using {len(portfolio_skills)} portfolio skills for {student_id}")
        for skill in portfolio_skills:
            skill_scores[skill.skill_name] = skill.final_score
            skill_levels[skill.skill_name] = skill.final_level
        verified_count = len(portfolio_skills)
    
    # Get claimed skills (from transcript) if no portfolio skills OR to supplement
    claimed_skills = db.query(SkillProfileClaimed).filter(
        SkillProfileClaimed.student_id == student_id
    ).all()
    
    # Add claimed skills only for skills NOT in portfolio (avoid duplicates)
    portfolio_skill_names = set(skill_scores.keys())
    for skill in claimed_skills:
        if skill.skill_name not in portfolio_skill_names:
            skill_scores[skill.skill_name] = skill.claimed_score
            # Infer level from score if not in portfolio
            if skill.claimed_score >= 75:
                skill_levels[skill.skill_name] = "Advanced"
            elif skill.claimed_score >= 50:
                skill_levels[skill.skill_name] = "Intermediate"
            else:
                skill_levels[skill.skill_name] = "Beginner"
            claimed_count += 1
    
    logger.info(
        f"Student profile: {len(skill_scores)} total skills "
        f"({verified_count} verified from quizzes, {claimed_count} claimed from transcript)"
    )
    
    return skill_scores, skill_levels


def calculate_skill_gap(
    student_scores: Dict[str, float],
    student_levels: Dict[str, str],
    job_required_skills: List[str],
    threshold: float = 70.0
) -> Dict:
    """
    Calculate skill gaps between student profile and job requirements.
    
    Args:
        student_scores: Student's skill scores
        student_levels: Student's skill levels
        job_required_skills: List of skills required for job
        threshold: Minimum score to consider "proficient"
        
    Returns:
        Dictionary with matched, missing, and improvement suggestions
    """
    proficient_skills = []
    needs_improvement = []
    missing_skills = []
    
    for skill in job_required_skills:
        score = student_scores.get(skill, 0.0)
        level = student_levels.get(skill, "Not Assessed")
        
        if score >= threshold:
            proficient_skills.append({
                "skill": skill,
                "score": round(score, 1),
                "level": level,
                "status": "Proficient"
            })
        elif score > 0:
            gap = threshold - score
            needs_improvement.append({
                "skill": skill,
                "score": round(score, 1),
                "level": level,
                "gap": round(gap, 1),
                "status": "Needs Improvement",
                "recommendation": _get_improvement_recommendation(score)
            })
        else:
            missing_skills.append({
                "skill": skill,
                "score": 0.0,
                "level": "Not Assessed",
                "gap": threshold,
                "status": "Missing",
                "recommendation": "Start with foundational courses"
            })
    
    return {
        "proficient": proficient_skills,
        "needs_improvement": needs_improvement,
        "missing": missing_skills,
        "match_percentage": (len(proficient_skills) / len(job_required_skills) * 100) 
                           if job_required_skills else 0
    }


def _get_improvement_recommendation(score: float) -> str:
    """Generate skill improvement recommendation based on score."""
    if score >= 60:
        return "Take advanced courses or work on real projects"
    elif score >= 40:
        return "Complete intermediate tutorials and practice exercises"
    else:
        return "Start with beginner courses and build foundations"


def recommend_jobs_ml(
    db: Session,
    student_id: str,
    top_k: int = 10,
    threshold: float = 70.0,
    use_verified: bool = True,
    role_key: Optional[str] = None
) -> List[Dict]:
    """
    ML-enhanced job recommendation with skill gap analysis.
    
    Args:
        db: Database session
        student_id: Student identifier
        top_k: Number of top jobs to return
        threshold: Minimum score for skill proficiency
        use_verified: Prefer verified skills over claimed
        role_key: Optional filter by role category
        
    Returns:
        List of job recommendations with detailed skill gap analysis
    """
    # Load job features
    jobs_df = load_jobs_feature_table()
    
    # Filter by role_key if specified
    if role_key:
        jobs_df = jobs_df[jobs_df['role_key'] == role_key].copy()
        if len(jobs_df) == 0:
            logger.warning(f"No jobs found for role_key: {role_key}")
            return []
    
    # Filter for entry-level and internship positions only
    if 'seniority_level' in jobs_df.columns:
        jobs_df = jobs_df[jobs_df['seniority_level'].isin(['Entry level', 'Internship'])].copy()
        logger.info(f"Filtered to {len(jobs_df)} entry-level and internship positions")
        if len(jobs_df) == 0:
            logger.warning("No entry-level or internship jobs found")
            return []
    
    # Get student skill profile
    student_scores, student_levels = get_student_skill_profile(
        db, student_id, prefer_verified=use_verified
    )
    
    if not student_scores:
        raise ValueError(f"No skills found for student {student_id}")
    
    # Identify skill columns (exclude metadata)
    metadata_cols = ['job_id', 'title', 'company', 'role_key', 'description', 'seniority_level']
    skill_cols = [col for col in jobs_df.columns if col not in metadata_cols]
    
    # Try ML-based prediction first
    ml_model = load_ml_model()
    ml_scores = None
    
    if ml_model is not None:
        try:
            # Prepare student feature vector
            feature_vector = np.zeros(len(skill_cols))
            for i, skill in enumerate(skill_cols):
                feature_vector[i] = student_scores.get(skill, 0.0) / 100.0
            
            # Reshape for prediction
            X = feature_vector.reshape(1, -1)
            
            # Get prediction probabilities for each job role
            ml_scores = ml_model.predict_proba(X)[0]
            logger.info("✅ Using ML model predictions for intelligent job ranking")
        except Exception as e:
            logger.error(f"ML prediction failed: {e}. Falling back to cosine similarity (still accurate).")
            ml_scores = None
    
    # Calculate recommendations
    recommendations = []
    
    for idx, job_row in jobs_df.iterrows():
        # Get required skills (where feature = 1)
        required_skills = [
            skill for skill in skill_cols
            if job_row[skill] == 1
        ]
        
        if not required_skills:
            continue
        
        # Calculate skill gap analysis
        gap_analysis = calculate_skill_gap(
            student_scores,
            student_levels,
            required_skills,
            threshold
        )
        
        # Calculate match score
        if ml_scores is not None and idx < len(ml_scores):
            # Use ML model confidence
            match_score = ml_scores[idx] * 100
        else:
            # Fallback to cosine similarity
            job_vector = job_row[skill_cols].values
            student_vector = np.array([
                student_scores.get(skill, 0.0) / 100.0 
                for skill in skill_cols
            ])
            
            similarity = cosine_similarity(
                student_vector.reshape(1, -1),
                job_vector.reshape(1, -1)
            )[0][0]
            match_score = similarity * 100
        
        # Build recommendation
        recommendations.append({
            "job_id": job_row['job_id'],
            "title": job_row['title'],
            "company": job_row['company'],
            "role_key": job_row.get('role_key', 'N/A'),
            "description": job_row.get('description', ''),
            "match_score": round(match_score, 1),
            "ml_prediction": ml_scores is not None,
            
            # Skill analysis
            "total_required_skills": len(required_skills),
            "proficient_skills_count": len(gap_analysis["proficient"]),
            "needs_improvement_count": len(gap_analysis["needs_improvement"]),
            "missing_skills_count": len(gap_analysis["missing"]),
            "skill_match_percentage": round(gap_analysis["match_percentage"], 1),
            
            # Detailed breakdowns
            "proficient_skills": gap_analysis["proficient"],
            "needs_improvement": gap_analysis["needs_improvement"],
            "missing_skills": gap_analysis["missing"],
            
            # Recommendations
            "readiness": _calculate_readiness(gap_analysis),
            "next_steps": _generate_next_steps(gap_analysis)
        })
    
    # Sort by match score
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)
    
    logger.info(
        f"Generated {len(recommendations)} ML recommendations for {student_id}, "
        f"returning top {top_k}"
    )
    
    return recommendations[:top_k]


def _calculate_readiness(gap_analysis: Dict) -> Dict:
    """
    Calculate job readiness level.
    
    Returns:
        Dict with readiness level and score
    """
    match_pct = gap_analysis["match_percentage"]
    
    if match_pct >= 80:
        return {
            "level": "Ready to Apply",
            "score": match_pct,
            "color": "green",
            "message": "You have most required skills. Apply now!"
        }
    elif match_pct >= 60:
        return {
            "level": "Almost Ready",
            "score": match_pct,
            "color": "yellow",
            "message": "Improve a few skills and you'll be ready."
        }
    elif match_pct >= 40:
        return {
            "level": "Developing",
            "score": match_pct,
            "color": "orange",
            "message": "Focus on building missing skills."
        }
    else:
        return {
            "level": "Early Stage",
            "score": match_pct,
            "color": "red",
            "message": "This role requires significant skill development."
        }


def _generate_next_steps(gap_analysis: Dict) -> List[str]:
    """Generate actionable next steps based on skill gaps."""
    steps = []
    
    missing_count = len(gap_analysis["missing"])
    improvement_count = len(gap_analysis["needs_improvement"])
    proficient_count = len(gap_analysis["proficient"])
    
    if missing_count > 0:
        top_missing = gap_analysis["missing"][:3]
        skills_str = ", ".join([s["skill"] for s in top_missing])
        steps.append(f"Learn fundamental skills: {skills_str}")
    
    if improvement_count > 0:
        top_improve = gap_analysis["needs_improvement"][:3]
        skills_str = ", ".join([s["skill"] for s in top_improve])
        steps.append(f"Take practice quizzes to improve: {skills_str}")
    
    if proficient_count >= gap_analysis.get("match_percentage", 0) * 0.8:
        steps.append("Build a portfolio project showcasing your skills")
        steps.append("Update your resume with verified skills")
    
    if not steps:
        steps.append("Continue building your skill profile")
    
    return steps


def clear_cache():
    """Clear all cached data and models."""
    global _job_features_cache, _ml_model_cache, _feature_columns_cache
    _job_features_cache = None
    _ml_model_cache = None
    _feature_columns_cache = None
    logger.info("All caches cleared")
