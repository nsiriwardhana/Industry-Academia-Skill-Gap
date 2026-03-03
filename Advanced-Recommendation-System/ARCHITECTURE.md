# Advanced Recommendation System - Restructured Architecture

## 📁 Folder Structure

```
Advanced-Recommendation-System/
├── config/                      # Configuration and settings
│   ├── __init__.py
│   └── settings.py             # NEO4J credentials, evidence weights, cache TTL
│
├── models/                      # Pydantic schemas for validation
│   ├── __init__.py
│   └── schemas.py              # Request/response models
│
├── database/                    # Database connection management
│   ├── __init__.py
│   └── neo4j_connection.py     # Singleton Neo4j driver
│
├── services/                    # Business logic (pure Python + Cypher)
│   ├── __init__.py
│   ├── skill_confidence_service.py      # Multi-evidence confidence
│   ├── role_importance_service.py       # TF-IDF computation
│   ├── deficit_service.py               # Deficit ranking
│   └── course_recommendation_service.py # Course scoring
│
├── routes/                      # FastAPI route handlers
│   ├── __init__.py
│   └── recommendation_routes.py # API endpoints
│
├── utils/                       # Helper utilities
│   ├── __init__.py
│   └── cache.py                # In-memory cache with TTL
│
├── main.py                      # Application entry point
├── requirements.txt
├── .env.example
└── README.md
```

## 🎯 Key Improvements

### ✅ Fixed Issues
1. **Neo4j Cypher Syntax Error**: Replaced deprecated `size()` with `COUNT {}`
   ```cypher
   # Before (deprecated):
   size((r)<-[:BELONGS_TO_ROLE]-(:Job)) AS total_jobs
   
   # After (correct):
   COUNT {(r)<-[:BELONGS_TO_ROLE]-(:Job)} AS total_jobs
   ```

2. **Modular Architecture**: Separated concerns into logical folders
   - **Easier maintenance**: Each component has single responsibility
   - **Better testability**: Services can be unit tested independently
   - **Improved readability**: 200-300 lines per file vs 900+ in one file

### 📦 Module Responsibilities

#### `config/settings.py`
- Environment variables (NEO4J_URI, USER, PASSWORD)
- Evidence weights (HAS_SKILL, USED_SKILL, etc.)
- Cache TTL configuration
- API metadata (title, version, description)

#### `models/schemas.py`
- Pydantic models for request validation
- Response schemas with examples
- Type safety and automatic documentation

#### `database/neo4j_connection.py`
- Singleton Neo4j driver
- Connection pooling
- Session context manager

#### `services/`
- **skill_confidence_service.py**: Computes P(has(skill)) from multiple evidence sources
- **role_importance_service.py**: Computes TF-IDF with caching
- **deficit_service.py**: Ranks deficits = importance × (1 - confidence)
- **course_recommendation_service.py**: Scores courses by gain

#### `routes/recommendation_routes.py`
- FastAPI endpoint definitions
- Request validation
- Error handling
- Response serialization

#### `utils/cache.py`
- In-memory cache with TTL
- Automatic expiration
- Cache statistics

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your Neo4j credentials
```

### 3. Run Server
```bash
python main.py
```

Server starts at: http://localhost:8001

### 4. View Documentation
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## 📊 API Endpoints

### 1. List Roles
```http
GET /roles
```

### 2. Role Skill Profile (TF-IDF)
```http
GET /roles/{role_key}/skill-profile?top_n=100
```

### 3. Candidate Skill Confidence
```http
GET /candidates/{candidate_id}/skill-confidence?top_n=100
```

### 4. Skill Gap Analysis
```http
GET /candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced?top_k=25
```

### 5. Course Recommendations
```http
GET /candidates/{candidate_id}/roles/{role_key}/recommendations?top_k=25&top_n=10
```

### 6. Clear Cache (Admin)
```http
GET /cache/clear
```

## 🔧 Configuration

### Evidence Weights (`config/settings.py`)
```python
EVIDENCE_WEIGHTS = {
    "HAS_SKILL": 0.70,           # CV direct claim
    "USED_SKILL": 0.90,          # Work experience (strongest)
    "USES_TECHNOLOGY": 0.80,     # Project evidence
    "CERTIFICATION": 0.60,       # Certification evidence
}
```

### Cache TTL (`config/settings.py`)
```python
CACHE_TTL = 3600  # seconds (1 hour)
```

Adjust based on:
- **Higher TTL**: Better performance, stale data risk
- **Lower TTL**: Fresher data, more database queries

## 🧪 Testing

### Test Skill Profile Endpoint (Fixed!)
```bash
curl "http://localhost:8001/roles/ai_ml_engineer/skill-profile?top_n=20"
```

**Expected Response**:
```json
{
  "role_key": "ai_ml_engineer",
  "role_name": "AI/ML Engineer",
  "total_jobs": 50,
  "total_roles": 15,
  "skills": [
    {
      "skill_name": "Python",
      "tf": 45,
      "df": 8,
      "idf": 0.845,
      "importance": 38.025,
      "percentage": 90.0
    }
  ]
}
```

### Test Candidate Confidence
```bash
curl "http://localhost:8001/candidates/CAND_001/skill-confidence?top_n=20"
```

### Test Skill Gap Analysis
```bash
curl "http://localhost:8001/candidates/CAND_001/roles/ai_ml_engineer/skill-gap-advanced?top_k=25"
```

### Test Course Recommendations
```bash
curl "http://localhost:8001/candidates/CAND_001/roles/ai_ml_engineer/recommendations?top_k=25&top_n=10"
```

## 🎨 Best Practices Applied

### 1. **Separation of Concerns**
- Configuration separate from logic
- Business logic separate from routing
- Database management isolated

### 2. **Single Responsibility Principle**
- Each service handles one concern
- Each model represents one entity
- Each route handles one endpoint group

### 3. **DRY (Don't Repeat Yourself)**
- Shared cache utility
- Reusable database connection
- Common Pydantic models

### 4. **Type Safety**
- Type hints throughout
- Pydantic validation
- Runtime type checking

### 5. **Error Handling**
- HTTP exceptions for client errors
- Logging for debugging
- Graceful degradation

### 6. **Performance**
- Connection pooling (Neo4j driver)
- Caching (role TF-IDF)
- Efficient Cypher queries

### 7. **Documentation**
- Docstrings on all functions
- Pydantic model examples
- API descriptions

## 📝 Development Workflow

### Adding a New Endpoint

1. **Define Models** (`models/schemas.py`):
```python
class NewRequest(BaseModel):
    param: str

