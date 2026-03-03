"""
Export Question Bank to CSV

Exports all questions from MySQL question_bank table to CSV file.
Alternative to JSON export for use with Excel/spreadsheet tools.

Usage:
    cd backend
    python scripts/export_question_bank_csv.py

    # Or specify custom output
    python scripts/export_question_bank_csv.py --output data/questions.csv

Output CSV Format:
    skill_name,difficulty,question_text,option_A,option_B,option_C,option_D,correct_option,explanation,model_name,created_at
"""

import sys
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.db import SessionLocal
from app.models.question_bank import QuestionBank


def export_to_csv(output_file: str = None):
    """
    Export all questions to CSV file.
    
    Args:
        output_file: Path to output CSV file
        
    Returns:
        Dict with export statistics
    """
    if output_file is None:
        output_file = Path(__file__).parent.parent / "data" / "question_bank_seed.csv"
    else:
        output_file = Path(output_file)
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    db = SessionLocal()
    
    try:
        # Query all questions
        questions = db.query(QuestionBank).order_by(
            QuestionBank.skill_name,
            QuestionBank.difficulty,
            QuestionBank.id
        ).all()
        
        if not questions:
            print("⚠️  Warning: No questions found in question_bank table")
            return {"exported": 0, "file": str(output_file)}
        
        # CSV fieldnames
        fieldnames = [
            "skill_name",
            "difficulty",
            "question_text",
            "option_A",
            "option_B",
            "option_C",
            "option_D",
            "correct_option",
            "explanation",
            "model_name",
            "created_at"
        ]
        
        # Write to CSV
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for q in questions:
                # Parse options JSON
                if isinstance(q.options_json, str):
                    options = json.loads(q.options_json)
                else:
                    options = q.options_json
                
                # Write row
                writer.writerow({
                    "skill_name": q.skill_name,
                    "difficulty": q.difficulty,
                    "question_text": q.question_text,
                    "option_A": options.get("A", ""),
                    "option_B": options.get("B", ""),
                    "option_C": options.get("C", ""),
                    "option_D": options.get("D", ""),
                    "correct_option": q.correct_option,
                    "explanation": q.explanation or "",
                    "model_name": q.model_name or "",
                    "created_at": q.created_at.isoformat() if q.created_at else ""
                })
        
        # Group by skill and difficulty for statistics
        stats = {}
        for q in questions:
            key = f"{q.skill_name} ({q.difficulty})"
            stats[key] = stats.get(key, 0) + 1
        
        # Print summary
        print("✅ Question Bank CSV Export Complete")
        print(f"📁 File: {output_file}")
        print(f"📊 Total Questions: {len(questions)}")
        print()
        print("📈 Breakdown by Skill and Difficulty:")
        for key, count in sorted(stats.items()):
            print(f"   {key}: {count} questions")
        
        return {
            "exported": len(questions),
            "file": str(output_file),
            "breakdown": stats
        }
    
    except Exception as e:
        print(f"❌ Error during export: {e}")
        raise
    
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Export question bank to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output CSV file path (default: data/question_bank_seed.csv)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  QUESTION BANK CSV EXPORTER")
    print("=" * 60)
    print()
    print("🔄 Exporting Question Bank from MySQL to CSV...")
    print()
    
    result = export_to_csv(output_file=args.output)
    
    print()
    print("=" * 60)
    print("✨ Export successful!")
    print("=" * 60)
    print()
    print("💡 Tip: You can open this CSV in Excel or import it using:")
    print("   python scripts/import_question_bank_csv.py")


if __name__ == "__main__":
    main()
