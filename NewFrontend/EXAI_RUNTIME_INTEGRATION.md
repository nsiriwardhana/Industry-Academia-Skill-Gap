# ExAI Runtime Integration - NewFrontend

## Overview

The **ExAI (Explainable AI) Runtime** has been successfully integrated into the NewFrontend, providing real-time, interpretable AI insights for skill gap predictions using SHAP (SHapley Additive exPlanations).

## What Was Added

### 1. Backend Changes (Agent-Runtime)

#### **Fixed: Project Relevance Score Issue**
- **Problem**: `project_relevance_score` was not being returned from the `/agent/run` endpoint
- **Solution**: 
  - Added `project_relevance_score` and `relevant_projects` fields to `AgentRunResponse` model
  - Modified `/agent/run` endpoint to automatically fetch project relevance from Recommendation API
  - Now returns project data as part of the main response (no separate API call needed)

**File: `Agent-Runtime/models/schemas.py`**
```python
class AgentRunResponse(BaseModel):
    # ... existing fields ...
    project_relevance_score: Optional[float] = Field(None, ...)
    relevant_projects: Optional[List[Dict[str, Any]]] = Field(None, ...)
```

**File: `Agent-Runtime/main.py`**
```python
# Step 6: Fetch Project Relevance (Optional)
try:
    project_url = f"{RECOMMENDATION_API_BASE_URL}/candidates/{candidate_id}/roles/{role_key}/project-relevance"
    project_response = requests.get(project_url, params={"top_n": 5, "top_k": 25}, timeout=5)
    if project_response.status_code == 200:
        project_data = project_response.json()
        project_relevance_score = project_data.get("candidate_project_score")
        relevant_projects = project_data.get("top_projects", [])
except Exception as proj_error:
    logger.warning(f"Failed to fetch project relevance (non-fatal): {proj_error}")

response = AgentRunResponse(
    # ... other fields ...
    project_relevance_score=project_relevance_score,
    relevant_projects=relevant_projects,
    xai=xai_result
)
```

### 2. Frontend Changes (NewFrontend)

#### **New Component: XAIExplanation**
A reusable React component that displays SHAP-based AI insights.

**File: `NewFrontend/src/components/XAIExplanation.tsx`**

**Features:**
- Displays predicted readiness score from ML model
- Shows factors that **increase** the skill gap (weaknesses)
- Shows factors that **reduce** the skill gap (strengths)
- Provides plain English explanations for each factor
- Visual impact scores with color coding
- Responsive grid layout

**Usage:**
```tsx
import { XAIExplanation } from "@/components/XAIExplanation";

<XAIExplanation 
  xai={results.xai?.shap_level} 
  className="mb-8"
/>
```

#### **Updated: SkillGap Page**
Added XAI insights display to the skill gap analysis results page.

**File: `NewFrontend/src/pages/SkillGap.tsx`**

**Changes:**
- Imported `XAIExplanation` component
- Added XAI display section after matched skills
- Shows SHAP-level insights if available
- Maintains existing Colab explainer display

#### **Updated: Pipeline Page**
Optimized to use project relevance from main response.

**File: `NewFrontend/src/pages/Pipeline.tsx`**

**Changes:**
- Removed separate `getProjectRelevance` API call
- Now uses `project_relevance_score` and `relevant_projects` from `runAgentPipeline` response
- Simplified Stage 5 (Project Relevance) logic

#### **Updated: Agent Service**
Enhanced TypeScript interfaces to match backend response.

**File: `NewFrontend/src/services/agentService.ts`**

**Changes:**
- Added `project_relevance_score` and `relevant_projects` to `AgentRunResponse`
- Added detailed `XAIResponse`, `SkillLevelXAI`, and `ShapLevelXAI` interfaces
- Properly typed all XAI-related fields

## How It Works

### Data Flow

```
User uploads CV → Pipeline Stage 1-3 → Stage 4: Agent Runtime API
                                           ↓
                                    /agent/run endpoint
                                           ↓
                        ┌──────────────────┴──────────────────┐
                        ↓                                      ↓
                 Gap Analysis                         XAI Service (SHAP)
                        ↓                                      ↓
              Recommendation API ←────── Project Relevance     │
                        │                                      │
                        └──────────────→ Merged Response ←─────┘
                                           ↓
                                    AgentRunResponse
                                    {
                                      readiness_score,
                                      skill_gap_top,
                                      project_relevance_score, ✅ NEW
                                      relevant_projects,        ✅ NEW
                                      xai: {
                                        shap_level: { ... }    ✅ NEW
                                      }
                                    }
                                           ↓
                                    Frontend Display
```

