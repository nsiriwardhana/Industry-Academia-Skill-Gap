# Agent Runtime Backend

Agentic orchestration backend for CV processing and skill gap analysis.

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Extractor  │ -> │ Normalizer  │ -> │  KG Writer  │ -> │Gap Analyzer │
│    Agent    │    │    Agent    │    │    Tool     │    │    Tool     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Agents

1. **Extractor Agent**: Validates incoming JSON (stub for future CV parsing)
2. **Normalizer Agent**: Maps skills to canonical names with 200+ aliases
3. **KG Writer Tool**: Creates/updates candidate graph in Neo4j with UNWIND batching
4. **Gap Analyzer Tool**: Calls existing recommendation API for analysis

---

## Quick Start

### Prerequisites

- Python 3.12+
- Neo4j 5.14.0+ running at `bolt://localhost:7687`
- Advanced-Recommendation-System running at `http://localhost:8001` (for gap analysis)

### Installation

```powershell
# Navigate to Agent-Runtime folder
cd "F:\CV Parser Agent\Agent-Runtime"

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Neo4j credentials
```

### Configuration

Edit `.env`:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

RECOMMENDATION_API_BASE_URL=http://localhost:8001
```

### Run Server

```powershell
# Development mode (auto-reload)
uvicorn main:app --reload --port 8003

# Or using venv Python
& "F:/CV Parser Agent/.venv/Scripts/python.exe" -m uvicorn main:app --reload --port 8003

