"""
Import Questions from CSV using Pandas (handles complex CSV better)

Usage:
    cd Nipuni_backend
    python scripts\\import_questions_pandas.py --input E:\\Integration\\questions.csv
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.db import SessionLocal
from app.models.question_bank import QuestionBank
from sqlalchemy import and_


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


def import_from_csv(input_file: str = None, skip_duplicates: bool = True):
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
        # Read CSV with pandas (better at handling complex formats)
        df = pd.read_csv(input_file, encoding='utf-8')
        
        stats["total"] = len(df)
        print(f"📊 Found {len(df)} questions in file")
        print()
        
        # Validate and import
        print("💾 Importing questions into database...")
        
        for idx, row in df.iterrows():
            try:
                # Validate required fields
                if pd.isna(row.get('skill_name')) or pd.isna(row.get('question_text')):
                    stats["invalid"] += 1
                    stats["errors"].append(f"Row {idx+2}: Missing required fields")
                    continue
                
                # Validate difficulty
                difficulty = str(row.get('difficulty', 'easy')).lower().strip()
                if difficulty not in ['easy', 'medium', 'hard']:
                    difficulty = 'easy'
                
                # Validate correct_option
                correct_option = str(row.get('correct_option', '')).strip()
                if correct_option not in ['A', 'B', 'C', 'D']:
                    stats["invalid"] += 1
                    stats["errors"].append(f"Row {idx+2}: Invalid correct_option '{correct_option}'")
                    continue
                
                # Validate options_json
                options_json = str(row.get('options_json', '')).strip()
                try:
                    options = json.loads(options_json)
                    if not all(key in options for key in ["A", "B", "C", "D"]):
                        stats["invalid"] += 1
                        stats["errors"].append(f"Row {idx+2}: options_json missing required keys")
                        continue
                except json.JSONDecodeError:
                    stats["invalid"] += 1
                    stats["errors"].append(f"Row {idx+2}: Invalid JSON in options_json")
                    continue
                
                stats["valid"] += 1
                
                # Parse created_at
                created_at_str = str(row.get("created_at", ""))
                if created_at_str and created_at_str != 'nan':
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    except:
                        try:
                            created_at = datetime.strptime(created_at_str, "%Y-%m-%d %H:%M:%S")
                        except:
                            created_at = datetime.utcnow()
                else:
                    created_at = datetime.utcnow()
                
                # Check for duplicates
                skill_name = str(row['skill_name']).strip()
                question_text = str(row['question_text']).strip()
                
                if skip_duplicates:
                    is_duplicate = check_duplicate(db, skill_name, difficulty, question_text)
                    if is_duplicate:
                        stats["duplicates"] += 1
                        continue
                
                # Insert into database
                question_obj = QuestionBank(
                    skill_name=skill_name,
                    difficulty=difficulty,
                    question_text=question_text,
                    options_json=options_json,
                    correct_option=correct_option,
                    explanation=str(row.get("explanation", "")).strip(),
                    model_name=str(row.get("model_name", "llama3.1:8b")).strip(),
                    created_at=created_at
                )
                
                db.add(question_obj)
                stats["inserted"] += 1
                
                # Commit in batches of 50
                if stats["inserted"] % 50 == 0:
                    db.commit()
                    print(f"  💾 Inserted {stats['inserted']} questions...")
            
            except Exception as e:
                stats["errors"].append(f"Row {idx+2}: {str(e)}")
                print(f"  ❌ Row {idx+2}: {str(e)}")
        
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
        skill_counts = df.groupby('skill_name').size().to_dict() if 'skill_name' in df.columns else {}
        
        for skill, count in sorted(skill_counts.items()):
            print(f"   {skill}: {count} questions")
        
        return stats
    
    except Exception as e:
        db.rollback()
        print(f"❌ Error during import: {e}")
        raise
    
    finally:
        db.close()