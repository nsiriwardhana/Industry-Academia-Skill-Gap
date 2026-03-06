"""
Setup Helper for Readiness Label Building

Checks all prerequisites and helps set up required relationships.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Neo4jConnection
from agents.gap_analyzer import GapAnalyzerTool
from config import RECOMMENDATION_API_BASE_URL, NEO4J_URI


def check_neo4j_connection():
    """Check Neo4j connection."""
    print("\n1. Checking Neo4j connection...")
    try:
        with Neo4jConnection.get_session() as session:
            result = session.run("RETURN 1 AS test")
            result.single()
        print("   ✓ Connected to Neo4j at", NEO4J_URI)
        return True
    except Exception as e:
        print(f"   ✗ Failed to connect to Neo4j: {e}")
        print(f"   → Check Neo4j is running at {NEO4J_URI}")
        return False


def check_recommendation_api():
    """Check Recommendation API availability."""
    print("\n2. Checking Recommendation API...")
    try:
        gap_analyzer = GapAnalyzerTool()
        if gap_analyzer.check_api_health():
            print(f"   ✓ API available at {RECOMMENDATION_API_BASE_URL}")
            return True
        else:
            print(f"   ✗ API not responding at {RECOMMENDATION_API_BASE_URL}")
            print("   → Start Advanced-Recommendation-System:")
            print("      cd 'F:\\CV Parser Agent\\Advanced-Recommendation-System'")
            print("      python main.py")
            return False
    except Exception as e:
        print(f"   ✗ Error checking API: {e}")
        return False


def check_data_structure():
    """Check Neo4j data structure."""
    print("\n3. Checking Neo4j data structure...")
    
    try:
        with Neo4jConnection.get_session() as session:
            # Check Person nodes
            result = session.run("""
                MATCH (p:Person)
                WHERE p.candidate_id IS NOT NULL
                RETURN COUNT(p) AS count
            """)
            person_count = result.single()["count"]
            
            if person_count == 0:
                print("   ✗ No Person nodes with candidate_id found")
                print("   → Load candidate data into Neo4j first")
                return False
            else:
                print(f"   ✓ Found {person_count} Person nodes with candidate_id")
            
            # Check Role nodes
            result = session.run("""
                MATCH (r:Role)
                WHERE r.role_key IS NOT NULL
                RETURN COUNT(r) AS count, COLLECT(r.role_key)[0..5] AS sample_roles
            """)
            record = result.single()
            role_count = record["count"]
            sample_roles = record["sample_roles"]
            
            if role_count == 0:
                print("   ✗ No Role nodes with role_key found")
                print("   → Load role data into Neo4j first")
                return False
            else:
                print(f"   ✓ Found {role_count} Role nodes")
                print(f"     Sample roles: {', '.join(sample_roles)}")
            
            # Check TARGETS_ROLE relationships
            result = session.run("""
                MATCH (p:Person)-[:TARGETS_ROLE]->(r:Role)
                WHERE p.candidate_id IS NOT NULL AND r.role_key IS NOT NULL
                RETURN COUNT(*) AS count
            """)
            targets_count = result.single()["count"]
            
            if targets_count == 0:
                print("   ⚠ No TARGETS_ROLE relationships found")
                print("   → Create relationships to specify which candidates target which roles")
                print("\n   Would you like to create default relationships? (y/n): ", end='')
                
                try:
                    response = input().strip().lower()
                    if response == 'y':
                        create_default_relationships()
                        return True
                except:
                    pass
                
                return False
            else:
                print(f"   ✓ Found {targets_count} TARGETS_ROLE relationships")
                return True
                
    except Exception as e:
        print(f"   ✗ Error checking data structure: {e}")
        return False


def create_default_relationships():
    """Create default TARGETS_ROLE relationships."""
    print("\n   Creating default relationships...")
    print("   Strategy: Each candidate targets all available roles")
    
    try:
        with Neo4jConnection.get_session() as session:
            # Create relationships (all candidates target all roles)
            result = session.run("""
                MATCH (p:Person), (r:Role)
                WHERE p.candidate_id IS NOT NULL AND r.role_key IS NOT NULL
                AND NOT EXISTS((p)-[:TARGETS_ROLE]->(r))
                CREATE (p)-[:TARGETS_ROLE]->(r)
                RETURN COUNT(*) AS created
            """)
            created = result.single()["created"]
            print(f"   ✓ Created {created} TARGETS_ROLE relationships")
            
            # Show summary
            result = session.run("""
                MATCH (p:Person)-[:TARGETS_ROLE]->(r:Role)
                WITH p.candidate_id AS candidate, COLLECT(r.role_key) AS roles
                RETURN candidate, SIZE(roles) AS role_count
                ORDER BY role_count DESC
                LIMIT 3
            """)
            
            print("\n   Sample candidate-role assignments:")
            for i, record in enumerate(result, 1):
                print(f"     {i}. {record['candidate']} targets {record['role_count']} roles")
                
    except Exception as e:
        print(f"   ✗ Error creating relationships: {e}")


def show_example_queries():
    """Show example queries for custom relationship creation."""
    print("\n" + "="*80)
    print("CUSTOM RELATIONSHIP QUERIES")
    print("="*80)
    print("""
If you want to create custom TARGETS_ROLE relationships based on your business logic:

Example 1: Candidates target roles based on their current role
──────────────────────────────────────────────────────────────
MATCH (p:Person), (r:Role)
WHERE p.current_role CONTAINS r.role_name
CREATE (p)-[:TARGETS_ROLE]->(r)

Example 2: Candidates with ML skills target ML roles
──────────────────────────────────────────────────────────────
MATCH (p:Person)-[:HAS_SKILL]->(s:Skill)
WHERE s.skill_name IN ['Machine Learning', 'Deep Learning', 'TensorFlow']
WITH p, COUNT(DISTINCT s) AS ml_skills
WHERE ml_skills >= 2
MATCH (r:Role {role_key: 'ai_ml_engineer'})
CREATE (p)-[:TARGETS_ROLE]->(r)

Example 3: All candidates target specific roles
──────────────────────────────────────────────────────────────
MATCH (p:Person), (r:Role)
WHERE p.candidate_id IS NOT NULL 
  AND r.role_key IN ['ai_ml_engineer', 'data_scientist', 'backend_engineer']
CREATE (p)-[:TARGETS_ROLE]->(r)

Example 4: Random assignment for testing
──────────────────────────────────────────────────────────────
MATCH (p:Person), (r:Role)
WHERE p.candidate_id IS NOT NULL AND r.role_key IS NOT NULL
WITH p, r, rand() AS random
WHERE random < 0.3  // 30% chance
CREATE (p)-[:TARGETS_ROLE]->(r)
""")


def main():
    """Main setup check."""
    print("="*80)
    print("READINESS LABEL BUILDER - SETUP CHECK")
    print("="*80)
    
    checks = {
        "Neo4j": check_neo4j_connection(),
        "Recommendation API": check_recommendation_api(),
        "Data Structure": check_data_structure()
    }
    
    print("\n" + "="*80)
    print("SETUP CHECK SUMMARY")
    print("="*80)
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n✓ All checks passed! Ready to build readiness labels.")
        print("\nRun the label builder:")
        print("  python build_readiness_labels.py")
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        print("\nFor custom relationship creation, see examples below:")
        show_example_queries()
    
    print("="*80)


if __name__ == "__main__":
    main()
