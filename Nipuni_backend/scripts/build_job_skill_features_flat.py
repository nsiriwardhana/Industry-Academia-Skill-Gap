"""
Build job-level skill features for flat skills system.

This script generates job_parent_skill_features.csv directly from Job_data.csv
without requiring parent skill mappings (works with flat skills).

Inputs:
  - backend/data/Job_data.csv

Output:
  - backend/data/job_parent_skill_features.csv

Run from backend root:
  python scripts/build_job_skill_features_flat.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter
import sys

# Paths
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR.parent  # backend/
DATA_DIR = BASE_DIR / "data"

JOB_DATA = DATA_DIR / "Job_data.csv"
OUTPUT_FILE = DATA_DIR / "job_parent_skill_features.csv"


def normalize_skill(skill: str) -> str:
    """Normalize a skill name: lowercase, strip whitespace, remove special chars."""
    return skill.strip().lower().replace('/', '_').replace('+', 'plus').replace('#', 'sharp').replace('.', '')


def main():
    print("=" * 70)
    print("🚀 Building Job Skill Features (Flat Skills)")
    print("=" * 70)
    print()
    
    # 1. Load job data
    print(f"📂 Loading job data from {JOB_DATA.name}")
    if not JOB_DATA.exists():
        print(f"❌ Error: {JOB_DATA} not found!")
        sys.exit(1)
    
    jobs_df = pd.read_csv(JOB_DATA)
    print(f"   ✅ Loaded {len(jobs_df):,} jobs")
    print()
    
    # 2. Extract all unique skills across all jobs
    print("📊 Extracting unique skills...")
    all_skills = set()
    jobs_with_skills = 0
    
    for idx, row in jobs_df.iterrows():
        skills_str = row.get('skills', '')
        
        if pd.isna(skills_str) or not skills_str:
            continue
        
        # Split by pipe and normalize
        job_skills = [normalize_skill(s) for s in str(skills_str).split('|') if s.strip()]
        if job_skills:
            jobs_with_skills += 1
            all_skills.update(job_skills)
    
    # Sort skills alphabetically for consistent column ordering
    skill_columns = sorted(list(all_skills))
    
    print(f"   ✅ Found {len(skill_columns)} unique skills across {jobs_with_skills} jobs")
    print()
    
    # 3. Initialize feature matrix
    print("🔨 Building binary feature matrix...")
    
    # Start with base columns (include seniority_level for filtering)
    base_cols = ['job_id', 'title', 'company', 'role_key']
    if 'seniority_level' in jobs_df.columns:
        base_cols.append('seniority_level')
    
    feature_df = jobs_df[base_cols].copy()
    
    # Initialize all skill columns to 0
    for skill in skill_columns:
        feature_df[skill] = 0
    
    # 4. Fill in binary features
    skill_usage_count = Counter()
    
    for idx, row in jobs_df.iterrows():
        skills_str = row.get('skills', '')
        
        if pd.isna(skills_str) or not skills_str:
            continue
        
        # Split and normalize skills
        job_skills = [normalize_skill(s) for s in str(skills_str).split('|') if s.strip()]
        
        # Set binary features
        for skill in job_skills:
            if skill in skill_columns:
                feature_df.loc[idx, skill] = 1
                skill_usage_count[skill] += 1
    
    print(f"   ✅ Created feature matrix: {len(feature_df):,} rows × {len(feature_df.columns)} columns")
    print()
    
    # 5. Save output
    print(f"💾 Saving to {OUTPUT_FILE.name}")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_csv(OUTPUT_FILE, index=False)
    print(f"   ✅ Saved successfully!")
    print()
    
    # 6. Print statistics
    print("=" * 70)
    print("📈 STATISTICS")
    print("=" * 70)
    print()
    
    # Jobs per role
    role_counts = jobs_df['role_key'].value_counts()
    print(f"📊 Jobs per Role:")
    for role, count in role_counts.items():
        print(f"   - {role}: {count} jobs")
    print()
    
    # Coverage
    jobs_with_features = (feature_df[skill_columns].sum(axis=1) > 0).sum()
    coverage_pct = (jobs_with_features / len(jobs_df)) * 100 if len(jobs_df) > 0 else 0
    print(f"Total Jobs:              {len(jobs_df):,}")
    print(f"Jobs with Skills:        {jobs_with_features:,}")
    print(f"Coverage:                {coverage_pct:.1f}%")
    print()
    
    # Top 20 most common skills
    print("🏆 Top 20 Most Common Skills:")
    print("-" * 70)
    for i, (skill, count) in enumerate(skill_usage_count.most_common(20), 1):
        pct = (count / len(jobs_df)) * 100
        print(f"   {i:2d}. {skill:50s} {count:4d} jobs ({pct:5.1f}%)")
    print()
    
    # Skill distribution stats
    skills_per_job = feature_df[skill_columns].sum(axis=1)
    print("📊 Skills per Job Distribution:")
    print(f"   Mean:   {skills_per_job.mean():.1f} skills/job")
    print(f"   Median: {skills_per_job.median():.1f} skills/job")
    print(f"   Min:    {skills_per_job.min():.0f} skills/job")
    print(f"   Max:    {skills_per_job.max():.0f} skills/job")
    print()
    
    print("=" * 70)
    print("✅ Done!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Verify the file: backend/data/job_parent_skill_features.csv")
    print("  2. Run: python scripts/verify_job_data.py")
    print("  3. Test job recommendations: python test_ml_job_recommendations.py")


if __name__ == "__main__":
    main()
