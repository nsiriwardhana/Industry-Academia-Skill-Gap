# Agent Runtime - Quick Start Guide

Get up and running in 5 minutes!

---

## Prerequisites

✅ Python 3.12+  
✅ Neo4j 5.14.0+ running  
✅ Advanced-Recommendation-System running (port 8001)  

---

## Installation

```powershell
# 1. Navigate to folder
cd "F:\CV Parser Agent\Agent-Runtime"

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env with your Neo4j password
```

---

## Configuration

Edit `.env`:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_actual_password

RECOMMENDATION_API_BASE_URL=http://localhost:8001
```

---

## Start Server

```powershell
# Development mode (auto-reload on changes)
uvicorn main:app --reload --port 8002

# Or run directly
python main.py
```

**Server starts at:** http://localhost:8002  
**Swagger docs:** http://localhost:8002/docs  

---

## Test the API

### Option 1: Using the test script

```powershell
python test_agent_runtime.py
```

### Option 2: Using curl with sample data

```powershell
curl -X POST "http://localhost:8002/agent/run" `
  -H "Content-Type: application/json" `
  -d "@sample_request.json"
```

### Option 3: Using Swagger UI

1. Open http://localhost:8002/docs
2. Click on `POST /agent/run`
3. Click "Try it out"
4. Use the example JSON or paste from `sample_request.json`
5. Click "Execute"

---

## Expected Response

```json
{
  "candidate_id": "CAND_001",
  "role_key": "data-scientist",
  "status": "success",
  "message": "Pipeline completed successfully",
  "normalized_skills_count": 8,
  "nodes_created": 15,
  "relationships_created": 22,
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

---

## Verify in Neo4j

```cypher
// Check candidate was created
MATCH (p:Person {candidate_id: "CAND_001"})
RETURN p

// Check skills
MATCH (p:Person {candidate_id: "CAND_001"})-[:HAS_SKILL]->(s:Skill)
RETURN s.name, count(*) AS skill_count

// Check complete profile
MATCH (p:Person {candidate_id: "CAND_001"})
OPTIONAL MATCH (p)-[r]-()
RETURN p, count(r) AS total_relationships
```

---

## Common Issues

### Issue: Connection refused

```
ConnectionError: Cannot connect to http://localhost:8002
```

**Solution:** Start the server first:
```powershell
uvicorn main:app --reload --port 8002
```

---

### Issue: Neo4j connection failed

```
✗ Failed to connect to Neo4j
```

**Solution:** 
1. Check Neo4j is running
2. Verify credentials in `.env`
3. Test connection: `neo4j://localhost:7687`

---

### Issue: Recommendation API unavailable

```
recommendation_api_available: false
```

**Solution:** Start the Advanced-Recommendation-System:
```powershell
cd "F:\CV Parser Agent\Advanced-Recommendation-System"
uvicorn main:app --reload --port 8001
```

---

### Issue: Module not found

```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:** Install dependencies:
```powershell
pip install -r requirements.txt
```

---

## Next Steps

1. ✅ Test with sample data
2. ✅ Verify data in Neo4j
3. ✅ Check gap analysis results
4. 🔧 Customize skill aliases in `agents/normalizer.py`
5. 🔧 Add your own test candidates
6. 🔧 Integrate with your frontend

---

## Architecture Recap

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Extractor  │ -> │ Normalizer  │ -> │  KG Writer  │ -> │Gap Analyzer │
│    Agent    │    │    Agent    │    │    Tool     │    │    Tool     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     ↓                  ↓                   ↓                   ↓
  Validate          Canonicalize       Write to Neo4j      Call API
   JSON             Skills (200+)      (UNWIND batch)     for Analysis
```

---

## Help & Documentation

- **Full README**: [README.md](README.md)
- **Cypher Queries**: [CYPHER_QUERIES.md](CYPHER_QUERIES.md)
- **Swagger Docs**: http://localhost:8002/docs
- **Sample Request**: [sample_request.json](sample_request.json)

---

## Production Checklist

Before deploying to production:

- [ ] Change `.env` passwords from defaults
- [ ] Set `LOG_LEVEL=WARNING` in production
- [ ] Configure proper CORS origins
- [ ] Set up monitoring/logging
- [ ] Add rate limiting
- [ ] Implement authentication
- [ ] Add input validation limits
- [ ] Set up backup strategy for Neo4j
- [ ] Load test with realistic data volumes
- [ ] Document API for frontend team

---

**Ready to go!** 🚀

If you encounter any issues, check the logs or visit http://localhost:8002/docs
