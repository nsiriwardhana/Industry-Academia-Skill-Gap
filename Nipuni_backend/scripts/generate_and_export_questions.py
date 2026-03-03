"""
Generate Questions and Export to JSON

Combined CLI script that:
1. Generates questions for specified skills using Ollama
2. Exports the generated questions to JSON file

This is a convenience script for offline quiz generation workflows.

Usage:
    # Generate questions for skills and export
    python scripts/generate_and_export_questions.py --skills SQL Python --count 10

    # Custom output path
    python scripts/generate_and_export_questions.py --skills "Data Structures" --count 15 --out exports/ds_quiz.json

    # Generate without exporting answers (for student quizzes)
    python scripts/generate_and_export_questions.py --skills Python --count 10 --include_answers false

Examples:
    python scripts/generate_and_export_questions.py --skills SQL Python --count 10 --model llama3.1:8b
    python scripts/generate_and_export_questions.py --skills "Machine Learning" --count 20 --format flat
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.db import SessionLocal
from app.models.question_bank import QuestionBank
from app.services import question_bank_service


def main():
    parser = argparse.ArgumentParser(
        description="Generate questions using Ollama and export to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--skills",
        nargs="+",
        required=True,
        help="Skill names to generate questions for (space-separated, required)"
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Questions per difficulty level (default: 10, max: 50)"
    )
    
    parser.add_argument(
        "--model",
        default="llama3.1:8b",
        help="Ollama model to use (default: llama3.1:8b)"
    )
    
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON file path (default: exports/questions_TIMESTAMP.json)"
    )
    
    parser.add_argument(
        "--format",
        choices=["grouped", "flat"],
        default="grouped",
        help="Export format: 'grouped' or 'flat' (default: grouped)"
    )
    
    parser.add_argument(
        "--include_answers",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Include correct answers in export (true|false, default: true)"
    )
    
    parser.add_argument(
        "--include_explanations",
        type=lambda x: x.lower() == "true",
        default=True,
        help="Include explanations in export (true|false, default: true)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it exists"
    )
    
    parser.add_argument(
        "--skip_generation",
        action="store_true",
        help="Skip generation, only export existing questions for these skills"
    )
    
    args = parser.parse_args()
    
    # Validate count
    if args.count < 1 or args.count > 50:
        print("Error: --count must be between 1 and 50")
        sys.exit(1)
    
    # Determine output path
    if args.out:
        out_path = Path(args.out)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = Path("exports") / f"questions_{timestamp}.json"
    
    # Check if output file exists
    if out_path.exists() and not args.force:
        print(f"Error: Output file {out_path} already exists. Use --force to overwrite.")
        sys.exit(1)
    
    # Create output directory
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Connect to database
    db = SessionLocal()
    
    try:
        # Step 1: Generate questions (unless --skip_generation)
        if not args.skip_generation:
            print(f"Generating questions for {len(args.skills)} skill(s)...")
            print(f"  Skills: {', '.join(args.skills)}")
            print(f"  Questions per difficulty: {args.count}")
            print(f"  Model: {args.model}")
            print(f"  Total expected: {len(args.skills) * args.count * 3} questions")
            print()
            
            stats = question_bank_service.generate_bank_for_skills(
                db=db,
                skill_names=args.skills,
                questions_per_difficulty=args.count,
                model_name=args.model
            )
            
            print(f"Generation complete:")
            print(f"  ✓ Generated: {stats['total_generated']}/{stats['total_requested']}")
            print(f"  - Duplicates skipped: {stats['duplicates_skipped']}")
            print(f"  - Errors: {stats['errors']}")
            print()
            
            if stats['errors'] > 0:
                print("Warning: Some questions failed to generate. Check logs for details.")
                print()
        else:
            print("Skipping generation (--skip_generation flag set)")
            print()
        
        # Step 2: Export questions
        print(f"Exporting questions to JSON...")
        
        # Query questions for export
        query = db.query(QuestionBank).filter(
            QuestionBank.skill_name.in_(args.skills)
        ).order_by(
            QuestionBank.skill_name,
            QuestionBank.difficulty,
            QuestionBank.created_at,
            QuestionBank.id
        )
        
        questions = query.all()
        
        if not questions:
            print("No questions found to export.")
            sys.exit(0)
        
        # Build export data
        if args.format == "grouped":
            data = _export_grouped(
                questions,
                args.include_answers,
                args.include_explanations
            )
        else:  # flat
            data = _export_flat(
                questions,
                args.include_answers,
                args.include_explanations
            )
        
        # Write to file
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Export complete:")
        print(f"  File: {out_path}")
        print(f"  Format: {args.format}")
        print(f"  Questions: {len(questions)}")
        print(f"  Skills: {', '.join(args.skills)}")
        print(f"  Answers included: {args.include_answers}")
        print(f"  Explanations included: {args.include_explanations}")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


def _export_grouped(questions: List, include_answers: bool, include_explanations: bool) -> dict:
    """Export in grouped format (by skill and difficulty)."""
    skills_dict = {}
    
    for q in questions:
        if q.skill_name not in skills_dict:
            skills_dict[q.skill_name] = {
                "skill_name": q.skill_name,
                "quizzes": {}
            }
        
        if q.difficulty not in skills_dict[q.skill_name]["quizzes"]:
            skills_dict[q.skill_name]["quizzes"][q.difficulty] = {
                "difficulty": q.difficulty,
                "questions": []
            }
        
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
            "question": q.question_text,
            "options": options_list
        }
        
        if include_answers:
            question_obj["answer"] = q.correct_option
        
        if include_explanations and q.explanation:
            question_obj["explanation"] = q.explanation
        
        question_obj["source"] = "ollama"
        question_obj["model"] = q.model_name
        
        skills_dict[q.skill_name]["quizzes"][q.difficulty]["questions"].append(question_obj)
    
    # Convert to list format
    skills_list = []
    for skill_name, skill_data in skills_dict.items():
        quizzes_list = list(skill_data["quizzes"].values())
        skills_list.append({
            "skill_name": skill_name,
            "quizzes": quizzes_list
        })
    
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_skills": len(skills_list),
        "total_questions": len(questions),
        "skills": skills_list
    }


def _export_flat(questions: List, include_answers: bool, include_explanations: bool) -> list:
    """Export in flat format (simple list)."""
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


if __name__ == "__main__":
    main()
