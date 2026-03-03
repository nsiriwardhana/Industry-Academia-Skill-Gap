# XAI Implementation Checklist

## ✅ Pre-Flight Checklist

### 1. Dependencies Installed
```bash
pip install shap>=0.41.0 xgboost>=1.5.0
```

**Verify**:
```bash
python -c "import shap; import xgboost; print('✅ Dependencies OK')"
```

### 2. Required Services Running
- [ ] Neo4j database accessible
- [ ] Existing API services operational (RoleImportanceService, SkillConfidenceService, GNN)
- [ ] readiness_labels.csv exists at `data/processed/readiness_labels.csv`

### 3. File Structure Verified
```bash
xai/
├── __init__.py
├── README.md
├── INTEGRATION_GUIDE.md
├── IMPLEMENTATION_SUMMARY.md
├── EXAMPLE_INTEGRATION.md
├── services/
│   ├── __init__.py
│   ├── xai_dataset_builder.py
│   ├── xai_surrogate_trainer.py
│   └── xai_explainer.py
├── scripts/
│   ├── __init__.py
│   ├── build_xai_dataset.py
│   ├── train_xai_surrogate.py
│   └── run_shap_and_generate_text.py
├── api/
│   ├── __init__.py
│   └── xai_routes.py
└── output/
    └── .gitkeep
```

**Verify**:
```bash
python -c "from xai import XAIDatasetBuilder, XAISurrogateTrainer, XAIExplainer; print('✅ Module imports OK')"
```

---

## 📋 Step-by-Step Execution Checklist

### Step 1: Build Dataset ⏱️ ~5-10 minutes

**Command**:
```bash
python -m xai.scripts.build_xai_dataset
```

**Expected Output**:
```
==========================================
Building XAI Dataset
==========================================
Labels source: data/processed/readiness_labels.csv
Found 200 labeled pairs
Processing 200 unique candidate-role pairs
Building dataset: 100%|███████████| 200/200
==========================================
Dataset built successfully!
Output: xai/output/xai_missing_skill_dataset.csv
Total rows: 25000
Features: ['candidate_id', 'role_key', 'skill', 'final_score', 'P_has', ...]
...
==========================================
```

**Checklist**:
- [ ] Script completes without errors
- [ ] Output file created: `xai/output/xai_missing_skill_dataset.csv`
- [ ] CSV has >1000 rows
- [ ] CSV has all 16 feature columns + label
- [ ] final_score values in range [0, 1]

**Troubleshooting**:
- **Error: "Labels file not found"** → Check `data/processed/readiness_labels.csv` exists
- **Error: "Neo4j connection failed"** → Verify Neo4j is running and credentials in config
- **Error: "GNN service not initialized"** → Check GNN model loaded in main app

---

### Step 2: Train Surrogate ⏱️ ~2-5 minutes

**Command**:
```bash
python -m xai.scripts.train_xai_surrogate
```

**Expected Output**:
```
==========================================
Training XAI Surrogate Model
==========================================
Dataset: xai/output/xai_missing_skill_dataset.csv
Loaded 25000 rows from dataset
Dataset has 180 unique candidates
Training surrogate model...
==========================================
Training Complete!
==========================================
Model saved to: xai/output/xai_surrogate.pkl

Performance Metrics:
  Train R²: 0.9123
  Test R²:  0.8742
  Train RMSE: 0.0234
  Test RMSE:  0.0287
  ...

✅ Quality check PASSED: R² (0.8742) >= 0.85

Top 10 Features by Importance:
   1. importance                   0.3215
   2. P_gnn                        0.2847
   3. gap_magnitude                0.1923
   ...
==========================================
```

**Checklist**:
- [ ] Script completes without errors
- [ ] Output file created: `xai/output/xai_surrogate.pkl`
- [ ] Test R² ≥ 0.85 ✅ (Quality check PASSED)
- [ ] Feature importance plot created: `xai/output/feature_importance.png`
- [ ] Top 3 features make sense (importance, P_gnn, gap_magnitude likely)

**Troubleshooting**:
- **Error: "Dataset not found"** → Run Step 1 first
- **Warning: R² < 0.85** → Try increasing training data (more candidate-role pairs) or tune hyperparameters
- **Error: "No train-test candidate overlap"** → This should never happen; indicates bug in GroupShuffleSplit

---

### Step 3: Generate SHAP Explanations ⏱️ ~3-5 minutes

