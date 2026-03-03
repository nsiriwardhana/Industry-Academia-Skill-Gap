"""
Generate sample candidate-role pairs CSV for evaluation.

Quick script to extract candidate-role combinations from Neo4j.
"""
import csv
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.neo4j_connection import Neo4jConnection


def generate_sample_pairs(output_file: str = "readiness_labels.csv", n_samples: int = 500):
    """
    Generate CSV with candidate_id, role_key pairs.
    
    Samples from existing Person nodes and all available Roles.
    """
    # Initialize Neo4j connection
    neo4j = Neo4jConnection()
    
    try:
        # Query to get candidate-role pairs
        # Strategy: Get all candidates and sample role combinations
        query = """
        MATCH (p:Person)
        WHERE p.candidate_id IS NOT NULL
        WITH p
        ORDER BY rand()
        LIMIT 200
        
        MATCH (r:Role)
        WITH p, r
        LIMIT $n_samples
        
        RETURN DISTINCT 
            p.candidate_id AS candidate_id, 
            r.role_key AS role_key,
            r.name AS role_name
        ORDER BY p.candidate_id, r.role_key
        """
        
        print(f"Querying Neo4j for candidate-role pairs...")
        
        with neo4j.get_session() as session:
            result = session.run(query, n_samples=n_samples)
            results = [dict(record) for record in result]
        
        if not results:
            print("ERROR: No data found in Neo4j!")
            print("Make sure you have Person and Role nodes in the database.")
            return False
        
        # Write to CSV
        output_path = Path(output_file)
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['candidate_id', 'role_key', 'role_name'])
            writer.writeheader()
            
            for record in results:
                writer.writerow({
                    'candidate_id': record['candidate_id'],
                    'role_key': record['role_key'],
                    'role_name': record['role_name']
                })
        
        print(f"✓ Generated {len(results)} candidate-role pairs")
        print(f"✓ Saved to: {output_path.absolute()}")
        
        # Show sample
        print("\nSample rows:")
        for i, record in enumerate(results[:5]):
            print(f"  {record['candidate_id']} -> {record['role_key']} ({record['role_name']})")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        neo4j.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate sample candidate-role pairs CSV')
    parser.add_argument('--output', type=str, default='readiness_labels.csv',
                        help='Output CSV filename')
    parser.add_argument('--n_samples', type=int, default=500,
                        help='Number of pairs to generate')
    
    args = parser.parse_args()
    
    success = generate_sample_pairs(args.output, args.n_samples)
    sys.exit(0 if success else 1)
