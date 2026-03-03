"""
Script to build skill hierarchy graph files from the wide course-skill mapping CSV.

Reads: backend/data/course_skill_mapping.csv
Outputs:
  - backend/data/skill_group_map.csv (child_skill -> parent_skill mappings)
  - backend/data/parent_skills_unique.csv (unique MainSkill values)
  - backend/data/child_skills_unique.csv (unique child skill values)
"""

import pandas as pd
from pathlib import Path


def main():
    # Resolve paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    
    input_file = data_dir / "course_skill_mapping.csv"
    output_skill_group_map = data_dir / "skill_group_map.csv"
    output_parent_skills = data_dir / "parent_skills_unique.csv"
    output_child_skills = data_dir / "child_skills_unique.csv"
    
    print(f"Reading input file: {input_file}")
    
    # Read the wide CSV with encoding handling
    try:
        df = pd.read_csv(input_file, encoding='utf-8')
    except UnicodeDecodeError:
        print("UTF-8 encoding failed, trying latin-1...")
        df = pd.read_csv(input_file, encoding='latin-1')
    
    print(f"Total rows in input: {len(df)}")
    
    # Drop duplicate CourseCode rows, keeping first occurrence
    original_count = len(df)
    df = df.drop_duplicates(subset=['CourseCode'], keep='first')
    duplicates_dropped = original_count - len(df)
    if duplicates_dropped > 0:
        print(f"Dropped {duplicates_dropped} duplicate CourseCode rows (kept first occurrence)")
    
    # Build skill_group_map
    skill_mappings = []
    
    for _, row in df.iterrows():
        main_skill = str(row['MainSkill']).strip() if pd.notna(row['MainSkill']) else None
        
        # Skip if no main skill
        if not main_skill:
            continue
        
        # Process Skill1 through Skill5
        for i in range(1, 6):
            skill_col = f'Skill{i}'
            if skill_col in row:
                child_skill = str(row[skill_col]).strip() if pd.notna(row[skill_col]) else None
                
                # Only add if child skill is not empty
                if child_skill:
                    skill_mappings.append({
                        'child_skill': child_skill,
                        'parent_skill': main_skill
                    })
    
    # Create DataFrame and drop duplicates
    skill_group_df = pd.DataFrame(skill_mappings)
    
    if len(skill_group_df) > 0:
        original_mappings = len(skill_group_df)
        skill_group_df = skill_group_df.drop_duplicates()
        duplicates_removed = original_mappings - len(skill_group_df)
        
        print(f"\nSkill Group Mappings:")
        print(f"  Total mappings created: {original_mappings}")
        print(f"  Duplicates removed: {duplicates_removed}")
        print(f"  Final unique mappings: {len(skill_group_df)}")
        
        # Save skill_group_map.csv
        skill_group_df.to_csv(output_skill_group_map, index=False)
        print(f"  Saved to: {output_skill_group_map}")
    else:
        print("\nWarning: No skill group mappings generated")
    
    # Extract unique parent skills (MainSkill values)
    parent_skills = df['MainSkill'].dropna().str.strip()
    parent_skills = parent_skills[parent_skills != '']  # Remove empty strings
    parent_skills = parent_skills.unique()
    parent_skills_df = pd.DataFrame({'parent_skill': sorted(parent_skills)})
    
    print(f"\nParent Skills (MainSkill):")
    print(f"  Unique parent skills: {len(parent_skills_df)}")
    parent_skills_df.to_csv(output_parent_skills, index=False)
    print(f"  Saved to: {output_parent_skills}")
    
    # Extract unique child skills (Skill1-5 values)
    child_skills_list = []
    for i in range(1, 6):
        skill_col = f'Skill{i}'
        if skill_col in df.columns:
            skills = df[skill_col].dropna().str.strip()
            skills = skills[skills != '']  # Remove empty strings
            child_skills_list.extend(skills.tolist())
    
    child_skills = pd.Series(child_skills_list).unique()
    child_skills_df = pd.DataFrame({'child_skill': sorted(child_skills)})
    
    print(f"\nChild Skills (Skill1-5):")
    print(f"  Unique child skills: {len(child_skills_df)}")
    child_skills_df.to_csv(output_child_skills, index=False)
    print(f"  Saved to: {output_child_skills}")
    
    print("\n✓ All files generated successfully!")


if __name__ == "__main__":
    main()