### XAI SHAP Response Structure

```typescript
{
  enabled: true,
  predicted_skill_gap_index: 0.35,      // ML model prediction
  predicted_readiness: 0.65,             // 1 - gap_index
  
  // Factors that INCREASE skill gap (bad for candidate)
  top_increasing_factors: [
    {
      feature: "Total Experience (Months)",
      value: 12,
      impact: 0.12,                       // Positive = increases gap
      message: "You have less professional experience than typically expected"
    }
  ],
  
  // Factors that REDUCE skill gap (good for candidate)
  top_reducing_factors: [
    {
      feature: "Role-Skill Match Coverage",
      value: 0.75,
      impact: -0.08,                      // Negative = reduces gap
      message: "You have good coverage of the role's required skills"
    }
  ],
  
  summary_text: "Main gap contributors: experience. Key strengths: skill coverage.",
  base_value: 0.5,
  notes: ["Graph-based readiness is authoritative; ML is an estimate"]
}
```

## Visual Display

### XAI Explanation Component Layout

```
┌─────────────────────────────────────────────────────────┐
│ 🧠 AI-Powered Insights                      65% Predicted│
│    Explainable AI analysis using SHAP                   │
├─────────────────────────────────────────────────────────┤
│ 💡 Main gap contributors: experience.                   │
│    Key strengths: skill coverage.                       │
├─────────────────────────────────────────────────────────┤
│ Areas for Improvement      │  Your Strengths           │
│ ──────────────────────────│───────────────────────────│
│ 📈 Total Experience         │ 📉 Role-Skill Coverage   │
│    +0.120                   │    -0.080                │
│    Less experience than     │    Good coverage of      │
│    typically required       │    role-required skills  │
│                             │                           │
│ 📈 Skill Proficiency        │ 📉 Project Portfolio     │
│    +0.095                   │    -0.065                │
│    Lower skill proficiency  │    Strong project        │
│    levels overall           │    portfolio             │
└─────────────────────────────────────────────────────────┘
```

## API Endpoints

### Agent Runtime API (Port 8003)

#### `POST /agent/run`
**Query Parameters:**
- `role_key`: Target role (e.g., "ai_ml_engineer")
- `top_k`: Number of skill deficits (default: 25)
- `include_xai`: Enable XAI analysis (default: true)

**Response:**
```json
{
  "candidate_id": "cand_001",
  "role_key": "ai_ml_engineer",
  "readiness_score": 0.65,
  "project_relevance_score": 0.72,
  "relevant_projects": [
    {
      "project_name": "ML Pipeline",
      "relevance_score": 0.85,
      "matched_role_skills": ["Python", "TensorFlow"]
    }
  ],
  "xai": {
    "skill_level": { /* Skill-level contributions */ },
    "shap_level": { /* SHAP feature impacts */ }
  }
}
```

#### `GET /runtime/predict-explain`
**Query Parameters:**
- `candidate_id`: Candidate ID
- `role_key`: Target role
- `top_k`: Number of top features (default: 5)

**Response:**
```json
{
  "enabled": true,
  "predicted_readiness": 0.65,
  "top_increasing_factors": [...],
  "top_reducing_factors": [...],
  "summary_text": "..."
}
```

## Configuration

### Environment Variables (NewFrontend)

**File: `.env`**
```bash
# Agent Runtime API (Port 8003)
VITE_JOB_GAP_API_URL=http://localhost:8003

# Advanced Recommendation System (Port 8001)
VITE_API_BASE_URL=http://localhost:8001

# Colab Explainer (ngrok tunnel)
VITE_COLAB_EXPLAIN_URL=https://YOUR-NGROK-URL.ngrok.io
```

### Backend Configuration

**File: `Agent-Runtime/config.py`**
```python
# Recommendation API
RECOMMENDATION_API_BASE_URL = "http://localhost:8001"

# XAI Model Path
XAI_MODEL_PATH = "ml_models/skillgap_pipeline.joblib"
```

## Testing the Integration

### 1. Start Backend Services

```powershell
# Terminal 1: Advanced Recommendation System (Port 8001)
cd "F:\CV Parser Agent\Advanced-Recommendation-System"
& "F:\CV Parser Agent\.venv\Scripts\Activate.ps1"
python main.py

# Terminal 2: Agent Runtime (Port 8003)
cd "F:\CV Parser Agent\Agent-Runtime"
& "F:\CV Parser Agent\.venv\Scripts\Activate.ps1"
uvicorn main:app --reload --port 8003
```

