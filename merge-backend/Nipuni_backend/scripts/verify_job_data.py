"""
Data Verification Script for Job Recommendation System

This script checks:
1. Job data completeness
2. Skill naming consistency between job features and student skills
3. Question bank coverage per role
4. Skill distribution analysis
"""

import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR / "src"))

import pandas as pd
from sqlalchemy import create_engine, text
from app.config import settings
from app.models.student_skill_portfolio import StudentSkillPortfolio
from app.models.skill import SkillProfileClaimed
from app.models.question_bank import QuestionBank
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
DATA_DIR = BACKEND_DIR / "data"
JOB_FEATURES_FILE = DATA_DIR / "job_parent_skill_features.csv"
JOB_DATA_FILE = DATA_DIR / "Job_data.csv"


def get_db_connection():
    """Get database connection"""
    engine = create_engine(settings.DATABASE_URL)
    return engine


def check_job_data():
    """Check job data files"""
    logger.info("=" * 80)
    logger.info("1. JOB DATA VERIFICATION")
    logger.info("=" * 80)
    
    # Check Job_data.csv
    if not JOB_DATA_FILE.exists():
        logger.error(f"❌ Job data file not found: {JOB_DATA_FILE}")
        return False, []
    
    jobs_df = pd.read_csv(JOB_DATA_FILE)
    logger.info(f"✅ Loaded {len(jobs_df)} jobs from {JOB_DATA_FILE.name}")
    
    # Check required columns
    required_cols = ['job_id', 'title', 'company', 'skills', 'role_key']
    missing_cols = [col for col in required_cols if col not in jobs_df.columns]
    if missing_cols:
        logger.error(f"❌ Missing columns in Job_data.csv: {missing_cols}")
        return False, []
    logger.info(f"✅ All required columns present")
    
    # Role distribution
    logger.info("\n📊 Jobs per Role:")
    role_counts = jobs_df['role_key'].value_counts()
    for role, count in role_counts.items():
        logger.info(f"  - {role}: {count} jobs")
    
    # Check job_parent_skill_features.csv
    if not JOB_FEATURES_FILE.exists():
        logger.error(f"❌ Job features file not found: {JOB_FEATURES_FILE}")
        return False, []
    
    features_df = pd.read_csv(JOB_FEATURES_FILE)
    logger.info(f"\n✅ Loaded job features matrix: {features_df.shape[0]} jobs × {features_df.shape[1]} columns")
    
    # Get skill columns (exclude metadata)
    metadata_cols = ['job_id', 'title', 'company', 'role_key', 'description']
    skill_cols = [col for col in features_df.columns if col not in metadata_cols]
    logger.info(f"✅ Found {len(skill_cols)} unique skills in feature matrix")
    
    return True, skill_cols


def check_skill_naming_consistency(db_skills):
    """Check skill naming consistency"""
    logger.info("\n" + "=" * 80)
    logger.info("2. SKILL NAMING CONSISTENCY CHECK")
    logger.info("=" * 80)
    
    # Get skill columns from job features
    if not JOB_FEATURES_FILE.exists():
        logger.error(f"❌ Cannot check consistency: {JOB_FEATURES_FILE} not found")
        return
    
    features_df = pd.read_csv(JOB_FEATURES_FILE)
    metadata_cols = ['job_id', 'title', 'company', 'role_key', 'description']
    job_skills = set([col for col in features_df.columns if col not in metadata_cols])
    
    # Compare with database skills
    db_skills_set = set(db_skills)
    
    # Skills in job features but not in DB
    extra_job_skills = job_skills - db_skills_set
    if extra_job_skills:
        logger.warning(f"\n⚠️  Skills in job features but NOT in student database ({len(extra_job_skills)}):")
        for skill in sorted(list(extra_job_skills)[:10]):  # Show first 10
            logger.warning(f"  - {skill}")
        if len(extra_job_skills) > 10:
            logger.warning(f"  ... and {len(extra_job_skills) - 10} more")
    
    # Skills in DB but not in job features
    extra_db_skills = db_skills_set - job_skills
    if extra_db_skills:
        logger.warning(f"\n⚠️  Skills in student database but NOT in job features ({len(extra_db_skills)}):")
        for skill in sorted(list(extra_db_skills)[:10]):  # Show first 10
            logger.warning(f"  - {skill}")
        if len(extra_db_skills) > 10:
            logger.warning(f"  ... and {len(extra_db_skills) - 10} more")
    
    # Common skills
    common_skills = job_skills & db_skills_set
    logger.info(f"\n✅ Common skills between job features and student DB: {len(common_skills)}")
    
    # Suggest normalization if needed
    if extra_job_skills or extra_db_skills:
        logger.info("\n💡 Recommendation: Create a skill normalization map")
        logger.info("   Example: {'Machine Learning': 'ML', 'Python Programming': 'Python'}")
        return False
    
    return True


