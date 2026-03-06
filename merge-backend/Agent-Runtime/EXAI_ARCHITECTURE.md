# Runtime EXAI Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    POST /agent/run                              │
│                  (include_xai=true)                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Step 1: Extractor     │
              │  (Validate JSON)       │
              └────────┬───────────────┘
                       │
                       ▼
              ┌────────────────────────┐
              │  Step 2: Normalizer    │
              │  (Skill Aliases)       │
              └────────┬───────────────┘
                       │
                       ▼
              ┌────────────────────────┐
              │  Step 3: KG Writer     │
              │  (Neo4j)               │
              └────────┬───────────────┘
                       │
                       ▼
              ┌────────────────────────┐
              │  Step 4: Gap Analyzer  │
              │  (Deficits API)        │
              └────────┬───────────────┘
                       │
                       ▼
              ┌────────────────────────┐
              │  Step 5: XAI Service   │◄────────┐
              └────────┬───────────────┘         │
                       │                         │
        ┌──────────────┴──────────────┐         │
        │                              │         │
        ▼                              ▼         │
┌───────────────┐              ┌───────────────┐│
│ Skill-Level   │              │ SHAP-Level    ││
│ Explainability│              │ Explainability││
└───────┬───────┘              └───────┬───────┘│
        │                              │         │
        │  Uses:                       │  Uses:  │
        │  • Deficits from             │  • Neo4j data     │
        │    Gap Analyzer              │  • ML Model       │
        │                              │  • SHAP           │
        │  Computes:                   │                   │
        │  • contribution_%            │  Computes:        │
        │    per skill                 │  • Feature row    │
        │                              │  • Prediction     │
        │  Fast: ~50ms                 │  • SHAP values    │
        │                              │                   │
        │                              │  Moderate: ~300ms │
        │                              │                   │
        └──────────────┬───────────────┘                   │
                       │                                   │
                       ▼                                   │
              ┌────────────────────────┐                  │
              │   XAI Response         │                  │
              │   {                    │                  │
              │     skill_level: {...},│                  │
              │     shap_level: {...}  │                  │
              │   }                    │                  │
              └────────────────────────┘                  │
                                                          │
                                                          │
┌─────────────────────────────────────────────────────────────────┤
│                    Standalone Endpoints                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GET /runtime/skill-explain                                     │
│      ↓                                                          │
│  ┌─────────────────────────────────┐                           │
│  │ • Calls Gap Analyzer            │                           │
│  │ • Computes contribution_%       │                           │
│  │ • Returns skill contributors    │                           │
│  └─────────────────────────────────┘                           │
│                                                                 │
│  GET /runtime/predict-explain                                   │
│      ↓                                                          │
│  ┌─────────────────────────────────┐                           │
│  │ • Queries Neo4j for features    │                           │
│  │ • Loads cached ML model         │                           │
│  │ • Computes SHAP values          │                           │
│  │ • Returns feature impacts       │                           │
│  └─────────────────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════
                        Data Flow Details
═══════════════════════════════════════════════════════════════════

Skill-Level Explanation:
───────────────────────
Input:  deficits = [
          {skill: "TensorFlow", deficit: 12.45, importance: 0.85, p_has: 0.0},
          {skill: "PyTorch", deficit: 10.32, importance: 0.82, p_has: 0.0},
          ...
        ]

Process:
  1. total_deficit = sum(d.deficit for d in deficits)
  2. For each skill:
       contribution_% = (deficit / total_deficit) × 100

Output: [
          {skill: "TensorFlow", contribution_%: 18.5, ...},
          {skill: "PyTorch", contribution_%: 15.3, ...},
          ...
        ]


SHAP-Level Explanation:
───────────────────────
Input:  candidate_id, role_key

Process:
  1. Query Neo4j:
       • experience_level, experience_months
       • num_skills, num_projects, num_work_experiences
       • institution_name
  
  2. Compute derived features:
       • avg_mastery_confidence (from API)
       • role_skill_coverage (Neo4j query)
       • role_project_relevance (Neo4j query)
  
  3. Build feature_row: [role_key, exp_level, exp_months, ...]
  
  4. Predict: skill_gap = model.predict(feature_row)
  
  5. SHAP: shap_values = explainer.shap_values(feature_row)
  
  6. Sort by |impact|, split positive/negative

Output: {
          skill_gap_prediction: 0.45,
          readiness_prediction: 0.55,
          top_positive: [{feature: "exp_level_Fresher", impact: +0.12}, ...],
          top_negative: [{feature: "num_projects", impact: -0.08}, ...]
        }


═══════════════════════════════════════════════════════════════════
                        Caching Strategy
