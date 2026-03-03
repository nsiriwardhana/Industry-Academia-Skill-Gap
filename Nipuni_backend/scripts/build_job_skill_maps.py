"""
Build Job Skill Mappings

Generates initial job_skills.csv and childskill_to_jobskill_map.csv
from existing child skills data.

Usage:
    python scripts/build_job_skill_maps.py [--force]
    
Options:
    --force    Overwrite existing mapping files (use with caution)
"""

import pandas as pd
import re
from pathlib import Path
import argparse
import sys

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
COURSE_SKILL_MAP = DATA_DIR / "course_skill_mapping.csv"
CHILD_SKILLS_UNIQUE = DATA_DIR / "child_skills_unique.csv"
JOB_SKILLS_OUTPUT = DATA_DIR / "job_skills.csv"
MAPPING_OUTPUT = DATA_DIR / "childskill_to_jobskill_map.csv"

# Master list of canonical job skills with categories
JOB_SKILLS_MASTER = [
    # Programming Languages
    ("PYTHON", "Python", "Programming Language", "Python,Py"),
    ("JAVA", "Java", "Programming Language", "Java"),
    ("JAVASCRIPT", "JavaScript", "Programming Language", "JavaScript,JS,Node"),
    ("TYPESCRIPT", "TypeScript", "Programming Language", "TypeScript,TS"),
    ("CPLUSPLUS", "C++", "Programming Language", "C++,Cpp"),
    ("C", "C Programming", "Programming Language", "C Language,C,Procedural"),
    ("CSHARP", "C#", "Programming Language", "C#,C Sharp"),
    ("PHP", "PHP", "Programming Language", "PHP"),
    ("SCALA", "Scala", "Programming Language", "Scala"),
    ("R", "R Programming", "Programming Language", "R Statistical"),
    
    # Databases
    ("SQL", "SQL", "Database", "SQL,Structured Query,Database Management"),
    ("NOSQL", "NoSQL", "Database", "NoSQL,MongoDB,Document Database"),
    ("POSTGRESQL", "PostgreSQL", "Database", "PostgreSQL,Postgres"),
    ("MYSQL", "MySQL", "Database", "MySQL"),
    ("MONGODB", "MongoDB", "Database", "MongoDB"),
    ("REDIS", "Redis", "Database", "Redis"),
    
    # Web Development
    ("HTML", "HTML", "Web Development", "HTML,Markup"),
    ("CSS", "CSS", "Web Development", "CSS,Styling"),
    ("REACT", "React", "Web Development", "React,React.js"),
    ("ANGULAR", "Angular", "Web Development", "Angular,AngularJS"),
    ("VUE", "Vue.js", "Web Development", "Vue"),
    ("RESTAPI", "REST API", "Web Development", "REST,RESTful,API"),
    ("GRAPHQL", "GraphQL", "Web Development", "GraphQL"),
    
    # DevOps & Cloud
    ("GIT", "Git", "DevOps", "Git,Version Control"),
    ("DOCKER", "Docker", "DevOps", "Docker,Container"),
    ("KUBERNETES", "Kubernetes", "DevOps", "Kubernetes,K8s,Orchestration"),
    ("CICD", "CI/CD", "DevOps", "CI/CD,Jenkins,Pipeline"),
    ("AWS", "AWS", "Cloud", "AWS,Amazon Web Services"),
    ("AZURE", "Azure", "Cloud", "Azure,Microsoft Azure"),
    ("GCP", "Google Cloud", "Cloud", "GCP,Google Cloud Platform"),
    ("TERRAFORM", "Terraform", "DevOps", "Terraform,IaC"),
    ("ANSIBLE", "Ansible", "DevOps", "Ansible,Configuration"),
    
    # Operating Systems
    ("LINUX", "Linux", "Operating System", "Linux,Unix"),
    ("WINDOWS", "Windows", "Operating System", "Windows"),
    
    # Data & Analytics
    ("PANDAS", "Pandas", "Data Science", "Pandas,DataFrame"),
    ("NUMPY", "NumPy", "Data Science", "NumPy,Numerical"),
    ("ETL", "ETL", "Data Engineering", "ETL,Extract Transform Load"),
    ("SPARK", "Apache Spark", "Data Engineering", "Spark,PySpark"),
    ("HADOOP", "Hadoop", "Data Engineering", "Hadoop"),
    ("KAFKA", "Apache Kafka", "Data Engineering", "Kafka,Streaming"),
    ("AIRFLOW", "Apache Airflow", "Data Engineering", "Airflow,Workflow"),
    
    # Machine Learning & AI
    ("MACHINELEARNING", "Machine Learning", "AI/ML", "Machine Learning,ML"),
    ("DEEPLEARNING", "Deep Learning", "AI/ML", "Deep Learning,Neural Network"),
    ("TENSORFLOW", "TensorFlow", "AI/ML", "TensorFlow"),
    ("PYTORCH", "PyTorch", "AI/ML", "PyTorch"),
    ("NLP", "Natural Language Processing", "AI/ML", "NLP,Text Processing"),
    ("COMPUTERVISION", "Computer Vision", "AI/ML", "Computer Vision,Image Processing"),
    
    # Methodologies
    ("AGILE", "Agile", "Methodology", "Agile"),
    ("SCRUM", "Scrum", "Methodology", "Scrum"),
    ("UML", "UML", "Methodology", "UML,Modeling"),
    ("OOP", "Object-Oriented Programming", "Methodology", "OOP,Object-Oriented"),
    
    # Mobile
    ("ANDROID", "Android", "Mobile Development", "Android"),
    ("IOS", "iOS", "Mobile Development", "iOS,iPhone"),
    ("REACTNATIVE", "React Native", "Mobile Development", "React Native"),
    
    # Testing & Quality
    ("UNITTESTING", "Unit Testing", "Testing", "Unit Test,Testing"),
    ("PYTEST", "Pytest", "Testing", "Pytest"),
    ("JUNIT", "JUnit", "Testing", "JUnit"),
    
    # Business Intelligence
    ("POWERBI", "Power BI", "Business Intelligence", "Power BI,PowerBI"),
    ("TABLEAU", "Tableau", "Business Intelligence", "Tableau"),
    ("OLAP", "OLAP", "Business Intelligence", "OLAP,Cube"),
    
    # Networking
    ("TCPIP", "TCP/IP", "Networking", "TCP/IP,Networking"),
    ("ROUTING", "Routing", "Networking", "Routing,Router"),
    ("VLAN", "VLAN", "Networking", "VLAN"),
    
    # Security
    ("SECURITY", "Security", "Security", "Security,Cyber"),
    ("ENCRYPTION", "Encryption", "Security", "Encryption"),
]


