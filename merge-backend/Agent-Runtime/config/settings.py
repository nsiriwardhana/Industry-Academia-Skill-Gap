"""
Configuration settings for Agent Runtime Backend.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "tharusha@2001")

# Existing Recommendation API
RECOMMENDATION_API_BASE_URL = os.getenv(
    "RECOMMENDATION_API_BASE_URL",
    "http://localhost:8001"
)

# Skill Gap Ranking Method
# Options: 'symbolic', 'hybrid', 'additive_gnn'
# - symbolic: Traditional TF-IDF based (fast, interpretable)
# - hybrid: GNN learnability × importance × gap (personalized, ML-powered)
# - additive_gnn: Weighted sum formula (experimental)
SKILL_GAP_RANKING_METHOD = os.getenv("SKILL_GAP_RANKING_METHOD", "hybrid")

# ============================================================================
# JOB GAP ANALYSIS CONFIGURATION
# ============================================================================

# Chandra OCR (HuggingFace)
CHANDRA_ENDPOINT = os.getenv(
    "CHANDRA_ENDPOINT",
    "https://api-inference.huggingface.co/models/yifeihu/chandra-ocr"
)
HF_TOKEN = os.getenv("HF_TOKEN", "")

# CV Parser LLM Configuration (for PDF upload)
# Open Router - Free LLM access (Llama 3.1, Gemini, etc.)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
# Google Gemini - Fallback option
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Ollama LLM for normalization and explanation
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
NORMALIZER_PROVIDER = os.getenv("NORMALIZER_PROVIDER", "ollama")
NORMALIZER_MODEL = os.getenv("NORMALIZER_MODEL", "qwen2.5:3b-instruct")

# ============================================================================

# CORS Configuration
CORS_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://localhost:3001",
    "http://localhost:5173",  # Vite dev server
    "http://localhost:5174",
    "http://localhost:8080",  # Vite dev server (alternative port)
    "http://localhost:8081",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",
    "http://172.28.8.46:8080",  # Network IP
    "http://172.28.8.46:8081",
    "http://172.28.8.46:5173",
    "http://172.28.8.46:5174",
]

# API Configuration
API_TITLE = "Agent Runtime Backend"
API_VERSION = "1.1.0"
API_DESCRIPTION = """
Agentic Runtime for CV Processing and Skill Gap Analysis

## Architecture

**Extractor Agent** → **Normalizer Agent** → **KG Writer Tool** → **Gap Analyzer Tool**

## NEW: Job Description Gap Analysis

Upload a JD image/PDF and get skill gap analysis for any candidate.

**Pipeline:**
1. **OCR** (Chandra/HuggingFace): Extract text from image/PDF
2. **Skill Extraction**: Identify required/optional skills
3. **Normalization** (Ollama LLM): Map to canonical skill names
4. **Profile Building**: Assign importance scores
5. **Gap Analysis**: Compute readiness with graded matching
6. **Explanation** (Ollama LLM): Generate plain English summary

### Endpoints

- `POST /job-gap/analyze` - Upload JD and analyze gap
- `GET /job-gap/{job_id}` - Get stored job posting
- `POST /agent/run` - Full CV processing pipeline
- `GET /health` - Health check
"""

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
