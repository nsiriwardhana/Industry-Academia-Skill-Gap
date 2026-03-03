"""
Import Question Bank from JSON

Imports pre-generated questions from JSON file into MySQL question_bank table.
Validates data and prevents duplicates.

This allows teams to share question banks without requiring Ollama on every machine.

Usage:
    cd backend
    python scripts/import_question_bank_json.py

    # Or specify custom file
    python scripts/import_question_bank_json.py --input data/custom_questions.json

    # Skip duplicate check (faster but may create duplicates)
    python scripts/import_question_bank_json.py --skip-duplicate-check

Input Format (Flat):
    [
      {
        "skill_name": "Python Programming",
        "difficulty": "easy",
        "question": "What is...?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "answer": "A",
        "explanation": "Because...",
        "model": "llama3.1:8b",
        "created_at": "2026-03-02T10:30:00" (optional)
      }
    ]

Input Format (Grouped):
    {
      "skills": [
        {
          "skill_name": "Python Programming",
          "quizzes": [
            {
              "difficulty": "easy",
              "questions": [...]
            }
          ]
        }
      ]
    }
"""

import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.db import SessionLocal
from app.models.question_bank import QuestionBank
from sqlalchemy import and_


def generate_question_hash(skill_name: str, difficulty: str, question_text: str) -> str:
    """
    Generate unique hash for a question to detect duplicates.
    
    Args:
        skill_name: Skill name
        difficulty: Difficulty level
        question_text: Question text
        
    Returns:
        SHA256 hash string
    """
    content = f"{skill_name}|{difficulty}|{question_text}".lower().strip()
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


def validate_question(question: Dict[str, Any], index: int) -> tuple[bool, str]:
    """
    Validate a single question object.
    
    Args:
        question: Question dict
        index: Question index for error reporting
        
    Returns:
        (is_valid, error_message)
    """
    # Check required fields
    required_fields = ["skill_name", "difficulty", "question", "options", "answer"]
    
    for field in required_fields:
        if field not in question:
            return False, f"Missing required field: {field}"
    
    # Validate difficulty
    valid_difficulties = ["easy", "medium", "hard"]
    if question["difficulty"].lower() not in valid_difficulties:
        return False, f"Invalid difficulty: {question['difficulty']} (must be easy/medium/hard)"
    
    # Validate options
    options = question["options"]
    
    # Support both list and dict format
    if isinstance(options, dict):
        # Dict format: {"A": "...", "B": "...", "C": "...", "D": "..."}
        required_keys = ["A", "B", "C", "D"]
        if not all(k in options for k in required_keys):
            return False, f"Options dict must have keys A, B, C, D"
    elif isinstance(options, list):
        # List format: ["...", "...", "...", "..."]
        if len(options) != 4:
            return False, f"Options list must have exactly 4 items (has {len(options)})"
    else:
        return False, "Options must be a list or dict"
    
    # Validate answer
    valid_answers = ["A", "B", "C", "D"]
    if question["answer"] not in valid_answers:
        return False, f"Invalid answer: {question['answer']} (must be A, B, C, or D)"
    
    return True, ""