def extract_child_skills_from_mapping():
    """Extract unique child skills from course_skill_mapping.csv"""
    try:
        df = pd.read_csv(COURSE_SKILL_MAP)
        
        # Columns with skills: Skill1-5, MainSkill
        skill_cols = ['Skill1', 'Skill2', 'Skill3', 'Skill4', 'Skill5', 'MainSkill']
        
        all_skills = []
        for col in skill_cols:
            if col in df.columns:
                skills = df[col].dropna().unique()
                all_skills.extend(skills)
        
        unique_skills = sorted(set(all_skills))
        print(f"✓ Extracted {len(unique_skills)} unique child skills from course mapping")
        return unique_skills
        
    except Exception as e:
        print(f"✗ Failed to extract child skills: {e}")
        return []


def load_existing_child_skills():
    """Load child skills from child_skills_unique.csv if it exists"""
    if CHILD_SKILLS_UNIQUE.exists():
        try:
            df = pd.read_csv(CHILD_SKILLS_UNIQUE)
            if 'child_skill' in df.columns:
                skills = df['child_skill'].tolist()
            else:
                skills = df.iloc[:, 0].tolist()
            print(f"✓ Loaded {len(skills)} child skills from {CHILD_SKILLS_UNIQUE.name}")
            return skills
        except Exception as e:
            print(f"⚠ Could not load {CHILD_SKILLS_UNIQUE.name}: {e}")
    
    # Fallback to extraction
    return extract_child_skills_from_mapping()


def create_job_skills_csv(force=False):
    """Create job_skills.csv with canonical job skill definitions"""
    
    if JOB_SKILLS_OUTPUT.exists() and not force:
        print(f"⚠ {JOB_SKILLS_OUTPUT.name} already exists. Use --force to overwrite.")
        return pd.read_csv(JOB_SKILLS_OUTPUT)
    
    # Create DataFrame
    df = pd.DataFrame(JOB_SKILLS_MASTER, columns=[
        'JobSkillID', 'JobSkillName', 'Category', 'Aliases'
    ])
    
    # Save
    df.to_csv(JOB_SKILLS_OUTPUT, index=False)
    print(f"✓ Created {JOB_SKILLS_OUTPUT.name} with {len(df)} job skills")
    
    return df


