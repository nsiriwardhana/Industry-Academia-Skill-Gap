# Interview Backend Endpoint Verification

**Date:** March 5, 2026  
**Purpose:** Verify all endpoints from `Nilmani-backend/app/main.py` exist in unified `merge-backend/main.py`

---

## ✅ Endpoint Comparison Summary

**Total Interview Backend Endpoints:** 8  
**Status:** ✅ **100% Coverage** - All endpoints migrated successfully

---

## 📋 Detailed Endpoint Mapping

| # | Original Endpoint | Method | Unified Endpoint | Status | Description |
|---|-------------------|--------|------------------|--------|-------------|
| 1 | `/` | GET | `/interview/` | ✅ | API info endpoint |
| 2 | `/health` | GET | `/interview/health` | ✅ | Health check with Gemini status |
| 3 | `/api/upload-jd` | POST | `/interview/api/upload-jd` | ✅ | Upload job description PDF |
| 4 | `/api/start-interview` | POST | `/interview/api/start-interview` | ✅ | Start interview session |
| 5 | `/api/next-question` | POST | `/interview/api/next-question` | ✅ | Submit answer, get next question |
| 6 | `/api/session/{session_id}` | GET | `/interview/api/session/{session_id}` | ✅ | Get session status |
| 7 | `/api/session/{session_id}` | DELETE | `/interview/api/session/{session_id}` | ✅ | End session |
| 8 | `/api/sessions` | GET | `/interview/api/sessions` | ✅ | List all sessions (debug) |

---

## 🔧 Implementation Details

### Location in Unified main.py

**Implementation Block** (Lines 358-544):
```python
if INTERVIEW_AVAILABLE:
    # Import dependencies
    from fastapi import UploadFile, File
    from pydantic import BaseModel
    import fitz  # PyMuPDF for PDF extraction
    from interview_gemini.rag.loader import chunk_text
    from interview_gemini.rag.vector_store import create_vector_store
    from interview_gemini.utils.session import create_session, get_session
    from interview_gemini.services.interview import generate_next_turn
    
    # Initialize embeddings and session storage
    interview_embeddings = get_local_embeddings()
    interview_sessions = {}
    
    # Define 4 Pydantic models
    # - JDUploadResponse
    # - QuestionRequest
    # - QuestionResponse
    # - SessionStatus
    
    # Define 8 endpoints (all with /interview prefix)
```

### Pydantic Models Defined

```python
class JDUploadResponse(BaseModel):
    session_id: str
    text: str  # Extracted job description text
    chunks_count: int
    message: str

class QuestionRequest(BaseModel):
    session_id: str
    user_answer: Optional[str] = None

class QuestionResponse(BaseModel):
    question: str
    question_number: int
    total_questions: int
    is_complete: bool

class SessionStatus(BaseModel):
    session_id: str
    is_active: bool
    question_count: int
    max_questions: int
```

### Key Dependencies

- **PyMuPDF (fitz)**: PDF text extraction
- **Gemini API**: Interview question generation with RAG
- **Local Embeddings**: Sentence transformers for vector search
- **Session Management**: In-memory session storage (dict)

---

## 🧪 Testing Commands

### 1. Health Check
```bash
# API info
curl http://localhost:8000/interview/

# Detailed health
curl http://localhost:8000/interview/health
```

### 2. Upload Job Description
```bash
# Upload JD PDF to create interview session
curl -X POST http://localhost:8000/interview/api/upload-jd \
  -F "file=@job_description.pdf"

# Response:
# {
#   "session_id": "uuid-string",
#   "text": "Job description text...",
#   "chunks_count": 5,
#   "message": "Job description processed successfully"
# }
```

### 3. Start Interview
```bash
# Get first question
curl -X POST http://localhost:8000/interview/api/start-interview \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id"
  }'

# Response:
# {
#   "question": "Tell me about your experience with...",
#   "question_number": 1,
#   "total_questions": 5,
#   "is_complete": false
# }
```

### 4. Submit Answer & Get Next Question
```bash
# Submit answer and continue
curl -X POST http://localhost:8000/interview/api/next-question \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "user_answer": "I have 3 years of experience working with Python and FastAPI..."
  }'

# Response:
# {
#   "question": "Next interview question...",
#   "question_number": 2,
#   "total_questions": 5,
#   "is_complete": false
# }
```

### 5. Session Management
```bash
# Get session status
curl http://localhost:8000/interview/api/session/your-session-id

# List all active sessions (debugging)
curl http://localhost:8000/interview/api/sessions

# End session
curl -X DELETE http://localhost:8000/interview/api/session/your-session-id
```

---

## 🔄 Frontend Migration Examples

### Before (Separate Backend - Port 8005)
```typescript
const INTERVIEW_URL = "http://localhost:8005";

// Old endpoints (no prefix)
fetch(`${INTERVIEW_URL}/api/upload-jd`, { ... });
fetch(`${INTERVIEW_URL}/api/start-interview`, { ... });
fetch(`${INTERVIEW_URL}/api/next-question`, { ... });
```

### After (Unified Backend - Port 8000)
```typescript
const BASE_URL = "http://localhost:8000";

// New endpoints with /interview prefix
fetch(`${BASE_URL}/interview/api/upload-jd`, { ... });
fetch(`${BASE_URL}/interview/api/start-interview`, { ... });
fetch(`${BASE_URL}/interview/api/next-question`, { ... });
```

---

## 📊 Interview Flow Diagram

```
┌─────────────────┐
│ Upload PDF (JD) │
└────────┬────────┘
         │ Creates session_id
         ▼
┌─────────────────┐
│ Start Interview │
└────────┬────────┘
         │ Returns Q1
         ▼
┌─────────────────┐
│ Submit Answer   │ ◄──┐
│ Get Next Q      │    │
└────────┬────────┘    │
         │             │
         └─ (Loop) ────┘
         │
         │ After N questions
         ▼
┌─────────────────┐
│ Interview Done  │
│ (is_complete)   │
└─────────────────┘
```

