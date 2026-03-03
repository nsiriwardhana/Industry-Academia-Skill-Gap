"""
Import Questions from CSV with options_json format

Imports questions from CSV file (with options_json column) into MySQL question_bank table.

Usage:
    cd Nipuni_backend
    python scripts\\import_questions_from_csv.py
    
    # Or specify custom file
    python scripts\\import_questions_from_csv.py --input E:\\Integration\\questions.csv
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


def parse_csv_manually(file_path: Path) -> list:
    """
    Manually parse CSV to handle nested JSON with commas.
    """
    rows = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Get header
    header = lines[0].strip().split(',')
    
    # Expected columns
    expected_cols = ['id', 'skill_name', 'difficulty', 'question_text', 
                     'options_json', 'correct_option', 'explanation', 
                     'model_name', 'created_at']
    
    for line_num, line in enumerate(lines[1:], start=2):
        line = line.strip()
        if not line:
            continue
        
        # Split carefully handling quoted fields with commas
        parts = []
        current = []
        in_quotes = False
        in_json = False
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
                current.append(char)
            elif char == '{' and in_quotes:
                in_json = True
                current.append(char)
            elif char == '}' and in_quotes and in_json:
                in_json = False
                current.append(char)
            elif char == ',' and not in_quotes:
                parts.append(''.join(current))
                current = []
            else:
                current.append(char)
        
        if current:
            parts.append(''.join(current))
        
        # Clean up parts
        cleaned_parts = []
        for part in parts:
            part = part.strip()
            # Remove outer quotes
            if part.startswith('"') and part.endswith('"'):
                part = part[1:-1]
            cleaned_parts.append(part)
        
        # Create row dict
        if len(cleaned_parts) >= len(expected_cols):
            row_dict = {}
            for i, col in enumerate(expected_cols):
                if i < len(cleaned_parts):
                    row_dict[col] = cleaned_parts[i]
            rows.append(row_dict)
        else:
            print(f"⚠️  Warning: Row {line_num} has {len(cleaned_parts)} parts, expected {len(expected_cols)}")
    
    return rows


def validate_row(row: dict, row_num: int) -> tuple[bool, str]:
    """Validate a CSV row."""
    
    # Check required fields
    required_fields = ["skill_name", "difficulty", "question_text", "options_json", "correct_option"]
    
    for field in required_fields:
        if field not in row or not row[field].strip():
            return False, f"Missing or empty required field: {field}"
    
    # Validate difficulty
    valid_difficulties = ["easy", "medium", "hard"]
    if row["difficulty"].lower() not in valid_difficulties:
        return False, f"Invalid difficulty: {row['difficulty']} (must be easy/medium/hard)"
    
    # Validate correct_option
    valid_answers = ["A", "B", "C", "D"]
    if row["correct_option"].strip() not in valid_answers:
        return False, f"Invalid correct_option: {row['correct_option']} (must be A, B, C, or D)"
    
    # Validate options_json is valid JSON
    try:
        options = json.loads(row["options_json"])
        if not all(key in options for key in ["A", "B", "C", "D"]):
            return False, "options_json must contain keys A, B, C, and D"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in options_json: {e}"
    
    return True, ""


def check_duplicate(db, skill_name: str, difficulty: str, question_text: str) -> bool:
    """Check if a question already exists in database."""
    
    existing = db.query(QuestionBank).filter(
        and_(
            QuestionBank.skill_name == skill_name,
            QuestionBank.difficulty == difficulty,
            QuestionBank.question_text == question_text
        )
    ).first()
    
    return existing is not None


def import_from_csv(input_file: str = None, skip_duplicates: bool = True, dry_run: bool = False):
    """Import questions from CSV file into database."""
    
    if input_file is None:
        input_file = Path(__file__).parent.parent.parent / "questions.csv"
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
        # Read CSV with manual parser to handle nested JSON
        rows = parse_csv_manually(input_file)
        
        stats["total"] = len(rows)
        print(f"📊 Found {len(rows)} questions in file")
        print()
        
        # Validate all rows first
        print("🔍 Validating questions...")
        valid_rows = []
        
        for idx, row in enumerate(rows, start=2):  # Start at 2 (header is row 1)
            is_valid, error_msg = validate_row(row, idx)
            
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
                    # Handle various datetime formats
                    created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                except:
                    try:
                        created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
                    except:
                        created_at = datetime.utcnow()
            else:
                created_at = datetime.utcnow()
            
            # Normalize difficulty
            difficulty = row["difficulty"].lower()
            
            # Check for duplicates
            if skip_duplicates:
                is_duplicate = check_duplicate(
                    db,
                    row["skill_name"].strip(),
                    difficulty,
                    row["question_text"].strip()
                )
                
                if is_duplicate:
                    stats["duplicates"] += 1
                    continue
            
            # Insert into database
            try:
                question_obj = QuestionBank(
                    skill_name=row["skill_name"].strip(),
                    difficulty=difficulty,
                    question_text=row["question_text"].strip(),
                    options_json=row["options_json"].strip(),
                    correct_option=row["correct_option"].strip(),
                    explanation=row.get("explanation", "").strip(),
                    model_name=row.get("model_name", "llama3.1:8b").strip(),
                    created_at=created_at
                )
                
                db.add(question_obj)
                stats["inserted"] += 1
                
                # Commit in batches of 50
                if stats["inserted"] % 50 == 0:
                    db.commit()
                    print(f"  💾 Inserted {stats['inserted']} questions...")
            
            except Exception as e:
                stats["errors"].append(f"Failed to insert question {idx}: {str(e)}")
                print(f"  ❌ Failed to insert question {idx}: {str(e)}")
        
        # Final commit
        db.commit()
        
        print()
        print("✅ Import complete!")
        print()
        print("📊 Summary:")
        print(f"   Total questions in file: {stats['total']}")
        print(f"   Valid questions: {stats['valid']}")
        print(f"   Invalid questions: {stats['invalid']}")
        if skip_duplicates:
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
        description="Import questions from CSV (with options_json) into QuestionBank table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="Input CSV file path (default: E:\\Integration\\questions.csv)"
    )
    
    parser.add_argument(
        "--no-skip-duplicates",
        action="store_true",
        help="Don't skip duplicate questions (may create duplicates)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate questions only, don't insert into database"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  QUESTION BANK CSV IMPORTER (options_json format)")
    print("=" * 60)
    print()
    
    try:
        stats = import_from_csv(
            input_file=args.input,
            skip_duplicates=not args.no_skip_duplicates,
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
