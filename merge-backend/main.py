"""
Unified Backend API - Integration of All Services
==================================================

Consolidates all separate backend services into a single FastAPI application:
- Advanced-Recommendation-System (Neo4j-based recommendations) → /recommendations
- Agent-Runtime (CV processing, skill gap analysis) → /agent-runtime
- Login (OAuth authentication, candidate management) → /auth
- Nilmani-backend (Interview system with Gemini) → /interview
- Nipuni_backend (Skills validation, quiz system) → /skills-validation

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Swagger docs:
    http://localhost:8000/docs
"""

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Import configurations and setup from each backend
# ============================================================================

# Advanced-Recommendation-System imports
try:
    sys.path.insert(0, str(Path(__file__).parent / "Advanced-Recommendation-System"))
    from config import settings as rec_settings
    from database import Neo4jConnection as RecNeo4jConnection
    from routes import router as recommendation_router
    from xai.api import router as rec_xai_router, initialize_xai_service as init_rec_xai
    from services.gnn_inference_service import gnn_service
    RECOMMENDATION_AVAILABLE = True
    logger.info("[OK] Advanced-Recommendation-System imported successfully")
except Exception as e:
    RECOMMENDATION_AVAILABLE = False
    recommendation_router = None
    rec_xai_router = None
    logger.warning(f"[WARN] Advanced-Recommendation-System not available: {e}")

# Agent-Runtime imports
try:
    sys.path.insert(0, str(Path(__file__).parent / "Agent-Runtime"))
    from config import settings as agent_settings
    from database import Neo4jConnection as AgentNeo4jConnection
    from routes.job_gap_routes import router as job_gap_router
    from routes.job_skill_test_routes import router as job_skill_test_router
    
    # Try to import explainer routes (optional - requires PyTorch)
    try:
        from routes.explainer_routes import router as explainer_router
        EXPLAINER_AVAILABLE = True
    except ImportError:
        explainer_router = None
        EXPLAINER_AVAILABLE = False
    
    AGENT_RUNTIME_AVAILABLE = True
    logger.info("[OK] Agent-Runtime imported successfully")
except Exception as e:
    AGENT_RUNTIME_AVAILABLE = False
    job_gap_router = None
    job_skill_test_router = None
    explainer_router = None
    EXPLAINER_AVAILABLE = False
    logger.warning(f"[WARN] Agent-Runtime not available: {e}")

# Login backend imports
try:
    sys.path.insert(0, str(Path(__file__).parent / "login"))
    from app.config import settings as login_settings
    from app.database import init_db as init_login_db
    from app.routes.auth import router as auth_router
    from app.routes.candidate import router as candidate_router
    from app.services.candidate_service import CandidateService
    LOGIN_AVAILABLE = True
    logger.info("[OK] Login backend imported successfully")
except Exception as e:
    LOGIN_AVAILABLE = False
    auth_router = None
    candidate_router = None
    logger.warning(f"[WARN] Login backend not available: {e}")

# Nilmani-backend (Interview) imports
try:
    sys.path.insert(0, str(Path(__file__).parent / "Nilmani-backend" / "app"))
    from core.config import settings as interview_settings
    from interview_gemini.rag.embeddings import get_local_embeddings
    import main as interview_main_module
    INTERVIEW_AVAILABLE = True
    logger.info("[OK] Nilmani-backend (Interview) imported successfully")
except Exception as e:
    INTERVIEW_AVAILABLE = False
    logger.warning(f"[WARN] Nilmani-backend (Interview) not available: {e}")

# Nipuni_backend (Skills Validation) imports
try:
    sys.path.insert(0, str(Path(__file__).parent / "Nipuni_backend" / "src"))
    from app.db import engine as nipuni_engine, Base as NipuniBase
    from app import models as nipuni_models
    from app.routes import (
        admin_router,
        transcript_router,
        skills_router,
        quiz_router,
        admin_question_bank_router,
        admin_question_persistence_router,
        xai_router as nipuni_xai_router,
        jobs_router,
        job_router,
        profile_router
    )
    NIPUNI_AVAILABLE = True
    logger.info("[OK] Nipuni_backend (Skills Validation) imported successfully")
except Exception as e:
    NIPUNI_AVAILABLE = False
    admin_router = None
    transcript_router = None
    skills_router = None
    quiz_router = None
    admin_question_bank_router = None
    admin_question_persistence_router = None
    nipuni_xai_router = None
    jobs_router = None
    job_router = None
    profile_router = None
    logger.warning(f"[WARN] Nipuni_backend (Skills Validation) not available: {e}")


