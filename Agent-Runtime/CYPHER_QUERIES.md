# Cypher Queries Reference - Agent Runtime

Complete reference of all Neo4j Cypher queries used in the Agent Runtime backend.

---

## 1. Person Node Queries

### 1.1 MERGE Person (Create or Update)

```cypher
MERGE (p:Person {candidate_id: $candidate_id})
ON CREATE SET
    p.name = $name,
    p.email = $email,
    p.phone = $phone,
    p.experience_level = $experience_level,
    p.total_experience_months = $total_experience_months,
    p.created_at = datetime()
ON MATCH SET
    p.name = $name,
    p.email = $email,
    p.phone = $phone,
    p.experience_level = $experience_level,
    p.total_experience_months = $total_experience_months,
    p.updated_at = datetime()
RETURN p, 
       CASE WHEN p.created_at = p.updated_at THEN 1 ELSE 0 END AS created
```

**Purpose**: Create new candidate or update existing one  
**Deduplication**: Uses candidate_id as unique identifier  
**Parameters**: `$candidate_id, $name, $email, $phone, $experience_level, $total_experience_months`

---

## 2. Skill Queries

### 2.1 Batch MERGE Skills (UNWIND)

```cypher
UNWIND $skill_names AS skill_name
MERGE (s:Skill {name: skill_name})
ON CREATE SET
    s.category = 'unknown',
    s.created_at = datetime()
RETURN count(*) AS total
```

**Purpose**: Batch create/merge all unique skills  
**Performance**: Uses UNWIND for efficient batch processing  
**Parameters**: `$skill_names` (array of strings)

### 2.2 Delete Existing HAS_SKILL Relationships

```cypher
MATCH (p:Person {candidate_id: $candidate_id})-[r:HAS_SKILL]->()
DELETE r
```

**Purpose**: Remove old skill relationships before creating new ones  
**Why**: Ensures clean state without duplicates

### 2.3 Create HAS_SKILL Relationships (Batch)

```cypher
MATCH (p:Person {candidate_id: $candidate_id})
UNWIND $skills AS skill_data
MATCH (s:Skill {name: skill_data.name})
MERGE (p)-[r:HAS_SKILL]->(s)
SET r.proficiency = skill_data.proficiency,
    r.created_at = datetime()
RETURN count(*) AS count
```

**Purpose**: Link candidate to skills with proficiency levels  
**Parameters**: `$candidate_id, $skills` (array of {name, proficiency})

---

## 3. Work Experience Queries

### 3.1 Delete Existing Work Experiences

```cypher
MATCH (p:Person {candidate_id: $candidate_id})-[r:WORKED_AT]->(w:WorkExperience)
DETACH DELETE w
```

**Purpose**: Remove old work experiences (cascade delete)  
**Note**: DETACH DELETE removes node and all relationships

### 3.2 Create Work Experience with Company and Skills

```cypher
MATCH (p:Person {candidate_id: $candidate_id})
MERGE (c:Company {name: $company})
CREATE (w:WorkExperience {
    title: $title,
    duration_months: $duration_months,
    created_at: datetime()
})
CREATE (p)-[:WORKED_AT]->(w)
CREATE (w)-[:FOR_COMPANY]->(c)

WITH w
UNWIND $skills AS skill_name
MATCH (s:Skill {name: skill_name})
CREATE (w)-[:USED_SKILL]->(s)

RETURN w
```

**Purpose**: Create work experience with company and skill relationships  
**Relationships Created**:
- `(Person)-[:WORKED_AT]->(WorkExperience)`
- `(WorkExperience)-[:FOR_COMPANY]->(Company)`
- `(WorkExperience)-[:USED_SKILL]->(Skill)` (multiple)

**Parameters**: `$candidate_id, $company, $title, $duration_months, $skills`

---

## 4. Project Queries

### 4.1 Delete Existing Projects

```cypher
MATCH (p:Person {candidate_id: $candidate_id})-[r:WORKED_ON]->(pr:Project)
DETACH DELETE pr
```

**Purpose**: Remove old projects (cascade delete)

### 4.2 Create Project with Technologies

```cypher
MATCH (p:Person {candidate_id: $candidate_id})
CREATE (pr:Project {
    name: $name,
    description: $description,
    created_at: datetime()
})
CREATE (p)-[:WORKED_ON]->(pr)

WITH pr
UNWIND $technologies AS tech_name
MATCH (s:Skill {name: tech_name})
CREATE (pr)-[:USES_TECHNOLOGY]->(s)

RETURN pr
```

**Purpose**: Create project with technology relationships  
**Relationships Created**:
- `(Person)-[:WORKED_ON]->(Project)`
- `(Project)-[:USES_TECHNOLOGY]->(Skill)` (multiple)

**Parameters**: `$candidate_id, $name, $description, $technologies`

---

## 5. Certification Queries

### 5.1 Delete Existing Certifications

```cypher
MATCH (p:Person {candidate_id: $candidate_id})-[r:HAS_CERTIFICATION]->(cert:Certification)
DETACH DELETE cert
```

### 5.2 Create Certifications (Batch)

```cypher
MATCH (p:Person {candidate_id: $candidate_id})
UNWIND $certs AS cert_data
CREATE (cert:Certification {
    name: cert_data.name,
    issuer: cert_data.issuer,
    year: cert_data.year,
    created_at: datetime()
})
CREATE (p)-[:HAS_CERTIFICATION]->(cert)
RETURN count(*) AS count
```

**Purpose**: Batch create certifications  
**Parameters**: `$candidate_id, $certs` (array of {name, issuer, year})

