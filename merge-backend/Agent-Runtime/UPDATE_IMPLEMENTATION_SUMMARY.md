# Agent-Runtime API Update Summary

## What Was Done

Updated the Agent-Runtime API to accept CV data in the **exact same format as your Knowledge Graph**, eliminating format conversion issues.

## Files Created

### 1. `/models/schemas_new.py`
- **New Pydantic models matching KG structure exactly**
- `ExtractedData`: Matches Person node properties
  - Uses `candidate_name` (not "name")
  - Uses `mobile_number` (not "mobile")
  - `all_skills`: Flat list (primary skill source)
  - `projects_and_technologies_involved`: With `technologies_used` (secondary skill source)
  - `certificates_or_qualifications`: String array format
  - `education`: Single object with degree/university
- `AgentRunResponse`: Complete pipeline results
- `SkillConfidenceResult`, `SkillDeficitResult`: Result models

### 2. `/agents/pipeline_new.py`
- **Complete agent pipeline implementation**

#### Extractor Class
- Validates `candidate_id` and `candidate_name` (NOT "name")
- Logs skills, projects, certifications counts
- Returns validated ExtractedData

#### Normalizer Class
- Extracts skills from:
  1. `all_skills` (primary)
  2. `projects_and_technologies_involved[].technologies_used` (secondary)
- Normalizes using skill aliases (Python3 → Python)
- Updates `all_skills` with canonical names
- Updates `num_skills` automatically

#### KGWriter Class
- **Step 1**: MERGE Person node by candidate_id
  - Sets all properties: candidate_name, email, mobile_number, current_role, etc.
- **Step 2**: MERGE Skills, CREATE (Person)-[:HAS_SKILL]->(Skill)
- **Step 3**: CREATE Projects, (Person)-[:WORKED_ON]->(Project)
  - CREATE (Project)-[:USES_TECHNOLOGY]->(Skill) for each technology
- **Step 4**: CREATE Certifications, (Person)-[:HAS_CERTIFICATION]->(Certification)
  - Parses "Name: Issuer" format
- **Step 5**: CREATE Education, (Person)-[:HAS_EDUCATION]->(Education)
  - CREATE (Education)-[:FROM_INSTITUTION]->(Institution)
- **Step 6**: CREATE (Person)-[:TARGETS_ROLE]->(Role {role_key})
  - Uses `role_key` query parameter (NOT cv_data.target_role)

#### GapAnalyzer Class
- Calls existing endpoints:
  1. `/candidates/{candidate_id}/skill-confidence`
  2. `/candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced?top_k=...`
- Combines results into single response

### 3. `/main_endpoint_new.py`
- **FastAPI endpoint implementation**
- Route: `POST /agent/run`
- Query parameters:
  - `role_key` (required): Target role for gap analysis
  - `top_k` (optional, default=25): Number of deficits to return
- Request body: `ExtractedData` in KG format
- Response: `AgentRunResponse` with complete results
- Includes error handling and logging

### 4. `/API_KG_FORMAT_GUIDE.md`
- **Comprehensive integration guide**
- Data format documentation
- Field name mappings (old → new)
- Cypher query examples
- Python usage examples
- Migration guide from old format
- Troubleshooting section

## Key Design Decisions

### 1. Exact KG Format Match
**Decision**: Accept data in exact same format as Graph-Builder creates
**Reason**: Eliminates format conversion, reduces errors, consistent with existing KG

### 2. Target Role from Query Parameter
**Decision**: `role_key` is query parameter, not in request body
**Reason**: 
- Frontend sends role separately from CV data
- CV's `target_role` field is informational only
- TARGETS_ROLE relationship uses the query param `role_key`

### 3. Dual Skill Sources
**Decision**: Extract skills from both `all_skills` AND `projects.technologies_used`
**Reason**:
- `all_skills` is primary source (comprehensive list)
- Projects provide additional context and validation
- Both are normalized and deduplicated

### 4. Certification String Format
**Decision**: Parse "Name: Issuer" from string array
**Reason**: Matches how Graph-Builder stores certifications in KG

### 5. Single Education Object
**Decision**: Education is single object, not array
**Reason**: Matches current KG structure (Person has one Education node)

## Field Name Changes

| Old Field | New Field | Reason |
|-----------|-----------|--------|
| `name` | `candidate_name` | Match KG Person.candidate_name |
| `mobile` | `mobile_number` | Match KG Person.mobile_number |
| `skills` (categorized object) | `all_skills` (flat list) | Match KG structure |
| `projects` | `projects_and_technologies_involved` | Match KG property name |
| `certifications` (object array) | `certificates_or_qualifications` (string array) | Match KG storage format |

## Pipeline Flow

```
Frontend → API → Extractor → Normalizer → KG Writer → Gap Analyzer → Response
           ↓                                    ↓              ↓
         Query:                            Neo4j KG      Existing APIs
         ?role_key=ai_ml_engineer                       (skill-confidence,
         &top_k=25                                       skill-gap-advanced)
```

## Cypher Queries Generated

### Person Node (MERGE)
```cypher
MERGE (p:Person {candidate_id: $candidate_id})
SET p.candidate_name = $candidate_name,
    p.email = $email,
    p.mobile_number = $mobile_number,
    p.current_role = $current_role,
    p.target_role = $target_role,
    p.experience_months = $experience_months,
    p.num_skills = $num_skills,
    p.num_projects = $num_projects
```