# Production mode
python main.py
```

**Endpoints:**
- API: http://localhost:8003
- Swagger docs: http://localhost:8003/docs
- Health check: http://localhost:8003/health
- Runtime XAI: http://localhost:8003/runtime/skill-explain
- SHAP XAI: http://localhost:8003/runtime/predict-explain

---

## API Usage

### POST /agent/run

Run complete pipeline: Extract → Normalize → Write → Analyze

**Request:**

```json
{
  "role_key": "data-scientist",
  "extracted_data": {
    "candidate_id": "CAND_001",
    "name": "John Doe",
    "email": "john@example.com",
    "experience_level": "mid",
    "total_experience_months": 36,
    "skills": [
      {"name": "Python", "proficiency": "expert"},
      {"name": "ML", "proficiency": "intermediate"},
      {"name": "TensorFlow", "proficiency": "intermediate"}
    ],
    "work_experiences": [
      {
        "company": "Tech Corp",
        "title": "Data Scientist",
        "duration_months": 24,
        "skills_used": ["Python", "TensorFlow", "SQL"]
      }
    ],
    "projects": [
      {
        "name": "Image Classifier",
        "description": "CNN for image classification",
        "technologies": ["Python", "PyTorch", "OpenCV"]
      }
    ],
    "certifications": [
      {
        "name": "AWS Certified Developer",
        "issuer": "Amazon",
        "year": 2023
      }
    ],
    "education": [
      {
        "institution_name": "MIT",
        "degree": "BS Computer Science",
        "field_of_study": "Computer Science",
        "graduation_year": 2020
      }
    ]
  },
  "top_k": 25
}
```

**Response:**

```json
{
  "candidate_id": "CAND_001",
  "role_key": "data-scientist",
  "status": "success",
  "message": "Pipeline completed successfully",
  "normalized_skills_count": 6,
  "nodes_created": 12,
  "relationships_created": 18,
  "skill_confidence_top": [
    {
      "skill_name": "Python",
      "confidence": 0.95,
      "evidence_count": 3,
      "evidence_sources": ["HAS_SKILL", "USED_SKILL", "USES_TECHNOLOGY"]
    }
  ],
  "skill_gap_top": [
    {
      "skill_name": "Deep Learning",
      "p_has": 0.6,
      "importance": 45.67,
      "deficit": 18.27,
      "tf": 28,
      "df": 4,
      "idf": 1.63
    }
  ],
  "readiness_score": 0.68
}
```

### GET /health

Check system health.

**Response:**

```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "recommendation_api_available": true
}
```

### GET /aliases

Get all skill aliases (200+ mappings).

### POST /aliases/add

Add custom alias at runtime:

```json
{
  "alias": "py3",
  "canonical": "Python"
}
```

---

## Project Structure

```
Agent-Runtime/
├── main.py                     # FastAPI application
├── config/
│   ├── __init__.py
│   └── settings.py            # Configuration
├── database/
│   ├── __init__.py
│   └── neo4j_connection.py    # Neo4j driver
├── agents/
│   ├── __init__.py
│   ├── extractor.py           # Extractor Agent (stub)
│   ├── normalizer.py          # Normalizer Agent (200+ aliases)
│   ├── kg_writer.py           # KG Writer Tool (UNWIND batching)
│   └── gap_analyzer.py        # Gap Analyzer Tool (API calls)
├── models/
│   ├── __init__.py
│   └── schemas.py             # Pydantic models
├── requirements.txt
├── .env.example
└── README.md
```

---

## Skill Normalization

The Normalizer Agent includes 200+ pre-configured aliases:

| Original | Canonical |
|----------|-----------|
| python3, py | Python |
| ml | Machine Learning |
| tf | TensorFlow |
| js | JavaScript |
| k8s | Kubernetes |
| aws | Amazon Web Services |

**Extend aliases:**

```python
# In agents/normalizer.py
SKILL_ALIASES = {
    "your_alias": "Canonical Name",
    ...
}
```

Or add at runtime via API:

```bash
curl -X POST "http://localhost:8002/aliases/add?alias=dl&canonical=Deep%20Learning"
```

---

## Neo4j Schema

### Nodes Created

- `Person`: Candidate profile
- `Skill`: Normalized skills
- `Company`: Employers
- `WorkExperience`: Work history
- `Project`: Projects
- `Certification`: Certifications
- `Education`: Education records

### Relationships

- `(Person)-[:HAS_SKILL {proficiency}]->(Skill)`
- `(Person)-[:WORKED_AT]->(WorkExperience)-[:FOR_COMPANY]->(Company)`
- `(WorkExperience)-[:USED_SKILL]->(Skill)`
- `(Person)-[:WORKED_ON]->(Project)-[:USES_TECHNOLOGY]->(Skill)`
- `(Person)-[:HAS_CERTIFICATION]->(Certification)`
- `(Person)-[:STUDIED_AT]->(Education)`

---

## Integration with Recommendation System

The Gap Analyzer Tool calls your existing recommendation API:

**Endpoints Used:**

1. `GET /candidates/{id}/skill-confidence` - Get skill confidence scores
2. `GET /candidates/{id}/roles/{role}/skill-gap-advanced` - Get skill deficits

**Configuration:**

Set `RECOMMENDATION_API_BASE_URL` in `.env`:

```env
RECOMMENDATION_API_BASE_URL=http://localhost:8001
```

---

## Future Enhancements

### Extractor Agent

Currently a validation stub. Future implementations:

- **PDF Parsing**: PyPDF2, pdfplumber
- **DOCX Parsing**: python-docx
- **LinkedIn Scraping**: LinkedIn API
- **NER Extraction**: spaCy, BERT-NER

### Normalizer Agent

- **Fuzzy Matching**: Use Levenshtein distance
- **Embedding Similarity**: Vector-based skill matching
- **Dynamic Learning**: Learn aliases from Neo4j SIMILAR_TO edges

### KG Writer Tool

- **Incremental Updates**: Only update changed data
- **Relationship Strengths**: Add confidence scores to edges
- **Temporal Tracking**: Track skill acquisition timeline

---

## Testing

```powershell
# Test with sample data
curl -X POST "http://localhost:8003/agent/run?role_key=data-scientist&top_k=25&include_xai=true" \
  -H "Content-Type: application/json" \
  -d @sample_request.json

# Check health
curl "http://localhost:8003/health"

# View aliases
curl "http://localhost:8003/aliases"

# Test XAI endpoints
curl "http://localhost:8003/runtime/skill-explain?candidate_id=CAND_001&role_key=ai_ml_engineer"
curl "http://localhost:8003/runtime/predict-explain?candidate_id=CAND_001&role_key=ai_ml_engineer"
```

---

## CORS Configuration

Enabled for React development servers:

- http://localhost:3000
- http://localhost:3001
- http://127.0.0.1:3000
- http://127.0.0.1:3001

Configure in `config/settings.py`:

```python
CORS_ORIGINS = [
    "http://localhost:3000",
    # Add your origins...
]
```

---

## Troubleshooting

### Neo4j Connection Failed

```
✗ Failed to connect to Neo4j: ...
```

**Solution**: Check Neo4j is running and credentials in `.env` are correct.

### Recommendation API Unavailable

```
recommendation_api_available: false
```

**Solution**: Start the Advanced-Recommendation-System on port 8001.

### Duplicate Nodes

**Solution**: KG Writer uses MERGE for Person/Skill and deletes old relationships before creating new ones.

### Slow Write Performance

**Solution**: Already optimized with UNWIND batching. For large datasets, consider transaction batching.

---

## License

Internal project - confidential.