class NewResponse(BaseModel):
    result: str
```

2. **Create Service** (`services/new_service.py`):
```python
class NewService:
    @staticmethod
    def process(session, param: str):
        # Business logic here
        return {"result": "processed"}
```

3. **Add Route** (`routes/recommendation_routes.py`):
```python
@router.get("/new-endpoint", response_model=NewResponse)
def new_endpoint(param: str):
    with Neo4jConnection.get_session() as session:
        result = NewService.process(session, param)
    return NewResponse(**result)
```

### Modifying Evidence Weights

Edit `config/settings.py`:
```python
EVIDENCE_WEIGHTS = {
    "HAS_SKILL": 0.75,      # Increased from 0.70
    "USED_SKILL": 0.95,     # Increased from 0.90
    # ...
}
```

Restart server for changes to take effect.

### Adding New Evidence Source

1. Add weight to `config/settings.py`
2. Add Cypher query to `services/skill_confidence_service.py`
3. Update documentation

## 🔍 Debugging

### Enable Debug Logging
```python
# config/settings.py
LOG_LEVEL = "DEBUG"  # Change from "INFO"
```

### Check Cache Statistics
```python
# In Python shell
from utils import cache
print(f"Cache size: {cache.size()}")
```

### Profile Cypher Queries
```cypher
PROFILE MATCH (r:Role {role_key: "ai_ml_engineer"})
OPTIONAL MATCH (r)<-[:BELONGS_TO_ROLE]-(j:Job)-[:REQUIRES_SKILL]->(s:Skill)
WITH r, s, count(DISTINCT j) AS tf, 
     COUNT {(r)<-[:BELONGS_TO_ROLE]-(:Job)} AS total_jobs
WHERE s IS NOT NULL
RETURN r.name, s.name, tf, total_jobs
```

## 📚 Architecture Diagram

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request
       ▼
┌─────────────┐
│   Routes    │ (FastAPI Endpoints)
└──────┬──────┘
       │ Call Service
       ▼
┌─────────────┐
│  Services   │ (Business Logic)
└──────┬──────┘
       │ Query Database
       ▼
┌─────────────┐
│  Database   │ (Neo4j Connection)
└──────┬──────┘
       │ Cypher Query
       ▼
┌─────────────┐
│   Neo4j     │ (Graph Database)
└─────────────┘
```

## 🎓 Research Applications

This modular structure makes it easy to:

1. **Swap Components**: Replace TF-IDF with other importance metrics
2. **A/B Testing**: Run multiple service versions in parallel
3. **Ablation Studies**: Disable evidence sources by commenting code
4. **Performance Profiling**: Time individual service calls
5. **Unit Testing**: Test services independently

## 📈 Performance Considerations

### Cached Operations
- ✅ Role TF-IDF computation (1 hour TTL)
- ✅ Total roles count (embedded in queries)

### Not Cached (By Design)
- ❌ Candidate skill confidence (user-specific)
- ❌ Skill gap analysis (combines user + role)
- ❌ Course recommendations (personalized)

### Optimization Tips
1. **Increase Cache TTL** for stable data
2. **Add Indexes** on Neo4j properties
3. **Batch Queries** for multiple candidates
4. **Use Connection Pooling** (already enabled)

## ✨ Summary

The restructured system:
- ✅ **Fixes** the Neo4j syntax error (`COUNT {}` instead of `size()`)
- ✅ **Organizes** code into logical modules
- ✅ **Improves** maintainability and testability
- ✅ **Follows** Python best practices
- ✅ **Maintains** all original functionality
- ✅ **Enables** easier research and experimentation

**No breaking changes** - all endpoints remain the same!
