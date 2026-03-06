# Quick Start: Runtime EXAI

## 1-Minute Setup

```bash
# 1. Install dependencies
cd Agent-Runtime
pip install -r requirements.txt

# 2. Place your trained model
# Copy skillgap_pipeline.joblib to models/

# 3. Start server
uvicorn main:app --reload --port 8003

# 4. Check startup logs
# Look for: "✓ Model and explainer loaded successfully"

# 5. Test endpoints
python test_xai_integration.py
```

## Quick Test

### Test 1: Skill-level Explainability
```bash
curl "http://localhost:8003/runtime/skill-explain?candidate_id=CAND_ML_2024_001&role_key=ai_ml_engineer&top_n=10"
```

**Expected Output**:
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

### Test 2: SHAP-level Explainability
```bash
curl "http://localhost:8003/runtime/predict-explain?candidate_id=CAND_ML_2024_001&role_key=ai_ml_engineer&top_k=10"
```

**Expected Output**:
```json
{
  "enabled": true,
  "candidate_id": "CAND_ML_2024_001",
  "role_key": "ai_ml_engineer",
  "skill_gap_prediction": 0.4523,
  "readiness_prediction": 0.5477,
  "top_positive_contributors": [
    {"feature": "experience_level_Fresher", "impact": 0.12}
  ],
  "top_negative_contributors": [
    {"feature": "num_projects", "impact": -0.08}
  ]
}
```

### Test 3: Full Pipeline with XAI
```bash
curl -X POST "http://localhost:8003/agent/run?role_key=ai_ml_engineer&top_k=25&include_xai=true" \
  -H "Content-Type: application/json" \
  -d @sample_extracted_cv_1.json
```

## Common Issues

### Issue: "enabled: false" in SHAP response

**Reason 1**: Model file not found
```bash
# Solution:
ls models/skillgap_pipeline.joblib  # Should exist
```

**Reason 2**: SHAP not installed
```bash
# Solution:
pip install shap
```

**Reason 3**: Candidate not in Neo4j
```bash
# Solution: Run /agent/run first to write candidate to Neo4j
```

### Issue: SHAP computation slow

**Solution**: Use tree-based model (RandomForest, XGBoost)
```python
# When training model:
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor()  # Fast SHAP
# NOT: LinearRegression()  # Slow SHAP
```

### Issue: Feature shape mismatch

**Error**: `X has 9 features but model expects 10`

**Solution**: Check your model's expected features
```python
# In model training:
features = [
    'role_key', 'experience_level', 'experience_months',
    'num_skills', 'num_projects', 'num_work_experiences',
    'avg_mastery_confidence', 'role_skill_coverage',
    'role_project_relevance', 'institution_name'
]
```

## API Endpoints

| Endpoint | Method | Purpose | Speed |
|----------|--------|---------|-------|
| `/runtime/skill-explain` | GET | Skill contributions | Fast (50ms) |
| `/runtime/predict-explain` | GET | SHAP explanations | Moderate (300ms) |
| `/agent/run?include_xai=true` | POST | Full pipeline + XAI | Slow (1.7s) |

## Swagger UI

Full API documentation:
```
http://localhost:8003/docs
```

## Minimal Model Training Example

```python
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline

# Load your training data
df = pd.read_csv('skillgap_dataset.csv')

# Features
features = [
    'role_key', 'experience_level', 'experience_months',
    'num_skills', 'num_projects', 'num_work_experiences',
    'avg_mastery_confidence', 'role_skill_coverage',
    'role_project_relevance', 'institution_name'
]

X = df[features]
y = df['skill_gap_index']

# Create pipeline
preprocessor = ColumnTransformer([
    ('cat', OneHotEncoder(handle_unknown='ignore'), 
     ['role_key', 'experience_level', 'institution_name']),
    ('num', StandardScaler(), 
     ['experience_months', 'num_skills', 'num_projects',
      'num_work_experiences', 'avg_mastery_confidence',
      'role_skill_coverage', 'role_project_relevance'])
])

model = Pipeline([
    ('preprocessor', preprocessor),
    ('regressor', RandomForestRegressor(n_estimators=100, random_state=42))
])

# Train
model.fit(X, y)

# Save
joblib.dump(model, 'Agent-Runtime/models/skillgap_pipeline.joblib')
print("✓ Model saved!")
```

## Frontend Integration Example

```javascript
// Call full pipeline with XAI
const response = await fetch(
  `http://localhost:8003/agent/run?role_key=ai_ml_engineer&top_k=25&include_xai=true`,
  {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(cvData)
  }
);

const data = await response.json();

// Display readiness
console.log(`Readiness: ${(data.readiness_score * 100).toFixed(1)}%`);

// Display skill-level explanation
if (data.xai?.skill_level) {
  console.log('Top skill gaps:');
  data.xai.skill_level.top_contributors.forEach(skill => {
    console.log(`  ${skill.skill_name}: ${skill.contribution_percent}% of gap`);
  });
}

// Display SHAP explanation
if (data.xai?.shap_level?.enabled) {
  const shap = data.xai.shap_level;
  console.log(`Predicted readiness: ${(shap.readiness_prediction * 100).toFixed(1)}%`);
  
  console.log('Features reducing gap:');
  shap.top_negative_contributors.forEach(feat => {
    console.log(`  ${feat.feature}: ${(-feat.impact * 100).toFixed(1)}%`);
  });
}
```

## Performance Tuning

### Reduce SHAP computation time
```python
# In xai_service.py, line ~340:
def compute_shap_explanation(self, feature_row, top_k=5):  # Reduce from 10
```

### Disable XAI by default
```python
# In main.py, line ~150:
include_xai: bool = Query(False, description="...")  # Change from True
```

### Cache feature rows (TODO)
```python
# Add Redis/in-memory cache for feature rows
# Avoid repeated Neo4j queries for same candidate+role
```

## Next Steps

1. ✅ Test endpoints work
2. ✅ Verify model predictions are reasonable
3. ✅ Check SHAP values make sense
4. ✅ Integrate into frontend UI
5. ✅ Monitor performance in production
6. ✅ Collect user feedback on explanations

## Documentation

- **XAI_INTEGRATION.md**: Complete user guide
- **EXAI_ARCHITECTURE.md**: Architecture diagrams
- **EXAI_IMPLEMENTATION_SUMMARY.md**: Technical summary
- **Swagger UI** (`/docs`): Interactive API docs

## Support

Check logs for errors:
```bash
# Startup logs
✓ Model and explainer loaded successfully

# Runtime logs
[INFO] Skill explain: candidate=..., role=...
[INFO] Built feature row: {...}
[INFO] ✓ XAI computed successfully
```

Common warnings (non-fatal):
```bash
[WARNING] Failed to get mastery confidence: <reason>
[WARNING] XAI computation failed (non-fatal): <error>
```

---

**Ready to go!** 🚀

Your Agent Runtime now has full explainability at two levels:
- **Skill-level**: "TensorFlow contributes 18.5% to your gap"
- **SHAP-level**: "Your 3 projects reduce gap by 8%"