def map_child_to_job_skill(child_skill, job_skills_df):
    """
    Map a child skill to one or more job skills using keyword matching.
    
    Returns list of tuples: (JobSkillID, MapWeight, MatchReason)
    """
    matches = []
    child_lower = child_skill.lower()
    
    for _, row in job_skills_df.iterrows():
        job_id = row['JobSkillID']
        job_name = row['JobSkillName']
        aliases = row['Aliases'].split(',')
        
        # Check if any alias appears in child skill
        for alias in aliases:
            alias_lower = alias.strip().lower()
            
            # Exact match
            if alias_lower == child_lower:
                matches.append((job_id, 1.0, f"Exact match: {alias}"))
                continue
            
            # Substring match (use word boundaries to avoid false positives)
            pattern = r'\b' + re.escape(alias_lower) + r'\b'
            if re.search(pattern, child_lower):
                matches.append((job_id, 0.8, f"Contains: {alias}"))
    
    # Remove duplicates (keep highest weight)
    unique_matches = {}
    for job_id, weight, reason in matches:
        if job_id not in unique_matches or weight > unique_matches[job_id][0]:
            unique_matches[job_id] = (weight, reason)
    
    return [(job_id, weight, reason) for job_id, (weight, reason) in unique_matches.items()]


def create_mapping_csv(child_skills, job_skills_df, force=False):
    """Create childskill_to_jobskill_map.csv with automated mappings"""
    
    if MAPPING_OUTPUT.exists() and not force:
        print(f"⚠ {MAPPING_OUTPUT.name} already exists. Use --force to overwrite.")
        return
    
    mappings = []
    unmapped_skills = []
    
    for child_skill in child_skills:
        matches = map_child_to_job_skill(child_skill, job_skills_df)
        
        if matches:
            for job_id, weight, reason in matches:
                mappings.append({
                    'ChildSkill': child_skill,
                    'JobSkillID': job_id,
                    'MapWeight': weight,
                    'Notes': reason
                })
        else:
            unmapped_skills.append(child_skill)
    
    # Create DataFrame
    df = pd.DataFrame(mappings)
    
    if len(df) > 0:
        df.to_csv(MAPPING_OUTPUT, index=False)
        print(f"✓ Created {MAPPING_OUTPUT.name} with {len(df)} mappings")
        print(f"  Mapped {len(set(df['ChildSkill']))} child skills to {len(set(df['JobSkillID']))} job skills")
    else:
        print("✗ No mappings generated")
    
    if unmapped_skills:
        print(f"\n⚠ {len(unmapped_skills)} child skills had no automatic mapping:")
        for skill in unmapped_skills[:10]:
            print(f"   - {skill}")
        if len(unmapped_skills) > 10:
            print(f"   ... and {len(unmapped_skills) - 10} more")
        print("\nManually edit the CSV to add these mappings as needed.")


def main():
    parser = argparse.ArgumentParser(description="Generate job skill mapping files")
    parser.add_argument('--force', action='store_true', 
                        help='Overwrite existing mapping files')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Job Skill Mapping Generator")
    print("=" * 60)
    
    # Step 1: Load child skills
    print("\n[1/3] Loading child skills...")
    child_skills = load_existing_child_skills()
    
    if not child_skills:
        print("✗ No child skills found. Cannot proceed.")
        sys.exit(1)
    
    # Step 2: Create job_skills.csv
    print("\n[2/3] Creating job skills master list...")
    job_skills_df = create_job_skills_csv(force=args.force)
    
    # Step 3: Create mapping
    print("\n[3/3] Generating child skill → job skill mappings...")
    create_mapping_csv(child_skills, job_skills_df, force=args.force)
    
    print("\n" + "=" * 60)
    print("✓ Job skill mapping generation complete!")
    print("=" * 60)
    print(f"\nGenerated files:")
    print(f"  - {JOB_SKILLS_OUTPUT.relative_to(BASE_DIR)}")
    print(f"  - {MAPPING_OUTPUT.relative_to(BASE_DIR)}")
    print(f"\nNext steps:")
    print(f"  1. Review and refine mappings in {MAPPING_OUTPUT.name}")
    print(f"  2. Add missing mappings manually")
    print(f"  3. Run skill scoring to generate job skill scores")


if __name__ == "__main__":
    main()