def check_question_bank_coverage():
    """Check question bank coverage per role and skill"""
    logger.info("\n" + "=" * 80)
    logger.info("3. QUESTION BANK COVERAGE")
    logger.info("=" * 80)
    
    engine = get_db_connection()
    
    try:
        # Get question counts per skill and difficulty
        query = text("""
            SELECT 
                skill_name,
                difficulty,
                COUNT(*) as question_count
            FROM question_bank
            GROUP BY skill_name, difficulty
            ORDER BY skill_name, difficulty
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query)
            questions_df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        if questions_df.empty:
            logger.warning("⚠️  Question bank is empty!")
            return
        
        logger.info(f"\n📊 Question Bank Statistics:")
        logger.info(f"  - Total questions: {questions_df['question_count'].sum()}")
        logger.info(f"  - Skills covered: {questions_df['skill_name'].nunique()}")
        
        # Questions per skill
        skill_totals = questions_df.groupby('skill_name')['question_count'].sum().sort_values(ascending=False)
        logger.info(f"\n📊 Top 10 Skills by Question Count:")
        for skill, count in skill_totals.head(10).items():
            logger.info(f"  - {skill}: {count} questions")
        
        # Questions per difficulty
        difficulty_totals = questions_df.groupby('difficulty')['question_count'].sum()
        logger.info(f"\n📊 Questions by Difficulty:")
        for diff in ['Easy', 'Medium', 'Hard']:
            count = difficulty_totals.get(diff, 0)
            logger.info(f"  - {diff}: {count} questions")
        
        # Check for skills with insufficient questions
        logger.info(f"\n⚠️  Skills with < 10 questions:")
        low_coverage = skill_totals[skill_totals < 10]
        if len(low_coverage) > 0:
            for skill, count in low_coverage.items():
                logger.warning(f"  - {skill}: only {count} questions")
        else:
            logger.info("  ✅ All skills have adequate question coverage")
            
    except Exception as e:
        logger.error(f"❌ Error checking question bank: {e}")


def check_student_portfolio_stats():
    """Check student skill portfolio statistics"""
    logger.info("\n" + "=" * 80)
    logger.info("4. STUDENT PORTFOLIO STATISTICS")
    logger.info("=" * 80)
    
    engine = get_db_connection()
    
    try:
        # Get portfolio stats
        query = text("""
            SELECT 
                COUNT(DISTINCT student_id) as student_count,
                COUNT(*) as total_portfolio_entries,
                AVG(final_score) as avg_final_score,
                COUNT(DISTINCT skill_name) as skills_covered
            FROM student_skill_portfolio
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query)
            stats = result.fetchone()
        
        if stats and stats[0] > 0:
            logger.info(f"  - Students with portfolios: {stats[0]}")
            logger.info(f"  - Total portfolio entries: {stats[1]}")
            logger.info(f"  - Average final score: {stats[2]:.2f}%")
            logger.info(f"  - Skills covered: {stats[3]}")
            
            # Get skill distribution
            query = text("""
                SELECT 
                    skill_name,
                    COUNT(DISTINCT student_id) as student_count,
                    AVG(final_score) as avg_score,
                    AVG(verified_score) as avg_verified_score
                FROM student_skill_portfolio
                GROUP BY skill_name
                ORDER BY student_count DESC
                LIMIT 20
            """)
            
            with engine.connect() as conn:
                result = conn.execute(query)
                skill_stats = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            logger.info(f"\n📊 Top 20 Skills in Student Portfolios:")
            for _, row in skill_stats.iterrows():
                logger.info(
                    f"  - {row['skill_name']}: "
                    f"{row['student_count']} students, "
                    f"avg score: {row['avg_score']:.1f}% "
                    f"(verified: {row['avg_verified_score']:.1f}%)"
                )
        else:
            logger.warning("⚠️  No student portfolios found in database")
            
        # Get skill names from both tables
        query = text("SELECT DISTINCT skill_name FROM student_skill_portfolio")
        with engine.connect() as conn:
            result = conn.execute(query)
            portfolio_skills = [row[0] for row in result.fetchall()]
        
        query = text("SELECT DISTINCT skill_name FROM skill_profile_claimed")
        with engine.connect() as conn:
            result = conn.execute(query)
            claimed_skills = [row[0] for row in result.fetchall()]
        
        return list(set(portfolio_skills + claimed_skills))
            
    except Exception as e:
        logger.error(f"❌ Error checking student portfolios: {e}")
        return []