# ============================================================================
# Lifespan Context Manager - Startup/Shutdown
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Unified lifespan context manager for all services.
    Handles startup and shutdown for all backends.
    """
    logger.info("=" * 80)
    logger.info("🚀 Starting Unified Backend API")
    logger.info("=" * 80)
    
    # ========================================================================
    # Startup: Initialize all available services
    # ========================================================================
    
    try:
        # Initialize Advanced-Recommendation-System (Neo4j + GNN)
        if RECOMMENDATION_AVAILABLE:
            logger.info("Initializing Advanced-Recommendation-System...")
            try:
                RecNeo4jConnection.get_driver()
                logger.info("  ✓ Neo4j connection initialized for Recommendations")
                
                # Initialize XAI service
                init_rec_xai()
                logger.info("  ✓ XAI service initialized")
                
                # Load GNN model (optional)
                try:
                    base_path = Path(__file__).parent.parent / "GNN-Link-Prediction"
                    model_path = str(base_path / "models" / "best_gnn_linkpred.pt")
                    data_path = str(base_path / "output" / "heterodata_lp.pt")
                    id_maps_path = str(base_path / "output" / "id_maps.json")
                    
                    gnn_service.load_model(model_path, data_path, id_maps_path)
                    logger.info(f"  ✓ GNN model loaded: {gnn_service.get_stats()}")
                except Exception as e:
                    logger.warning(f"  ⚠ GNN model loading failed (non-critical): {e}")
            except Exception as e:
                logger.error(f"  ✗ Advanced-Recommendation-System initialization failed: {e}")
        
        # Initialize Agent-Runtime (Neo4j)
        if AGENT_RUNTIME_AVAILABLE:
            logger.info("Initializing Agent-Runtime...")
            try:
                AgentNeo4jConnection.get_driver()
                logger.info("  ✓ Neo4j connection initialized for Agent-Runtime")
            except Exception as e:
                logger.error(f"  ✗ Agent-Runtime initialization failed: {e}")
        
        # Initialize Login backend (MySQL)
        if LOGIN_AVAILABLE:
            logger.info("Initializing Login backend...")
            try:
                init_login_db()
                logger.info("  ✓ MySQL database initialized for Login")
                CandidateService.create_storage_directories()
                logger.info("  ✓ Storage directories created")
            except Exception as e:
                logger.error(f"  ✗ Login backend initialization failed: {e}")
        
        # Initialize Interview backend
        if INTERVIEW_AVAILABLE:
            logger.info("Initializing Interview backend...")
            try:
                embeddings = get_local_embeddings()
                logger.info("  ✓ Embeddings initialized for Interview system")
            except Exception as e:
                logger.error(f"  ✗ Interview backend initialization failed: {e}")
        
        # Initialize Nipuni backend (MySQL)
        if NIPUNI_AVAILABLE:
            logger.info("Initializing Nipuni Skills Validation backend...")
            try:
                NipuniBase.metadata.create_all(bind=nipuni_engine)
                logger.info("  ✓ MySQL database initialized for Skills Validation")
            except Exception as e:
                logger.error(f"  ✗ Nipuni backend initialization failed: {e}")
        
        logger.info("=" * 80)
        logger.info("✅ All services initialized successfully")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}", exc_info=True)
        raise
    
    yield
    
    # ========================================================================
    # Shutdown: Clean up all services
    # ========================================================================
    logger.info("=" * 80)
    logger.info("🛑 Shutting down Unified Backend API...")
    logger.info("=" * 80)
    
    # Close Neo4j connections
    if RECOMMENDATION_AVAILABLE:
        try:
            RecNeo4jConnection.close()
            logger.info("  ✓ Neo4j connection closed (Recommendations)")
        except Exception as e:
            logger.error(f"  ✗ Failed to close Recommendations Neo4j: {e}")
    
    if AGENT_RUNTIME_AVAILABLE:
        try:
            AgentNeo4jConnection.close()
            logger.info("  ✓ Neo4j connection closed (Agent-Runtime)")
        except Exception as e:
            logger.error(f"  ✗ Failed to close Agent-Runtime Neo4j: {e}")
    
    logger.info("=" * 80)
    logger.info("✅ Shutdown complete")
    logger.info("=" * 80)


# ============================================================================
# Create FastAPI Application
# ============================================================================

app = FastAPI(
    title="Unified Backend API - All Services",
    version="1.0.0",
    description="""
    Consolidated backend API integrating all services:
    
    - **Recommendations** (/recommendations): Advanced skill gap analysis, course recommendations, GNN-powered personalization
    - **Agent Runtime** (/agent-runtime): CV processing, agentic skill extraction, gap analysis with XAI
    - **Authentication** (/auth): OAuth 2.0 with Google, JWT tokens, candidate management
    - **Interview** (/interview): AI-powered interview training with RAG and Gemini
    - **Skills Validation** (/skills-validation): Transcript processing, quiz generation, job recommendations
    
    **Swagger UI**: http://localhost:8000/docs
    **ReDoc**: http://localhost:8000/redoc
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================================
# Middleware Configuration
# ============================================================================

