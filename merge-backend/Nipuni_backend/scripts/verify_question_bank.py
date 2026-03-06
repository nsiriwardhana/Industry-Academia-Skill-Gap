"""
Verify Question Bank Setup

Quick script to verify question bank is properly set up and populated.

Usage:
    cd backend
    python scripts/verify_question_bank.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.db import SessionLocal
from app.models.question_bank import QuestionBank
from sqlalchemy import func


def verify_question_bank():
    """
    Verify question bank is properly populated.
    
    Returns:
        True if verification passes, False otherwise
    """
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("  QUESTION BANK VERIFICATION")
        print("=" * 60)
        print()
        
        # Check total count
        total = db.query(QuestionBank).count()
        
        if total == 0:
            print("❌ FAILED: No questions found in question_bank table")
            print()
            print("To fix this, run:")
            print("  python scripts/import_question_bank_json.py")
            print()
            return False
        
        print(f"✅ Total questions: {total}")
        print()
        
        # Check breakdown by skill and difficulty
        results = db.query(
            QuestionBank.skill_name,
            QuestionBank.difficulty,
            func.count(QuestionBank.id).label('count')
        ).group_by(
            QuestionBank.skill_name,
            QuestionBank.difficulty
        ).order_by(
            QuestionBank.skill_name,
            QuestionBank.difficulty
        ).all()
        
        print("📊 Breakdown by Skill and Difficulty:")
        print()
        
        skill_totals = {}
        min_questions_per_group = float('inf')
        issues = []
        
        for skill, diff, count in results:
            skill_totals[skill] = skill_totals.get(skill, 0) + count
            min_questions_per_group = min(min_questions_per_group, count)
            
            # Visual indicator
            if count >= 10:
                icon = "✅"
            elif count >= 5:
                icon = "⚠️"
            else:
                icon = "❌"
                issues.append(f"{skill} ({diff}): Only {count} questions")
            
            print(f"  {icon} {skill:<30} {diff:<10} {count:>3} questions")
        
        print()
        print(f"📈 Total skills: {len(skill_totals)}")
        print()
        
        # Show skill totals
        print("📋 Questions per skill:")
        for skill, count in sorted(skill_totals.items()):
            print(f"   {skill}: {count} questions")
        
        print()
        
        # Check for issues
        if issues:
            print("⚠️  Warning: Some skills have fewer questions:")
            for issue in issues:
                print(f"   - {issue}")
            print()
            print("Recommendation: Generate more questions for these skills")
            print()
        
        # Check minimum recommended counts
        if min_questions_per_group < 5:
            print("❌ FAILED: Some skill/difficulty groups have < 5 questions")
            print("   Minimum for production: 5 questions per group")
            print("   Recommended: 10+ questions per group")
            print()
            return False
        elif min_questions_per_group < 10:
            print("⚠️  WARNING: Some groups have < 10 questions")
            print("   Current minimum: 5 questions per group")
            print("   Recommended: 10+ questions per group")
            print()
        else:
            print("✅ All skill/difficulty groups have adequate questions (10+)")
            print()
        
        # Check for missing difficulties
        missing_difficulties = []
        for skill in skill_totals.keys():
            skill_difficulties = [
                diff for s, diff, _ in results if s == skill
            ]
            for required_diff in ["easy", "medium", "hard"]:
                if required_diff not in skill_difficulties:
                    missing_difficulties.append(f"{skill} is missing {required_diff} questions")
        
        if missing_difficulties:
            print("❌ FAILED: Missing difficulties:")
            for miss in missing_difficulties:
                print(f"   - {miss}")
            print()
            return False
        
        print("✅ All skills have questions for all difficulty levels (easy, medium, hard)")
        print()
        
        # Sample a few questions to verify format
        sample_questions = db.query(QuestionBank).limit(3).all()
        
        print("🔍 Sample questions (format check):")
        print()
        
        for idx, q in enumerate(sample_questions, 1):
            import json
            
            try:
                options = json.loads(q.options_json) if isinstance(q.options_json, str) else q.options_json
                
                print(f"  Question {idx}:")
                print(f"    Skill: {q.skill_name}")
                print(f"    Difficulty: {q.difficulty}")
                print(f"    Question: {q.question_text[:60]}...")
                print(f"    Options: {len(options)} choices")
                print(f"    Answer: {q.correct_option}")
                print(f"    Explanation: {'✅ Yes' if q.explanation else '❌ No'}")
                print()
            except Exception as e:
                print(f"  ❌ Question {idx}: Invalid format - {e}")
                print()
                return False
        
        print("=" * 60)
        print("✅ VERIFICATION PASSED")
        print("=" * 60)
        print()
        print("Your question bank is ready to use!")
        print("Students can now generate quizzes using: POST /quiz/from-bank")
        print()
        
        return True
    
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        db.close()


if __name__ == "__main__":
    success = verify_question_bank()
    sys.exit(0 if success else 1)