═══════════════════════════════════════════════════════════════════

Startup (one-time):
  ┌──────────────────────────────────┐
  │ Load model from                  │
  │ models/skillgap_pipeline.joblib  │
  └───────────┬──────────────────────┘
              │
              ▼
  ┌──────────────────────────────────┐
  │ Create SHAP TreeExplainer        │
  │ (cached in XAIService)           │
  └───────────┬──────────────────────┘
              │
              ▼
         ✓ Ready for requests

Runtime (every request):
  ┌──────────────────────────────────┐
  │ Use cached model                 │
  │ Use cached explainer             │
  │ ✓ No reload overhead (~300ms)    │
  └──────────────────────────────────┘


═══════════════════════════════════════════════════════════════════
                     Performance Breakdown
═══════════════════════════════════════════════════════════════════

POST /agent/run (with XAI):
  Step 1: Extractor       ~10ms
  Step 2: Normalizer      ~20ms
  Step 3: KG Writer       ~500ms  (Neo4j writes)
  Step 4: Gap Analyzer    ~800ms  (API calls)
  Step 5: XAI
    ├─ Skill-level        ~50ms   (arithmetic)
    └─ SHAP-level         ~300ms  (Neo4j + SHAP)
  ─────────────────────────────────
  Total:                  ~1.7s

GET /runtime/skill-explain:
  • Gap Analyzer API      ~800ms
  • Contribution calc     ~50ms
  ─────────────────────────────────
  Total:                  ~850ms

GET /runtime/predict-explain:
  • Feature extraction    ~100ms  (Neo4j queries)
  • SHAP computation      ~200ms  (TreeExplainer)
  ─────────────────────────────────
  Total:                  ~300ms


═══════════════════════════════════════════════════════════════════
                        Error Handling
═══════════════════════════════════════════════════════════════════

Scenario 1: Model file missing
  ┌────────────────────────────────┐
  │ SHAP endpoints return:         │
  │ {enabled: false, reason: "..."} │
  └────────────────────────────────┘
  • /agent/run: xai.shap_level.enabled = false
  • Skill-level XAI still works

Scenario 2: Neo4j query fails
  ┌────────────────────────────────┐
  │ Use default values:            │
  │ • exp_months: 0 (from level)   │
  │ • avg_mastery: 0.50            │
  │ • coverage: 0.0                │
  └────────────────────────────────┘
  • Logged as WARNING
  • Prediction continues with defaults

Scenario 3: XAI computation error (in /agent/run)
  ┌────────────────────────────────┐
  │ response.xai = null            │
  │ Pipeline still returns success │
  └────────────────────────────────┘
  • Non-fatal error
  • Logged with full stack trace

Scenario 4: XAI computation error (standalone endpoint)
  ┌────────────────────────────────┐
  │ Return proper error response   │
  │ HTTP 500 or 200 with           │
  │ {enabled: false, reason: "..."} │
  └────────────────────────────────┘


═══════════════════════════════════════════════════════════════════
                        Feature Engineering
═══════════════════════════════════════════════════════════════════

From Neo4j (direct):
  • Person.experience_level       ─┐
  • Person.experience_months       │
  • count(HAS_SKILL)              ├─── Single Query
  • count(WORKED_ON)              │
  • count(WORKED_AT)              │
  • Education.institution_name    ─┘

From API:
  • avg_mastery_confidence ───► GET /candidates/{id}/skill-confidence

Computed (Neo4j):
  • role_skill_coverage ──────► MATCH (Role)-[:REQUIRES]->(Skill)
                                 Calculate match fraction
  
  • role_project_relevance ───► MATCH (Project)-[:USES]->(Skill)
                                 Calculate role overlap

Parameters:
  • role_key ─────────────────► From request

Final Feature Vector:
  [role_key, exp_level, exp_months, num_skills, num_projects,
   num_work_exp, avg_mastery, coverage, relevance, institution]
                                                         ↓
                                                    ML Model
                                                         ↓
                                              skill_gap_prediction


═══════════════════════════════════════════════════════════════════
                        Technology Stack
═══════════════════════════════════════════════════════════════════

Backend:
  • FastAPI         ─── REST API framework
  • Pydantic        ─── Data validation
  • Neo4j Driver    ─── Graph database
  • Requests        ─── HTTP client (Gap Analyzer API)

ML/XAI:
  • scikit-learn    ─── Model pipeline
  • SHAP            ─── Explainability (TreeExplainer)
  • joblib          ─── Model serialization
  • pandas          ─── Data handling
  • numpy           ─── Numerical operations

Deployment:
  • uvicorn         ─── ASGI server
  • python-dotenv   ─── Configuration
