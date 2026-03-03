# ML Models Directory

## Purpose

This directory stores trained machine learning models for runtime prediction and explainability.

## Required File

Place your trained skill gap prediction model here:

```
ml_models/
  └── skillgap_pipeline.joblib
```

## Model Requirements

The model must be:

1. **A scikit-learn Pipeline** (or compatible estimator)
2. **Trained on these 10 features** (in this order):
   - `role_key` (categorical)
   - `experience_level` (categorical)
   - `experience_months` (numeric)
   - `num_skills` (numeric)
   - `num_projects` (numeric)
   - `num_work_experiences` (numeric)
   - `avg_mastery_confidence` (numeric)
   - `role_skill_coverage` (numeric)
   - `role_project_relevance` (numeric)
   - `institution_name` (categorical)

3. **Predicts a single float**: `skill_gap_index` (range 0-1)

4. **Tree-based preferred**: RandomForest, GradientBoosting, XGBoost, LightGBM
   - Faster SHAP computation with TreeExplainer
   - Linear/neural models work but slower

## Example Training Script

```python
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline

# Load training data
df = pd.read_csv('path/to/skillgap_dataset.csv')

# Define features
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

pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('regressor', RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42
    ))
])

# Train
pipeline.fit(X, y)

# Save
joblib.dump(pipeline, 'Agent-Runtime/ml_models/skillgap_pipeline.joblib')
print("✓ Model saved to ml_models/skillgap_pipeline.joblib")
```

## Verification

After placing the model, start the server and check logs:

```bash
uvicorn main:app --reload --port 8003
```

**Expected logs**:
```
Loading model from ml_models/skillgap_pipeline.joblib...
Creating SHAP TreeExplainer...
✓ Model and explainer loaded successfully
```

**If model not found**:
```
Model file not found: ml_models/skillgap_pipeline.joblib
XAI endpoints will return enabled=false
```

## Testing

Test SHAP explanation:
```bash
curl "http://localhost:8003/runtime/predict-explain?candidate_id=CAND_ML_2024_001&role_key=ai_ml_engineer"
```

**Expected**: `"enabled": true` with SHAP values

**If model missing**: `"enabled": false, "reason": "Model not loaded"`

## Model Performance Metrics

Document your model's performance here:

| Metric | Value |
|--------|-------|
| R² Score | ??? |
| MAE | ??? |
| RMSE | ??? |
| Training samples | ??? |
| Model size | ??? MB |

## Version History

| Date | Version | Changes | Performance |
|------|---------|---------|-------------|
| YYYY-MM-DD | 1.0 | Initial model | ??? |

## Notes

- Model is loaded once at startup and cached in memory
- SHAP explainer is created at startup (~2-3 seconds)
- Runtime predictions are fast (~200-300ms per sample)
- Update this README when deploying new model versions