---

## ⚙️ Configuration Requirements

### Environment Variables (.env)

```bash
# Required for interview backend
GOOGLE_API_KEY=your_gemini_api_key

# Interview settings
CHAT_MODEL=gemini-1.5-flash
EMBEDDING_MODEL=all-MiniLM-L6-v2
MAX_INTERVIEW_QUESTIONS=5

# Optional
INTERVIEW_MODEL_TEMPERATURE=0.7
```

### Dependencies

```txt
# RAG & Embeddings
langchain>=0.1.0
sentence-transformers>=2.2.0
chromadb>=0.4.0
faiss-cpu>=1.7.4

# Gemini API
google-generativeai>=0.3.0

# PDF Processing
PyMuPDF>=1.23.0  # fitz module

# Core
pydantic>=2.0.0
python-multipart>=0.0.6
```

---

## 🎯 Key Features

1. **RAG-Based Interview**: Uses job description as context for personalized questions
2. **Vector Store**: FAISS/ChromaDB for semantic search of JD content
3. **Session Management**: In-memory sessions tracking interview progress
4. **Gemini Integration**: Google's Gemini 1.5 Flash for intelligent question generation
5. **PDF Upload**: Direct PDF job description upload with text extraction
6. **Conversational Flow**: Multi-turn interview with context awareness

---

## 🔐 Security Considerations

### Production Recommendations:

1. **Session Storage**: Replace in-memory dict with Redis/database
   ```python
   # Current (development)
   interview_sessions = {}
   
   # Production
   import redis
   redis_client = redis.Redis(host='localhost', port=6379)
   ```

2. **File Upload Limits**: Add size restrictions
   ```python
   @app.post("/interview/api/upload-jd")
   async def upload_jd(file: UploadFile = File(..., max_size=10*1024*1024)):  # 10MB limit
   ```

3. **Rate Limiting**: Prevent API abuse
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/interview/api/upload-jd")
   @limiter.limit("5/minute")
   async def upload_jd(...):
   ```

4. **Session Expiry**: Auto-cleanup old sessions
   ```python
   # Add TTL to sessions
   session["created_at"] = time.time()
   session["expires_at"] = time.time() + 3600  # 1 hour
   ```

---

## 📈 Startup/Shutdown Events

### ✅ Startup (Migrated to Lifespan)

**Unified main.py Lines 207-215:**
```python
if INTERVIEW_AVAILABLE:
    logger.info("Initializing Interview backend...")
    try:
        embeddings = get_local_embeddings()
        logger.info("  ✓ Embeddings initialized for Interview system")
    except Exception as e:
        logger.error(f"  ✗ Interview backend initialization failed: {e}")
```

### Shutdown

No specific cleanup needed (in-memory sessions cleared automatically).  
For production with Redis/DB, add session cleanup in shutdown event.

---

## ✅ Verification Checklist

- [x] All 8 endpoints migrated with `/interview` prefix
- [x] Pydantic models defined (4 models)
- [x] PyMuPDF integration for PDF extraction
- [x] Embeddings initialization in lifespan
- [x] Session management implemented (in-memory dict)
- [x] Gemini API integration preserved
- [x] RAG vector store functionality maintained
- [x] Error handling for invalid PDFs
- [x] Health check with Gemini status

---

## 🚀 Usage Example (Complete Flow)

```python
import requests

BASE_URL = "http://localhost:8000"

# Step 1: Upload job description
files = {"file": open("software_engineer.pdf", "rb")}
response = requests.post(f"{BASE_URL}/interview/api/upload-jd", files=files)
session_id = response.json()["session_id"]

# Step 2: Start interview
response = requests.post(
    f"{BASE_URL}/interview/api/start-interview",
    json={"session_id": session_id}
)
question = response.json()["question"]
print(f"Q1: {question}")

# Step 3: Submit answers in loop
answers = [
    "I have 5 years of Python development experience...",
    "I've worked on microservices using FastAPI and Docker...",
    "My biggest challenge was scaling a system to handle millions of requests..."
]

for answer in answers:
    response = requests.post(
        f"{BASE_URL}/interview/api/next-question",
        json={"session_id": session_id, "user_answer": answer}
    )
    data = response.json()
    if not data["is_complete"]:
        print(f"Q{data['question_number']}: {data['question']}")
    else:
        print("Interview complete!")
        break

# Step 4: Cleanup
requests.delete(f"{BASE_URL}/interview/api/session/{session_id}")
```

---

## 📚 Related Documentation

- **Complete Integration Guide**: [UNIFIED_BACKEND_GUIDE.md](UNIFIED_BACKEND_GUIDE.md)
- **Agent-Runtime Endpoints**: [ENDPOINT_COMPARISON_AGENT_RUNTIME.md](ENDPOINT_COMPARISON_AGENT_RUNTIME.md)
- **Advanced-Recommendation Endpoints**: [ENDPOINT_COMPARISON_RECOMMENDATIONS.md](ENDPOINT_COMPARISON_RECOMMENDATIONS.md)
- **Login Endpoints**: [ENDPOINT_COMPARISON_LOGIN.md](ENDPOINT_COMPARISON_LOGIN.md)
- **Integration Summary**: [INTEGRATION_SUMMARY.md](INTEGRATION_SUMMARY.md)

---

**Status:** ✅ All interview backend endpoints successfully integrated into unified backend!

**Frontend Impact:** 🔄 **Prefix change required** - Update all API calls to include `/interview` prefix
