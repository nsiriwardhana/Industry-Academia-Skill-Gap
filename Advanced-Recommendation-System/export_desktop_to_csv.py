"""
Export Neo4j Desktop database to CSV files for Aura import.
Exports all nodes and relationships with proper formatting.
"""
import csv
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

# Desktop connection (from .env)
DESKTOP_URI = "bolt://localhost:7687"
DESKTOP_USER = "neo4j"
DESKTOP_PASSWORD = "tharusha@2001"

# Output directory
OUTPUT_DIR = Path("neo4j_export/csv")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Node types to export
NODE_TYPES = [
    "Person", "Company", "Institution", "Role", "Skill", "SkillCategory",
    "Project", "Certification", "Education", "WorkExperience",
    "Job", "JobPosting", "Vacancy", "Course", "LearningResource",
    "Provider", "ReadinessLabel"
]

# Relationship types to export
REL_TYPES = [
    "HAS_SKILL", "WORKED_ON", "USED_SKILL", "HAS_CERTIFICATION",
    "HAS_EDUCATION", "WORKED_AT", "AT_COMPANY", "FROM_INSTITUTION",
    "STUDIED_AT", "REQUIRES_SKILL", "BELONGS_TO_CATEGORY",
    "TEACHES_SKILL", "HOSTED_ON", "TARGETS_ROLE", "FOR_ROLE",
    "FOR_COMPANY", "BELONGS_TO_ROLE", "HAS_LABEL", "SIMILAR_TO",
    "GROUPED_WITH", "USES_TECHNOLOGY"
]

def export_nodes(session, node_type):
    """Export all nodes of a specific type to CSV."""
    print(f"  📦 Exporting {node_type} nodes...")
    
    # Query all nodes of this type
    query = f"""
    MATCH (n:{node_type})
    RETURN id(n) as _id, n
    """
    
    results = list(session.run(query))
    if not results:
        print(f"    ⚠️  No {node_type} nodes found")
        return
    
    # Prepare CSV file
    csv_file = OUTPUT_DIR / f"nodes_{node_type}.csv"
    
    # Get all property keys from first node
    first_node = results[0]["n"]
    prop_keys = list(first_node.keys())
    
    # Add internal ID as first column
    headers = [":ID"] + prop_keys + [":LABEL"]
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for record in results:
            internal_id = record["_id"]
            node = record["n"]
            
            row = [internal_id]
            for key in prop_keys:
                value = node.get(key, "")
                # Handle lists (like embeddings)
                if isinstance(value, list):
                    # Convert to semicolon-separated string
                    value = ";".join([str(v) for v in value])
                row.append(value)
            row.append(node_type)
            
            writer.writerow(row)
    
    print(f"    ✓ Exported {len(results)} nodes to {csv_file.name}")

def export_relationships(session, rel_type):
    """Export all relationships of a specific type to CSV."""
    print(f"  🔗 Exporting {rel_type} relationships...")
    
    # Query all relationships of this type
    query = f"""
    MATCH (a)-[r:{rel_type}]->(b)
    RETURN id(a) as start_id, id(b) as end_id, type(r) as rel_type, properties(r) as props
    """
    
    results = list(session.run(query))
    if not results:
        print(f"    ⚠️  No {rel_type} relationships found")
        return
    
    csv_file = OUTPUT_DIR / f"rels_{rel_type}.csv"
    
    # Get all property keys from all relationships
    all_props = set()
    for record in results:
        if record["props"]:
            all_props.update(record["props"].keys())
    
    prop_keys = sorted(list(all_props))
    
    # Headers: START_ID, END_ID, TYPE, properties
    headers = [":START_ID", ":END_ID", ":TYPE"] + prop_keys
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for record in results:
            row = [
                record["start_id"],
                record["end_id"],
                record["rel_type"]
            ]
            
            props = record["props"] or {}
            for key in prop_keys:
                value = props.get(key, "")
                # Handle lists
                if isinstance(value, list):
                    value = ";".join([str(v) for v in value])
                row.append(value)
            
            writer.writerow(row)
    
    print(f"    ✓ Exported {len(results)} relationships to {csv_file.name}")

def main():
    """Main export function."""
    print("🚀 Exporting Neo4j Desktop to CSV files for Aura\n")
    
    driver = GraphDatabase.driver(DESKTOP_URI, auth=(DESKTOP_USER, DESKTOP_PASSWORD))
    
    try:
        driver.verify_connectivity()
        print("✓ Connected to Neo4j Desktop\n")
    except Exception as e:
        print(f"❌ Cannot connect to Neo4j Desktop: {e}")
        print("   Make sure Neo4j Desktop is running!")
        return
    
    with driver.session() as session:
        # Get database stats
        stats = session.run("""
            MATCH (n)
            WITH count(n) as nodes
            MATCH ()-[r]->()
            RETURN nodes, count(r) as rels
        """).single()
        
        print(f"📊 Database Stats:")
        print(f"   Nodes: {stats['nodes']:,}")
        print(f"   Relationships: {stats['rels']:,}\n")
        
        # Export nodes
        print("📦 EXPORTING NODES")
        print("=" * 50)
        for node_type in NODE_TYPES:
            export_nodes(session, node_type)
        
        # Export relationships
        print("\n🔗 EXPORTING RELATIONSHIPS")
        print("=" * 50)
        for rel_type in REL_TYPES:
            export_relationships(session, rel_type)
    
    driver.close()
    
    print("\n" + "=" * 50)
    print("✅ Export completed successfully!")
    print(f"📁 Files saved to: {OUTPUT_DIR.absolute()}")
    print("\n📌 Next steps:")
    print("   1. Verify CSV files in neo4j_export/csv/")
    print("   2. Update .env to use Aura credentials")
    print("   3. Run: python import_to_aura.py")

if __name__ == "__main__":
    main()