---

## 6. Education Queries

### 6.1 Delete Existing Education

```cypher
MATCH (p:Person {candidate_id: $candidate_id})-[r:STUDIED_AT]->(edu:Education)
DETACH DELETE edu
```

### 6.2 Create Education Records (Batch)

```cypher
MATCH (p:Person {candidate_id: $candidate_id})
UNWIND $education AS edu_data
CREATE (edu:Education {
    institution_name: edu_data.institution_name,
    degree: edu_data.degree,
    field_of_study: edu_data.field_of_study,
    graduation_year: edu_data.graduation_year,
    created_at: datetime()
})
CREATE (p)-[:STUDIED_AT]->(edu)
RETURN count(*) AS count
```

**Purpose**: Batch create education records  
**Parameters**: `$candidate_id, $education` (array of {institution_name, degree, field_of_study, graduation_year})

---

## 7. Verification Queries

### 7.1 Get Complete Candidate Profile

```cypher
MATCH (p:Person {candidate_id: $candidate_id})
OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)
OPTIONAL MATCH (p)-[:WORKED_AT]->(w:WorkExperience)-[:FOR_COMPANY]->(c:Company)
OPTIONAL MATCH (w)-[:USED_SKILL]->(ws:Skill)
OPTIONAL MATCH (p)-[:WORKED_ON]->(pr:Project)-[:USES_TECHNOLOGY]->(ps:Skill)
OPTIONAL MATCH (p)-[:HAS_CERTIFICATION]->(cert:Certification)
OPTIONAL MATCH (p)-[:STUDIED_AT]->(edu:Education)

RETURN p,
       collect(DISTINCT s.name) AS skills,
       collect(DISTINCT {company: c.name, title: w.title, skills: collect(DISTINCT ws.name)}) AS work,
       collect(DISTINCT {name: pr.name, technologies: collect(DISTINCT ps.name)}) AS projects,
       collect(DISTINCT cert) AS certifications,
       collect(DISTINCT edu) AS education
```

**Purpose**: Retrieve complete candidate profile for verification

### 7.2 Count Nodes and Relationships

```cypher
MATCH (p:Person {candidate_id: $candidate_id})
OPTIONAL MATCH (p)-[r]-()
RETURN 
    count(DISTINCT p) AS person_count,
    count(DISTINCT r) AS relationship_count
```

**Purpose**: Get statistics for write verification

---

## 8. Cleanup Queries

### 8.1 Delete Entire Candidate Profile

```cypher
MATCH (p:Person {candidate_id: $candidate_id})
OPTIONAL MATCH (p)-[:WORKED_AT]->(w:WorkExperience)
OPTIONAL MATCH (p)-[:WORKED_ON]->(pr:Project)
OPTIONAL MATCH (p)-[:HAS_CERTIFICATION]->(cert:Certification)
OPTIONAL MATCH (p)-[:STUDIED_AT]->(edu:Education)
DETACH DELETE p, w, pr, cert, edu
```

**Purpose**: Complete cleanup of candidate data  
**Warning**: Destructive operation, use with caution

---

## Performance Optimization Tips

### 1. Use UNWIND for Batch Operations

**Bad (N+1 queries):**
```cypher
// For each skill in Python loop:
CREATE (s:Skill {name: $skill_name})
```

**Good (Single query):**
```cypher
UNWIND $skill_names AS skill_name
MERGE (s:Skill {name: skill_name})
```

### 2. MERGE vs CREATE

- **MERGE**: Use when you want deduplication (e.g., Skills, Companies)
- **CREATE**: Use when you know it's new (e.g., WorkExperience, Project)

### 3. Index Critical Properties

```cypher
CREATE INDEX person_candidate_id IF NOT EXISTS FOR (p:Person) ON (p.candidate_id);
CREATE INDEX skill_name IF NOT EXISTS FOR (s:Skill) ON (s.name);
CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name);
```

### 4. Delete Before Recreate

For entities that may change (work experiences, projects), delete old ones before creating new:
1. Prevents duplicates
2. Simpler than complex MERGE logic
3. Cleaner data model

---

## Transaction Strategy

All queries in KG Writer are executed within a single Neo4j session for consistency:

```python
with Neo4jConnection.get_session() as session:
    # All writes happen in this session
    result = KGWriterTool.write_candidate(session, data)
```

This ensures:
- Atomicity: All-or-nothing writes
- Consistency: No partial updates
- Isolation: No interference from other requests

---

## Common Patterns

### Pattern: MERGE + ON CREATE + ON MATCH

Used for nodes that should be updated if they exist:

```cypher
MERGE (n:Node {id: $id})
ON CREATE SET
    n.property = $value,
    n.created_at = datetime()
ON MATCH SET
    n.property = $value,
    n.updated_at = datetime()
```

### Pattern: UNWIND + MATCH + CREATE

Used for batch relationship creation:

```cypher
UNWIND $items AS item
MATCH (a:NodeA {id: item.a_id})
MATCH (b:NodeB {id: item.b_id})
CREATE (a)-[:RELATES_TO]->(b)
```

### Pattern: DETACH DELETE

Used to remove nodes with all their relationships:

```cypher
MATCH (n:Node {id: $id})
DETACH DELETE n
```

---

## Error Handling

All queries include error handling in the KG Writer:

```python
try:
    result = session.run(query, parameters)
    # Process result
except Exception as e:
    logger.error(f"Query failed: {e}")
    return error_result
```

Common errors:
- Node not found
- Constraint violation
- Connection timeout
- Transaction conflict
