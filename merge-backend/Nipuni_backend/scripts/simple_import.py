"""
Simple direct import of questions from CSV to database
"""
import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.db import SessionLocal
from app.models.question_bank import QuestionBank

def main():
    csv_file = r"E:\Integration\questions.csv"
    
    print(f"Reading CSV: {csv_file}")
    
    # Read CSV with pandas
    df = pd.read_csv(csv_file, encoding='utf-8')
    
    print(f"Found {len(df)} questions")
    print(f"Columns: {list(df.columns)}")
    
    db = SessionLocal()
    
    inserted = 0
    errors = 0
    
    try:
        for idx, row in df.iterrows():
            try:
                # Skip if required fields are missing
                if pd.isna(row['skill_name']) or pd.isna(row['question_text']) or pd.isna(row['correct_option']):
                    print(f"Row {idx+2}: Skipping - missing required fields")
                    errors += 1
                    continue
                
                # Get correct_option and validate
                correct_option = str(row['correct_option']).strip()
                if correct_option not in ['A', 'B', 'C', 'D']:
                    print(f"Row {idx+2}: Skipping - invalid correct_option '{correct_option}'")
                    errors += 1
                    continue
                
                # Parse created_at
                try:
                    created_at = datetime.strptime(str(row['created_at']), "%Y-%m-%d %H:%M:%S")
                except:
                    created_at = datetime.utcnow()
                
                # Create question object
                question = QuestionBank(
                    skill_name=str(row['skill_name']).strip(),
                    difficulty=str(row['difficulty']).lower().strip(),
                    question_text=str(row['question_text']).strip(),
                    options_json=str(row['options_json']).strip(),
                    correct_option=correct_option,
                    explanation=str(row.get('explanation', '')).strip(),
                    model_name=str(row.get('model_name', 'llama3.1:8b')).strip(),
                    created_at=created_at
                )
                
                db.add(question)
                inserted += 1
                
                if inserted % 10 == 0:
                    print(f"Inserted {inserted} questions...")
                    db.commit()
            
            except Exception as e:
                print(f"Row {idx+2}: Error - {e}")
                errors += 1
                continue
        
        # Final commit
        db.commit()
        
        print(f"\n✅ Import complete!")
        print(f"   Successfully inserted: {inserted}")
        print(f"   Errors: {errors}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
