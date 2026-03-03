# Category Fix for Hybrid Endpoint

## Problem
The hybrid endpoint was returning `"category": "Unknown"` for all skills because the `RoleImportanceService` wasn't fetching category information from the database.

## Root Cause
In `services/role_importance_service.py`, the TF-IDF computation query didn't include the `BELONGS_TO_CATEGORY` relationship, so category data was never retrieved or returned.

## Solution
Updated `RoleImportanceService.compute_role_importance()` to:

1. **Join with SkillCategory** in the Cypher query:
```cypher
OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(cat:SkillCategory)
...
RETURN ... COALESCE(cat.name, 'Uncategorized') AS category
```

2. **Include category in returned data**:
```python
skill_importance[skill_name] = {
    "tf": tf,
    "df": df,
    "idf": idf,
    "importance": importance,
    "percentage": percentage,
    "category": category,  # NEW
}
```

3. **Changed default fallback** from "Unknown" to "Uncategorized" for consistency

## Files Modified
- ✅ `services/role_importance_service.py` (3 changes)
- ✅ `services/hybrid_ranking_service.py` (1 change - default fallback)
- ✅ Cache cleared to force fresh data fetch

## Test Results
```
Sample skill: Python
Fields: ['tf', 'df', 'idf', 'importance', 'percentage', 'category']
✓ Category field present: 'Programming Languages'

Category coverage:
  Total skills: 230
  With category: 230 (100.0%)
  Uncategorized: 0 (0.0%)
```

## Expected Output (After Fix)

### Before:
```json
{
  "skill": "Tableau",
  "category": "Unknown",  ❌
  "final_score": 0.812279224395752,
  ...
}
```

### After:
```json
{
  "skill": "Tableau",
  "category": "Business Intelligence (BI) & Visualization",  ✅
  "final_score": 0.812279224395752,
  ...
}
```

## Verify the Fix

### 1. Test the hybrid endpoint:
```bash
curl "http://localhost:8001/candidates/{candidate_id}/roles/{role_key}/skill-gap-hybrid?top_k=25"
```

### 2. Check response for proper categories:
- Categories should show actual names like "Programming Languages", "Cloud & Infrastructure", etc.
- Only skills without mappings in Neo4j will show "Uncategorized"

### 3. Sample categories you should see:
- Programming Languages
- Cloud & Infrastructure
- Machine Learning
- Deep Learning
- DevOps & CI/CD
- Databases & Data Modeling
- Data Engineering & Pipelines
- Business Intelligence (BI) & Visualization
- Backend Development
- LLM & Generative AI
- ... and more

## Impact on Other Endpoints

This fix also benefits:
- ✅ `/candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced` (symbolic ranking)
- ✅ `/roles/{role_key}/skill-profile` (role skill profiles)
- ✅ Any service using `RoleImportanceService.compute_role_importance()`

The GNN endpoint (`/missing-skills-gnn`) was already retrieving categories separately via `CategoryService.get_skill_category()`, so it was unaffected.

## Status
✅ **FIXED** - Categories now properly retrieved and displayed in all endpoints
✅ **TESTED** - 100% category coverage for ai_ml_engineer role
✅ **DEPLOYED** - API server restarted with changes at 2026-02-08 10:04:31
