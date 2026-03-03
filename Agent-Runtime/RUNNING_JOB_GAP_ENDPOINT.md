# Running the Job Gap Analysis Endpoint

## Overview
The Job Gap Analysis endpoint allows you to upload a Job Description (image/PDF) and analyze the skill gap between a candidate and that specific job posting.

## Prerequisites

### 1. Backend Services Running
You need THREE services running simultaneously:

#### A. Neo4j Database
```powershell
# Make sure Neo4j is running on bolt://localhost:7687
# Check with Neo4j Desktop or:
neo4j status
```

#### B. Advanced Recommendation System API (Port 8001)
```powershell
# Terminal 1
cd "F:\CV Parser Agent\Advanced-Recommendation-System"
& "F:\CV Parser Agent\.venv\Scripts\Activate.ps1"
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

#### C. Agent Runtime API (Port 8002)
```powershell
# Terminal 2
cd "F:\CV Parser Agent\Agent-Runtime"
& "F:\CV Parser Agent\.venv\Scripts\Activate.ps1"
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### 2. Environment Configuration

Create/update your `.env` file in `Agent-Runtime` folder:

```env
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# Recommendation API
RECOMMENDATION_API_BASE_URL=http://localhost:8001

# OCR Service (HuggingFace Chandra)
CHANDRA_ENDPOINT=https://api-inference.huggingface.co/models/yifeihu/chandra-ocr
HF_TOKEN=your_huggingface_token_here

# LLM Normalization Provider - OPTION 1: HuggingFace (RECOMMENDED)
NORMALIZER_PROVIDER=huggingface
NORMALIZER_MODEL=Qwen/Qwen2.5-3B-Instruct

# LLM Normalization Provider - OPTION 2: Local Ollama (ALTERNATIVE)
# NORMALIZER_PROVIDER=ollama
# NORMALIZER_MODEL=qwen2.5:3b-instruct
# OLLAMA_BASE_URL=http://localhost:11434
```

**Important:** 
- If using `NORMALIZER_PROVIDER=huggingface`, you MUST have `HF_TOKEN` set (same token used for OCR)
- If using `NORMALIZER_PROVIDER=ollama`, you need Ollama installed and running locally

### 3. Get Your HuggingFace Token

1. Go to https://huggingface.co/ and login
2. Click profile → Settings → Access Tokens
3. Create a new token with "Read" permissions
4. Copy the token (starts with `hf_...`)
5. Add to `.env` file as `HF_TOKEN=hf_your_token_here`

## Starting the Services

### Option 1: Using HuggingFace (Recommended - No Ollama Install Needed)

```powershell
# 1. Set environment variables
cd "F:\CV Parser Agent\Agent-Runtime"
$env:HF_TOKEN = "hf_your_token_here"
$env:NORMALIZER_PROVIDER = "huggingface"
$env:NORMALIZER_MODEL = "Qwen/Qwen2.5-3B-Instruct"

# 2. Activate virtual environment
& "F:\CV Parser Agent\.venv\Scripts\Activate.ps1"

# 3. Start the server
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### Option 2: Using Local Ollama

```powershell
# Terminal 1: Start Ollama (keep running)
ollama serve

# Terminal 2: Start Agent Runtime
cd "F:\CV Parser Agent\Agent-Runtime"
$env:NORMALIZER_PROVIDER = "ollama"
$env:NORMALIZER_MODEL = "qwen2.5:3b-instruct"
& "F:\CV Parser Agent\.venv\Scripts\Activate.ps1"
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

## Testing the Endpoint

### Method 1: Using cURL (PowerShell)

```powershell
# Prepare a test Job Description image
$testImage = "C:\path\to\job_description.png"

# Call the endpoint
curl.exe -X POST "http://localhost:8002/job-gap/analyze" `
  -F "candidate_id=emp_12345" `
  -F "file=@$testImage" `
  -F "job_title=Senior Python Developer" `
  -F "company_name=TechCorp" `
  -F "store_job=true" `
  -F "top_k=25"
```

### Method 2: Using Python Requests

