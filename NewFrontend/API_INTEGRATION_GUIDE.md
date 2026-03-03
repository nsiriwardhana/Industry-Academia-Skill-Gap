# New Frontend - API Integration Guide

## Overview
The new frontend is a modern TypeScript/React application with separate routes for different functionalities. This document outlines the complete API integration.

## Architecture

### Routes
- `/` - Landing page
- `/analysis` - Configure analysis (JSON input + role/job selection)
- `/pipeline` - Processing status & pipeline execution
- `/skill-gap` - Skill gap analysis results & visualization
- `/recommendations` - Actionable recommendations & learning paths

### API Services
All API calls are centralized in `/src/services/`:
- `agentService.ts` - Agent Runtime (Port 8003)
- `jobGapService.ts` - Job Gap Analysis (Port 8003)
- `recommendationService.ts` - Advanced Recommendation System (Port 8001)
- `explainerService.ts` - Colab Explainer (ngrok tunnel)

### Configuration
- `/src/config/api.ts` - Central API configuration
- `/.env` - Environment variables

## Data Flow

### Role-Based Analysis Flow
```
Analysis Page (User Input)
    ↓
Pipeline Page (Execute)
    ↓ 1. runAgentPipeline() → Agent Runtime:8003
    ↓    - Extracts, normalizes, writes to Neo4j
    ↓    - Returns: readiness, skill gaps, XAI
    ↓
    ↓ 2. getProjectRelevance() → Recommendation:8001
    ↓    - Fetches project relevance scores
    ↓    - Returns: top projects with relevance
    ↓
    ↓ 3. generateExplanation() → Colab Explainer
    ↓    - Generates AI explanation
    ↓    - Returns: natural language explanation
    ↓
Skill Gap Page (Display Results)
    ↓
Recommendations Page (Action Items)
```

### Job-Based Analysis Flow
```
Analysis Page (User Input + JD File)
    ↓
Pipeline Page (Execute)
    ↓ 1. analyzeJobGap() → Job Gap:8003
    ↓    - Extracts JD, compares with candidate
    ↓    - Returns: readiness, skill gaps
    ↓
    ↓ 2. generateExplanation() → Colab Explainer
    ↓    - Generates AI explanation
    ↓    - Returns: natural language explanation
    ↓
Skill Gap Page (Display Results)
    ↓
Recommendations Page (Action Items)
```

## API Endpoints

### Agent Runtime (Port 8003)
- `POST /agent/run` - Run complete pipeline
- `GET /runtime/skill-explain` - Get skill-level explanation
- `GET /runtime/predict-explain` - Get SHAP explanation
- `GET /health` - Health check

### Job Gap Analysis (Port 8003)
- `POST /job-gap/analyze` - Analyze job gap
- `GET /job-gap/health` - Health check

### Advanced Recommendation System (Port 8001)
- `GET /roles` - Get all roles
- `GET /candidates/{id}/roles/{role}/skill-confidence` - Skill confidence
- `GET /candidates/{id}/roles/{role}/skill-gap` - Skill gap
- `GET /candidates/{id}/roles/{role}/project-relevance` - Project relevance

### Colab Explainer (ngrok)
- `POST /explain` - Generate AI explanation
- `GET /health` - Health check

## State Management

### Analysis State (passed via React Router state)
```typescript
{
  type: 'role-based' | 'job-based',
  profile: CandidateProfile,
  targetRole?: string,
  jobFile?: File,
  storeInGraph?: boolean
}
```

### Pipeline Results State
```typescript
{
  candidate_id: string,
  role_key: string,
  readiness_score: number,
  skill_gap_index: number,
  skill_confidence_top: SkillConfidence[],
  skill_gap_top: SkillGap[],
  relevant_projects: ProjectRelevance[],
  project_relevance_score: number,
  explanation: string,
  xai: XAIResponse
}
```

## Error Handling

### Error Types
1. **Network Errors** - Backend service unavailable
2. **Validation Errors** - Invalid JSON or missing fields
3. **API Errors** - 404, 500, etc.
4. **Timeout Errors** - Long-running operations

### Error Display
- Toast notifications for user actions
- Inline error messages for form validation
- Error states in Pipeline page for failed stages

## Key Features to Implement

### 1. Analysis Page ✅
- [x] JSON validation with real-time feedback
- [x] Example profile template
- [x] Role selection from predefined list
- [x] Job description file upload
- [ ] Integration with actual role list from API
- [ ] Save/load profile functionality

### 2. Pipeline Page ⏳
- [ ] Step-by-step pipeline visualization
- [ ] Real-time progress updates
- [ ] API call to Agent Runtime
- [ ] API call to Recommendation System
- [ ] API call to Colab Explainer
- [ ] Error handling for each stage
- [ ] Retry mechanism for failed stages

### 3. Skill Gap Page ⏳
- [ ] Display readiness score with animation
- [ ] List skill gaps with priority
- [ ] Show matched skills
- [ ] Project relevance visualization
- [ ] AI explanation display
- [ ] XAI visualization (SHAP values)

### 4. Recommendations Page ⏳
- [ ] Personalized learning paths
- [ ] Course recommendations
- [ ] Certification suggestions
- [ ] Timeline estimation
- [ ] Export report functionality

## Next Steps

1. **Update Pipeline Page** - Integrate all API calls
2. **Update Skill Gap Page** - Display real API results
3. **Update Recommendations Page** - Generate actionable items
4. **Add Loading States** - Skeleton loaders, spinners
5. **Add Error Boundaries** - Graceful error handling
6. **Add Analytics** - Track user interactions
7. **Add Export** - PDF/JSON export functionality

## Testing

### Manual Testing Checklist
- [ ] Role-based analysis with valid JSON
- [ ] Job-based analysis with PDF/image upload
- [ ] Error handling (invalid JSON, network errors)
- [ ] All three backend services running
- [ ] Colab explainer running (ngrok tunnel active)
- [ ] Navigation between pages
- [ ] State persistence across routes

### Sample Test Data
Located in `/src/sampleData.ts` (to be created)
