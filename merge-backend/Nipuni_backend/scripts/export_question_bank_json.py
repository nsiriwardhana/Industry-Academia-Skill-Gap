"""
Export Question Bank to JSON

CLI script to export questions from QuestionBank table to JSON files.

Usage:
    # Export all questions
    python scripts/export_question_bank_json.py

    # Export specific skills
    python scripts/export_question_bank_json.py --skills SQL Python

    # Export with options
    python scripts/export_question_bank_json.py --skills SQL --out exports/sql_quiz.json --format flat

    # Export without answers (for student quizzes)
    python scripts/export_question_bank_json.py --include_answers false

Examples:
    python scripts/export_question_bank_json.py --skills "Data Structures" "Python Programming"
    python scripts/export_question_bank_json.py --out exports/all_questions.json --format grouped
    python scripts/export_question_bank_json.py --skills SQL --include_explanations false
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.db import SessionLocal
from app.models.question_bank import QuestionBank
from sqlalchemy import func


def load_job_skills_categories():
    """Load job skills categories from CSV if available."""
    try:
        import pandas as pd
        csv_path = Path(__file__).parent.parent / "data" / "job_skills.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            return {row['JobSkillID']: row['Category'] for _, row in df.iterrows()}
        return {}
    except Exception:
        return {}


def export_questions_grouped(
    db,
    skill_names: Optional[List[str]] = None,
    include_answers: bool = True,
    include_explanations: bool = True
) -> dict:
    """
    Export questions in grouped format (by skill and difficulty).
    
    Returns:
        Dict with grouped structure
    """
    query = db.query(QuestionBank)
    
    if skill_names:
        query = query.filter(QuestionBank.skill_name.in_(skill_names))
    
    # Order by skill, difficulty, created_at
    query = query.order_by(
        QuestionBank.skill_name,
        QuestionBank.difficulty,
        QuestionBank.created_at,
        QuestionBank.id
    )
    
    questions = query.all()
    
    # Load categories mapping
    categories_map = load_job_skills_categories()
    
    # Group by skill
    skills_dict = {}
    for q in questions:
        if q.skill_name not in skills_dict:
            skills_dict[q.skill_name] = {
                "skill_name": q.skill_name,
                "quizzes": {}
            }
            # Try to add category if skill matches job skill
            if q.skill_name in categories_map:
                skills_dict[q.skill_name]["category"] = categories_map[q.skill_name]
        
        # Group by difficulty within skill
        if q.difficulty not in skills_dict[q.skill_name]["quizzes"]:
            skills_dict[q.skill_name]["quizzes"][q.difficulty] = {
                "difficulty": q.difficulty,
                "questions": []
            }
        
        # Parse options JSON
        try:
            options = json.loads(q.options_json)
            # Convert dict to list if needed
            if isinstance(options, dict):
                options_list = [options.get(k, "") for k in ["A", "B", "C", "D"]]
            else:
                options_list = options
        except:
            options_list = []
        
        # Build question object
        question_obj = {
            "id": q.id,
            "question": q.question_text,
            "options": options_list
        }
        
        if include_answers:
            question_obj["answer"] = q.correct_option
        
        if include_explanations and q.explanation:
            question_obj["explanation"] = q.explanation
        
        # Add optional metadata
        question_obj["source"] = "ollama"
        question_obj["model"] = q.model_name
        
        skills_dict[q.skill_name]["quizzes"][q.difficulty]["questions"].append(question_obj)
    
    # Convert to list format
    skills_list = []
    for skill_name, skill_data in skills_dict.items():
        quizzes_list = list(skill_data["quizzes"].values())
        skill_export = {
            "skill_name": skill_name,
            "quizzes": quizzes_list
        }
        if "category" in skill_data:
            skill_export["category"] = skill_data["category"]
        skills_list.append(skill_export)
    
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_skills": len(skills_list),
        "total_questions": len(questions),
        "skills": skills_list
    }


def export_questions_flat(
    db,
    skill_names: Optional[List[str]] = None,
    include_answers: bool = True,
    include_explanations: bool = True
) -> list:
    """
    Export questions in flat format (list of questions).
    
    Returns:
        List of question dicts
    """
    query = db.query(QuestionBank)
    
    if skill_names:
        query = query.filter(QuestionBank.skill_name.in_(skill_names))
    
    query = query.order_by(
        QuestionBank.skill_name,
        QuestionBank.difficulty,
        QuestionBank.created_at,
        QuestionBank.id
    )
    
    questions = query.all()
    
    flat_list = []
    for q in questions:
        # Parse options JSON
        try:
            options = json.loads(q.options_json)
            if isinstance(options, dict):
                options_list = [options.get(k, "") for k in ["A", "B", "C", "D"]]
            else:
                options_list = options
        except:
            options_list = []
        
        question_obj = {
            "id": q.id,
            "skill_name": q.skill_name,
            "difficulty": q.difficulty,
            "question": q.question_text,
            "options": options_list
        }
        
        if include_answers:
            question_obj["answer"] = q.correct_option
        
        if include_explanations and q.explanation:
            question_obj["explanation"] = q.explanation
        
        question_obj["model"] = q.model_name
        question_obj["created_at"] = q.created_at.isoformat() if q.created_at else None
        
        flat_list.append(question_obj)
    
    return flat_list


def main():
    parser = argparse.ArgumentParser(
        description="Export questions from QuestionBank to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--skills",
        nargs="+",
        help="Skill names to export (space-separated). If omitted, exports all skills."
    )
    
    parser.add_argument(
        "--out",
        default="exports/question_bank_export.json",
        help="Output file path (default: exports/question_bank_export.json)"
    )
    
    parser.add_argument(
        "--format",
        choices=["grouped", "flat"],
        default="grouped",
        help="Export format: 'grouped' (by skill/difficulty) or 'flat' (list)"
    )
    
    parser.add_argument(
        "--include_answers",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Include correct answers (true|false, default: true)"
    )
    
    parser.add_argument(
        "--include_explanations",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Include explanations (true|false, default: true)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it exists"
    )
    
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output (default: compact)"
    )
    
    args = parser.parse_args()
    
    # Check if output file exists
    out_path = Path(args.out)
    if out_path.exists() and not args.force:
        print(f"Error: Output file {args.out} already exists. Use --force to overwrite.")
        sys.exit(1)
    
    # Create output directory if needed
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    db = SessionLocal()
    
    try:
        # Count total questions
        query = db.query(QuestionBank)
        if args.skills:
            query = query.filter(QuestionBank.skill_name.in_(args.skills))
        
        total = query.count()
        
        if total == 0:
            print("No questions found matching the criteria.")
            if args.skills:
                print(f"Requested skills: {', '.join(args.skills)}")
            sys.exit(0)
        
        print(f"Exporting {total} questions...")
        
        # Export based on format
        if args.format == "grouped":
            data = export_questions_grouped(
                db,
                skill_names=args.skills,
                include_answers=args.include_answers,
                include_explanations=args.include_explanations
            )
        else:  # flat
            data = export_questions_flat(
                db,
                skill_names=args.skills,
                include_answers=args.include_answers,
                include_explanations=args.include_explanations
            )
        
        # Write to file
        with open(out_path, "w", encoding="utf-8") as f:
            if args.pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)
        
        print(f"✓ Exported to: {out_path}")
        print(f"  Format: {args.format}")
        print(f"  Questions: {total}")
        if args.skills:
            print(f"  Skills: {', '.join(args.skills)}")
        print(f"  Answers included: {args.include_answers}")
        print(f"  Explanations included: {args.include_explanations}")
        
    finally:
        db.close()


if __name__ == "__main__":
    main()
