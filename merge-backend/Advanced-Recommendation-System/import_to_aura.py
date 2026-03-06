"""
Import Knowledge Graph to Neo4j Aura from CSV exports.
Optimized for Aura's constraints and large datasets.
"""
import os
import time
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

# Aura connection
URI = os.getenv('NEO4J_URI')
USERNAME = os.getenv('NEO4J_USERNAME')
PASSWORD = os.getenv('NEO4J_PASSWORD')

print(f"Connecting to: {URI}")
driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

CSV_DIR = Path("neo4j_export/csv")

# Node types in dependency order
NODE_TYPES = [
    "Person", "Company", "Institution", "Role", "Skill", "SkillCategory",
    "Project", "Certification", "Education", "WorkExperience",
    "Job", "JobPosting", "Vacancy", "Course", "LearningResource",
    "Provider", "ReadinessLabel"
]

# Relationship types
REL_TYPES = [
    "HAS_SKILL", "WORKED_ON", "USED_SKILL", "HAS_CERTIFICATION",
    "HAS_EDUCATION", "WORKED_AT", "AT_COMPANY", "FROM_INSTITUTION",
    "STUDIED_AT", "REQUIRES_SKILL", "BELONGS_TO_CATEGORY",
    "TEACHES_SKILL", "HOSTED_ON", "TARGETS_ROLE", "FOR_ROLE",
    "FOR_COMPANY", "BELONGS_TO_ROLE", "HAS_LABEL", "SIMILAR_TO",
    "GROUPED_WITH", "USES_TECHNOLOGY"
]

