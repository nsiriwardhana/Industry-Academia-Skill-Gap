# XAI Integration Troubleshooting Guide

## Quick Fix Commands

### Issue 1: Skill-level Explainability Timeout

**Error:** `Read timed out. (read timeout=10)`

**Root Cause:** Advanced-Recommendation-System not running on port 8001

**Solution:**
```bash
# Terminal 1: Start Advanced-Recommendation-System
cd "f:\CV Parser Agent\Advanced-Recommendation-System"
uvicorn main:app --reload --port 8001
```

**Verify:** Open browser to http://localhost:8001/docs

---

### Issue 2: SHAP Disabled (Model Not Loaded)

**Error:** `SHAP disabled: Model not loaded (file missing or SHAP not installed)`

**Solution A: Install SHAP**
```bash
cd "f:\CV Parser Agent\Agent-Runtime"
pip install shap
```

**Solution B: Create Dummy Model (for testing)**
```bash
cd "f:\CV Parser Agent\Agent-Runtime"
python ml_models/create_dummy_model.py
```

**Solution C: Use Your Trained Model**
```bash
# Copy your trained model to:
f:\CV Parser Agent\Agent-Runtime\ml_models\skillgap_pipeline.joblib
```

---

## Complete System Startup Sequence

### Step 1: Start Neo4j
```bash
# Ensure Neo4j is running
# Default: http://localhost:7474
# Bolt: bolt://localhost:7687
```

### Step 2: Start Advanced-Recommendation-System (Port 8001)
```bash
cd "f:\CV Parser Agent\Advanced-Recommendation-System"
uvicorn main:app --reload --port 8001
```

**Verify:**
```bash
curl http://localhost:8001/health
# Should return: {"status": "healthy", ...}
```

### Step 3: Install SHAP (if not already installed)
```bash
cd "f:\CV Parser Agent\Agent-Runtime"
pip install shap
```

### Step 4: Create/Place Model File
```bash
# Option A: Create dummy model for testing
python ml_models/create_dummy_model.py

# Option B: Copy your trained model
# Ensure file exists at: ml_models/skillgap_pipeline.joblib
```

### Step 5: Start Agent-Runtime (Port 8003)
```bash
cd "f:\CV Parser Agent\Agent-Runtime"
uvicorn main:app --reload --port 8003
```

**Check startup logs for:**
```
✓ Model and explainer loaded successfully
```

If you see this warning:
```
WARNING: Model file not found: ml_models/skillgap_pipeline.joblib
```

Then SHAP will be disabled (but skill-level XAI still works).

### Step 6: Run Tests
```bash
cd "f:\CV Parser Agent\Agent-Runtime"
python test_xai_integration.py
```

**Expected Output:**
```
TEST 1: Skill-level Explainability
✓ Success!
Total deficit: 67.30
Top 10 contributors: ...

TEST 2: SHAP-level Explainability
✓ SHAP enabled!
Predicted skill gap: 0.4523
Predicted readiness: 0.5477
```

---

## Common Errors & Solutions

### Error: `Connection refused (port 8001)`

**Cause:** Advanced-Recommendation-System not running

**Fix:**
```bash
cd "f:\CV Parser Agent\Advanced-Recommendation-System"
uvicorn main:app --reload --port 8001
```

---

### Error: `ModuleNotFoundError: No module named 'shap'`

**Cause:** SHAP library not installed

**Fix:**
```bash
pip install shap
```

---

### Error: `Model file not found: ml_models/skillgap_pipeline.joblib`

**Cause:** No trained model available

**Fix (Quick - Dummy Model):**
```bash
python ml_models/create_dummy_model.py
```

**Fix (Production - Real Model):**
1. Train model using your dataset
2. Save as: `ml_models/skillgap_pipeline.joblib`
3. Restart Agent-Runtime

---

### Error: `Read timed out`

**Cause:** Gap Analyzer API call taking too long

**Fix 1:** Ensure services are running:
```bash
# Check if port 8001 is listening
netstat -an | findstr :8001
```

