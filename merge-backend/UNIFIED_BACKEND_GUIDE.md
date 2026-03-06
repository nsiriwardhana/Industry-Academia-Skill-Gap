# Unified Backend API - Integration Guide

## Overview

All separate backend services have been consolidated into a **single FastAPI application** in `merge-backend/main.py`. This eliminates the need to run multiple backend servers on different ports.

## Consolidated Services

| Service | Original Port | New Prefix | Description |
|---------|--------------|------------|-------------|
| **Advanced-Recommendation-System** | 8001 | `/recommendations` | Skill gap analysis, course recommendations, GNN-powered personalization |
| **Agent-Runtime** | 8002 | `/agent-runtime` | CV processing, agentic skill extraction, gap analysis with XAI |
| **Login** | 8000 | `/auth`, `/candidate` | OAuth 2.0 with Google, JWT tokens, candidate management |
| **Nilmani-backend** (Interview) | 8005 | `/interview` | AI-powered interview training with RAG and Gemini |
| **Nipuni_backend** (Skills Validation) | N/A | `/skills-validation` | Transcript processing, quiz generation, job recommendations |

## Running the Unified Backend

### Prerequisites

1. **Python Virtual Environment** (if not already created):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```powershell
   cd merge-backend
   pip install -r requirements.txt
   ```

3. **Environment Variables**: Ensure all `.env` files are properly configured in each subdirectory:
   - `merge-backend/Advanced-Recommendation-System/.env`
   - `merge-backend/Agent-Runtime/.env`
   - `merge-backend/login/.env`
   - `merge-backend/Nilmani-backend/app/.env`
   - `merge-backend/Nipuni_backend/src/.env`

### Start the Server

```powershell
cd merge-backend
python main.py
```

Or with uvicorn directly:
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The unified API will be available at:
- **Root**: http://localhost:8000/
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints by Service

### 1. Recommendations (`/recommendations`)

**Original**: Running on port 8001  
**New**: Prefixed with `/recommendations`

- `GET /recommendations/` - Service info
- `GET /recommendations/roles` - List available roles
- `GET /recommendations/candidates/{candidate_id}/roles/{role_key}/skill-gap` - Get skill gap analysis
- `GET /recommendations/candidates/{candidate_id}/roles/{role_key}/course-recommendations` - Get course recommendations
- `GET /recommendations/candidates/{candidate_id}/roles/{role_key}/project-relevance` - Get project relevance scores
- `GET /recommendations/xai/explain` - XAI explanations for recommendations

### 2. Agent Runtime (`/agent-runtime`)

**Original**: Running on port 8002  
**New**: Prefixed with `/agent-runtime`

#### Core Endpoints
- `GET /agent-runtime/` - Service info
- `GET /agent-runtime/health` - Health check
- `POST /agent-runtime/run` - Run complete agentic pipeline (JSON input)
- `POST /agent-runtime/run-from-pdf` - Run pipeline from PDF upload

#### Explainability (XAI)
- `GET /agent-runtime/skill-explain` - Skill-level explainability
- `GET /agent-runtime/predict-explain` - Model-level explainability (user-friendly)

#### Job Gap Analysis
- `POST /agent-runtime/job-gap/analyze` - Analyze job description gap
- `POST /agent-runtime/job-gap/analyze-image` - Analyze from JD image
- `POST /agent-runtime/job-gap/analyze-pdf` - Analyze from JD PDF

#### Utilities
- `GET /agent-runtime/aliases` - Get skill normalization aliases

### 3. Authentication (`/auth`)

**Original**: Running on port 8000  
**New**: Prefixed with `/auth`

- `GET /auth/login/google` - Initiate Google OAuth login
- `GET /auth/google/callback` - OAuth callback
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Logout
- `GET /auth/health` - Health check

### 4. Candidate Management (`/candidate`)

**Original**: Running on port 8000  
**New**: Prefixed with `/candidate`

- `POST /candidate/init` - Initialize candidate data collection
- `GET /candidate/{candidate_id}/status` - Get candidate status
- `GET /candidate/me` - Get my candidate profile
- `DELETE /candidate/me` - Delete my candidate data
- `GET /candidate/health` - Health check

### 5. Interview System (`/interview`)

**Original**: Running on port 8005  
**New**: Prefixed with `/interview`

**Note**: Interview endpoints require manual integration. For now, refer to the original `Nilmani-backend/app/main.py` for available endpoints:
- `POST /interview/api/upload-jd` - Upload job description PDF
- `POST /interview/api/start-interview` - Start interview session
- `POST /interview/api/next-question` - Get next question
- `GET /interview/api/session/{session_id}` - Get session status

### 6. Skills Validation (`/skills-validation`)

**Original**: No specific port  
**New**: Prefixed with `/skills-validation`

#### Admin
- Skills admin endpoints under `/skills-validation/admin`

#### Transcripts
- Transcript processing endpoints under `/skills-validation/transcript`

#### Skills Management
- Skill management endpoints under `/skills-validation/skills`

#### Quiz System
- Quiz generation and submission under `/skills-validation/quiz`

#### Question Bank
- Question bank management under `/skills-validation/question-bank`

#### Job Recommendations
- ML-based job recommendations under `/skills-validation/jobs`

