"""
Add skills to a candidate in Neo4j for intervention test.
"""
from neo4j import GraphDatabase

# Connection details
URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "tharusha@2001"

# Skills to add
CANDIDATE_ID = "CAND_7EEB74EA"
SKILLS = ["Deep Learning", "NLP"]

# Connect and add skills
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

with driver.session() as session:
    for skill in SKILLS:
        query = """
        MATCH (p:Person {candidate_id: $candidate_id})
        MATCH (s:Skill {name: $skill_name})
        MERGE (p)-[:HAS_SKILL]->(s)
        RETURN p.candidate_id AS candidate, s.name AS skill
        """
        result = session.run(query, candidate_id=CANDIDATE_ID, skill_name=skill)
        record = result.single()
        
        if record:
            print(f"✓ Added skill: {record['skill']} to candidate {record['candidate']}")
        else:
            print(f"✗ Failed to add skill: {skill} (check if skill exists in database)")

driver.close()

print(f"\nDone! Added {len(SKILLS)} skills to candidate {CANDIDATE_ID}")
print("\nNow re-run the test:")
print("python scripts/test_realtime_gnn.py --candidate_id CAND_7EEB74EA --role_keys ai_ml_engineer,data_engineer --top_k=20")
