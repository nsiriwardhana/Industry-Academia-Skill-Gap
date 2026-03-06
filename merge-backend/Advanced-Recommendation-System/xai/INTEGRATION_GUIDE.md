# XAI Integration Guide

## Quick Start

### 1. Install Dependencies

Add to your `requirements.txt`:

```
shap>=0.41.0
xgboost>=1.5.0
```

Install:

```bash
pip install shap xgboost
```

### 2. Build Complete Pipeline

Run all three steps in sequence:

```bash
# Step 1: Build dataset (5-10 minutes)
python -m xai.scripts.build_xai_dataset

# Step 2: Train surrogate (2-5 minutes)
python -m xai.scripts.train_xai_surrogate

# Step 3: Generate explanations (3-5 minutes)
python -m xai.scripts.run_shap_and_generate_text
```

### 3. Integrate with FastAPI

Modify `main.py`:

```python
from fastapi import FastAPI
from xai.api import router as xai_router, initialize_xai_service

app = FastAPI(
    title="CV Parser Agent API",
    description="Skill recommendation system with XAI"
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    # ... existing initialization ...
    
    # Initialize XAI service
    initialize_xai_service()

# Register existing routers
# ...

# Register XAI router
app.include_router(xai_router)
```

### 4. Test Endpoint

```bash
# Check health
curl http://localhost:8000/explain/health

# Get explanation
curl "http://localhost:8000/explain/missing-skill?candidate_id=person_0&role_key=role_0&skill=Python"
```

## Expected Outputs

### After Step 1 (build_xai_dataset)

```
xai/output/xai_missing_skill_dataset.csv
```

**Structure**:
- Columns: candidate_id, role_key, skill, final_score, P_has, importance, P_gnn, ...
- Rows: ~10,000-50,000 (depends on number of candidate-role pairs)
- One row per (candidate, role, required_skill) triple

### After Step 2 (train_xai_surrogate)

```
xai/output/xai_surrogate.pkl
xai/output/feature_importance.png
```

**Console Output**:
```
Training Complete!
Performance Metrics:
  Train R²: 0.9123
  Test R²:  0.8742
  ...
✅ Quality check PASSED: R² (0.8742) >= 0.85

Top 10 Features by Importance:
   1. importance                   0.3215
   2. P_gnn                        0.2847
   3. gap_magnitude                0.1923
   ...
```

### After Step 3 (run_shap_and_generate_text)

```
xai/output/shap_summary.png              # Global beeswarm plot
xai/output/shap_summary_bar.png          # Feature importance bar chart
xai/output/shap_dependence_importance.png
xai/output/shap_dependence_pgnn.png
xai/output/shap_dependence_phas.png
xai/output/shap_local_person_X_role_Y.png  # Local waterfall plots
```

## Troubleshooting

### Issue: "XAI service not available"

**Cause**: Model not trained yet

**Solution**:
```bash
python -m xai.scripts.build_xai_dataset
python -m xai.scripts.train_xai_surrogate
```

### Issue: R² < 0.85

**Cause**: Surrogate quality below threshold

**Solutions**:
1. Add more training data (increase candidate-role pairs)
2. Engineer better features
3. Tune hyperparameters in `xai_surrogate_trainer.py`

### Issue: "No data found for candidate/role/skill"

**Cause**: Requested triple not in dataset

**Solution**:
- Check that candidate_id exists: `df['candidate_id'].unique()`
- Check that role_key exists: `df['role_key'].unique()`
- Check that skill is required by role: `df[(df['candidate_id']==X) & (df['role_key']==Y)]['skill'].tolist()`

### Issue: Long training time

**Cause**: Large dataset (>50k rows)

**Solutions**:
1. Reduce `n_background` in `run_shap_and_generate_text.py` (default 100)
2. Sample fewer candidate-role pairs in `build_xai_dataset.py`
3. Use fewer estimators in `xai_surrogate_trainer.py` (default 200)

## Performance Optimization

### For Production

1. **Cache SHAP values**: Pre-compute for common queries
2. **Reduce background samples**: Use 50 instead of 100
3. **Lazy loading**: Only initialize XAI service if needed

### For Development

1. **Limit dataset**: Use `max_pairs=10` in `build_xai_dataset.py`
2. **Fewer estimators**: Set `n_estimators=50` in trainer
3. **Skip plots**: Comment out plot generation in explainer

## API Response Examples

### Success Response

```json
{
  "candidate_id": "person_0",
  "role_key": "role_0",
  "skill": "Python",
  "final_score": 0.7823,
  "top_factors": [
    {
      "feature": "importance",
      "shap": 0.214,
      "value": 0.969,
      "meaning": "This skill is critical for the role (high TF-IDF importance)"
    },
    {
      "feature": "P_has",
      "shap": 0.142,
      "value": 0.0,
      "meaning": "You currently lack this skill (low proficiency)"
    },
    {
      "feature": "P_gnn",
      "shap": 0.108,
      "value": 0.815,
      "meaning": "Strong graph alignment (0.82) - GNN predicts high learning potential"
    }
  ],
  "explanation_text": "This skill ranks with a score of 0.782. Primary driver: This skill is critical for the role (high TF-IDF importance) (SHAP contribution: +0.214). Additional factors: you currently lack this skill (low proficiency); strong graph alignment (0.82) - gnn predicts high learning potential."
}
```

### Error Responses

**404 Not Found**:
```json
{
  "detail": "No data for person_0/role_0/Python"
}
```

**503 Service Unavailable**:
```json
{
  "detail": "XAI service not available. Please train the surrogate model first."
}
```

## Next Steps

1. ✅ Build dataset
2. ✅ Train surrogate (validate R² ≥ 0.85)
3. ✅ Generate SHAP plots
4. ✅ Integrate API endpoint
5. Test with sample queries
6. Document findings (compare to OLD vs NEW ranking evaluation)
7. Add to production deployment

## Maintenance

### When to Retrain

Retrain surrogate model when:
- New candidates added to system
- Role definitions change significantly
- GNN model updated
- Feature engineering improvements

### Monitoring

Track these metrics:
- XAI endpoint latency (should be <100ms)
- Surrogate R² on new data (should stay ≥0.85)
- Feature importance stability (top features shouldn't change drastically)
