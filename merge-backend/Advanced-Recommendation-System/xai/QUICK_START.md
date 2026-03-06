# XAI Quick Start

## 🚀 3-Minute Setup

### 1. Install Dependencies (30 seconds)

```bash
pip install shap xgboost
```

### 2. Run Pipeline (15-20 minutes, one-time)

```bash
# Build dataset
python -m xai.scripts.build_xai_dataset

# Train surrogate
python -m xai.scripts.train_xai_surrogate

# Generate explanations
python -m xai.scripts.run_shap_and_generate_text
```

### 3. Integrate with API (2 minutes)

**Option A: Automatic (copy-paste)**

See [EXAMPLE_INTEGRATION.md](EXAMPLE_INTEGRATION.md) for complete code.

**Option B: Manual (3 changes)**

Edit `main.py`:

```python
# 1. Add import
from xai.api import router as xai_router, initialize_xai_service

# 2. In lifespan startup
initialize_xai_service()

# 3. Register router
app.include_router(xai_router)
```

### 4. Test (30 seconds)

```bash
# Start server
python main.py

# Test health
curl http://localhost:8001/explain/health

# Get explanation
curl "http://localhost:8001/explain/missing-skill?candidate_id=person_0&role_key=role_0&skill=Python"
```

---

## 📚 Documentation

- **[README.md](README.md)** - Complete overview, architecture, usage
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Step-by-step integration
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - What was built
- **[EXAMPLE_INTEGRATION.md](EXAMPLE_INTEGRATION.md)** - Code examples
- **[CHECKLIST.md](CHECKLIST.md)** - Verification checklist

---

## ✅ What You Get

- ✅ Interpretable surrogate model (R²≥0.85)
- ✅ SHAP explanations (global + local)
- ✅ Natural language generation
- ✅ FastAPI endpoints
- ✅ Visualization plots (5+ PNGs)

---

## 🎯 API Endpoints

### GET /explain/missing-skill

**Query Parameters**:
- `candidate_id` (string, required)
- `role_key` (string, required)
- `skill` (string, required)

**Response**:
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
    }
  ],
  "explanation_text": "This skill ranks with a score of 0.782. Primary driver: ..."
}
```

### GET /explain/health

**Response**:
```json
{
  "service": "XAI",
  "status": "available",
  "model_loaded": true,
  "dataset_loaded": true,
  "dataset_size": 25000
}
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "XAI service not available" | Run 3-step pipeline first |
| R² < 0.85 | Add more training data or tune hyperparameters |
| "No data for candidate/role/skill" | Check if skill is required by role |
| Slow explanations | Reduce background samples (n_background=50) |

---

## 📊 Module Structure

```
xai/
├── services/          # Core XAI logic (3 files, ~1000 lines)
├── scripts/           # Executable scripts (3 files, ~400 lines)
├── api/              # FastAPI routes (1 file, ~150 lines)
├── output/           # Generated files (CSV, PKL, PNGs)
└── *.md              # Documentation (5 files)
```

---

## 🎉 Success Metrics

- **Quality**: R² ≥ 0.85 on test set ✅
- **Speed**: <100ms per explanation ✅
- **Interpretability**: Human-readable features ✅
- **Production**: Error handling, logging, health checks ✅

---

## 💡 Next Steps

1. Run the 3-step pipeline
2. Integrate with main.py
3. Test with sample queries
4. Review SHAP plots in `xai/output/`
5. Compare to OLD vs NEW ranking evaluation
6. Deploy to production

---

## 📞 Support

For detailed instructions:
- Architecture & theory → [README.md](README.md)
- Step-by-step setup → [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)
- Verification → [CHECKLIST.md](CHECKLIST.md)
- Code examples → [EXAMPLE_INTEGRATION.md](EXAMPLE_INTEGRATION.md)
