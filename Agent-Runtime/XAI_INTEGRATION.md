# Runtime Explainable AI (XAI) Integration

## Overview

The Agent Runtime now includes **runtime explainability** at two levels:
1. **Skill-level**: Shows which skills contribute most to the skill gap
2. **SHAP-level**: Machine learning model feature importance using SHAP values

## Architecture

```
POST /agent/run
    ↓
    ├─ Extractor → Normalizer → KG Writer → Gap Analyzer
    ↓
    └─ XAI Service (if include_xai=true)
         ├─ Skill-level explanation (from deficits)
         └─ SHAP-level explanation (from ML model)
```

## Endpoints

### 1. GET /runtime/skill-explain

**Purpose**: Explains which skills contribute most to the gap.

**Query Parameters**:
- `candidate_id`: Candidate ID (required)
- `role_key`: Target role (required)
- `top_n`: Number of top contributors (default: 10)

**Response**:
```json
{
  "candidate_id": "CAND_ML_2024_001",
  "role_key": "ai_ml_engineer",
  "top_contributors": [
    {
      "skill_name": "TensorFlow",
      "deficit": 12.45,
      "importance": 0.85,
      "match_strength": 0.0,
      "contribution_percent": 18.5
    }
  ],
  "total_deficit": 67.3
}
```

**Formula**: `contribution_percent = (deficit / sum(all_deficits)) × 100`

---

### 2. GET /runtime/predict-explain

**Purpose**: SHAP-based feature importance for skill gap prediction.

**Query Parameters**:
- `candidate_id`: Candidate ID (required)
- `role_key`: Target role (required)
- `top_k`: Number of top features (default: 10)

**Response**:
```json
{
  "enabled": true,
  "candidate_id": "CAND_ML_2024_001",
  "role_key": "ai_ml_engineer",
  "skill_gap_prediction": 0.4523,
  "readiness_prediction": 0.5477,
  "top_positive_contributors": [
    {"feature": "experience_months", "impact": -0.15},
    {"feature": "num_projects", "impact": -0.08}
  ],
  "top_negative_contributors": [
    {"feature": "experience_level_Fresher", "impact": 0.12}
  ],
  "base_value": 0.50
}
```

**Note**: 
- Positive impact = **increases** skill gap (bad)
- Negative impact = **decreases** skill gap (good)

---

### 3. POST /agent/run (Updated)

**New Query Parameter**: `include_xai` (default: `true`)

**Response** now includes `xai` field:
```json
{
  "candidate_id": "...",
  "role_key": "...",
  "status": "success",
  "readiness_score": 0.65,
  "skill_gap_top": [...],
  "xai": {
    "skill_level": {
      "candidate_id": "...",
      "role_key": "...",
      "top_contributors": [...]
    },
    "shap_level": {
      "enabled": true,
      "skill_gap_prediction": 0.45,
      "top_positive_contributors": [...],
      "top_negative_contributors": [...]
    }
  }
}
```

## Setup

### 1. Install Dependencies

```bash
cd Agent-Runtime
pip install -r requirements.txt
```

**Key additions**:
- `shap>=0.43.0` - SHAP explainability
- `joblib>=1.3.0` - Model loading
- `pandas>=2.0.0` - Data handling
- `scikit-learn>=1.3.0` - Model support

### 2. Place Trained Model

Put your trained model pipeline at:
```
Agent-Runtime/
  └── models/
       └── skillgap_pipeline.joblib
```

The model should be a scikit-learn Pipeline with:
- Preprocessing (encoding, scaling)
- Final estimator (RandomForest, XGBoost, etc.)

**Expected features** (in order):
1. `role_key` (categorical)
2. `experience_level` (categorical)
3. `experience_months` (numeric)
4. `num_skills` (numeric)
5. `num_projects` (numeric)
6. `num_work_experiences` (numeric)
7. `avg_mastery_confidence` (numeric)
8. `role_skill_coverage` (numeric)
9. `role_project_relevance` (numeric)
10. `institution_name` (categorical)

### 3. Run Server

```bash
uvicorn main:app --reload --port 8003
```

XAI service loads at startup. Check logs:
```
Loading model from models/skillgap_pipeline.joblib...
Creating SHAP TreeExplainer...
✓ Model and explainer loaded successfully
```

If model not found:
```
Model file not found: models/skillgap_pipeline.joblib
XAI endpoints will return enabled=false
```

## Feature Engineering

The XAI service automatically computes features from Neo4j:

### Direct from Neo4j:
- `experience_level` (Person property)
- `experience_months` (Person property)
- `num_skills` (count of HAS_SKILL edges)
- `num_projects` (count of WORKED_ON edges)
- `num_work_experiences` (count of WORKED_AT edges)
- `institution_name` (Education node property)

### Computed:
- `avg_mastery_confidence`: From `/candidates/{id}/skill-confidence` API
- `role_skill_coverage`: Fraction of top role skills matched (graded)
- `role_project_relevance`: Fraction of project skills matching role

### Defaults (if missing):
- `experience_months`: Derived from `experience_level`
  - Fresher → 0 months
  - Junior → 12 months
  - Mid → 36 months