### Skills (MERGE + Relationship)
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
MERGE (s:Skill {name: $skill_name})
MERGE (p)-[:HAS_SKILL]->(s)
```

### Projects (CREATE + Technology Links)
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
CREATE (pr:Project {
    project_name: $project_name,
    project_description: $project_description,
    duration: $duration,
    complexity: $complexity
})
MERGE (p)-[:WORKED_ON]->(pr)

// For each technology_used:
MATCH (pr:Project {project_name: $project_name})
MERGE (s:Skill {name: $tech})
MERGE (pr)-[:USES_TECHNOLOGY]->(s)
```

### Certifications (CREATE)
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
CREATE (c:Certification {
    name: $cert_name,
    issuer: $cert_issuer
})
MERGE (p)-[:HAS_CERTIFICATION]->(c)
```

### Education (CREATE + Institution)
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
MERGE (inst:Institution {name: $university})
CREATE (edu:Education {degree: $degree})
MERGE (p)-[:HAS_EDUCATION]->(edu)
MERGE (edu)-[:FROM_INSTITUTION]->(inst)
```

### Target Role (MERGE)
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
MERGE (r:Role {role_key: $role_key})
MERGE (p)-[:TARGETS_ROLE]->(r)
```

## Integration Steps

### To Use These New Files:

1. **Replace models/schemas.py** with models/schemas_new.py:
   ```bash
   mv models/schemas.py models/schemas_old.py
   mv models/schemas_new.py models/schemas.py
   ```

2. **Replace agent pipeline**:
   ```bash
   mv agents/pipeline_new.py agents/pipeline.py
   ```

3. **Update main.py** with endpoint from main_endpoint_new.py:
   - Copy the `/agent/run` endpoint code
   - Update imports to use new classes
   - Add skill aliases dictionary (your 64 aliases)

4. **Update models/__init__.py**:
   ```python
   from .schemas import (
       ExtractedData,
       EducationData,
       ProjectData,
       AgentRunResponse,
       SkillConfidenceResult,
       SkillDeficitResult,
       HealthResponse
   )
   
   __all__ = [
       "ExtractedData",
       "EducationData", 
       "ProjectData",
       "AgentRunResponse",
       "SkillConfidenceResult",
       "SkillDeficitResult",
       "HealthResponse"
   ]
   ```

5. **Restart server**:
   ```bash
   uvicorn main:app --reload --port 8002
   ```

## Example Request

```bash
curl -X POST "http://localhost:8002/agent/run?role_key=ai_ml_engineer&top_k=20" \
  -H "Content-Type: application/json" \
  -d '{
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
        "project_name": "Image Classifier",
        "project_description": "CNN model",
        "technologies_used": ["Python", "TensorFlow"],
        "complexity": "High"
      }
    ],
    "certificates_or_qualifications": [
      "TensorFlow Developer: Google"
    ],
    "education": {
      "degree": "MSc Computer Science",
      "university": "Stanford"
    }
  }'
```

## Expected Response

```json
{
  "candidate_id": "CAND_TEST_001",
  "status": "success",
  "normalized_skills_count": 4,
  "nodes_created": 12,
  "relationships_created": 18,
  "top_skills": [
    {
      "skill_name": "Python",
      "confidence_score": 0.92,
      "evidence_sources": ["HAS_SKILL", "USES_TECHNOLOGY"]
    }
  ],
  "top_deficits": [
    {
      "skill_name": "Kubernetes",
      "demand": 85,
      "deficit_score": 0.78
    }
  ],
  "readiness_score": 0.68,
  "role_key": "ai_ml_engineer",
  "processing_time_ms": 1450.2
}
```

## Benefits

✅ **No Format Conversion**: Same format as KG uses
✅ **Consistent Field Names**: candidate_name, mobile_number match KG
✅ **Dual Skill Sources**: all_skills + project technologies
✅ **Complete Graph**: All nodes and relationships created
✅ **Role from Parameter**: Frontend sends role separately
✅ **Normalized Skills**: Canonical names (Python3 → Python)
✅ **Gap Analysis**: Integrated with existing APIs
✅ **Error Handling**: Proper validation and logging

## Next Steps

1. Test with your existing combined_resumes.json data
2. Add your 64 skill aliases to SKILL_ALIASES dict
3. Verify Neo4j queries create correct graph structure
4. Update frontend to send role_key as query parameter
5. Test gap analysis results

## Testing Checklist

- [ ] Person node created with correct properties
- [ ] Skills from all_skills linked via HAS_SKILL
- [ ] Projects created with WORKED_ON relationships
- [ ] Project technologies linked via USES_TECHNOLOGY
- [ ] Certifications created and linked
- [ ] Education and Institution created
- [ ] TARGETS_ROLE relationship created with role_key
- [ ] Skill confidence API called successfully
- [ ] Gap analysis API called successfully
- [ ] Response contains all expected fields

## Notes

- The `target_role` field in CV data is informational only
- The actual role for TARGETS_ROLE comes from `role_key` query parameter
- Skills are normalized using your existing 64 aliases
- Certifications parse "Name: Issuer" format automatically
- Education is single object (not array)
- All optional fields handled gracefully

## Support

See `API_KG_FORMAT_GUIDE.md` for:
- Complete documentation
- Cypher query examples
- Migration guide from old format
- Troubleshooting tips
- Available role keys
