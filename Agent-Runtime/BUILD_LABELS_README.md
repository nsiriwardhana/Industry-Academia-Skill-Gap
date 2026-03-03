# Readiness Label Builder

Generates training labels for GNN readiness prediction by computing skill gap index and readiness scores for all candidate-role pairs.

## Overview

This script:
1. Fetches all candidate-role pairs from Neo4j
2. Computes skill gap index and readiness using the existing advanced skill gap engine
3. Saves results to CSV
4. Writes labels back to Neo4j as `ReadinessLabel` nodes

## Architecture

```
Neo4j Query → GapAnalyzer → Advanced API → Skill Gap Computation
                                ↓
                          Label Creation
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
            CSV Output              Neo4j Labels
        readiness_labels.csv    (:ReadinessLabel)
```

## Requirements

### Services Running
- **Neo4j**: bolt://localhost:7687
- **Advanced-Recommendation-System**: http://localhost:8001

### Python Dependencies
All dependencies are already in your project:
- `neo4j`
- `requests`
- Standard library modules

## Usage

### Basic Usage
```bash
cd "F:\CV Parser Agent\Agent-Runtime"
python build_readiness_labels.py
```

### Advanced Options
```bash
# Custom output filename
python build_readiness_labels.py --output my_labels.csv

# Adjust rate limiting (0.5 second delay between API calls)
python build_readiness_labels.py --rate-limit 0.5

# Skip writing to Neo4j (CSV only)
python build_readiness_labels.py --no-neo4j

# Combine options
python build_readiness_labels.py --output labels_2025.csv --rate-limit 0.2
```

## Output Files

### 1. CSV File: `readiness_labels.csv`
Columns:
- `candidate_id`: Candidate identifier
- `role_key`: Target role key
- `skill_gap_index`: Computed skill gap (0-1, higher = more gap)
- `readiness`: 1 - skill_gap_index (0-1, higher = better)
- `total_deficit`: Sum of all skill deficits
- `total_importance`: Sum of all skill importances
- `num_deficits`: Number of missing/weak skills
- `matched_required_skills`: Number of skills candidate has
- `role_skill_coverage`: Proportion of role skills matched

Example:
```csv
candidate_id,role_key,skill_gap_index,readiness,total_deficit,total_importance,num_deficits,matched_required_skills,role_skill_coverage
CAND_001,ai_ml_engineer,0.3456,0.6544,45.23,130.89,12,8,0.6667
CAND_002,data_scientist,0.2134,0.7866,28.45,133.42,10,12,0.5455
```

### 2. Neo4j Nodes: `ReadinessLabel`
Created in Neo4j with relationships:
```cypher
(Person)-[:HAS_LABEL]->(ReadinessLabel)-[:FOR_ROLE]->(Role)
```

Node properties:
```cypher
(:ReadinessLabel {
  candidate_id: "CAND_001",
  role_key: "ai_ml_engineer",
  skill_gap_index: 0.3456,
  readiness: 0.6544,
  total_deficit: 45.23,
  total_importance: 130.89,
  num_deficits: 12,
  matched_required_skills: 8,
  role_skill_coverage: 0.6667,
  created_at: datetime(),
  label_version: "v1.0"
})
```

### 3. Log File: `build_readiness_labels.log`
Detailed execution log with timestamps

## Example Run

```bash
$ python build_readiness_labels.py
2025-12-29 10:30:15 - INFO - ================================================================================
2025-12-29 10:30:15 - INFO - READINESS LABEL BUILDER - Starting
2025-12-29 10:30:15 - INFO - ================================================================================
2025-12-29 10:30:15 - INFO - Neo4j URI: bolt://localhost:7687
2025-12-29 10:30:15 - INFO - Recommendation API: http://localhost:8001
2025-12-29 10:30:15 - INFO - Output CSV: readiness_labels.csv
2025-12-29 10:30:15 - INFO - ✓ Recommendation API is healthy
2025-12-29 10:30:16 - INFO - Fetching candidate-role pairs from Neo4j...
2025-12-29 10:30:16 - INFO - ✓ Found 25 candidate-role pairs
2025-12-29 10:30:16 - INFO - 
2025-12-29 10:30:16 - INFO - Processing 25 candidate-role pairs...
2025-12-29 10:30:17 - INFO - [1/25] Processing: CAND_001 -> ai_ml_engineer
2025-12-29 10:30:17 - INFO - ✓ Computed: skill_gap=0.3456, readiness=0.6544, deficits=12
2025-12-29 10:30:17 - INFO - ✓ Wrote label to Neo4j
...
2025-12-29 10:30:45 - INFO - ✓ CSV saved successfully
2025-12-29 10:30:45 - INFO - 
2025-12-29 10:30:45 - INFO - ================================================================================
2025-12-29 10:30:45 - INFO - SUMMARY STATISTICS
2025-12-29 10:30:45 - INFO - ================================================================================
2025-12-29 10:30:45 - INFO - Total pairs processed: 25
2025-12-29 10:30:45 - INFO - Successfully computed: 23
2025-12-29 10:30:45 - INFO - Failed: 2
2025-12-29 10:30:45 - INFO - 
2025-12-29 10:30:45 - INFO - Overall Metrics:
2025-12-29 10:30:45 - INFO -   Mean Readiness: 0.6234
2025-12-29 10:30:45 - INFO -   Min Readiness: 0.3456
2025-12-29 10:30:45 - INFO -   Max Readiness: 0.9123
2025-12-29 10:30:45 - INFO -   Mean Skill Gap Index: 0.3766
2025-12-29 10:30:45 - INFO - 
2025-12-29 10:30:45 - INFO - Per-Role Statistics:
2025-12-29 10:30:45 - INFO -   ai_ml_engineer: n=8, mean_readiness=0.5845
2025-12-29 10:30:45 - INFO -   data_scientist: n=7, mean_readiness=0.6723
2025-12-29 10:30:45 - INFO -   backend_engineer: n=8, mean_readiness=0.6145
2025-12-29 10:30:45 - INFO - ✓ Process completed in 28.43 seconds
2025-12-29 10:30:45 - INFO - ✓ Output saved to: readiness_labels.csv
2025-12-29 10:30:45 - INFO - ✓ Labels written to Neo4j as ReadinessLabel nodes
```