```python
import requests

url = "http://localhost:8002/job-gap/analyze"

# Prepare the form data
files = {
    'file': open('job_description.png', 'rb')
}

data = {
    'candidate_id': 'emp_12345',
    'job_title': 'Senior Python Developer',
    'company_name': 'TechCorp',
    'store_job': 'true',
    'top_k': '25'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

### Method 3: Using the Frontend (Port 3000)

```powershell
# Terminal 3: Start Frontend
cd "F:\CV Parser Agent\frontend"
npm run dev
```

Then open http://localhost:3000 in your browser:
1. Enter candidate ID (e.g., `emp_12345`)
2. Click "Analyze by Job Image" tab
3. Upload a Job Description file (PNG, JPG, or PDF)
4. Click "Run Job Gap Analysis"

## API Response Example

```json
{
  "job_id": "job_abc123",
  "job_title": "Senior Python Developer",
  "company": "TechCorp",
  "candidate_id": "emp_12345",
  "readiness_score": 0.72,
  "skill_gap_index": 0.28,
  "skills_matched": 7,
  "skills_missing": 3,
  "matched_skills": ["Python", "FastAPI", "PostgreSQL", "Git"],
  "skill_gaps": [
    {
      "skill_name": "Kubernetes",
      "required_level": "expert",
      "current_level": "beginner",
      "gap_severity": "high",
      "importance": "required"
    },
    {
      "skill_name": "AWS",
      "required_level": "intermediate",
      "current_level": "none",
      "gap_severity": "medium",
      "importance": "required"
    }
  ],
  "explanation": "You meet 7 of 10 required skills for this Senior Python Developer role. The main gaps are in Kubernetes (high priority) and AWS (medium priority). Your strong foundation in Python, FastAPI, and PostgreSQL aligns well with the core requirements. Consider taking a Kubernetes certification course to strengthen your DevOps capabilities.",
  "job_posting": {
    "required_skills": ["Python", "FastAPI", "PostgreSQL", "Kubernetes", "Docker", "AWS"],
    "optional_skills": ["Redis", "GraphQL", "React"],
    "raw_text_preview": "We are looking for a Senior Python Developer..."
  }
}
```

## Pipeline Execution Flow

When you call the endpoint, here's what happens:

```
1. OCR Extraction (Chandra HuggingFace)
   ├── Upload: job_description.png
   ├── Extract: Raw text from image
   └── Clean: Remove legal/EEO sections

2. Skill Extraction (Rule-based)
   ├── Parse: Job requirements section
   ├── Identify: Required vs Optional skills
   └── Output: ["Python", "Kubernetes", "AWS", ...]

3. Skill Normalization (HuggingFace LLM)
   ├── Query Neo4j: Top-5 canonical skill candidates
   ├── LLM Selection: Best match for each raw skill
   └── Output: Canonical skill names with confidence

4. Job Profile Building
   ├── Assign importance weights
   └── Build: job_skill_profile {}

5. Knowledge Graph Write (Optional)
   ├── Create: JobPosting node
   └── Create: REQUIRES_SKILL edges

6. Gap Analysis
   ├── Fetch: Candidate skills from Neo4j
   ├── Compare: Candidate vs Job requirements
   └── Compute: readiness_score, skill_gap_index

7. Explanation Generation (HuggingFace LLM)
   ├── Prompt: Missing skills + matched skills
   └── Generate: Plain English summary
```

## Troubleshooting

### Error: "HF_TOKEN environment variable is required"
- **Solution:** Set your HuggingFace token in `.env` file or as environment variable

### Error: "Unsupported provider: ollama"
- **Solution:** Change `NORMALIZER_PROVIDER=huggingface` in your `.env` file

### Error: "Failed to connect to Ollama"
- **Solution 1:** Switch to HuggingFace provider (recommended)
- **Solution 2:** Make sure `ollama serve` is running if you want to use Ollama

### Error: "Candidate not found in KG"
- **Solution:** The candidate ID must exist in your Neo4j database
- **Alternative:** Use the role-based endpoint instead which accepts CV JSON

### Slow Response Times
- **HuggingFace:** First request may take 20-30 seconds (model loading). Subsequent requests are faster.
- **Ollama:** Consistently fast but requires local model download (~4.5 GB)

## Performance Comparison

| Provider | Setup Time | First Request | Subsequent Requests | Disk Space | Internet Required |
|----------|------------|---------------|---------------------|------------|-------------------|
| **HuggingFace** | 2 min | 20-30 sec | 5-10 sec | 0 MB | Yes (API calls) |
| **Ollama** | 10 min | 2-3 sec | 2-3 sec | 4500 MB | No (runs locally) |

**Recommendation:** Use HuggingFace for development/testing. Use Ollama for production if you need fast response times and offline capability.

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8002/docs
- **ReDoc:** http://localhost:8002/redoc

These provide interactive API documentation with "Try it out" functionality.

## Next Steps

1. ✅ Set `NORMALIZER_PROVIDER=huggingface` in `.env`
2. ✅ Set your `HF_TOKEN` in `.env`
3. ✅ Start both backend services (ports 8001 and 8002)
4. ✅ Test the endpoint with a sample Job Description image
5. ✅ View results in the frontend or via API response

---

**Need Help?** Check the logs in the terminal where `uvicorn` is running for detailed error messages.