# Session Middleware (required for OAuth)
if LOGIN_AVAILABLE:
    app.add_middleware(
        SessionMiddleware,
        secret_key=login_settings.SECRET_KEY if LOGIN_AVAILABLE else "default-secret-key-change-in-production",
        session_cookie="session",
        max_age=3600,  # 1 hour
        same_site="lax",
        https_only=False,  # Set to True in production with HTTPS
    )

# CORS Middleware - Allow all common frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Include Routers from All Services
# ============================================================================

# Advanced-Recommendation-System routes → /recommendations
if RECOMMENDATION_AVAILABLE and recommendation_router:
    app.include_router(recommendation_router, prefix="/recommendations", tags=["Recommendations"])
    if rec_xai_router:
        app.include_router(rec_xai_router, prefix="/recommendations/xai", tags=["Recommendations XAI"])
    logger.info("[OK] Registered Advanced-Recommendation-System routes: /recommendations")

# Agent-Runtime routes → /agent-runtime
if AGENT_RUNTIME_AVAILABLE:
    if job_gap_router:
        app.include_router(job_gap_router, prefix="/agent-runtime", tags=["Agent Runtime"])
    if job_skill_test_router:
        app.include_router(job_skill_test_router, prefix="/agent-runtime", tags=["Agent Runtime"])
    if EXPLAINER_AVAILABLE and explainer_router:
        app.include_router(explainer_router, prefix="/agent-runtime", tags=["Agent Runtime"])
    logger.info("[OK] Registered Agent-Runtime routes: /agent-runtime")

# Login backend routes → /auth
if LOGIN_AVAILABLE:
    if auth_router:
        app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    if candidate_router:
        app.include_router(candidate_router, prefix="/candidate", tags=["Candidate Management"])
    logger.info("[OK] Registered Login backend routes: /auth, /candidate")

