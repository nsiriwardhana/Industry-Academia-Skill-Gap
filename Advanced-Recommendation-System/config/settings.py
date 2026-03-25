"""
Configuration settings for Advanced Recommendation System.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env file
# Search up to root .env (3 levels up from settings.py: config/settings.py)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Evidence Weights - Tunable Parameters
EVIDENCE_WEIGHTS = {
    "HAS_SKILL": 0.70,           # Direct CV claim
    "USED_SKILL": 0.90,          # Work experience (strongest signal)
    "USES_TECHNOLOGY": 0.80,     # Project evidence
    "CERTIFICATION": 0.60,       # Certification keywords
}

# Cache Configuration
CACHE_TTL = 3600  # seconds (1 hour)

# API Configuration
API_TITLE = "Advanced Skill Gap & Course Recommendation API"
API_VERSION = "1.0.0"
API_DESCRIPTION = """
## Research-Grade Recommendation System

### Features
- **Evidence-Weighted Skill Confidence**: Multi-source evidence aggregation
- **TF-IDF Role Importance**: Skill importance scoring per role
- **Deficit-Driven Ranking**: Prioritized skill gaps
- **Course Recommendations**: Optimized for deficit reduction

### Evidence Formula
`P(has(skill)) = 1 - Π(1 - evidence_i)`

### TF-IDF Formula
`importance(role, skill) = TF × IDF`

Where:
- TF = count(jobs in role requiring skill)
- IDF = log(total_roles / df)
- df = count(roles where skill appears)

### Deficit Formula
`deficit(skill) = importance(role, skill) × (1 - P(has(skill)))`
"""

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
