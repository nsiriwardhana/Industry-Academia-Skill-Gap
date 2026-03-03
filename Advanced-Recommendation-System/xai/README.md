# XAI Module: Explainable AI for Missing Skill Rankings

## Overview

This module provides research-grade explainability for the missing skill recommendation system using a **surrogate model + SHAP** approach.

### Decision Function

The system ranks missing skills using:

```
final_score(person, skill, role) = (1 - P_has) × importance × P_gnn
```

Where:
- **P_has**: Current proficiency level (multi-evidence aggregation)
- **importance**: TF-IDF role importance  
- **P_gnn**: GNN-predicted learning potential

### Architecture

```
┌─────────────────┐
│ System Outputs  │  (P_has, importance, P_gnn for all skills)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Dataset Builder │  (Extract features, compute label)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ XGBoost         │  (Train interpretable surrogate)
│ Surrogate       │  (Validates R² ≥ 0.85)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SHAP Explainer  │  (TreeExplainer for attributions)
│                 │  (Global + Local plots)
│                 │  (Natural language generation)
└─────────────────┘
```

## Features

### 11 Interpretable Features

**Core Features (Formula Components):**
- `P_has`: Current skill proficiency [0,1]
- `importance`: TF-IDF role importance [0,1]
- `P_gnn`: GNN learning potential [0,1]
- `gap_magnitude`: 1 - P_has

**Additional Features:**
- `category`: Skill category (one-hot encoded)
- `category_coverage`: % of candidate skills in target category
- `project_support`: Count of projects using category skills
- `neighbor_overlap`: Co-occurrence score with existing skills [0,1]
- `skill_popularity`: Global popularity (person + role mentions)

**Profile Features:**
- `num_candidate_skills`: Total skills in candidate profile
- `num_candidate_projects`: Total projects in candidate profile
- `num_candidate_categories`: Unique categories covered

### Surrogate Model

- **Algorithm**: XGBoostRegressor
- **Configuration**: 200 estimators, max_depth=6, early stopping
- **Quality Threshold**: R² ≥ 0.85 on held-out test set
- **Split Strategy**: GroupShuffleSplit by candidate_id (prevents leakage)

### SHAP Explanations

**Global Explanations:**
- Summary plot (beeswarm): Feature importance across all predictions
- Bar plot: Mean absolute SHAP values
- Dependence plots: How features impact score (importance, P_gnn, P_has)

**Local Explanations:**
- Waterfall plots: SHAP decomposition for individual predictions
- Natural language: Human-readable explanation generation

## Usage

### Step 1: Build Dataset

```bash
python -m xai.scripts.build_xai_dataset
```

**Input**: `data/processed/readiness_labels.csv`  
**Output**: `xai/output/xai_missing_skill_dataset.csv`

Creates one row per (candidate, role, required_skill) triple with all features.

### Step 2: Train Surrogate

```bash
python -m xai.scripts.train_xai_surrogate
```

**Input**: `xai/output/xai_missing_skill_dataset.csv`  
**Output**: 
- `xai/output/xai_surrogate.pkl` (model + metadata)
- `xai/output/feature_importance.png`

Trains XGBoost and validates R² ≥ 0.85.

### Step 3: Generate SHAP Explanations

```bash
python -m xai.scripts.run_shap_and_generate_text
```

**Input**: Model + dataset  
**Output**: 
- `xai/output/shap_summary.png`
- `xai/output/shap_summary_bar.png`
- `xai/output/shap_dependence_importance.png`
- `xai/output/shap_dependence_pgnn.png`
- `xai/output/shap_dependence_phas.png`
- `xai/output/shap_local_{candidate}_{role}.png`

### Step 4: FastAPI Integration

Add to your `main.py`:

```python
from xai.api import router as xai_router, initialize_xai_service

app = FastAPI()

# On startup
@app.on_event("startup")
async def startup_event():
    initialize_xai_service()

# Register router
app.include_router(xai_router)
```

**Endpoint**:

```
GET /explain/missing-skill?candidate_id=person_0&role_key=role_0&skill=Python
```

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

## Module Structure

```
xai/
├── __init__.py               # Module exports
├── README.md                 # This file
├── services/
│   ├── __init__.py
│   ├── xai_dataset_builder.py    # Feature extraction
│   ├── xai_surrogate_trainer.py  # XGBoost training
│   └── xai_explainer.py           # SHAP + NLG
├── scripts/
│   ├── __init__.py
│   ├── build_xai_dataset.py       # Step 1
│   ├── train_xai_surrogate.py     # Step 2
│   └── run_shap_and_generate_text.py  # Step 3
├── api/
│   ├── __init__.py
│   └── xai_routes.py              # FastAPI endpoints
└── output/
    ├── .gitkeep
    ├── xai_missing_skill_dataset.csv
    ├── xai_surrogate.pkl
    ├── feature_importance.png
    ├── shap_summary.png
    ├── shap_summary_bar.png
    ├── shap_dependence_*.png
    └── shap_local_*.png
```

## Quality Assurance

### Data Leakage Prevention

- **GroupShuffleSplit**: Train-test split ensures no candidate appears in both sets
- **Verification**: Checks for candidate overlap (should be zero)

### Model Validation

- **Metrics**: R², RMSE, MAE on train and test sets
- **Threshold**: Test R² must be ≥ 0.85
- **Feature Importance**: Logs top 10 features

### Reproducibility

- **Seeds**: `random_state=42` for XGBoost and sampling
- **Deterministic**: No stochastic components in feature engineering

## Comparison to Previous SHAP Implementation

### Old Approach (services/shap_explainer_service.py)

- **Method**: Direct SHAP on GNN predictions
- **Levels**: 3-level decomposition (formula, feature, graph)
- **Limitation**: Heuristic feature attributions (didn't re-run GNN)

### New Approach (xai/ module)

- **Method**: Surrogate model + SHAP
- **Advantages**:
  - Interpretable surrogate can be validated (R² metric)
  - Fast explanations (no GNN queries)
  - Reliable SHAP attributions from tree model
  - Natural language generation

## Dependencies

```python
pandas>=1.3.0
numpy>=1.21.0
scikit-learn>=1.0.0
xgboost>=1.5.0
shap>=0.41.0
matplotlib>=3.4.0
seaborn>=0.11.0
tqdm>=4.62.0
fastapi>=0.95.0
```

## Citation

If you use this XAI module, please cite:

```
@software{xai_missing_skills,
  title={Explainable AI for GNN-based Skill Recommendations},
  author={CV Parser Agent Team},
  year={2024},
  version={1.0.0}
}
```

## Contact

For questions or issues, please contact the development team.