def normalize_question(question: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize question format for database insertion.
    
    Args:
        question: Question dict (raw from JSON)
        
    Returns:
        Normalized question dict
    """
    # Convert options to dict format if it's a list
    options = question["options"]
    if isinstance(options, list):
        options_dict = {
            "A": options[0],
            "B": options[1],
            "C": options[2],
            "D": options[3]
        }
    else:
        options_dict = options
    
    # Normalize difficulty to lowercase
    difficulty = question["difficulty"].lower()
    
    # Map field names (handle both "question" and "question_text")
    question_text = question.get("question") or question.get("question_text", "")
    
    # Get explanation (optional)
    explanation = question.get("explanation", "")
    
    # Get model name (optional, default to "llama3.1:8b")
    model_name = question.get("model") or question.get("model_name", "llama3.1:8b")
    
    # Get created_at (optional, default to now)
    created_at_str = question.get("created_at")
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        except:
            created_at = datetime.utcnow()
    else:
        created_at = datetime.utcnow()
    
    return {
        "skill_name": question["skill_name"],
        "difficulty": difficulty,
        "question_text": question_text,
        "options_json": json.dumps(options_dict),
        "correct_option": question["answer"],
        "explanation": explanation,
        "model_name": model_name,
        "created_at": created_at
    }


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


def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Load questions from JSON file (supports both flat and grouped formats).
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        List of question dicts in flat format
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Detect format
    if isinstance(data, list):
        # Flat format - already a list of questions
        return data
    
    elif isinstance(data, dict) and "skills" in data:
        # Grouped format - need to flatten
        flat_questions = []
        
        for skill_group in data["skills"]:
            skill_name = skill_group["skill_name"]
            
            for quiz in skill_group.get("quizzes", []):
                difficulty = quiz["difficulty"]
                
                for q in quiz.get("questions", []):
                    # Convert to flat format
                    flat_q = {
                        "skill_name": skill_name,
                        "difficulty": difficulty,
                        "question": q.get("question"),
                        "options": q.get("options"),
                        "answer": q.get("answer"),
                        "explanation": q.get("explanation", ""),
                        "model": q.get("model", "llama3.1:8b"),
                        "created_at": q.get("created_at")
                    }
                    flat_questions.append(flat_q)
        
        return flat_questions
    
    else:
        raise ValueError("Unrecognized JSON format. Expected flat list or grouped dict.")


def import_question_bank(
    input_file: str = None,
    skip_duplicate_check: bool = False,
    dry_run: bool = False
):
    """
    Import questions from JSON file into database.
    
    Args:
        input_file: Path to input JSON file
        skip_duplicate_check: Skip duplicate checking (faster but may create duplicates)
        dry_run: Validate only, don't insert into database
        
    Returns:
        Dict with import statistics
    """
    if input_file is None:
        input_file = Path(__file__).parent.parent / "data" / "question_bank_seed.json"
    else:
        input_file = Path(input_file)
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    print(f"📂 Loading questions from: {input_file}")
    
    # Load JSON
    questions = load_json_file(input_file)
    
    print(f"📊 Found {len(questions)} questions in file")
    print()
    
    # Statistics
    stats = {
        "total": len(questions),
        "valid": 0,
        "invalid": 0,
        "duplicates": 0,
        "inserted": 0,
        "errors": []
    }
    
    db = SessionLocal()
    
    try:
        # Validate all questions first
        print("🔍 Validating questions...")
        valid_questions = []
        
        for idx, q in enumerate(questions):
            is_valid, error_msg = validate_question(q, idx)
            
            if not is_valid:
                stats["invalid"] += 1
                stats["errors"].append(f"Question {idx + 1}: {error_msg}")
                print(f"  ❌ Question {idx + 1}: {error_msg}")
            else:
                stats["valid"] += 1
                valid_questions.append(q)
        
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
        
        for idx, q in enumerate(valid_questions):
            # Normalize question format
            normalized = normalize_question(q)
            
            # Check for duplicates (unless skipped)
            if not skip_duplicate_check:
                is_duplicate = check_duplicate(
                    db,
                    normalized["skill_name"],
                    normalized["difficulty"],
                    normalized["question_text"]
                )
                
                if is_duplicate:
                    stats["duplicates"] += 1
                    continue
            
            # Insert into database
            try:
                question_obj = QuestionBank(**normalized)
                db.add(question_obj)
                stats["inserted"] += 1
                
                # Commit in batches of 50
                if stats["inserted"] % 50 == 0:
                    db.commit()
                    print(f"  💾 Inserted {stats['inserted']} questions...")
            
            except Exception as e:
                stats["errors"].append(f"Failed to insert question {idx + 1}: {str(e)}")
                print(f"  ❌ Failed to insert question {idx + 1}: {str(e)}")
        
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
        for q in valid_questions:
            skill = q.get("skill_name", "Unknown")
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
        description="Import questions from JSON into QuestionBank table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        help="Input JSON file path (default: data/question_bank_seed.json)"
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
    print("  QUESTION BANK IMPORTER")
    print("=" * 60)
    print()
    
    try:
        stats = import_question_bank(
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
