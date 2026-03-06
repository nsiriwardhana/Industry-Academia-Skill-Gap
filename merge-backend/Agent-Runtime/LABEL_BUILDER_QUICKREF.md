# Readiness Label Builder - Quick Reference

## 🚀 Quick Start (3 Steps)

### Step 1: Check Prerequisites
```bash
cd "F:\CV Parser Agent\Agent-Runtime"
python setup_label_builder.py
```
This checks:
- ✓ Neo4j connection
- ✓ Recommendation API
- ✓ Required data structure
- ✓ TARGETS_ROLE relationships

### Step 2: Build Labels
```bash
python build_readiness_labels.py
```
Output:
- `readiness_labels.csv` - Training data
- `build_readiness_labels.log` - Execution log
- Neo4j `ReadinessLabel` nodes

### Step 3: Verify Results
```bash
python verify_readiness_labels.py
```
Validates:
- ✓ CSV file contents
- ✓ Neo4j label nodes
- ✓ Relationships
- ✓ Statistics

---

## 📊 Output Structure

### CSV Columns
```
candidate_id, role_key, skill_gap_index, readiness, 
total_deficit, total_importance, num_deficits,
matched_required_skills, role_skill_coverage
```

### Neo4j Structure
```
(Person)-[:HAS_LABEL]->(ReadinessLabel)-[:FOR_ROLE]->(Role)
```

---

## 🛠️ Common Commands

### Generate labels (basic)
```bash
python build_readiness_labels.py
```

### Custom output file
```bash
python build_readiness_labels.py --output labels_2025_12_29.csv
```

### CSV only (skip Neo4j write)
```bash
python build_readiness_labels.py --no-neo4j
```

### Slower processing (reduce API load)
```bash
python build_readiness_labels.py --rate-limit 0.5
```

---

## 🔍 Neo4j Queries

### View all labels
```cypher
MATCH (l:ReadinessLabel)
RETURN l.candidate_id, l.role_key, l.readiness
ORDER BY l.readiness DESC
LIMIT 10
```

### Statistics per role
```cypher
MATCH (l:ReadinessLabel)
RETURN l.role_key AS role,
       COUNT(*) AS count,
       AVG(l.readiness) AS avg_readiness,
       MIN(l.readiness) AS min_readiness,
       MAX(l.readiness) AS max_readiness
ORDER BY avg_readiness DESC
```

### Find high-readiness candidates
```cypher
MATCH (p:Person)-[:HAS_LABEL]->(l:ReadinessLabel)
WHERE l.readiness >= 0.8
RETURN p.candidate_id, p.candidate_name, 
       l.role_key, l.readiness
ORDER BY l.readiness DESC
```

### Delete all labels (rebuild)
```cypher
MATCH (l:ReadinessLabel)
DETACH DELETE l
```

---

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| API not available | Start Advanced-Recommendation-System:<br>`cd "F:\CV Parser Agent\Advanced-Recommendation-System"`<br>`python main.py` |
| Neo4j connection failed | Check Neo4j is running at bolt://localhost:7687 |
| No candidate-role pairs | Run `setup_label_builder.py` to create relationships |
| High failure rate | Check log file for specific errors |

---

## 📈 Performance

| Dataset Size | Expected Time |
|-------------|---------------|
| < 50 pairs | 5-15 seconds |
| 50-200 pairs | 30-90 seconds |
| > 200 pairs | 2-5 minutes |

Rate limit: 0.1s delay = 10 requests/sec (default)

---

## 📁 Files Created

| File | Description |
|------|-------------|
| `build_readiness_labels.py` | Main script |
| `verify_readiness_labels.py` | Verification tool |
| `setup_label_builder.py` | Prerequisites checker |
| `readiness_labels.csv` | Output data (CSV) |
| `build_readiness_labels.log` | Execution log |
| `BUILD_LABELS_README.md` | Full documentation |

---

## 🎯 Use in GNN Training

```python
import pandas as pd

# Load labels
labels = pd.read_csv('readiness_labels.csv')

# Use readiness as regression target
X = ... # Node features
y = labels['readiness'].values

# Or use skill_gap_index for classification
y_class = (labels['skill_gap_index'] > 0.5).astype(int)
```

---

## 📞 Support

Check in this order:
1. **Log file**: `build_readiness_labels.log`
2. **Verify script**: `python verify_readiness_labels.py`
3. **Setup check**: `python setup_label_builder.py`
4. **Full docs**: `BUILD_LABELS_README.md`
