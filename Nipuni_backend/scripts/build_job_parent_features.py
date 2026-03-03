"""
Build job-level parent skill features for ML training.

Reads job data, maps raw job skills to parent skills, and creates
a binary feature matrix where each column represents a parent skill category.

Inputs:
  - backend/data/Job_data.csv
  - backend/data/job_skill_to_parent_skill.csv
  - backend/data/parent_skills_unique.csv (or skill_group_map.csv)

Output:
  - backend/data/job_parent_skill_features.csv

Run from backend root:
  python scripts/build_job_parent_features.py
"""

import pandas as pd
from pathlib import Path
from collections import Counter
import sys

# Paths
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent  # backend/
DATA_DIR = BASE_DIR / "data"

JOB_DATA = DATA_DIR / "Job_data.csv"
SKILL_MAPPING = DATA_DIR / "job_skill_to_parent_skill.csv"
PARENT_SKILLS_FILE = DATA_DIR / "parent_skills_unique.csv"
SKILL_GROUP_MAP = DATA_DIR / "skill_group_map.csv"
OUTPUT_FILE = DATA_DIR / "job_parent_skill_features.csv"


def normalize_skill(skill: str) -> str:
    """Normalize a skill name: lowercase and strip whitespace."""
    return skill.strip().lower()


def load_parent_skills():
    """Load the list of parent skills."""
    if PARENT_SKILLS_FILE.exists():
        print(f"📂 Loading parent skills from {PARENT_SKILLS_FILE.name}")
        df = pd.read_csv(PARENT_SKILLS_FILE)
        # Assume column is 'parent_skill' or first column
        col = 'parent_skill' if 'parent_skill' in df.columns else df.columns[0]
        return sorted(df[col].unique().tolist())
    elif SKILL_GROUP_MAP.exists():
        print(f"📂 Loading parent skills from {SKILL_GROUP_MAP.name}")
        df = pd.read_csv(SKILL_GROUP_MAP)
        # Assume it has a 'parent_skill' column
        col = 'parent_skill' if 'parent_skill' in df.columns else df.columns[1]
        return sorted(df[col].unique().tolist())
    else:
        print("⚠️  No parent skills file found. Using defaults from mapping file.")
        return []


def main():
    print("=" * 70)
    print("🚀 Building Job Parent Skill Features")
    print("=" * 70)
    print()
    
    # 1. Load job data
    print(f"📂 Loading job data from {JOB_DATA.name}")
    if not JOB_DATA.exists():
        print(f"❌ Error: {JOB_DATA} not found!")
        sys.exit(1)
    
    jobs_df = pd.read_csv(JOB_DATA)
    print(f"   Loaded {len(jobs_df):,} jobs")
    print()
    
    # 2. Load skill to parent skill mapping
    print(f"📂 Loading skill mapping from {SKILL_MAPPING.name}")
    if not SKILL_MAPPING.exists():
        print(f"❌ Error: {SKILL_MAPPING} not found!")
        sys.exit(1)
    
    mapping_df = pd.read_csv(SKILL_MAPPING)
    skill_to_parent = dict(zip(
        mapping_df['job_skill_normalized'].str.lower().str.strip(),
        mapping_df['parent_skill']
    ))
    print(f"   Loaded {len(skill_to_parent):,} skill mappings")
    print()
    
    # 3. Load parent skills list
    parent_skills = load_parent_skills()
    if not parent_skills:
        # Derive from mapping file
        parent_skills = sorted(mapping_df['parent_skill'].unique().tolist())
    
    print(f"📊 Found {len(parent_skills)} parent skill categories:")
    for i, ps in enumerate(parent_skills, 1):
        print(f"   {i:2d}. {ps}")
    print()
    
    # 4. Initialize feature matrix
    print("🔨 Building feature matrix...")
    
    # Start with base columns
    feature_df = jobs_df[['job_id', 'title', 'company', 'role_key']].copy()
    
    # Initialize parent skill columns to 0
    for ps in parent_skills:
        feature_df[ps] = 0
    
    # Track unmapped skills
    unmapped_skills = []
    jobs_with_mappings = 0
    
    # 5. Process each job
    for idx, row in jobs_df.iterrows():
        job_id = row['job_id']
        skills_str = row.get('skills', '')
        
        if pd.isna(skills_str) or not skills_str:
            continue
        
        # Split and normalize skills
        job_skills = [normalize_skill(s) for s in str(skills_str).split('|')]
        
        # Map to parent skills
        mapped_parents = set()
        for skill in job_skills:
            if skill in skill_to_parent:
                parent = skill_to_parent[skill]
                mapped_parents.add(parent)
            else:
                unmapped_skills.append(skill)
        
        # Set binary features
        if mapped_parents:
            jobs_with_mappings += 1
            for parent in mapped_parents:
                if parent in parent_skills:
                    feature_df.loc[idx, parent] = 1
    
    print(f"   ✅ Processed {len(jobs_df):,} jobs")
    print()
    
    # 6. Save output
    print(f"💾 Saving to {OUTPUT_FILE.name}")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_csv(OUTPUT_FILE, index=False)
    print(f"   ✅ Saved {len(feature_df):,} rows × {len(feature_df.columns)} columns")
    print()
    
    # 7. Print statistics
    print("=" * 70)
    print("📈 COVERAGE STATISTICS")
    print("=" * 70)
    print()
    
    print(f"Total Jobs:              {len(jobs_df):,}")
    print(f"Jobs with Mappings:      {jobs_with_mappings:,}")
    coverage_pct = (jobs_with_mappings / len(jobs_df)) * 100 if len(jobs_df) > 0 else 0
    print(f"Coverage:                {coverage_pct:.1f}%")
    print()
    
    # Top 10 parent skills by job count
    print("🏆 Top 10 Parent Skills by Job Count:")
    print("-" * 70)
    parent_counts = feature_df[parent_skills].sum().sort_values(ascending=False)
    for i, (parent, count) in enumerate(parent_counts.head(10).items(), 1):
        pct = (count / len(jobs_df)) * 100
        print(f"   {i:2d}. {parent:50s} {count:4.0f} ({pct:5.1f}%)")
    print()
    
    # Top 30 unmapped skills
    print("⚠️  Top 30 Unmapped Job Skills (extend mapping file):")
    print("-" * 70)
    unmapped_counter = Counter(unmapped_skills)
    for i, (skill, count) in enumerate(unmapped_counter.most_common(30), 1):
        print(f"   {i:2d}. {skill:50s} {count:4d} occurrences")
    
    if not unmapped_counter:
        print("   ✅ No unmapped skills! All job skills are mapped.")
    
    print()
    print("=" * 70)
    print("✅ Done!")
    print("=" * 70)


if __name__ == "__main__":
    main()