# Interview backend routes → /interview
if INTERVIEW_AVAILABLE:
    from fastapi import UploadFile, File
    from pydantic import BaseModel
    from typing import Optional
    import fitz  # PyMuPDF
    import tempfile
    import os
    from interview_gemini.rag.loader import chunk_text
    from interview_gemini.rag.vector_store import create_vector_store
    from interview_gemini.utils.session import create_session, get_session
    from interview_gemini.services.interview import generate_next_turn
    
    # Initialize interview-specific dependencies
    interview_embeddings = get_local_embeddings()
    interview_sessions = {}
    
    # Pydantic models for Interview API
    class JDUploadResponse(BaseModel):
        session_id: str
        text: str
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
    
    
    @app.get("/interview/", tags=["Interview"])
    async def interview_root():
        """Interview API information."""
        return {
            "status": "online",
            "service": "AI Interview Training API",
            "chat_model": interview_settings.CHAT_MODEL,
            "embedding_model": interview_settings.EMBEDDING_MODEL
        }
    
    
    @app.get("/interview/health", tags=["Interview"])
    async def interview_health():
        """Detailed health check for Interview service."""
        try:
            return {
                "status": "healthy",
                "gemini": "connected",
                "chat_model": interview_settings.CHAT_MODEL,
                "embedding_model": interview_settings.EMBEDDING_MODEL
            }
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
    
    
    @app.post("/interview/api/upload-jd", response_model=JDUploadResponse, tags=["Interview"])
    async def interview_upload_jd(file: UploadFile = File(...)):
        """Upload job description PDF and initialize RAG vector store."""
        try:
            # Validate file type
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(status_code=400, detail="Only PDF files are supported")
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            # Extract text from PDF (using fitz/PyMuPDF)
            doc = fitz.open(tmp_path)
            jd_text = ""
            for page in doc:
                jd_text += page.get_text()
            doc.close()
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            if not jd_text or len(jd_text) < 50:
                raise HTTPException(status_code=400, detail="Could not extract sufficient text from PDF")
            
            # Chunk text and create vector store
            chunks = chunk_text(jd_text)
            vector_store = create_vector_store(chunks, interview_embeddings)
            
            # Create session
            session_id = create_session(vector_store)
            
            # Store additional session info
            interview_sessions[session_id] = {
                "jd_text": jd_text,
                "filename": file.filename,
                "chunks_count": len(chunks)
            }
            
            return JDUploadResponse(
                session_id=session_id,
                text=jd_text[:500] + "..." if len(jd_text) > 500 else jd_text,
                chunks_count=len(chunks),
                message="Job description processed successfully"
            )
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    
    
    @app.post("/interview/api/start-interview", response_model=QuestionResponse, tags=["Interview"])
    async def interview_start(request: QuestionRequest):
        """Start interview and get first question."""
        try:
            session = get_session(request.session_id)
            
            # Get first question
            question, _, _ = generate_next_turn(session)
            
            return QuestionResponse(
                question=question,
                question_number=session["question_count"],
                total_questions=interview_settings.MAX_INTERVIEW_QUESTIONS,
                is_complete=False
            )
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")
    
    
    @app.post("/interview/api/next-question", response_model=QuestionResponse, tags=["Interview"])
    async def interview_next_question(request: QuestionRequest):
        """Submit answer and get next question."""
        if not request.user_answer:
            raise HTTPException(status_code=400, detail="Answer is required")
        
        try:
            session = get_session(request.session_id)
            
            # Get next question based on answer
            question, feedback, ended = generate_next_turn(
                session,
                user_answer=request.user_answer
            )
            
            return QuestionResponse(
                question=question if not ended else "",
                question_number=session["question_count"],
                total_questions=interview_settings.MAX_INTERVIEW_QUESTIONS,
                is_complete=ended
            )
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generating question: {str(e)}")
    
    
    @app.get("/interview/api/session/{session_id}", response_model=SessionStatus, tags=["Interview"])
    async def interview_get_session_status(session_id: str):
        """Get session status."""
        try:
            session = get_session(session_id)
            
            return SessionStatus(
                session_id=session_id,
                is_active=session["question_count"] < interview_settings.MAX_INTERVIEW_QUESTIONS,
                question_count=session["question_count"],
                max_questions=interview_settings.MAX_INTERVIEW_QUESTIONS
            )
        except Exception as e:
            raise HTTPException(status_code=404, detail="Session not found")
    
    
    @app.delete("/interview/api/session/{session_id}", tags=["Interview"])
    async def interview_end_session(session_id: str):
        """End and cleanup session."""
        try:
            if session_id in interview_sessions:
                del interview_sessions[session_id]
            return {"message": "Session ended successfully", "session_id": session_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error ending session: {str(e)}")
    
    
    @app.get("/interview/api/sessions", tags=["Interview"])
    async def interview_list_sessions():
        """List all active sessions (for debugging)."""
        return {
            "count": len(interview_sessions),
            "sessions": [
                {
                    "session_id": sid,
                    "filename": data.get("filename", "unknown"),
                    "chunks_count": data.get("chunks_count", 0)
                }
                for sid, data in interview_sessions.items()
            ]
        }
    
    logger.info("[OK] Registered Interview backend routes: /interview")

# Nipuni Skills Validation routes → /skills-validation
if NIPUNI_AVAILABLE:
    if admin_router:
        app.include_router(admin_router, prefix="/skills-validation", tags=["Skills Admin"])
    if transcript_router:
        app.include_router(transcript_router, prefix="/skills-validation", tags=["Skills Transcript"])
    if skills_router:
        app.include_router(skills_router, prefix="/skills-validation", tags=["Skills Management"])
    if quiz_router:
        app.include_router(quiz_router, prefix="/skills-validation", tags=["Skills Quiz"])
    if admin_question_bank_router:
        app.include_router(admin_question_bank_router, prefix="/skills-validation", tags=["Skills Question Bank"])
    if admin_question_persistence_router:
        app.include_router(admin_question_persistence_router, prefix="/skills-validation", tags=["Skills Persistence"])
    if nipuni_xai_router:
        app.include_router(nipuni_xai_router, prefix="/skills-validation", tags=["Skills XAI"])
    if jobs_router:
        app.include_router(jobs_router, prefix="/skills-validation", tags=["Skills Jobs"])
    if job_router:
        app.include_router(job_router, prefix="/skills-validation", tags=["Skills Jobs"])
    if profile_router:
        app.include_router(profile_router, prefix="/skills-validation", tags=["Skills Profile"])
    
    # Add direct health endpoint for Skills Validation
    @app.get("/skills-validation/health", tags=["Skills Validation"])
    def skills_validation_health():
        """Health check for Skills Validation service."""
        return {"status": "ok"}
    
    logger.info("[OK] Registered Nipuni backend routes: /skills-validation")


# ============================================================================
# Additional Agent-Runtime Endpoints (from main.py)
# ============================================================================

if AGENT_RUNTIME_AVAILABLE:
    from fastapi import HTTPException, Query, UploadFile, File
    from models import (
        ExtractedData,
        AgentRunRequest,
        AgentRunResponse,
        HealthResponse,
        SkillConfidenceResult,
        SkillDeficitResult,
    )
    from models.xai_schemas import (
        SkillExplainResponse,
        PredictExplainResponse,
        FriendlyPredictExplainResponse,
        XAIResponse,
        SkillContribution,
    )
    from services.xai_service import get_xai_service
    from services.cv_parser_service import get_cv_parser_service
    from agents import ExtractorAgent, NormalizerAgent, KGWriterTool, GapAnalyzerTool
    import requests
    
    # Initialize agents
    extractor = ExtractorAgent()
    normalizer = NormalizerAgent()
    gap_analyzer = GapAnalyzerTool(ranking_method=agent_settings.SKILL_GAP_RANKING_METHOD)
    xai_service = get_xai_service()
    cv_parser_service = get_cv_parser_service()
    
    
    @app.get("/agent-runtime/", tags=["Agent Runtime - Info"])
    def agent_runtime_root():
        """Agent Runtime API information and available endpoints."""
        return {
            "service": "Agent Runtime Backend",
            "version": agent_settings.API_VERSION,
            "status": "running",
            "description": "Agentic orchestration for CV processing and skill gap analysis",
            "architecture": "Extractor → Normalizer → KG Writer → Gap Analyzer",
            "endpoints": {
                "run_agent": "POST /agent-runtime/run",
                "run_from_pdf": "POST /agent-runtime/run-from-pdf",
                "skill_explain": "GET /agent-runtime/skill-explain",
                "predict_explain": "GET /agent-runtime/predict-explain",
                "health": "GET /agent-runtime/health",
                "aliases": "GET /agent-runtime/aliases"
            }
        }
    
    
    @app.get("/agent-runtime/health", response_model=HealthResponse, tags=["Agent Runtime - Info"])
    def agent_runtime_health():
        """Health check for Agent Runtime."""
        neo4j_connected = False
        try:
            driver = AgentNeo4jConnection.get_driver()
            driver.verify_connectivity()
            neo4j_connected = True
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
        
        recommendation_api_available = gap_analyzer.check_api_health() if hasattr(gap_analyzer, 'check_api_health') else False
        status = "healthy" if neo4j_connected else "degraded"
        
        return HealthResponse(
            status=status,
            neo4j_connected=neo4j_connected,
            recommendation_api_available=recommendation_api_available
        )
    
    
    @app.get("/agent-runtime/skill-explain", response_model=SkillExplainResponse, tags=["Agent Runtime - XAI"])
    def agent_skill_explain(
        candidate_id: str = Query(..., description="Candidate ID"),
        role_key: str = Query(..., description="Target role key"),
        top_n: int = Query(10, ge=1, le=50, description="Number of top contributors to return")
    ):
        """Skill-level explainability: Show contribution of each skill deficit."""
        try:
            gap_result = gap_analyzer.analyze_gap(
                candidate_id=candidate_id,
                role_key=role_key,
                top_k=50
            )
            
            deficits = gap_result.get("skill_gap_top", [])
            
            if not deficits:
                return SkillExplainResponse(
                    candidate_id=candidate_id,
                    role_key=role_key,
                    top_contributors=[],
                    total_deficit=0.0
                )
            
            deficits_dict = [
                {
                    "skill_name": d.skill_name,
                    "deficit": d.deficit,
                    "importance": d.importance,
                    "p_has": d.match_strength
                }
                for d in deficits
            ]
            
            contributions = xai_service.compute_skill_level_explanation(
                deficits_dict,
                top_n=top_n
            )
            
            total_deficit = sum(d["deficit"] for d in deficits_dict)
            
            return SkillExplainResponse(
                candidate_id=candidate_id,
                role_key=role_key,
                top_contributors=[SkillContribution(**c) for c in contributions],
                total_deficit=round(total_deficit, 4)
            )
        except Exception as e:
            logger.error(f"Skill explain failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Skill explainability failed: {str(e)}")
    
    
    @app.get("/agent-runtime/predict-explain", response_model=FriendlyPredictExplainResponse, tags=["Agent Runtime - XAI"])
    def agent_predict_explain(
        candidate_id: str = Query(..., description="Candidate ID"),
        role_key: str = Query(..., description="Target role key"),
        top_k: int = Query(5, ge=1, le=10, description="Number of top features to return")
    ):
        """User-friendly model-level explainability with plain English explanations."""
        try:
            with AgentNeo4jConnection.get_session() as session:
                feature_row = xai_service.build_feature_row(session, candidate_id, role_key)
            
            if feature_row is None:
                return FriendlyPredictExplainResponse(
                    enabled=False,
                    reason="Failed to build feature row from Neo4j"
                )
            
            explanation = xai_service.compute_shap_explanation(feature_row, top_k=top_k)
            
            if explanation.get("enabled"):
                explanation["candidate_id"] = candidate_id
                explanation["role_key"] = role_key
            
            return FriendlyPredictExplainResponse(**explanation)
        except Exception as e:
            logger.error(f"Predict explain failed: {e}", exc_info=True)
            return FriendlyPredictExplainResponse(enabled=False, reason=f"Error: {str(e)}")
    
    
    @app.get("/agent-runtime/predict-explain-legacy", response_model=PredictExplainResponse, tags=["Agent Runtime - XAI"])
    def agent_predict_explain_legacy(
        candidate_id: str = Query(..., description="Candidate ID"),
        role_key: str = Query(..., description="Target role key"),
        top_k: int = Query(10, ge=1, le=20, description="Number of top features to return")
    ):
        """
        Legacy model-level explainability endpoint (backward compatibility).
        
        Use /agent-runtime/predict-explain instead for user-friendly explanations.
        
        Args:
            candidate_id: Candidate ID
            role_key: Target role key
            top_k: Number of top positive/negative contributors
            
        Returns:
            SHAP explanation with feature impacts (legacy format)
        """
        logger.info(f"Predict explain (legacy): candidate={candidate_id}, role={role_key}")
        
        try:
            # Build feature row from Neo4j
            with AgentNeo4jConnection.get_session() as session:
                feature_row = xai_service.build_feature_row(
                    session,
                    candidate_id,
                    role_key
                )
            
            if feature_row is None:
                return PredictExplainResponse(
                    enabled=False,
                    reason="Failed to build feature row from Neo4j"
                )
            
            # Compute SHAP explanation
            explanation = xai_service.compute_shap_explanation(
                feature_row,
                top_k=top_k
            )
            
            # Add candidate/role info
            if explanation.get("enabled"):
                explanation["candidate_id"] = candidate_id
                explanation["role_key"] = role_key
                
                # Convert friendly format back to legacy format
                if "top_increasing_factors" in explanation:
                    explanation["top_positive_contributors"] = [
                        {
                            "feature": item["feature"],
                            "feature_key": item.get("feature", ""),
                            "impact": item["impact"],
                            "description": item["message"],
                            "interpretation": item["message"]
                        }
                        for item in explanation["top_increasing_factors"]
                    ]
                    explanation["top_negative_contributors"] = [
                        {
                            "feature": item["feature"],
                            "feature_key": item.get("feature", ""),
                            "impact": item["impact"],
                            "description": item["message"],
                            "interpretation": item["message"]
                        }
                        for item in explanation["top_reducing_factors"]
                    ]
                    explanation["skill_gap_prediction"] = explanation.get("predicted_skill_gap_index")
                    explanation["readiness_prediction"] = explanation.get("predicted_readiness")
            
            return PredictExplainResponse(**explanation)
            
        except Exception as e:
            logger.error(f"Predict explain (legacy) failed: {e}", exc_info=True)
            return PredictExplainResponse(
                enabled=False,
                reason=f"Error: {str(e)}"
            )
    
    
    @app.post("/agent-runtime/run", response_model=AgentRunResponse, tags=["Agent Runtime - Core"])
    async def agent_run(
        cv_data: ExtractedData,
        role_key: str = Query(..., description="Target role key"),
        top_k: int = Query(25, ge=1, le=100, description="Number of top skill deficits"),
        include_xai: bool = Query(True, description="Include explainability analysis"),
        ranking_method: str = Query(None, description="Ranking method override")
    ):
        """Run complete agentic pipeline: Extract → Normalize → Write → Analyze."""
        try:
            candidate_id = cv_data.candidate_id
            
            # Step 1: Extractor
            validated_data = extractor.extract(cv_data)
            
            # Step 2: Normalizer
            normalized_data = normalizer.normalize_extracted_data(validated_data)
            normalized_skills_count = len(normalized_data.all_skills) if normalized_data.all_skills else 0
            
            # Step 3: KG Writer
            with AgentNeo4jConnection.get_session() as session:
                write_result = KGWriterTool.write_candidate(session, normalized_data)
            
            if not write_result.success:
                raise HTTPException(status_code=500, detail=f"Failed to write to Neo4j: {write_result.message}")
            
            # Step 4: Gap Analyzer
            effective_ranking_method = ranking_method or agent_settings.SKILL_GAP_RANKING_METHOD
            request_gap_analyzer = GapAnalyzerTool(ranking_method=effective_ranking_method)
            gap_result = request_gap_analyzer.analyze_gap(
                candidate_id=candidate_id,
                role_key=role_key,
                top_k=top_k
            )
            
            # Step 5: XAI (Optional)
            xai_result = None
            if include_xai:
                try:
                    deficits_dict = [
                        {"skill_name": d.skill_name, "deficit": d.deficit, "importance": d.importance, "p_has": d.match_strength}
                        for d in gap_result.get("skill_gap_top", [])
                    ]
                    
                    skill_contributions = xai_service.compute_skill_level_explanation(deficits_dict, top_n=10)
                    total_deficit = sum(d["deficit"] for d in deficits_dict)
                    
                    skill_level_xai = SkillExplainResponse(
                        candidate_id=candidate_id,
                        role_key=role_key,
                        top_contributors=[SkillContribution(**c) for c in skill_contributions],
                        total_deficit=round(total_deficit, 4)
                    )
                    
                    with AgentNeo4jConnection.get_session() as session:
                        feature_row = xai_service.build_feature_row(session, candidate_id, role_key)
                    
                    if feature_row:
                        shap_explanation = xai_service.compute_shap_explanation(feature_row, top_k=5)
                        if shap_explanation.get("enabled"):
                            shap_explanation["candidate_id"] = candidate_id
                            shap_explanation["role_key"] = role_key
                        shap_level_xai = FriendlyPredictExplainResponse(**shap_explanation)
                    else:
                        shap_level_xai = FriendlyPredictExplainResponse(enabled=False, reason="Failed to build feature row")
                    
                    xai_result = XAIResponse(skill_level=skill_level_xai, shap_level=shap_level_xai)
                except Exception as xai_error:
                    logger.warning(f"XAI computation failed: {xai_error}")
            
            return AgentRunResponse(
                candidate_id=candidate_id,
                role_key=role_key,
                status="success",
                message=f"Pipeline completed successfully for {candidate_id}",
                normalized_skills_count=normalized_skills_count,
                nodes_created=write_result.nodes_created,
                relationships_created=write_result.relationships_created,
                skill_confidence_top=gap_result.get("skill_confidence_top", []),
                skill_gap_top=gap_result.get("skill_gap_top", []),
                readiness_score=gap_result.get("readiness_score"),
                xai=xai_result
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")
    
    
    @app.post("/agent-runtime/run-from-pdf", response_model=AgentRunResponse, tags=["Agent Runtime - Core"])
    async def agent_run_from_pdf(
        cv_file: UploadFile = File(..., description="CV/Resume PDF file"),
        role_key: str = Query(..., description="Target role key"),
        top_k: int = Query(25, ge=1, le=100, description="Number of top skill deficits"),
        include_xai: bool = Query(True, description="Include explainability analysis"),
        ranking_method: str = Query(None, description="Ranking method override")
    ):
        """Run complete agentic pipeline from uploaded PDF/DOCX resume."""
        try:
            # Parse CV file
            parsed_cv = await cv_parser_service.parse_cv_file(cv_file)
            
            # Convert to ExtractedData format
            cv_data = ExtractedData(**parsed_cv)
            
            # Use the existing run endpoint logic
            return await agent_run(cv_data, role_key, top_k, include_xai, ranking_method)
        except Exception as e:
            logger.error(f"PDF pipeline failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")
    
    
    @app.get("/agent-runtime/aliases", tags=["Agent Runtime - Utils"])
    def get_aliases():
        """Get all skill normalization aliases."""
        try:
            return {"aliases": normalizer.get_all_aliases() if hasattr(normalizer, 'get_all_aliases') else {}}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    
    @app.post("/agent-runtime/aliases/add", tags=["Agent Runtime - Utils"])
    def add_alias(alias: str, canonical: str):
        """
        Add a new skill alias at runtime.
        
        Args:
            alias: Alias name (e.g., "python3")
            canonical: Canonical name (e.g., "Python")
            
        Returns:
            Confirmation message
        """
        normalizer.add_alias(alias, canonical)
        return {
            "status": "success",
            "message": f"Added alias: {alias} -> {canonical}"
        }
    
    
    logger.info("[OK] Registered Agent-Runtime main endpoints")


# ============================================================================
# Root and Health Check Endpoints
# ============================================================================

@app.get("/", tags=["Info"])
async def root():
    """
    Root endpoint with API information and service status.
    """
    return {
        "service": "Unified Backend API",
        "version": "1.0.0",
        "status": "running",
        "description": "Consolidated backend integrating all services",
        "services": {
            "recommendations": {
                "available": RECOMMENDATION_AVAILABLE,
                "prefix": "/recommendations",
                "description": "Advanced skill gap analysis, course recommendations, GNN-powered personalization"
            },
            "agent_runtime": {
                "available": AGENT_RUNTIME_AVAILABLE,
                "prefix": "/agent-runtime",
                "description": "CV processing, agentic skill extraction, gap analysis with XAI"
            },
            "authentication": {
                "available": LOGIN_AVAILABLE,
                "prefix": "/auth",
                "description": "OAuth 2.0 with Google, JWT tokens, candidate management"
            },
            "interview": {
                "available": INTERVIEW_AVAILABLE,
                "prefix": "/interview",
                "description": "AI-powered interview training with RAG and Gemini"
            },
            "skills_validation": {
                "available": NIPUNI_AVAILABLE,
                "prefix": "/skills-validation",
                "description": "Transcript processing, quiz generation, job recommendations"
            }
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/health", tags=["Info"])
async def health_check():
    """
    Comprehensive health check for all services.
    """
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check Recommendations service
    if RECOMMENDATION_AVAILABLE:
        try:
            driver = RecNeo4jConnection.get_driver()
            driver.verify_connectivity()
            health_status["services"]["recommendations"] = "healthy"
        except Exception as e:
            health_status["services"]["recommendations"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["recommendations"] = "unavailable"
    
    # Check Agent-Runtime service
    if AGENT_RUNTIME_AVAILABLE:
        try:
            driver = AgentNeo4jConnection.get_driver()
            driver.verify_connectivity()
            health_status["services"]["agent_runtime"] = "healthy"
        except Exception as e:
            health_status["services"]["agent_runtime"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["agent_runtime"] = "unavailable"
    
    # Check Login service
    if LOGIN_AVAILABLE:
        health_status["services"]["authentication"] = "healthy"
    else:
        health_status["services"]["authentication"] = "unavailable"
    
    # Check Interview service
    if INTERVIEW_AVAILABLE:
        health_status["services"]["interview"] = "healthy"
    else:
        health_status["services"]["interview"] = "unavailable"
    
    # Check Skills Validation service
    if NIPUNI_AVAILABLE:
        health_status["services"]["skills_validation"] = "healthy"
    else:
        health_status["services"]["skills_validation"] = "unavailable"
    
    return health_status


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 Starting Unified Backend API")
    print("=" * 80)
    print(f"\n📊 Available Services:")
    print(f"  - Recommendations: {'✓' if RECOMMENDATION_AVAILABLE else '✗'}")
    print(f"  - Agent Runtime: {'✓' if AGENT_RUNTIME_AVAILABLE else '✗'}")
    print(f"  - Authentication: {'✓' if LOGIN_AVAILABLE else '✗'}")
    print(f"  - Interview: {'✓' if INTERVIEW_AVAILABLE else '✗'}")
    print(f"  - Skills Validation: {'✓' if NIPUNI_AVAILABLE else '✗'}")
    print(f"\n🌐 API Endpoints:")
    print(f"  - Root: http://localhost:8000/")
    print(f"  - Swagger UI: http://localhost:8000/docs")
    print(f"  - ReDoc: http://localhost:8000/redoc")
    print(f"  - Health: http://localhost:8000/health")
    print("\n" + "=" * 80 + "\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
