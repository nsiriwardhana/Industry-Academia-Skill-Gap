"""Check if candidate has projects."""
from database.neo4j_connection import Neo4jConnection

candidate_id = "CAND_01B77EB1"

with Neo4jConnection.get_session() as session:
    # Check if person exists
    result = session.run(
        "MATCH (p:Person {candidate_id: $cid}) RETURN p.candidate_id AS cid, p.name AS name",
        cid=candidate_id
    )
    person = result.single()
    if person:
        print(f"✓ Person found: {person['name']} ({person['cid']})")
    else:
        print(f"✗ Person not found: {candidate_id}")
    
    # Check projects
    result = session.run(
        """
        MATCH (p:Person {candidate_id: $cid})-[:WORKED_ON]->(proj:Project)
        RETURN proj.name AS name, proj.description AS desc, proj.complexity AS complexity
        LIMIT 10
        """,
        cid=candidate_id
    )
    
    projects = list(result)
    print(f"\nProjects: {len(projects)}")
    for proj in projects:
        desc = proj['desc'][:50] if proj['desc'] else "No description"
        print(f"  - {proj['name']}: {desc} (complexity: {proj['complexity']})")
    
    # Check project skills
    if projects:
        result = session.run(
            """
            MATCH (p:Person {candidate_id: $cid})-[:WORKED_ON]->(proj:Project)
            OPTIONAL MATCH (proj)-[:USES_TECHNOLOGY]->(s:Skill)
            RETURN proj.name AS project_name, collect(DISTINCT s.name) AS skills
            LIMIT 5
            """,
            cid=candidate_id
        )
        print(f"\nProject Skills:")
        for record in result:
            skills = [s for s in record['skills'] if s]
            print(f"  - {record['project_name']}: {len(skills)} skills - {', '.join(skills[:5])}")
