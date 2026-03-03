# Quick Start: Job Gap Analysis with HuggingFace

## ✅ You're Using HuggingFace (No Ollama Required!)

Since you've configured `NORMALIZER_PROVIDER=huggingface`, you **don't need to install Ollama**.

## Step-by-Step Setup

### 1. Configure Environment Variables

Edit `Agent-Runtime\.env`:

```env
# HuggingFace Token (REQUIRED - get from https://huggingface.co/settings/tokens)
HF_TOKEN=hf_your_token_here

# LLM Provider Configuration
NORMALIZER_PROVIDER=huggingface
NORMALIZER_MODEL=Qwen/Qwen2.5-3B-Instruct

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Recommendation API
RECOMMENDATION_API_BASE_URL=http://localhost:8001
```

### 2. Start the Services

**Terminal 1: Advanced Recommendation System (Port 8001)**
```powershell
cd "F:\CV Parser Agent\Advanced-Recommendation-System"
& "F:\CV Parser Agent\.venv\Scripts\Activate.ps1"
uvicorn main:app --port 8001 --reload
```

**Terminal 2: Agent Runtime (Port 8002)**
```powershell
cd "F:\CV Parser Agent\Agent-Runtime"
& "F:\CV Parser Agent\.venv\Scripts\Activate.ps1"
uvicorn main:app --port 8002 --reload
```

**Terminal 3: Frontend (Port 3000)**
```powershell
cd "F:\CV Parser Agent\frontend"
npm run dev
```

### 3. Test the Endpoint

**Option A: Via Frontend**
1. Open http://localhost:3000
2. Enter candidate ID: `emp_12345`
3. Click "Analyze by Job Image" tab
4. Upload a Job Description (PNG/JPG/PDF)
5. Click "Run Job Gap Analysis"

**Option B: Via cURL**
```powershell
curl.exe -X POST "http://localhost:8002/job-gap/analyze" `
  -F "candidate_id=emp_12345" `
  -F "file=@C:\path\to\job_description.png" `
  -F "job_title=Senior Developer" `
  -F "company_name=TechCorp"
```

**Option C: Via Swagger UI**
1. Go to http://localhost:8002/docs
2. Find "POST /job-gap/analyze"
3. Click "Try it out"
4. Fill in the form and upload a file
5. Click "Execute"

## What Happens Behind the Scenes

```
Job Description Image
       ↓
[1] Chandra OCR (HuggingFace) → Extract text
       ↓
[2] Skill Extraction (Rule-based) → Identify skills
       ↓
[3] Skill Normalization (HuggingFace Qwen 2.5) → Map to canonical skills
       ↓
[4] Gap Analysis (Neo4j + Advanced Recommendation API) → Compare with candidate
       ↓
[5] Explanation Generation (HuggingFace Qwen 2.5) → Plain English summary
       ↓
Result: Readiness score + Skill gaps + Recommendations
```

## Expected Response Time

- **First request:** 20-30 seconds (HuggingFace model loading)
- **Subsequent requests:** 5-10 seconds

## Troubleshooting

### "HF_TOKEN environment variable is required"
→ Add your HuggingFace token to `.env` file

### "Model yifeihu/chandra-ocr is currently loading"
→ Wait 20 seconds and retry (HuggingFace cold start)

### "Candidate not found"
→ Make sure the candidate ID exists in Neo4j

### Port already in use
→ Change ports in uvicorn commands: `--port 8003` etc.

## Files Modified for HuggingFace Support

- ✅ `services/skill_normalize_llm.py` - Added `_call_huggingface()` method
- ✅ `.env.example` - Updated with HuggingFace config
- ✅ Documentation - Added this guide

## Performance Comparison

| Feature | HuggingFace | Ollama |
|---------|-------------|--------|
| Setup Time | 2 minutes | 10 minutes |
| Internet Required | Yes | No |
| Disk Space | 0 MB | 4500 MB |
| First Request | 20-30 sec | 2-3 sec |
| Subsequent | 5-10 sec | 2-3 sec |
| Cost | Free (rate limited) | Free (unlimited) |

**Your Choice:** HuggingFace is perfect for development and testing!

---

**Ready to test?** Just start the three services above and open http://localhost:3000 🚀
