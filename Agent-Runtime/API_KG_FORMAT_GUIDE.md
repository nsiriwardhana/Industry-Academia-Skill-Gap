# Updated Agent-Runtime API - KG Format

## Overview

The Agent-Runtime API now accepts CV data in the **exact same format as the Knowledge Graph** uses. No more format conversion needed!

## Key Changes

### 1. Data Format Matches KG Exactly

**Person Node Properties → API Request:**
```python
# What Graph-Builder creates = What API accepts
{
    "candidate_id": "CAND_ABC12345",          # REQUIRED
    "candidate_name": "John Doe",              # REQUIRED (not "name")
    "mobile_number": "+1 555 123-4567",        # Optional (not "mobile")
    "email": "john@example.com",               # Optional
    "current_role": "Software Engineer",       # Optional
    "target_role": "Senior Data Scientist",    # Optional (info only)
    "current_employment": "Tech Corp",         # Optional
    "experience_months": 48,                   # Optional
    "experience_level": "Mid-Level",           # Optional
    "all_skills": ["Python", "TensorFlow"],    # PRIMARY skill source
    "num_skills": 2,                           # Auto-calculated
    "projects_and_technologies_involved": [...], # SECONDARY skill source
    "certificates_or_qualifications": [...],   # List of strings
    "education": {...},                        # Single object
    "evaluation_score": 85.5,                  # Optional
    "skill_score": 78.0                        # Optional
}
```

### 2. Target Role Comes from Query Parameter

**Important:** The `target_role` field in CV data is informational only. The actual role for gap analysis comes from the `role_key` query parameter:

```
POST /agent/run?role_key=ai_ml_engineer&top_k=25
```

This creates the `(Person)-[:TARGETS_ROLE]->(Role {role_key: "ai_ml_engineer"})` relationship.

### 3. Skill Sources

The pipeline extracts skills from TWO sources:

1. **`all_skills`** (primary): Flat list of skill names
2. **`projects_and_technologies_involved[].technologies_used`** (secondary): Skills used in projects

Both are normalized and deduplicated.

## API Endpoint

### POST /agent/run

**Query Parameters:**
- `role_key` (required): Target role key for gap analysis (e.g., "ai_ml_engineer")
- `top_k` (optional, default=25): Number of top deficits to return

**Request Body:** ExtractedData (see format above)

**Response:**
```json
{
  "candidate_id": "CAND_ABC12345",
  "status": "success",
  "normalized_skills_count": 15,
  "nodes_created": 25,
  "relationships_created": 40,
  "top_skills": [
    {
      "skill_name": "Python",
      "confidence_score": 0.95,
      "evidence_sources": ["HAS_SKILL", "USES_TECHNOLOGY"]
    }
  ],
  "top_deficits": [
    {
      "skill_name": "Kubernetes",
      "demand": 120,
      "deficit_score": 0.85
    }
  ],
  "readiness_score": 0.72,
  "role_key": "ai_ml_engineer",
  "processing_time_ms": 1250.5
}
```

## Pipeline Flow

```
1. EXTRACTOR
   - Validates schema
   - Checks candidate_id, candidate_name (NOT "name")
   - Returns validated data

2. NORMALIZER
   - Collects skills from all_skills
   - Collects skills from projects[].technologies_used
   - Normalizes with 64 skill aliases (Python3 → Python)
   - Updates all_skills with canonical names
   - Updates num_skills count

3. KG WRITER (Neo4j)
   - MERGE Person node by candidate_id
   - Set all Person properties
   - MERGE Skills, CREATE (Person)-[:HAS_SKILL]->(Skill)
   - CREATE Projects, (Person)-[:WORKED_ON]->(Project)
   - CREATE (Project)-[:USES_TECHNOLOGY]->(Skill)
   - CREATE Certifications, (Person)-[:HAS_CERTIFICATION]->(Certification)
   - CREATE Education, (Person)-[:HAS_EDUCATION]->(Education)
   - CREATE (Education)-[:FROM_INSTITUTION]->(Institution)
   - CREATE (Person)-[:TARGETS_ROLE]->(Role {role_key})

4. GAP ANALYZER
   - Call GET /candidates/{candidate_id}/skill-confidence
   - Call GET /candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced?top_k=...
   - Combine results into response
```

## Cypher Queries Generated

### Person Node
```cypher
MERGE (p:Person {candidate_id: $candidate_id})
SET p.candidate_name = $candidate_name,
    p.email = $email,
    p.mobile_number = $mobile_number,
    p.current_role = $current_role,
    p.target_role = $target_role,
    p.experience_months = $experience_months,
    p.num_skills = $num_skills
```

### Skills
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
MERGE (s:Skill {name: $skill_name})
MERGE (p)-[:HAS_SKILL]->(s)
```

### Projects
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
CREATE (pr:Project {
    project_name: $project_name,
    project_description: $project_description
})
MERGE (p)-[:WORKED_ON]->(pr)

// For each technology
MERGE (s:Skill {name: $tech})
MERGE (pr)-[:USES_TECHNOLOGY]->(s)
```

### Certifications
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
CREATE (c:Certification {
    name: $cert_name,
    issuer: $cert_issuer
})
MERGE (p)-[:HAS_CERTIFICATION]->(c)
```

### Education
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
MERGE (inst:Institution {name: $university})
CREATE (edu:Education {degree: $degree})
MERGE (p)-[:HAS_EDUCATION]->(edu)
MERGE (edu)-[:FROM_INSTITUTION]->(inst)
```

