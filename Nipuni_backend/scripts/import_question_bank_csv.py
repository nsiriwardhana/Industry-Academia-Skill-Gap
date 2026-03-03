"""
Import Question Bank from CSV

Imports pre-generated questions from CSV file into MySQL question_bank table.
Validates data and prevents duplicates.

Usage:
    cd backend
    python scripts/import_question_bank_csv.py

    # Or specify custom file
    python scripts/import_question_bank_csv.py --input data/custom_questions.csv

CSV Format:
    skill_name,difficulty,question_text,option_A,option_B,option_C,option_D,correct_option,explanation,model_name,created_at
    Python Programming,easy,"What is...?","Answer A","Answer B","Answer C","Answer D",A,"Because...",llama3.1:8b,2026-03-02T10:30:00
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
from sqlalchemy import and_


def validate_csv_row(row: dict, row_num: int) -> tuple[bool, str]:
    """
    Validate a CSV row.
    
    Args:
        row: CSV row as dict
        row_num: Row number for error reporting
        
    Returns:
        (is_valid, error_message)
    """
    # Check required fields
    required_fields = [
        "skill_name", "difficulty", "question_text",
        "option_A", "option_B", "option_C", "option_D",
        "correct_option"
    ]
    
    for field in required_fields:
        if field not in row or not row[field].strip():
            return False, f"Missing or empty required field: {field}"
    
    # Validate difficulty
    valid_difficulties = ["easy", "medium", "hard"]
    if row["difficulty"].lower() not in valid_difficulties:
        return False, f"Invalid difficulty: {row['difficulty']} (must be easy/medium/hard)"
    
    # Validate correct_option
    valid_answers = ["A", "B", "C", "D"]
    if row["correct_option"] not in valid_answers:
        return False, f"Invalid correct_option: {row['correct_option']} (must be A, B, C, or D)"
    
    # Validate all options are non-empty
    for opt in ["option_A", "option_B", "option_C", "option_D"]:
        if not row[opt].strip():
            return False, f"Empty option: {opt}"
    
    return True, ""


def check_duplicate(db, skill_name: str, difficulty: str, question_text: str) -> bool:
    """
    Check if a question already exists in database.
    
    Args:
        db: Database session
        skill_name: Skill name
        difficulty: Difficulty level
        question_text: Question text
        
    Returns:
        True if duplicate exists, False otherwise
    """
    existing = db.query(QuestionBank).filter(
        and_(
            QuestionBank.skill_name == skill_name,
            QuestionBank.difficulty == difficulty,
            QuestionBank.question_text == question_text
        )
    ).first()
    
    return existing is not None


def import_from_csv(
    input_file: str = None,
    skip_duplicate_check: bool = False,
    dry_run: bool = False
):
    """
    Import questions from CSV file into database.
    
    Args:
        input_file: Path to input CSV file
        skip_duplicate_check: Skip duplicate checking (faster but may create duplicates)
        dry_run: Validate only, don't insert into database
        
    Returns:
        Dict with import statistics
    """
    if input_file is None:
        input_file = Path(__file__).parent.parent / "data" / "question_bank_seed.csv"
    else:
        input_file = Path(input_file)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    print(f"📂 Loading questions from: {input_file}")
    
    # Statistics
    stats = {
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "duplicates": 0,
        "inserted": 0,
        "errors": []
    }
    
    db = SessionLocal()
    
    try:
        # Read CSV
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        stats["total"] = len(rows)
        print(f"📊 Found {len(rows)} questions in file")
        print()
        
        # Validate all rows first
        print("🔍 Validating questions...")
        valid_rows = []
        
        for idx, row in enumerate(rows, start=2):  # Start at 2 (header is row 1)
            is_valid, error_msg = validate_csv_row(row, idx)
            
            if not is_valid:
                stats["invalid"] += 1
                stats["errors"].append(f"Row {idx}: {error_msg}")
                print(f"  ❌ Row {idx}: {error_msg}")
            else:
                stats["valid"] += 1
                valid_rows.append(row)
        
        print(f"✅ Validation complete: {stats['valid']} valid, {stats['invalid']} invalid")
        print()
        
        if stats["invalid"] > 0:
            print(f"⚠️  {stats['invalid']} invalid questions will be skipped")
            print()
        
        if dry_run:
            print("🔵 Dry run mode - no database changes will be made")
            return stats
        
        # Import valid questions
        print("💾 Importing questions into database...")
        
        for idx, row in enumerate(valid_rows, start=1):
            # Parse created_at
            created_at_str = row.get("created_at", "")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                except:
                    created_at = datetime.utcnow()
            else:
                created_at = datetime.utcnow()
            
            # Build options JSON
            options_json = json.dumps({
                "A": row["option_A"],
                "B": row["option_B"],
                "C": row["option_C"],
                "D": row["option_D"]
            })
            
            # Normalize difficulty
            difficulty = row["difficulty"].lower()
            
            # Check for duplicates (unless skipped)
            if not skip_duplicate_check:
                is_duplicate = check_duplicate(
                    db,
                    row["skill_name"],
                    difficulty,
                    row["question_text"]
                )
                
                if is_duplicate:
                    stats["duplicates"] += 1
                    continue
            
            # Insert into database
            try:
                question_obj = QuestionBank(
                    skill_name=row["skill_name"],
                    difficulty=difficulty,
                    question_text=row["question_text"],
                    options_json=options_json,
                    correct_option=row["correct_option"],
                    explanation=row.get("explanation", ""),
                    model_name=row.get("model_name", "llama3.1:8b"),
                    created_at=created_at
                )
                
                db.add(question_obj)
                stats["inserted"] += 1
                
                # Commit in batches of 50
                if stats["inserted"] % 50 == 0:
                    db.commit()
                    print(f"  💾 Inserted {stats['inserted']} questions...")
            
            except Exception as e:
                stats["errors"].append(f"Failed to insert row {idx}: {str(e)}")
                print(f"  ❌ Failed to insert row {idx}: {str(e)}")
        
        # Final commit
        db.commit()
        
        print()
        print("✅ Import complete!")
        print()
        print("📊 Summary:")
        print(f"   Total questions in file: {stats['total']}")
        print(f"   Valid questions: {stats['valid']}")
        print(f"   Invalid questions: {stats['invalid']}")
        if not skip_duplicate_check:
            print(f"   Duplicates skipped: {stats['duplicates']}")
        print(f"   Successfully inserted: {stats['inserted']}")
        
        if stats["errors"]:
            print()
            print(f"⚠️  {len(stats['errors'])} errors occurred:")
            for error in stats["errors"][:10]:  # Show first 10 errors
                print(f"   - {error}")
            if len(stats["errors"]) > 10:
                print(f"   ... and {len(stats['errors']) - 10} more errors")
        
        # Show breakdown by skill
        print()
        print("📈 Questions by skill:")
        skill_counts = {}
        for row in valid_rows:
            skill = row.get("skill_name", "Unknown")
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        for skill, count in sorted(skill_counts.items()):
            print(f"   {skill}: {count} questions")
        
        return stats
    
    except Exception as e:
        db.rollback()
        print(f"❌ Error during import: {e}")
        raise
    
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import questions from CSV into QuestionBank table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="Input CSV file path (default: data/question_bank_seed.csv)"
    )
    
    parser.add_argument(
        "--skip-duplicate-check",
        action="store_true",
        help="Skip duplicate checking (faster but may create duplicates)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate questions only, don't insert into database"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  QUESTION BANK CSV IMPORTER")
    print("=" * 60)
    print()
    
    try:
        stats = import_from_csv(
            input_file=args.input,
            skip_duplicate_check=args.skip_duplicate_check,
            dry_run=args.dry_run
        )
        
        print()
        print("=" * 60)
        print("✨ Import process completed successfully!")
        print("=" * 60)
        
        # Exit with non-zero if there were errors
        if stats["errors"]:
            sys.exit(1)
    
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