#### Profile
- User profile management under `/skills-validation/profile`

#### XAI
- Explainability for skills validation under `/skills-validation/xai`

## Database Connections

The unified backend manages multiple database connections:

### Neo4j (for Recommendations & Agent Runtime)
- **Advanced-Recommendation-System**: Uses its own Neo4j connection
- **Agent-Runtime**: Uses its own Neo4j connection
- Both can connect to the same or different Neo4j instances based on `.env` configuration

### MySQL (for Login & Skills Validation)
- **Login**: Used for OAuth user data and candidate management
- **Nipuni_backend**: Used for transcripts, skills, quizzes, and job recommendations

## Configuration

Each service maintains its own configuration in its respective directory:

```
merge-backend/
├── Advanced-Recommendation-System/
│   ├── .env                    # Neo4j, GNN model paths
│   └── config/settings.py
├── Agent-Runtime/
│   ├── .env                    # Neo4j, LLM API keys
│   └── config/settings.py
├── login/
│   ├── .env                    # MySQL, Google OAuth credentials
│   └── app/config.py
├── Nilmani-backend/app/
│   ├── .env                    # Gemini API key
│   └── core/config.py
└── Nipuni_backend/src/
    ├── .env                    # MySQL, ML model paths
    └── app/config.py
```

## Frontend Integration

Update your frontend to point all API calls to `http://localhost:8000` with the appropriate prefix:

### Before (Multiple Ports)
```javascript
// Recommendations
fetch('http://localhost:8001/roles')

// Agent
fetch('http://localhost:8002/agent/run')

// Auth
fetch('http://localhost:8000/auth/login/google')
```

### After (Unified Backend)
```javascript
// Recommendations
fetch('http://localhost:8000/recommendations/roles')

// Agent
fetch('http://localhost:8000/agent-runtime/run')

// Auth (unchanged)
fetch('http://localhost:8000/auth/login/google')
```

## Health Monitoring

The unified backend provides comprehensive health checks:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "services": {
    "recommendations": "healthy",
    "agent_runtime": "healthy",
    "authentication": "healthy",
    "interview": "healthy",
    "skills_validation": "healthy"
  }
}
```

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Unified Backend API (Port 8000)            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────┐  ┌──────────────────┐             │
│  │ Recommendations   │  │  Agent Runtime   │             │
│  │   (Neo4j)         │  │    (Neo4j)       │             │
│  └───────────────────┘  └──────────────────┘             │
│                                                             │
│  ┌───────────────────┐  ┌──────────────────┐             │
│  │ Authentication    │  │   Interview      │             │
│  │   (MySQL)         │  │   (Gemini)       │             │
│  └───────────────────┘  └──────────────────┘             │
│                                                             │
│  ┌───────────────────┐                                    │
│  │ Skills Validation │                                    │
│  │    (MySQL)        │                                    │
│  └───────────────────┘                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Import Errors

If you encounter import errors when starting the server:

1. **Verify Python Path**: The unified `main.py` dynamically adds each service directory to `sys.path`
2. **Check Dependencies**: Ensure all requirements are installed: `pip install -r requirements.txt`
3. **Service-Specific Issues**: Check logs for which service failed to import and verify its `.env` file

### Database Connection Errors

- **Neo4j**: Verify connection strings in `Advanced-Recommendation-System/.env` and `Agent-Runtime/.env`
- **MySQL**: Verify connection strings in `login/.env` and `Nipuni_backend/src/.env`

### Missing Endpoints

Some services may not load if:
- Required dependencies are missing (e.g., PyTorch for AI Explainer)
- Configuration files are incomplete
- Database connections fail

Check the startup logs to see which services loaded successfully.

## Migration Checklist

- [x] ✅ Created unified `main.py`
- [x] ✅ Consolidated all routers with unique prefixes
- [x] ✅ Configured shared CORS middleware
- [x] ✅ Added comprehensive health checks
- [x] ✅ Documented all endpoint mappings
- [ ] ⚠️ Integrate Interview system endpoints manually
- [ ] 📝 Update frontend API calls
- [ ] 📝 Test all endpoints end-to-end

## Known Limitations

1. **Interview System**: The Nilmani-backend (Interview) endpoints are not fully integrated due to complex dependencies. For now, they can be accessed by importing the app separately.

2. **Session Management**: The unified backend uses session middleware primarily for the Login service. Ensure cookies are properly handled in your frontend.

3. **Database Isolation**: Each service maintains its own database connection pool. This is by design to avoid conflicts but means you cannot directly share transactions across services.

## Next Steps

1. **Test the Unified Backend**: Start the server and verify all endpoints work correctly
2. **Update Frontend**: Change all API base URLs to use the new prefixed endpoints
3. **Monitor Logs**: Watch for any import or runtime errors during startup
4. **Gradual Migration**: Test each service endpoint individually before full deployment

## Support

If you encounter issues:
1. Check the console logs for detailed error messages
2. Verify all `.env` files are properly configured
3. Ensure all required services (Neo4j, MySQL) are running
4. Review the `/health` endpoint for service status

---

**Created**: March 5, 2026  
**Author**: GitHub Copilot  
**Version**: 1.0.0