def generate_normalization_recommendations(job_skills, db_skills):
    """Generate skill name normalization recommendations"""
    logger.info("\n" + "=" * 80)
    logger.info("5. SKILL NORMALIZATION RECOMMENDATIONS")
    logger.info("=" * 80)
    
    job_skills_lower = {skill.lower(): skill for skill in job_skills}
    db_skills_lower = {skill.lower(): skill for skill in db_skills}
    
    potential_matches = []
    
    for job_skill_lower, job_skill in job_skills_lower.items():
        for db_skill_lower, db_skill in db_skills_lower.items():
            # Check for similar names
            if job_skill_lower in db_skill_lower or db_skill_lower in job_skill_lower:
                if job_skill != db_skill:
                    potential_matches.append((job_skill, db_skill))
    
    if potential_matches:
        logger.info("\n💡 Suggested skill name mappings (job → student):")
        for job_skill, db_skill in potential_matches[:20]:
            logger.info(f"  '{job_skill}' → '{db_skill}'")
        
        logger.info("\n📝 To implement, add to ml_job_recommendation_service.py:")
        logger.info("```python")
        logger.info("SKILL_NORMALIZATION_MAP = {")
        for job_skill, db_skill in potential_matches[:10]:
            logger.info(f"    '{job_skill}': '{db_skill}',")
        logger.info("}")
        logger.info("```")
    else:
        logger.info("✅ No obvious normalization opportunities found")


def main():
    """Run all verification checks"""
    logger.info("\n" + "=" * 80)
    logger.info("JOB RECOMMENDATION SYSTEM - DATA VERIFICATION")
    logger.info("=" * 80)
    
    # 1. Check job data
    success, job_skill_cols = check_job_data()
    if not success:
        logger.error("\n❌ Job data verification failed. Fix errors and try again.")
        return
    
    # 2. Check student portfolios and get DB skills
    db_skills = check_student_portfolio_stats()
    
    # 3. Check skill naming consistency
    if db_skills:
        check_skill_naming_consistency(db_skills)
        generate_normalization_recommendations(job_skill_cols, db_skills)
    
    # 4. Check question bank coverage
    check_question_bank_coverage()
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ VERIFICATION COMPLETE")
    logger.info("=" * 80)
    logger.info("\nNext Steps:")
    logger.info("  1. Review warnings and recommendations above")
    logger.info("  2. Implement skill normalization if needed")
    logger.info("  3. Add more questions for skills with low coverage")
    logger.info("  4. Test ML job recommendations with real student data")
    logger.info("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nVerification cancelled by user")
    except Exception as e:
        logger.error(f"\n❌ Verification failed with error: {e}", exc_info=True)
        sys.exit(1)