**Command**:
```bash
python -m xai.scripts.run_shap_and_generate_text
```

**Expected Output**:
```
==========================================
Generating SHAP Explanations
==========================================
Loaded 25000 rows
Initializing XAI explainer...
Preparing features...
Feature matrix shape: (25000, 23)
Sampling 100 background instances...
==========================================
Generating Global Explanations
==========================================
Generating summary plot...
Saved: xai/output/shap_summary.png
Generating dependence plot for 'importance'...
Saved: xai/output/shap_dependence_importance.png
...
==========================================
Generating Local Explanations (3 examples)
==========================================
Example 1: person_0 / role_0
Saved local explanation: xai/output/shap_local_person_0_role_0.png
...
==========================================
Generating Natural Language Explanations
==========================================
Example 1: person_0 / role_0
  Skill 1: Python
    Score: 0.7823
    Explanation: This skill ranks with a score of 0.782. Primary driver: ...
    Top factors:
      - importance         (SHAP: +0.2140): This skill is critical for the role (high TF-IDF importance)
      - P_has              (SHAP: +0.1420): You currently lack this skill (low proficiency)
      - P_gnn              (SHAP: +0.1080): Strong graph alignment (0.82) - GNN predicts high learning potential
...
==========================================
SHAP Generation Complete!
==========================================
```

**Checklist**:
- [ ] Script completes without errors
- [ ] Global plots created (5 files):
  - [ ] `xai/output/shap_summary.png`
  - [ ] `xai/output/shap_summary_bar.png`
  - [ ] `xai/output/shap_dependence_importance.png`
  - [ ] `xai/output/shap_dependence_pgnn.png`
  - [ ] `xai/output/shap_dependence_phas.png`
- [ ] Local plots created (≥1 file):
  - [ ] `xai/output/shap_local_*.png`
- [ ] Natural language explanations printed to console
- [ ] Explanations are human-readable and make sense

**Troubleshooting**:
- **Error: "Model not found"** → Run Step 2 first
- **Error: "Dataset not found"** → Run Step 1 first
- **Plots look wrong** → Check feature engineering consistency between trainer and explainer

---

### Step 4: Integrate with FastAPI ⏱️ ~2 minutes

**Instructions**:
1. Open `main.py`
2. Add import: `from xai.api import router as xai_router, initialize_xai_service`
3. In `lifespan()` startup, add: `initialize_xai_service()`
4. After existing routers, add: `app.include_router(xai_router)`

**Or** use the example from `xai/EXAMPLE_INTEGRATION.md`

**Start server**:
```bash
python main.py
```

