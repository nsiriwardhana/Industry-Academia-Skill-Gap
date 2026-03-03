"""
Test ML Job Recommendation Endpoint

Quick test to verify the ML job recommendation endpoint works.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.ml_job_recommendation_service import recommend_jobs_ml, load_jobs_feature_table, load_ml_model
import pandas as pd


def main():
    print("=" * 70)
    print("ML JOB RECOMMENDATION ENDPOINT TEST")
    print("=" * 70)
    print()
    
    # Test 1: Load ML Model
    print("1️⃣  Testing ML Model Loading...")
    model = load_ml_model()
    if model is not None:
        print("   ✅ ML model loaded successfully")
    else:
        print("   ⚠️  ML model not found - using cosine similarity fallback")
    print()
    
    # Test 2: Load Job Features
    print("2️⃣  Testing Job Features Loading...")
    try:
        jobs_df = load_jobs_feature_table()
        print(f"   ✅ Loaded {len(jobs_df)} jobs with {len(jobs_df.columns)} columns")
        
        # Show sample jobs
        print(f"\n   📋 Sample Jobs:")
        for idx, row in jobs_df.head(3).iterrows():
            print(f"      - {row['title']} at {row['company']} [{row['role_key']}]")
        print()
    except Exception as e:
        print(f"   ❌ Failed to load jobs: {e}")
        return
    
    # Test 3: Database Connection
    print("3️⃣  Testing Database Connection...")
    try:
        engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Check for existing students with portfolios
        from app.models.student_skill_portfolio import StudentSkillPortfolio
        
        students_with_portfolio = db.query(StudentSkillPortfolio.student_id).distinct().all()
        print(f"   ✅ Connected to database")
        print(f"   📊 Found {len(students_with_portfolio)} students with skill portfolios")
        
        if students_with_portfolio:
            test_student_id = students_with_portfolio[0][0]
            print(f"   🎯 Using student ID: {test_student_id}")
            print()
            
            # Show student's portfolio
            portfolio = db.query(StudentSkillPortfolio).filter(
                StudentSkillPortfolio.student_id == test_student_id
            ).all()
            
            print(f"   📚 Student Portfolio ({len(portfolio)} skills):")
            for skill in portfolio:
                print(f"      - {skill.skill_name}: {skill.final_score:.1f}% ({skill.final_level})")
            print()
            
            # Test 4: Generate Recommendations
            print("4️⃣  Testing Job Recommendations...")
            try:
                recommendations = recommend_jobs_ml(
                    db=db,
                    student_id=test_student_id,
                    top_k=5,
                    threshold=50.0,
                    use_verified=True
                )
                
                print(f"   ✅ Generated {len(recommendations)} job recommendations")
                print()
                print("   🎯 Top Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    match_score = rec.get('match_score', 0)
                    print(f"\n   {i}. {rec['title']} at {rec['company']}")
                    print(f"      Match Score: {match_score:.1f}%")
                    print(f"      Role: {rec['role_key']}")
                    if 'skill_gap' in rec:
                        gap = rec['skill_gap']
                        print(f"      Skills: {gap.get('matched', 0)} matched, {gap.get('missing', 0)} missing")
                
                print()
                print("=" * 70)
                print("✅ ALL TESTS PASSED!")
                print("=" * 70)
                
            except Exception as e:
                print(f"   ❌ Failed to generate recommendations: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("   ⚠️  No students with portfolios found in database")
            print("   💡 Create a student portfolio first by:")
            print("      1. Uploading a transcript")
            print("      2. Computing skills")
            print("      3. Taking a quiz")
        
        db.close()
        
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
