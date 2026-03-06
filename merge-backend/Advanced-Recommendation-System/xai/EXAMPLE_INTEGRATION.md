# XAI Module Integration Example

## File: main.py

Add XAI service initialization to your existing startup routine:

```python
"""
Advanced Skill Gap & Course Recommendation API
==============================================

Main application entry point with FastAPI.

Architecture:
- config/: Configuration and constants
- models/: Pydantic schemas for validation
- database/: Neo4j connection management
- services/: Business logic (confidence, importance, deficit, recommendation, GNN)
- routes/: FastAPI route handlers
- utils/: Cache and helper utilities
- xai/: Explainable AI module (NEW)
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import API_TITLE, API_VERSION, API_DESCRIPTION, LOG_LEVEL, LOG_FORMAT
from database import Neo4jConnection
from routes import router
from services.gnn_inference_service import gnn_service

# NEW: Import XAI module
from xai.api import router as xai_router, initialize_xai_service

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    
    Startup:
        - Initialize Neo4j connection
        - Load GNN model and graph data
        - Initialize XAI service (NEW)
    
    Shutdown:
        - Close Neo4j connection
    """
    # Startup
    logger.info("Starting Advanced Recommendation API with GNN support...")
    try:
        # Initialize Neo4j connection
        Neo4jConnection.get_driver()
        logger.info("[OK] Neo4j connection initialized")
        
        # Load GNN model
        logger.info("Loading GNN model for link prediction...")
        base_path = Path(__file__).parent.parent / "GNN-Link-Prediction"
        model_path = str(base_path / "models" / "best_gnn_linkpred.pt")
        data_path = str(base_path / "output" / "heterodata_lp.pt")
        id_maps_path = str(base_path / "output" / "id_maps.json")
        
        gnn_service.load_model(model_path, data_path, id_maps_path)
        logger.info("[OK] GNN model loaded successfully")
        logger.info(f"  - Stats: {gnn_service.get_stats()}")
        
        # NEW: Initialize XAI service
        logger.info("Initializing XAI service...")
        try:
            initialize_xai_service()
            logger.info("[OK] XAI service initialized")
        except Exception as xai_error:
            logger.warning(f"[SKIP] XAI service initialization failed: {xai_error}")
            logger.warning("XAI endpoints will not be available")
            logger.warning("To enable XAI:")
            logger.warning("  1. python -m xai.scripts.build_xai_dataset")
            logger.warning("  2. python -m xai.scripts.train_xai_surrogate")
        
        logger.info("[OK] Application startup complete")
    except Exception as e:
        logger.error(f"[FAIL] Startup failed: {e}", exc_info=True)
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    Neo4jConnection.close()
    logger.info("[OK] Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION + "\n\n## XAI Support\n\nExplainable AI endpoints for skill recommendations.",
    lifespan=lifespan,
)

# Configure CORS - Allow frontend to access API
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

# Include routes
app.include_router(router)
app.include_router(xai_router)  # NEW: Register XAI routes


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
```

## Changes Summary

### Additions:
1. **Import XAI module** (line 20-21):
   ```python
   from xai.api import router as xai_router, initialize_xai_service
   ```

2. **Initialize XAI in lifespan** (lines 63-72):
   ```python
   logger.info("Initializing XAI service...")
   try:
       initialize_xai_service()
       logger.info("[OK] XAI service initialized")
   except Exception as xai_error:
       logger.warning(f"[SKIP] XAI service initialization failed: {xai_error}")
       logger.warning("XAI endpoints will not be available")
       logger.warning("To enable XAI:")
       logger.warning("  1. python -m xai.scripts.build_xai_dataset")
       logger.warning("  2. python -m xai.scripts.train_xai_surrogate")
   ```

3. **Register XAI router** (line 112):
   ```python
   app.include_router(xai_router)
   ```

### Behavior:
- If XAI model not found → Warning logged, but app continues (XAI endpoints return 503)
- If XAI model found → Service initialized, endpoints available
- Non-blocking: Main app works even if XAI fails

## Testing After Integration

### 1. Start server
```bash
python main.py
```

### 2. Check XAI health
```bash
curl http://localhost:8001/explain/health
```

Expected response (if XAI initialized):
```json
{
  "service": "XAI",
  "status": "available",
  "model_loaded": true,
  "dataset_loaded": true,
  "dataset_size": 25000
}
```

### 3. Get explanation
```bash
curl "http://localhost:8001/explain/missing-skill?candidate_id=person_0&role_key=role_0&skill=Python"
```

Expected response:
```json
{
  "candidate_id": "person_0",
  "role_key": "role_0",
  "skill": "Python",
  "final_score": 0.7823,
  "top_factors": [...],
  "explanation_text": "..."
}
```

## API Documentation

After integration, visit:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

You'll see new XAI endpoints:
- `GET /explain/missing-skill` - Get skill explanation
- `GET /explain/health` - Check XAI service health