**Fix 2:** Increase timeout in test script:
```python
# In test_xai_integration.py
response = requests.get(url, params=params, timeout=30)  # Increase from 10
```

**Fix 3:** Add timeout handling in `agents/gap_analyzer.py`:
```python
try:
    response = requests.get(url, timeout=10)
except requests.Timeout:
    logger.warning("API timeout, returning empty results")
    return {"skill_confidence_top": [], "skill_gap_top": []}
```

---

### Error: `Feature shape mismatch`

**Cause:** Model expects different features than provided

**Fix:** Ensure your model was trained with these exact 10 features:
1. role_key
2. experience_level
3. experience_months
4. num_skills
5. num_projects
6. num_work_experiences
7. avg_mastery_confidence
8. role_skill_coverage
9. role_project_relevance
10. institution_name

---

## Verification Checklist

Before running tests, verify:

- [ ] Neo4j running on port 7687
- [ ] Advanced-Recommendation-System running on port 8001
- [ ] Agent-Runtime running on port 8003
- [ ] SHAP installed (`pip show shap`)
- [ ] Model file exists (`ml_models/skillgap_pipeline.joblib`)
- [ ] Candidate data exists in Neo4j (run `/agent/run` first)

---

## Testing Strategy

### Test 1: Backend Only (No Model)

```bash
# Disable SHAP temporarily
# Skip model loading in startup

# Should work:
- Skill-level explainability ✓
- Skill confidence ✓
- Skill gap analysis ✓

# Should gracefully fail:
- SHAP explainability (returns enabled=false)
```

### Test 2: With Dummy Model

```bash
# Create dummy model
python ml_models/create_dummy_model.py

# All tests should pass ✓
```

### Test 3: With Production Model

```bash
# Use real trained model
# All tests should pass with accurate predictions ✓
```

---

## Port Summary

| Service | Port | Status Check |
|---------|------|-------------|
| Neo4j Browser | 7474 | http://localhost:7474 |
| Neo4j Bolt | 7687 | bolt://localhost:7687 |
| Advanced-Recommendation | 8001 | http://localhost:8001/docs |
| Agent-Runtime | 8003 | http://localhost:8003/docs |
| Frontend (optional) | 3000 | http://localhost:3000 |

---

## Quick Health Check

```bash
# Check all services
curl http://localhost:8001/health  # Advanced-Recommendation
curl http://localhost:8003/health  # Agent-Runtime
```

Expected responses:
```json
// Advanced-Recommendation
{"status": "healthy", "neo4j_connected": true}

// Agent-Runtime  
{"status": "healthy", "neo4j_connected": true, "recommendation_api_available": true}
```

---

## Debug Mode

Enable debug logging in Agent-Runtime:

```python
# In config/settings.py
LOG_LEVEL = "DEBUG"  # Change from "INFO"
```

Restart server to see detailed logs:
```
DEBUG: cv_data type = <class 'ExtractedData'>
DEBUG: skills type = <class 'list'>
DEBUG: Built feature row: {'role_key': 'ai_ml_engineer', ...}
```

---

## Production Checklist

Before deploying to production:

- [ ] Train model on real dataset (1000+ samples)
- [ ] Validate model accuracy (R² > 0.7)
- [ ] Test SHAP computation time (< 500ms)
- [ ] Load test API endpoints (concurrent requests)
- [ ] Set up error monitoring/logging
- [ ] Configure production timeouts
- [ ] Enable CORS for frontend domain
- [ ] Secure API endpoints (authentication)
- [ ] Set up health check monitoring

---

## Need Help?

1. **Check logs:** Look for errors in server startup
2. **Verify ports:** Ensure no port conflicts
3. **Test endpoints:** Use Swagger UI at `/docs`
4. **Run tests:** `python test_xai_integration.py`
5. **Check model:** Verify joblib file exists and is valid

**Still stuck?** Check the implementation documentation:
- `XAI_INTEGRATION.md` - User guide
- `EXAI_ARCHITECTURE.md` - Architecture details
- `QUICK_START_EXAI.md` - Quick start guide