### Target Role
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
MERGE (r:Role {role_key: $role_key})
MERGE (p)-[:TARGETS_ROLE]->(r)
```

## Example Usage

### Python
```python
import requests

cv_data = {
    "candidate_id": "CAND_TEST_001",
    "candidate_name": "Alice Johnson",
    "mobile_number": "+1 555 987-6543",
    "email": "alice@example.com",
    "current_role": "ML Engineer",
    "experience_months": 36,
    "experience_level": "Mid-Level",
    "all_skills": ["Python", "TensorFlow", "Docker", "AWS"],
    "projects_and_technologies_involved": [
        {
            "project_name": "Image Classification System",
            "project_description": "CNN-based classifier",
            "technologies_used": ["Python", "TensorFlow", "OpenCV"],
            "complexity": "High"
        }
    ],
    "certificates_or_qualifications": [
        "TensorFlow Developer: Google",
        "AWS ML Specialty: Amazon"
    ],
    "education": {
        "degree": "MSc Computer Science",
        "university": "Stanford University"
    }
}

response = requests.post(
    "http://localhost:8002/agent/run",
    params={"role_key": "ai_ml_engineer", "top_k": 20},
    json=cv_data
)

print(response.json())
```

### PowerShell (curl)
```powershell
$cv = Get-Content "candidate_data.json" -Raw

Invoke-RestMethod `
    -Uri "http://localhost:8002/agent/run?role_key=ai_ml_engineer&top_k=20" `
    -Method POST `
    -Body $cv `
    -ContentType "application/json"
```

## Data Validation

### Required Fields
- ✅ `candidate_id`
- ✅ `candidate_name` (NOT "name")

### Optional Fields
All other fields are optional but recommended:
- `mobile_number` (NOT "mobile")
- `email`
- `all_skills` (empty list OK)
- `projects_and_technologies_involved` (empty list OK)

### Field Name Changes
| Old Name | New Name | Reason |
|----------|----------|--------|
| `name` | `candidate_name` | Match KG property |
| `mobile` | `mobile_number` | Match KG property |
| `skills` (array of objects) | `all_skills` (flat array) | Match KG structure |
| `projects` | `projects_and_technologies_involved` | Match KG property |
| `certifications` (object array) | `certificates_or_qualifications` (string array) | Match KG structure |

## Migration Guide

If you have data in the OLD format, here's how to convert:

```python
def convert_to_kg_format(old_data):
    """Convert old format to KG format."""
    return {
        "candidate_id": old_data["candidate_id"],
        "candidate_name": old_data["name"],  # name → candidate_name
        "mobile_number": old_data.get("mobile"),  # mobile → mobile_number
        "email": old_data.get("email"),
        "current_role": old_data.get("current_role"),
        "target_role": old_data.get("target_role"),
        "experience_months": old_data.get("experience_months"),
        "experience_level": old_data.get("experience_level"),
        
        # Flatten skills from categorized to flat list
        "all_skills": flatten_skills(old_data.get("skills", [])),
        
        # Projects unchanged
        "projects_and_technologies_involved": old_data.get("projects", []),
        
        # Certifications: convert objects to strings
        "certificates_or_qualifications": [
            f"{c['name']}: {c['issuer']}" 
            for c in old_data.get("certifications", [])
        ],
        
        # Education: take first if array
        "education": old_data["education"][0] if isinstance(old_data.get("education"), list) else old_data.get("education")
    }

def flatten_skills(skills_categorized):
    """Flatten categorized skills to list."""
    if not skills_categorized:
        return []
    
    all_skills = []
    for category in skills_categorized:
        all_skills.extend(category.get("programming_languages", []))
        all_skills.extend(category.get("frameworks", []))
        all_skills.extend(category.get("technologies", []))
        all_skills.extend(category.get("technical_skills", []))
        all_skills.extend(category.get("database", []))
        all_skills.extend(category.get("soft_skills", []))
    
    return list(set(all_skills))  # Deduplicate
```

## Available Role Keys

Use these values for `role_key` parameter:

- `ai_ml_engineer`
- `data_scientist`
- `data_engineer`
- `full_stack_developer`
- `devops_engineer`
- `cloud_architect`

(Check your Role nodes in Neo4j for complete list)

## Troubleshooting

### 400 Error: "candidate_name is required"
You're using `"name"` instead of `"candidate_name"`. Update your JSON.

### 400 Error: "candidate_id is required"
Missing required field. Every CV must have a unique candidate_id.

### 404 Error: "Role 'xyz' not found"
The role_key doesn't exist in your KG. Check available roles with:
```cypher
MATCH (r:Role) RETURN r.role_key, r.name
```

### 500 Error: "Pipeline execution failed"
Check logs for details. Common causes:
- Neo4j connection failed
- Gap Analyzer API unavailable
- Invalid data in fields

## Testing

Test with minimal valid data:
```json
{
  "candidate_id": "CAND_TEST_001",
  "candidate_name": "Test User",
  "all_skills": ["Python"]
}
```

Query:
```
POST /agent/run?role_key=ai_ml_engineer
```

This should create Person + Skill nodes and return gap analysis.

## Summary

✅ **Accepts same format as KG uses**
✅ **Target role from query parameter**
✅ **Skills from all_skills + projects**
✅ **Creates complete candidate graph**
✅ **Returns combined gap analysis**

No more format conversion needed between your CV data and the API!