- `avg_mastery_confidence`: 0.50
- Coverage/relevance: 0.0

## API Behavior

### If Model Missing

SHAP endpoint returns:
```json
{
  "enabled": false,
  "reason": "Model not loaded (file missing or SHAP not installed)"
}
```

Skill-level explanation still works (doesn't need ML model).

### Error Handling

- XAI errors are **non-fatal** in `/agent/run`
- If XAI fails, `xai` field is `null`, but pipeline succeeds
- Standalone endpoints (`/runtime/*`) return proper error responses

## Testing

### Test Skill-level Explanation
```bash
curl "http://localhost:8003/runtime/skill-explain?candidate_id=CAND_ML_2024_001&role_key=ai_ml_engineer&top_n=10"
```

### Test SHAP Explanation
```bash
curl "http://localhost:8003/runtime/predict-explain?candidate_id=CAND_ML_2024_001&role_key=ai_ml_engineer&top_k=10"
```

### Test Full Pipeline
```bash
curl -X POST "http://localhost:8003/agent/run?role_key=ai_ml_engineer&top_k=25&include_xai=true" \
  -H "Content-Type: application/json" \
  -d @sample_extracted_cv_1.json
```

## Performance

### Skill-level Explanation
- **Fast**: ~50ms (just arithmetic on existing deficits)
- No additional API calls

### SHAP Explanation
- **Moderate**: ~200-500ms
  - Feature extraction: ~100ms (Neo4j queries)
  - SHAP computation: ~100-400ms (single row)
- Uses cached model/explainer (loaded once at startup)
- TreeExplainer optimized for tree-based models

### Recommendations
- Keep `top_k ≤ 10` for SHAP (default)
- Use `include_xai=false` if explainability not needed
- SHAP works best with tree-based models (faster than neural nets)

## Model Requirements

Your saved model (`skillgap_pipeline.joblib`) must:

1. **Be a scikit-learn Pipeline or compatible estimator**
2. **Accept the 10 features** listed above (in that order)
3. **Predict a single float** (skill_gap_index from 0-1)
4. **Be tree-based for TreeExplainer** (or use KernelExplainer)

**Supported models**:
- ✅ RandomForestRegressor
- ✅ GradientBoostingRegressor
- ✅ XGBRegressor
- ✅ LGBMRegressor
- ⚠️ Linear models (slower SHAP, use KernelExplainer)
- ⚠️ Neural networks (slower SHAP, use DeepExplainer)

## Logging

XAI service logs:
```
[INFO] Loading model from models/skillgap_pipeline.joblib...
[INFO] Creating SHAP TreeExplainer...
[INFO] ✓ Model and explainer loaded successfully
[INFO] Built feature row: {'role_key': 'ai_ml_engineer', ...}
[INFO] Skill explain: candidate=CAND_ML_2024_001, role=ai_ml_engineer
[INFO] Predict explain: candidate=CAND_ML_2024_001, role=ai_ml_engineer
```

Warnings (non-fatal):
```
[WARNING] SHAP library not installed. Install with: pip install shap
[WARNING] Model file not found: models/skillgap_pipeline.joblib
[WARNING] Failed to get mastery confidence: Connection timeout
[WARNING] XAI computation failed (non-fatal): <error>
```

## Swagger UI

Full API documentation at:
```
http://localhost:8003/docs
```

New endpoints appear under:
- **Explainability** tag: `/runtime/skill-explain`, `/runtime/predict-explain`
- **Agent** tag: `/agent/run` (with updated response schema)

## Example Use Case

**Frontend flow**:
1. Submit CV via `/agent/run`
2. Display readiness score (e.g., 65%)
3. Show skill-level explanation:
   - "TensorFlow contributes 18.5% to your gap"
   - "PyTorch contributes 15.3% to your gap"
4. Show SHAP explanation:
   - "Your 3 projects reduce gap by 8%"
   - "Being a Fresher increases gap by 12%"
5. Recommend upskilling in top deficit skills

## Troubleshooting

### "enabled: false" in SHAP response

**Reasons**:
1. Model file not found → Check `models/skillgap_pipeline.joblib`
2. SHAP not installed → Run `pip install shap`
3. Candidate not in Neo4j → Check candidate_id
4. Feature extraction failed → Check Neo4j connectivity

**Fix**: Check startup logs for specific error

### SHAP computation slow

**Solutions**:
1. Reduce `top_k` parameter (default: 10)
2. Use tree-based model (RandomForest, XGBoost)
3. Ensure model is cached (loaded once at startup)

### Skill-level explanation empty

**Cause**: No skill deficits found (candidate matches role perfectly)

**Expected**: `top_contributors: []`, `total_deficit: 0.0`

## Summary

✅ **Skill-level**: Fast, always available, shows deficit contributions  
✅ **SHAP-level**: Moderate speed, requires model, shows feature impacts  
✅ **Integrated**: Automatically included in `/agent/run` response  
✅ **Standalone**: Can call `/runtime/skill-explain` and `/runtime/predict-explain` independently  
✅ **Graceful degradation**: XAI failures don't break pipeline