## Neo4j Query Examples

### View all labels
```cypher
MATCH (label:ReadinessLabel)
RETURN label
ORDER BY label.readiness DESC
LIMIT 10
```

### View labels for a specific candidate
```cypher
MATCH (p:Person {candidate_id: "CAND_001"})-[:HAS_LABEL]->(label:ReadinessLabel)
RETURN p.candidate_id, label.role_key, label.readiness, label.skill_gap_index
ORDER BY label.readiness DESC
```

### View labels for a specific role
```cypher
MATCH (label:ReadinessLabel {role_key: "ai_ml_engineer"})
RETURN label.candidate_id, label.readiness
ORDER BY label.readiness DESC
LIMIT 10
```

### Get statistics per role
```cypher
MATCH (label:ReadinessLabel)
RETURN 
  label.role_key AS role,
  COUNT(*) AS count,
  AVG(label.readiness) AS avg_readiness,
  MIN(label.readiness) AS min_readiness,
  MAX(label.readiness) AS max_readiness
ORDER BY avg_readiness DESC
```

### Delete all labels (if you need to rebuild)
```cypher
MATCH (label:ReadinessLabel)
DETACH DELETE label
```

## Troubleshooting

### Error: "Recommendation API is not available"
**Solution**: Start the Advanced-Recommendation-System
```bash
cd "F:\CV Parser Agent\Advanced-Recommendation-System"
python main.py
```

### Error: "Failed to connect to Neo4j"
**Solution**: 
1. Check Neo4j is running
2. Verify credentials in `.env` file
3. Test connection: `bolt://localhost:7687`

### Error: "No candidate-role pairs found"
**Solution**: Check your Neo4j data has the required structure:
```cypher
MATCH (p:Person)-[:TARGETS_ROLE]->(r:Role)
WHERE p.candidate_id IS NOT NULL
RETURN COUNT(*) AS pair_count
```

If count is 0, you need to create the relationships:
```cypher
MATCH (p:Person), (r:Role)
WHERE p.candidate_id IS NOT NULL AND r.role_key IS NOT NULL
// Add your logic to determine target roles
CREATE (p)-[:TARGETS_ROLE]->(r)
```

### Warning: "No deficits found (perfect match or no role skills)"
This is normal for candidates who perfectly match the role requirements. The label will have `readiness=1.0` and `skill_gap_index=0.0`.

### High failure rate (>20%)
**Common causes**:
1. Missing candidate data in Neo4j
2. Missing role skill profiles
3. API timeout issues

**Solution**: Check the log file for specific error messages and fix data issues.

## Rate Limiting

The script includes rate limiting to avoid overloading the API:
- Default: 0.1 seconds between calls (10 requests/second)
- Adjust with `--rate-limit` flag
- For large datasets (>100 pairs), use `--rate-limit 0.2` or higher

## Performance

Expected processing time:
- **Small dataset** (<50 pairs): 5-15 seconds
- **Medium dataset** (50-200 pairs): 30-90 seconds  
- **Large dataset** (>200 pairs): 2-5 minutes

Performance factors:
- API response time (dominant factor)
- Neo4j query speed
- Network latency
- Rate limiting delay

## Integration with GNN

Once labels are generated, use them for GNN training:

```python
# In your GNN training script
from neo4j import GraphDatabase

# Fetch labels for training
query = """
MATCH (p:Person)-[:HAS_LABEL]->(label:ReadinessLabel)
RETURN p.candidate_id, label.role_key, label.readiness
"""

# Use readiness as target variable for node regression
# Use skill_gap_index for classification (threshold at 0.5)
```

## Next Steps

1. **Generate labels**: Run this script
2. **Verify data**: Check CSV and Neo4j nodes
3. **Train GNN**: Use labels as supervision signal
4. **Evaluate**: Compare GNN predictions vs these labels
5. **Iterate**: Regenerate labels as data changes

## Support

For issues or questions:
1. Check log file: `build_readiness_labels.log`
2. Review error messages in console
3. Verify services are running
4. Check Neo4j data structure