**Expected Output**:
```
Starting Advanced Recommendation API with GNN support...
[OK] Neo4j connection initialized
Loading GNN model for link prediction...
[OK] GNN model loaded successfully
Initializing XAI service...
Loading XAI explainer...
[OK] XAI service initialized
[OK] Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**Checklist**:
- [ ] Server starts without errors
- [ ] XAI service initializes successfully
- [ ] No warnings about missing XAI model

**Troubleshooting**:
- **Warning: "XAI service initialization failed"** → Check model file exists at `xai/output/xai_surrogate.pkl`
- **Warning: "XAI dataset not found"** → Check dataset exists at `xai/output/xai_missing_skill_dataset.csv`
- **Server won't start** → Check for syntax errors in main.py

---

### Step 5: Test XAI Endpoints ⏱️ ~2 minutes

**Test 1: Health Check**
```bash
curl http://localhost:8001/explain/health
```

**Expected Response**:
```json
{
  "service": "XAI",
  "status": "available",
  "model_loaded": true,
  "dataset_loaded": true,
  "dataset_size": 25000
}
```

**Checklist**:
- [ ] Status: "available"
- [ ] model_loaded: true
- [ ] dataset_loaded: true
- [ ] dataset_size > 1000

---

**Test 2: Get Explanation**
```bash
curl "http://localhost:8001/explain/missing-skill?candidate_id=person_0&role_key=role_0&skill=Python"
```

**Expected Response**:
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

**Checklist**:
- [ ] Response status: 200 OK
- [ ] All fields present (candidate_id, role_key, skill, final_score, top_factors, explanation_text)
- [ ] top_factors has 3-5 items
- [ ] SHAP values are non-zero
- [ ] Meanings are human-readable
- [ ] explanation_text is coherent

---

**Test 3: API Documentation**

Visit: http://localhost:8001/docs

**Checklist**:
- [ ] Swagger UI loads
- [ ] "XAI" tag visible in endpoint list
- [ ] `/explain/missing-skill` endpoint listed
- [ ] `/explain/health` endpoint listed
- [ ] Can execute test requests from Swagger UI

---

## 🎯 Final Verification

### Visual Inspection

**Open and review plots**:
1. `xai/output/feature_importance.png` → Should show horizontal bars (top: importance, P_gnn)
2. `xai/output/shap_summary.png` → Should show beeswarm plot (colored dots)
3. `xai/output/shap_dependence_importance.png` → Should show scatter plot
4. `xai/output/shap_local_*.png` → Should show waterfall plots with arrows

**Checklist**:
- [ ] All plots render correctly (not blank or corrupted)
- [ ] Feature names are human-readable (not "feature_12")
- [ ] Colors/axes make sense

---

### Integration Verification

**Test with existing endpoints**:
1. Get missing skills: `GET /api/recommendations/missing-skills-gnn?person_key=person_0&role_key=role_0`
2. For top-ranked skill, get explanation: `GET /explain/missing-skill?candidate_id=person_0&role_key=role_0&skill=<skill>`
3. Verify final_score matches ranking

**Checklist**:
- [ ] XAI endpoint returns explanation for skills from missing-skills-gnn
- [ ] final_score values are consistent with ranking order
- [ ] explanation_text makes sense given the skill context

---

## ✅ Success Criteria

All of the following should be true:

- [x] **Dataset built**: CSV with >1000 rows, 16 features
- [x] **Surrogate trained**: R² ≥ 0.85 on test set
- [x] **SHAP plots generated**: 5+ global plots, ≥1 local plot
- [x] **API integrated**: XAI endpoints available at `/explain/*`
- [x] **Health check passes**: status="available", model_loaded=true
- [x] **Explanation endpoint works**: Returns valid JSON with top_factors and explanation_text
- [x] **Natural language quality**: Explanations are human-readable and coherent
- [x] **Consistency**: final_score matches expected ranking behavior

---

## 🐛 Common Issues and Solutions

### Issue: R² < 0.85

**Causes**:
- Insufficient training data
- Feature engineering doesn't capture decision logic
- Model underfitting

**Solutions**:
1. Increase training data (more candidate-role pairs in readiness_labels.csv)
2. Add more features to XAIDatasetBuilder
3. Tune XGBoost hyperparameters (increase n_estimators, max_depth)

---

### Issue: "No data for candidate/role/skill"

**Causes**:
- Skill not required by role
- Candidate-role pair not in training data
- Skill name mismatch

**Solutions**:
1. Verify skill is in role requirements: Check Neo4j or role_importance
2. Check dataset: `df[(df['candidate_id']=='X') & (df['role_key']=='Y')]`
3. Check exact skill name (case-sensitive)

---

### Issue: All SHAP values close to zero

**Causes**:
- Model predictions are constant
- Background dataset not representative
- Feature scaling issues

**Solutions**:
1. Check surrogate R² (should be ≥0.85)
2. Increase background sample size (n_background=200)
3. Verify feature variance: `df[feature_cols].describe()`

---

### Issue: Slow explanation generation

**Causes**:
- Large background dataset
- Too many features
- Expensive SHAP computation

**Solutions**:
1. Reduce n_background (50-100 sufficient)
2. Use TreeExplainer (already used, most efficient for XGBoost)
3. Pre-compute SHAP values for common queries (caching)

---

## 📊 Expected Timings

| Step | Duration | Output Size |
|------|----------|-------------|
| Build dataset | 5-10 min | ~5-50 MB CSV |
| Train surrogate | 2-5 min | ~1-5 MB PKL |
| Generate SHAP | 3-5 min | ~2-10 MB PNGs |
| API explanation | <100 ms | ~1-2 KB JSON |

**Total setup time**: ~15-20 minutes (one-time)
**Runtime latency**: <100 ms per explanation

---

## 🎉 Completion

If all steps pass, you now have:

✅ **Research-grade XAI system** with validated surrogate (R²≥0.85)  
✅ **Global explanations** (SHAP plots for feature importance)  
✅ **Local explanations** (waterfall plots for individual predictions)  
✅ **Natural language generation** (human-readable explanations)  
✅ **Production API** (FastAPI endpoints with error handling)  
✅ **Complete documentation** (README, integration guide, examples)

**Next steps**: Deploy to production, monitor performance, iterate on features!
