"""
Verify Readiness Labels

Quick script to verify generated labels and Neo4j structure.
"""
import sys
import os
import csv
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Neo4jConnection


def verify_csv(csv_file: str = "readiness_labels.csv"):
    """Verify CSV file contents."""
    print("\n" + "="*80)
    print("CSV FILE VERIFICATION")
    print("="*80)
    
    if not os.path.exists(csv_file):
        print(f"✗ File not found: {csv_file}")
        return False
    
    print(f"✓ File exists: {csv_file}")
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        print(f"✓ Total labels: {len(rows)}")
        
        if rows:
            # Show first few rows
            print("\nFirst 3 labels:")
            for i, row in enumerate(rows[:3], 1):
                print(f"  {i}. {row['candidate_id']} -> {row['role_key']}: "
                      f"readiness={float(row['readiness']):.4f}")
            
            # Statistics
            readiness_values = [float(row['readiness']) for row in rows]
            role_counts = Counter(row['role_key'] for row in rows)
            
            print(f"\nReadiness Statistics:")
            print(f"  Mean: {sum(readiness_values)/len(readiness_values):.4f}")
            print(f"  Min: {min(readiness_values):.4f}")
            print(f"  Max: {max(readiness_values):.4f}")
            
            print(f"\nRoles Distribution:")
            for role, count in role_counts.most_common():
                print(f"  {role}: {count} candidates")
        
        return True
        
    except Exception as e:
        print(f"✗ Error reading CSV: {e}")
        return False


def verify_neo4j():
    """Verify Neo4j label nodes."""
    print("\n" + "="*80)
    print("NEO4J VERIFICATION")
    print("="*80)
    
    try:
        with Neo4jConnection.get_session() as session:
            # Count labels
            result = session.run("MATCH (l:ReadinessLabel) RETURN COUNT(l) AS count")
            count = result.single()["count"]
            print(f"✓ ReadinessLabel nodes: {count}")
            
            if count > 0:
                # Sample labels
                result = session.run("""
                    MATCH (l:ReadinessLabel)
                    RETURN l.candidate_id AS candidate_id, 
                           l.role_key AS role_key,
                           l.readiness AS readiness
                    ORDER BY l.readiness DESC
                    LIMIT 5
                """)
                
                print("\nTop 5 by readiness:")
                for i, record in enumerate(result, 1):
                    print(f"  {i}. {record['candidate_id']} -> {record['role_key']}: "
                          f"readiness={record['readiness']:.4f}")
                
                # Check relationships
                result = session.run("""
                    MATCH (p:Person)-[:HAS_LABEL]->(l:ReadinessLabel)
                    RETURN COUNT(*) AS count
                """)
                rel_count = result.single()["count"]
                print(f"\n✓ Person-[:HAS_LABEL]->Label relationships: {rel_count}")
                
                result = session.run("""
                    MATCH (l:ReadinessLabel)-[:FOR_ROLE]->(r:Role)
                    RETURN COUNT(*) AS count
                """)
                role_rel_count = result.single()["count"]
                print(f"✓ Label-[:FOR_ROLE]->Role relationships: {role_rel_count}")
                
                # Statistics per role
                result = session.run("""
                    MATCH (l:ReadinessLabel)
                    RETURN l.role_key AS role,
                           COUNT(*) AS count,
                           AVG(l.readiness) AS avg_readiness
                    ORDER BY avg_readiness DESC
                """)
                
                print("\nPer-Role Statistics:")
                for record in result:
                    print(f"  {record['role']}: n={record['count']}, "
                          f"avg_readiness={record['avg_readiness']:.4f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error querying Neo4j: {e}")
        return False


def verify_candidate_role_structure():
    """Verify Neo4j has the required structure."""
    print("\n" + "="*80)
    print("DATA STRUCTURE VERIFICATION")
    print("="*80)
    
    try:
        with Neo4jConnection.get_session() as session:
            # Check Person nodes with candidate_id
            result = session.run("""
                MATCH (p:Person)
                WHERE p.candidate_id IS NOT NULL
                RETURN COUNT(p) AS count
            """)
            person_count = result.single()["count"]
            print(f"✓ Person nodes with candidate_id: {person_count}")
            
            # Check Role nodes
            result = session.run("""
                MATCH (r:Role)
                WHERE r.role_key IS NOT NULL
                RETURN COUNT(r) AS count
            """)
            role_count = result.single()["count"]
            print(f"✓ Role nodes with role_key: {role_count}")
            
            # Check TARGETS_ROLE relationships
            result = session.run("""
                MATCH (p:Person)-[:TARGETS_ROLE]->(r:Role)
                WHERE p.candidate_id IS NOT NULL AND r.role_key IS NOT NULL
                RETURN COUNT(*) AS count
            """)
            targets_count = result.single()["count"]
            print(f"✓ Person-[:TARGETS_ROLE]->Role relationships: {targets_count}")
            
            if targets_count == 0:
                print("\n⚠ WARNING: No TARGETS_ROLE relationships found!")
                print("  You need to create these relationships before running build_readiness_labels.py")
                print("\n  Example query to create relationships:")
                print("  MATCH (p:Person), (r:Role)")
                print("  WHERE p.candidate_id IS NOT NULL AND r.role_key IS NOT NULL")
                print("  // Add your logic here to determine which candidates target which roles")
                print("  CREATE (p)-[:TARGETS_ROLE]->(r)")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ Error verifying structure: {e}")
        return False


def main():
    """Main verification function."""
    print("="*80)
    print("READINESS LABELS VERIFICATION")
    print("="*80)
    
    # Check data structure
    structure_ok = verify_candidate_role_structure()
    
    # Check CSV
    csv_ok = verify_csv()
    
    # Check Neo4j labels
    neo4j_ok = verify_neo4j()
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    print(f"Data Structure: {'✓ PASS' if structure_ok else '✗ FAIL'}")
    print(f"CSV File: {'✓ PASS' if csv_ok else '✗ FAIL'}")
    print(f"Neo4j Labels: {'✓ PASS' if neo4j_ok else '✗ FAIL'}")
    
    if structure_ok and csv_ok and neo4j_ok:
        print("\n✓ All checks passed! Labels are ready for GNN training.")
    else:
        print("\n✗ Some checks failed. Please review the errors above.")
    
    print("="*80)


if __name__ == "__main__":
    main()
