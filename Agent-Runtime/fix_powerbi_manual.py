"""
Manual cleanup for remaining Power BI variations
"""
from database import Neo4jConnection

driver = Neo4jConnection.get_driver()

with driver.session() as session:
    print("Fixing remaining Power BI variations...")
    
    # Fix "Power Bi" -> "Power BI"
    print("\n1. Merging 'Power Bi' into 'Power BI'...")
    
    query1 = """
    // Find both nodes
    MATCH (wrong:Skill {name: 'Power Bi'})
    MATCH (correct:Skill {name: 'Power BI'})
    
    // Move all relationships
    OPTIONAL MATCH (p:Person)-[r:HAS_SKILL]->(wrong)
    WITH wrong, correct, p, r
    WHERE r IS NOT NULL
    MERGE (p)-[new_r:HAS_SKILL]->(correct)
    ON CREATE SET new_r = properties(r)
    DELETE r
    
    WITH wrong, correct, count(*) AS moved
    
    // Move project relationships
    OPTIONAL MATCH (proj:Project)-[r2:USES_TECHNOLOGY]->(wrong)
    WITH wrong, correct, proj, r2, moved
    WHERE r2 IS NOT NULL
    MERGE (proj)-[new_r2:USES_TECHNOLOGY]->(correct)
    DELETE r2
    
    WITH wrong, moved
    
    // Delete the wrong node
    DELETE wrong
    
    RETURN moved
    """
    
    result = session.run(query1).single()
    if result:
        print(f"   Moved {result['moved']} relationships")
        print("   ✓ Deleted 'Power Bi'")
    
    # Fix "power BI" -> "Power BI"
    print("\n2. Merging 'power BI' into 'Power BI'...")
    
    query2 = """
    // Find both nodes
    MATCH (wrong:Skill {name: 'power BI'})
    MATCH (correct:Skill {name: 'Power BI'})
    
    // Move all relationships
    OPTIONAL MATCH (p:Person)-[r:HAS_SKILL]->(wrong)
    WITH wrong, correct, p, r
    WHERE r IS NOT NULL
    MERGE (p)-[new_r:HAS_SKILL]->(correct)
    ON CREATE SET new_r = properties(r)
    DELETE r
    
    WITH wrong, correct, count(*) AS moved
    
    // Move project relationships
    OPTIONAL MATCH (proj:Project)-[r2:USES_TECHNOLOGY]->(wrong)
    WITH wrong, correct, proj, r2, moved
    WHERE r2 IS NOT NULL
    MERGE (proj)-[new_r2:USES_TECHNOLOGY]->(correct)
    DELETE r2
    
    WITH wrong, moved
    
    // Delete the wrong node
    DELETE wrong
    
    RETURN moved
    """
    
    result = session.run(query2).single()
    if result:
        print(f"   Moved {result['moved']} relationships")
        print("   ✓ Deleted 'power BI'")
    
    # Verify
    print("\n3. Verification:")
    verify_query = """
    MATCH (s:Skill)
    WHERE toLower(s.name) = 'power bi'
    RETURN s.name AS name
    ORDER BY name
    """
    
    results = list(session.run(verify_query))
    print(f"   Skills matching 'power bi' (case-insensitive): {len(results)}")
    for r in results:
        print(f"     - {r['name']}")
    
    if len(results) == 1:
        print("\n✓ SUCCESS! Only canonical 'Power BI' remains")
    else:
        print(f"\n⚠ Warning: {len(results)} variations still exist")

print("\nDone!")
