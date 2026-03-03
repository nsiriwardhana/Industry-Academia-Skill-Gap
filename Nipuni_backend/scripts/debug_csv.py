"""Quick debug script to check CSV parsing"""
import csv

csv_file = r"E:\Integration\questions.csv"

with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i < 3:  # Print first 3 rows
            print(f"\n=== Row {i+1} ===")
            print(f"Columns: {list(row.keys())}")
            print(f"skill_name: {repr(row.get('skill_name', 'MISSING'))}")
            print(f"correct_option: {repr(row.get('correct_option', 'MISSING'))}")
            print(f"correct_option length: {len(row.get('correct_option', ''))}")
        else:
            break
