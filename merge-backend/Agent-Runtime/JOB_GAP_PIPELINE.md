# Job Description Gap Analysis Pipeline

## Overview

This feature enables gap analysis between a candidate and a **specific job description** uploaded as an image or PDF, rather than generic role-based analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    JD Image/PDF Upload                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  1. OCR EXTRACTION (Chandra/HuggingFace)                            │
│     - Extract text from image/PDF                                    │
│     - Clean: remove EEO, benefits, company info                      │
│     - Keep: requirements, skills, responsibilities                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. SKILL EXTRACTION (Rule-based)                                    │
│     - Identify required vs optional sections                         │
│     - Extract bullet points and list items                           │
│     - Match against known tech keywords + KG skills                  │
│     Output: raw_required_skills[], raw_optional_skills[]             │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. SKILL NORMALIZATION (Ollama LLM)                                 │
│     - Query Neo4j for top-5 canonical candidates                     │
│     - Send ONLY candidates to LLM for selection                      │
│     - Return: {canonical_skill, confidence}                          │
│     - Filter: confidence >= 0.6                                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. JOB SKILL PROFILE                                                │
│     - Required skills: base weight = 1.0                             │
│     - Optional skills: base weight = 0.4                             │
│     - Boost for emphasis keywords ("must", "strong", "expert")       │
│     - Normalize importance to [0, 1]                                 │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. OPTIONAL KG WRITE                                                │
│     - Create (:JobPosting {job_id, title, source, created_at})       │
│     - Create edges: (JobPosting)-[:REQUIRES_SKILL {importance}]->    │
│     - NO duplicate Skill nodes created                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  6. GAP ANALYSIS (Reuses existing logic)                             │
│     - Graded matching: exact (1.0), cluster (0.7), similar (0.4-0.6) │
│     - deficit = importance × (1 - match_strength)                    │
│     - skill_gap_index = Σdeficit / Σimportance                       │
│     - readiness = 1 - skill_gap_index                                │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  7. EXPLANATION (Ollama LLM)                                         │
│     - 4-6 sentence plain English explanation                         │
│     - No technical jargon                                            │
│     - Covers: overall fit, strengths, gaps, recommendation           │
└─────────────────────────────────────────────────────────────────────┘
```

## API Endpoint

### POST /job-gap/analyze

**Request (multipart/form-data):**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| candidate_id | string | Yes | Candidate identifier (must exist in KG) |
| jd_file | file | Yes | Job description image (PNG/JPG) or PDF |
| store_job | bool | No | Store JobPosting in KG (default: true) |
| top_k | int | No | Number of top skills to analyze (default: 25) |

**Response:**
```json
{
  "job_id": "uuid-string",
  "job_title": "Senior ML Engineer",
  "readiness": 0.72,
  "skill_gap_index": 0.28,
  "matched_skills": [
    {"skill": "Python", "importance": 0.95, "match_strength": 1.0, "deficit": 0.0},
    {"skill": "PyTorch", "importance": 0.88, "match_strength": 0.8, "deficit": 0.176}
  ],
  "missing_skills_ranked": [
    {"skill": "RAG", "importance": 0.82, "match_strength": 0.0, "deficit": 0.82},
    {"skill": "LangChain", "importance": 0.75, "match_strength": 0.0, "deficit": 0.75}
  ],
  "explanation_text": "This candidate shows strong alignment with the Senior ML Engineer role..."
}
```

## Example Usage

### cURL
```bash
curl -X POST "http://localhost:8002/job-gap/analyze" \
     -H "Content-Type: multipart/form-data" \
     -F "candidate_id=cand_001" \
     -F "jd_file=@job_description.png" \
     -F "store_job=true" \
     -F "top_k=25"
```

### Python
```python
import requests

url = "http://localhost:8002/job-gap/analyze"

with open("job_description.png", "rb") as f:
    response = requests.post(
        url,
        data={"candidate_id": "cand_001", "store_job": "true", "top_k": "25"},
        files={"jd_file": ("jd.png", f, "image/png")}
    )

result = response.json()
print(f"Readiness: {result['readiness']:.0%}")
print(f"Explanation: {result['explanation_text']}")
```

## Configuration

Add to `.env`:
```bash
# Chandra OCR (HuggingFace)
CHANDRA_ENDPOINT=https://api-inference.huggingface.co/models/yifeihu/chandra-ocr
HF_TOKEN=your_huggingface_token

# Ollama LLM
OLLAMA_BASE_URL=http://localhost:11434
NORMALIZER_PROVIDER=ollama
NORMALIZER_MODEL=qwen2.5:3b-instruct
```

## Prerequisites

1. **Ollama** running locally with the configured model:
   ```bash
   ollama pull qwen2.5:3b-instruct
   ollama serve
   ```

2. **HuggingFace Token** (optional, for Chandra OCR):
   - Get token from https://huggingface.co/settings/tokens
   - Set `HF_TOKEN` in `.env`

3. **PDF Support** (optional):
   ```bash
   pip install pdf2image PyPDF2
   # For pdf2image, you also need poppler:
   # Windows: https://github.com/oschwartz10612/poppler-windows/releases
   ```

## Files Added

```
Agent-Runtime/
├── services/
│   ├── chandra_ocr_service.py      # OCR extraction
│   ├── skill_extract_service.py    # Skill extraction from text
│   ├── skill_normalize_llm.py      # LLM-based normalization
│   └── job_gap_service.py          # End-to-end pipeline
├── routes/
│   └── job_gap_routes.py           # FastAPI router
└── JOB_GAP_PIPELINE.md             # This documentation
```

## Integration with Existing System

- **Does NOT modify** existing role-based gap analysis
- **Reuses** graded matching logic from `skill_matching.py`
- **Reuses** skill confidence queries
- **Extends** KG with optional `JobPosting` nodes

## Known Limitations

1. OCR quality depends on image clarity
2. LLM normalization requires local Ollama (or modify for cloud LLM)
3. First request may be slow (model loading)
4. PDF support requires additional dependencies