def run_query(session, query, params=None):
    """Execute query with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = session.run(query, params or {})
            result.consume()
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  Retry {attempt + 1}/{max_retries}...")
                time.sleep(2)
            else:
                print(f"  Error: {e}")
                return False

def create_constraints(session):
    """Create uniqueness constraints for faster imports."""
    print("\n📋 Creating constraints...")
    
    constraints = [
        "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.person_key IS UNIQUE",
        "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.company_key IS UNIQUE",
        "CREATE CONSTRAINT skill_id IF NOT EXISTS FOR (s:Skill) REQUIRE s.skill_key IS UNIQUE",
        "CREATE CONSTRAINT role_id IF NOT EXISTS FOR (r:Role) REQUIRE r.role_key IS UNIQUE",
        "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.project_key IS UNIQUE",
        "CREATE CONSTRAINT category_id IF NOT EXISTS FOR (sc:SkillCategory) REQUIRE sc.category_name IS UNIQUE",
        "CREATE CONSTRAINT institution_id IF NOT EXISTS FOR (i:Institution) REQUIRE i.institution_key IS UNIQUE",
        "CREATE CONSTRAINT cert_id IF NOT EXISTS FOR (c:Certification) REQUIRE c.cert_key IS UNIQUE",
        "CREATE CONSTRAINT edu_id IF NOT EXISTS FOR (e:Education) REQUIRE e.education_key IS UNIQUE",
        "CREATE CONSTRAINT work_id IF NOT EXISTS FOR (w:WorkExperience) REQUIRE w.work_key IS UNIQUE",
        "CREATE CONSTRAINT job_id IF NOT EXISTS FOR (j:Job) REQUIRE j.job_key IS UNIQUE",
        "CREATE CONSTRAINT course_id IF NOT EXISTS FOR (c:Course) REQUIRE c.course_key IS UNIQUE",
        "CREATE CONSTRAINT provider_id IF NOT EXISTS FOR (p:Provider) REQUIRE p.provider_key IS UNIQUE",
    ]
    
    for constraint in tqdm(constraints, desc="Constraints"):
        run_query(session, constraint)
    
    print("✅ Constraints created")

def import_nodes(session, node_type):
    """Import nodes from CSV by reading and batching in Python."""
    import csv
    
    csv_file = CSV_DIR / f"nodes_{node_type}.csv"
    
    if not csv_file.exists():
        print(f"⏭️  Skipping {node_type} (file not found)")
        return
    
    # Check file size
    size_mb = csv_file.stat().st_size / (1024 * 1024)
    print(f"\n📦 Importing {node_type} ({size_mb:.1f} MB)...")
    
    # Determine ID field
    id_fields = {
        "Person": "person_key", "Skill": "skill_key", "Role": "role_key",
        "Company": "company_key", "Project": "project_key", "SkillCategory": "category_name",
        "Institution": "institution_key", "Certification": "cert_key", "Education": "education_key",
        "WorkExperience": "work_key", "Job": "job_key", "Course": "course_key",
        "Provider": "provider_key", "JobPosting": "job_posting_key", "Vacancy": "vacancy_key",
        "LearningResource": "resource_key", "ReadinessLabel": "label_key"
    }
    id_field = id_fields.get(node_type, "id")
    
    # Read CSV and import in batches
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []
        total = 0
        
        for row in reader:
            # Clean row data
            clean_row = {}
            for key, value in row.items():
                if key and key != ':ID' and value:
                    clean_key = key.strip().replace('"', '')
                    clean_row[clean_key] = value
            
            if clean_row:
                batch.append(clean_row)
                total += 1
            
            # Process batch
            if len(batch) >= 500:
                query = f"""
                UNWIND $batch AS row
                MERGE (n:{node_type} {{{id_field}: row.{id_field}}})
                SET n += row
                """
                run_query(session, query, {'batch': batch})
                batch = []
        
        # Process remaining
        if batch:
            query = f"""
            UNWIND $batch AS row
            MERGE (n:{node_type} {{{id_field}: row.{id_field}}})
            SET n += row
            """
            run_query(session, query, {'batch': batch})
        
        print(f"✅ {node_type}: {total:,} nodes imported")

def import_relationships(session, rel_type):
    """Import relationships from CSV by reading and batching in Python."""
    import csv
    
    csv_file = CSV_DIR / f"rels_{rel_type}.csv"
    
    if not csv_file.exists():
        print(f"⏭️  Skipping {rel_type} (file not found)")
        return
    
    size_mb = csv_file.stat().st_size / (1024 * 1024)
    print(f"\n🔗 Importing {rel_type} ({size_mb:.1f} MB)...")
    
    # Read CSV and import in batches
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        batch = []
        total = 0
        
        for row in reader:
            # Extract IDs and properties
            start_id = row.get(':START_ID')
            end_id = row.get(':END_ID')
            
            if not start_id or not end_id:
                continue
            
            # Get properties (excluding ID columns)
            props = {}
            for key, value in row.items():
                if key not in [':START_ID', ':END_ID', ':TYPE'] and value:
                    clean_key = key.strip().replace('"', '')
                    props[clean_key] = value
            
            batch.append({
                'start': int(start_id),
                'end': int(end_id),
                'props': props
            })
            total += 1
            
            # Process batch
            if len(batch) >= 500:
                query = f"""
                UNWIND $batch AS rel
                MATCH (a) WHERE id(a) = rel.start
                MATCH (b) WHERE id(b) = rel.end
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += rel.props
                """
                run_query(session, query, {'batch': batch})
                batch = []
        
        # Process remaining
        if batch:
            query = f"""
            UNWIND $batch AS rel
            MATCH (a) WHERE id(a) = rel.start
            MATCH (b) WHERE id(b) = rel.end
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += rel.props
            """
            run_query(session, query, {'batch': batch})
        
        print(f"✅ {rel_type}: {total:,} relationships imported")

def verify_import(session):
    """Verify import results."""
    print("\n📊 Verifying import...")
    
    # Count nodes
    result = session.run("MATCH (n) RETURN count(n) as count")
    node_count = result.single()['count']
    print(f"  Nodes: {node_count:,}")
    
    # Count relationships
    result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
    rel_count = result.single()['count']
    print(f"  Relationships: {rel_count:,}")
    
    # Count by label
    result = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label")
    labels = [record['label'] for record in result]
    print(f"  Labels: {len(labels)}")
    
    return node_count > 0 and rel_count > 0

def main():
    print("="*60)
    print("🚀 Neo4j Aura Import Starting")
    print("="*60)
    
    start_time = time.time()
    
    with driver.session() as session:
        # Step 1: Create constraints
        create_constraints(session)
        
        # Step 2: Import nodes
        print("\n" + "="*60)
        print("📦 IMPORTING NODES")
        print("="*60)
        for node_type in NODE_TYPES:
            import_nodes(session, node_type)
        
        # Step 3: Import relationships
        print("\n" + "="*60)
        print("🔗 IMPORTING RELATIONSHIPS")
        print("="*60)
        for rel_type in REL_TYPES:
            import_relationships(session, rel_type)
        
        # Step 4: Verify
        if verify_import(session):
            print("\n✅ Import completed successfully!")
        else:
            print("\n⚠️  Import may have issues, check logs")
    
    driver.close()
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed/60:.1f} minutes")
    print("="*60)

if __name__ == "__main__":
    main()