### 2. Start Frontend

```powershell
# Terminal 3: NewFrontend
cd "F:\CV Parser Agent\NewFrontend"
npm run dev
```

### 3. Test Workflow

1. Go to `http://localhost:5173` (or your Vite port)
2. Navigate to **Analysis** page
3. Paste candidate JSON in **Role-Based Analysis** tab
4. Select a target role (e.g., "AI/ML Engineer")
5. Click **Run Analysis**
6. Watch pipeline progress through 6 stages:
   - Extracting
   - Normalizing
   - Writing to Neo4j
   - Analyzing Gaps
   - **Project Relevance** ✅ (now automatic)
   - AI Explanation
7. View results with:
   - Readiness score
   - Matched skills
   - **XAI Insights** ✅ (SHAP-based explanations)
   - AI Explanation (Colab explainer)
   - Skill gaps
   - **Relevant projects** ✅ (with scores)

### 4. Verify XAI Display

Look for the **"AI-Powered Insights"** card with:
- 🧠 Brain icon
- Predicted readiness percentage
- Two-column layout:
  - **Areas for Improvement** (red, factors increasing gap)
  - **Your Strengths** (green, factors reducing gap)
- Plain English messages for each factor
- Impact scores

## Benefits

### For Users
1. **Transparency**: Understand WHY the AI predicted a certain skill gap
2. **Actionable Insights**: Clear explanations of what to improve
3. **Confidence**: See what you're already good at
4. **Trust**: SHAP is industry-standard explainable AI

### For Developers
1. **Maintainability**: Modular component design
2. **Type Safety**: Full TypeScript interfaces
3. **Performance**: Single API call includes all data
4. **Error Handling**: Graceful fallbacks if XAI unavailable

### For Researchers
1. **Validation**: Compare ML predictions with graph-based scores
2. **Feature Importance**: Identify which factors matter most
3. **Model Debugging**: Understand model behavior
4. **Publication Ready**: SHAP is academically recognized

## Troubleshooting

### XAI Not Displaying

**Check:**
1. Agent Runtime is running on port 8003
2. `include_xai=true` in API call
3. Model file exists: `Agent-Runtime/ml_models/skillgap_pipeline.joblib`
4. SHAP library installed: `pip install shap`
5. Check browser console for `results.xai` object

**Expected Console Log:**
```javascript
{
  xai: {
    shap_level: {
      enabled: true,
      predicted_readiness: 0.65,
      top_increasing_factors: [...],
      top_reducing_factors: [...]
    }
  }
}
```

### Project Relevance Score Missing

**Check:**
1. Recommendation API running on port 8001
2. Candidate has projects in Neo4j
3. Projects have skills: `(Project)-[:USES_TECHNOLOGY]->(Skill)`
4. Backend logs show successful project fetch

**Expected Response:**
```json
{
  "project_relevance_score": 0.72,
  "relevant_projects": [...]
}
```

### Performance Issues

**Optimization:**
- SHAP computation can be slow (2-5 seconds)
- Pipeline stages simulate progress
- Consider caching SHAP results if same candidate analyzed multiple times

## Future Enhancements

1. **Skill-Level XAI Display**: Add visualization for `xai.skill_level` contributions
2. **Interactive SHAP Plots**: Integrate SHAP waterfall/force plots
3. **Comparison View**: Compare XAI insights across multiple roles
4. **Customization**: Allow users to adjust `top_k` for more/fewer factors
5. **Export**: Download XAI report as PDF

## Related Files

### Backend
- `Agent-Runtime/main.py` - Main API endpoints
- `Agent-Runtime/services/xai_service.py` - SHAP computation logic
- `Agent-Runtime/models/schemas.py` - Response models

### Frontend
- `NewFrontend/src/components/XAIExplanation.tsx` - XAI display component
- `NewFrontend/src/pages/SkillGap.tsx` - Results page
- `NewFrontend/src/pages/Pipeline.tsx` - Analysis pipeline
- `NewFrontend/src/services/agentService.ts` - API service
- `NewFrontend/src/config/api.ts` - API configuration

## Summary

✅ **Project relevance score** now automatically included in `/agent/run` response  
✅ **XAI Runtime** integrated with SHAP-based explanations  
✅ **NewFrontend** displays AI insights in user-friendly format  
✅ **Full TypeScript** type safety for all XAI interfaces  
✅ **Production ready** with error handling and fallbacks  

The ExAI Runtime integration provides transparent, interpretable AI predictions that help users understand their skill gaps and build trust in the system's recommendations! 🚀
