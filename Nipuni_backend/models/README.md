# Trained Models Directory

This directory contains trained machine learning models for the SkillBridge project.

## Files

- **`skill_score_model.pkl`** - Random Forest Regressor for predicting skill scores
- **`prediction_plot.png`** - Visualization of model predictions vs actual scores

## Model Information

### Skill Score Prediction Model

- **Algorithm**: Random Forest Regressor
- **Features**: 4 (grade_normalized, credits, recency, map_weight)
- **Target**: Skill score (0-100)
- **Training Script**: `backend/scripts/model_training.py`

### Usage

```python
import pickle

# Load model
with open('backend/models/skill_score_model.pkl', 'rb') as f:
    model = pickle.load(f)

# Predict
import numpy as np
X_new = np.array([[0.85, 3.0, 0.60, 0.35]])  # [grade_norm, credits, recency, map_weight]
prediction = model.predict(X_new)
print(f"Predicted score: {prediction[0]:.2f}")
```

## Regenerating Models

To retrain the model with latest data:

```powershell
cd backend\scripts
python model_training.py
```

## Model Versioning

When updating models in production:
1. Train new model with `model_training.py`
2. Test performance with `test_model.py`
3. If performance improves, backup old model
4. Deploy new model

## Notes

- Models are binary files and should not be committed to Git if >100MB
- Current model size: ~250 KB (safe for Git)
- Retrain periodically as new student data is added
