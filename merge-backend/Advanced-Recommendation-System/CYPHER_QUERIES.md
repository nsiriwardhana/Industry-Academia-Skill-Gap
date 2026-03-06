# Cypher Queries Reference

Complete list of Cypher queries used in the Advanced Recommendation System.

---

## 1. Candidate Skill Evidence Queries

### 1.1 HAS_SKILL Evidence (CV Claims)
```cypher
MATCH (p:Person {candidate_id: $candidate_id})-[:HAS_SKILL]->(s:Skill)
RETURN s.name AS skill_name
```

**Purpose**: Fetch skills directly claimed in CV  
**Weight**: 0.70  
**Expected Return**: List of skill names

---

### 1.2 USED_SKILL Evidence (Work Experience)
```cypher
MATCH (p:Person {candidate_id: $candidate_id})-[:WORKED_AT]->(w:WorkExperience)
      -[:USED_SKILL]->(s:Skill)
RETURN s.name AS skill_name, count(DISTINCT w) AS work_count
```

**Purpose**: Fetch skills used in work experiences  
**Weight**: 0.90 per work experience (capped at 3)  
**Expected Return**: Skill names with work experience counts

---

### 1.3 USES_TECHNOLOGY Evidence (Projects)
```cypher
MATCH (p:Person {candidate_id: $candidate_id})-[:WORKED_ON]->(pr:Project)
      -[:USES_TECHNOLOGY]->(s:Skill)
RETURN s.name AS skill_name, count(DISTINCT pr) AS project_count
```

**Purpose**: Fetch skills used in projects  
**Weight**: 0.80 per project (capped at 3)  
**Expected Return**: Skill names with project counts

---

### 1.4 CERTIFICATION Evidence
```cypher
MATCH (p:Person {candidate_id: $candidate_id})-[:HAS_CERTIFICATION]->(cert:Certification)
RETURN cert.name AS cert_name, cert.issuer AS cert_issuer
```

**Purpose**: Fetch certifications for keyword matching  
**Weight**: 0.60 (applied when certification keywords match skill name)  
**Expected Return**: Certification names and issuers

---

## 2. Role TF-IDF Queries

### 2.1 Term Frequency (TF) for Role
```cypher
MATCH (r:Role {role_key: $role_key})
OPTIONAL MATCH (r)<-[:BELONGS_TO_ROLE]-(j:Job)-[:REQUIRES_SKILL]->(s:Skill)
WITH r, s, count(DISTINCT j) AS tf, 
     size((r)<-[:BELONGS_TO_ROLE]-(:Job)) AS total_jobs
WHERE s IS NOT NULL
RETURN r.name AS role_name,
       s.name AS skill_name,
       tf,
       total_jobs
LIMIT 1000
```

**Purpose**: Count jobs in role requiring each skill  
**Variables**:
- `tf`: Number of jobs requiring skill
- `total_jobs`: Total jobs in role
**Expected Return**: Role name, skill names with TF counts

---

### 2.2 Document Frequency (DF) Across All Roles
```cypher
MATCH (r:Role)<-[:BELONGS_TO_ROLE]-(j:Job)-[:REQUIRES_SKILL]->(s:Skill)
WITH s.name AS skill_name, count(DISTINCT r) AS df
RETURN skill_name, df
```

**Purpose**: Count how many roles require each skill  
**Variables**:
- `df`: Number of distinct roles requiring skill
**Expected Return**: Skill names with DF counts

---

### 2.3 Total Number of Roles
```cypher
MATCH (r:Role)
RETURN count(DISTINCT r) AS total_roles
```

**Purpose**: Get total role count for IDF calculation  
**Formula**: IDF = log(total_roles / df)  
**Expected Return**: Single integer

---

## 3. Course Recommendation Queries

### 3.1 Courses Teaching Deficit Skills
```cypher
MATCH (c:Course)-[:TEACHES_SKILL]->(s:Skill)
WHERE s.name IN $deficit_skills
WITH c, collect(DISTINCT s.name) AS taught_skills
RETURN c.id AS course_id,
       c.name AS title,
       c.provider AS provider,
       c.avgRating AS avg_rating,
       c.difficulty AS difficulty,
       taught_skills
```

**Purpose**: Find courses that teach deficit skills  
**Input**: `$deficit_skills` = List of skill names from top-K deficits  
**Expected Return**: Course details with list of taught skills

---

## 4. Administrative Queries

### 4.1 List All Roles
```cypher
MATCH (r:Role)
OPTIONAL MATCH (r)<-[:BELONGS_TO_ROLE]-(j:Job)
WITH r, count(DISTINCT j) AS job_count
RETURN r.role_key AS role_key,
       r.name AS name,
       job_count
ORDER BY job_count DESC
```

**Purpose**: Get all roles with job counts  
**Expected Return**: Role key, name, and job count

---

## 5. Optional Optimization Queries

### 5.1 Create Indexes (Run Once)
```cypher
CREATE INDEX candidate_id_index IF NOT EXISTS 
FOR (p:Person) ON (p.candidate_id);

CREATE INDEX role_key_index IF NOT EXISTS 
FOR (r:Role) ON (r.role_key);

CREATE INDEX skill_name_index IF NOT EXISTS 
FOR (s:Skill) ON (s.name);

CREATE INDEX course_id_index IF NOT EXISTS 
FOR (c:Course) ON (c.id);
```

**Purpose**: Speed up lookups by indexed properties

---

### 5.2 Check Candidate Exists
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
RETURN count(p) AS exists
```

**Purpose**: Validate candidate before processing  
**Expected Return**: 1 if exists, 0 if not

---

### 5.3 Check Role Exists
```cypher
MATCH (r:Role {role_key: $role_key})
RETURN count(r) AS exists
```

**Purpose**: Validate role before processing  
**Expected Return**: 1 if exists, 0 if not

---

## 6. Query Performance Analysis

### 6.1 Explain Plan for TF Query
```cypher
EXPLAIN
MATCH (r:Role {role_key: $role_key})
OPTIONAL MATCH (r)<-[:BELONGS_TO_ROLE]-(j:Job)-[:REQUIRES_SKILL]->(s:Skill)
WITH r, s, count(DISTINCT j) AS tf
WHERE s IS NOT NULL
RETURN r.name, s.name, tf
```

**Purpose**: Analyze query execution plan

---

### 6.2 Profile Query Performance
```cypher
PROFILE
MATCH (r:Role {role_key: $role_key})
OPTIONAL MATCH (r)<-[:BELONGS_TO_ROLE]-(j:Job)-[:REQUIRES_SKILL]->(s:Skill)
WITH r, s, count(DISTINCT j) AS tf
WHERE s IS NOT NULL
RETURN r.name, s.name, tf
```

**Purpose**: Get detailed performance metrics

---

## 7. Data Validation Queries

### 7.1 Count Evidence Types for Candidate
```cypher
MATCH (p:Person {candidate_id: $candidate_id})
OPTIONAL MATCH (p)-[:HAS_SKILL]->(s1:Skill)
OPTIONAL MATCH (p)-[:WORKED_AT]->(w)-[:USED_SKILL]->(s2:Skill)
OPTIONAL MATCH (p)-[:WORKED_ON]->(pr)-[:USES_TECHNOLOGY]->(s3:Skill)
OPTIONAL MATCH (p)-[:HAS_CERTIFICATION]->(cert)
RETURN count(DISTINCT s1) AS has_skill_count,
       count(DISTINCT s2) AS used_skill_count,
       count(DISTINCT s3) AS uses_tech_count,
       count(DISTINCT cert) AS cert_count
```

**Purpose**: Validate candidate data quality

---

### 7.2 Count Skills per Role
```cypher
MATCH (r:Role {role_key: $role_key})<-[:BELONGS_TO_ROLE]-(j:Job)
      -[:REQUIRES_SKILL]->(s:Skill)
WITH r, count(DISTINCT s) AS skill_count, count(DISTINCT j) AS job_count
RETURN r.role_key, r.name, skill_count, job_count
```

**Purpose**: Validate role data completeness

---

### 7.3 Check Course Coverage
```cypher
MATCH (c:Course)-[:TEACHES_SKILL]->(s:Skill)
WITH c, count(DISTINCT s) AS skill_count
RETURN c.id, c.name, c.provider, skill_count
ORDER BY skill_count DESC
```

**Purpose**: Analyze course-skill coverage

---

## 8. Batch Processing Queries

### 8.1 Get All Candidate IDs
```cypher
MATCH (p:Person)
WHERE p.candidate_id IS NOT NULL
RETURN p.candidate_id AS candidate_id
ORDER BY candidate_id
```

**Purpose**: Batch process all candidates

---

### 8.2 Get All Role Keys
```cypher
MATCH (r:Role)
WHERE r.role_key IS NOT NULL
RETURN r.role_key AS role_key, r.name AS role_name
ORDER BY role_key
```

**Purpose**: Batch process all roles

---

## 9. Advanced Analytics Queries

### 9.1 Skill Co-occurrence in Roles
```cypher
MATCH (r:Role)<-[:BELONGS_TO_ROLE]-(j:Job)-[:REQUIRES_SKILL]->(s1:Skill)
MATCH (j)-[:REQUIRES_SKILL]->(s2:Skill)
WHERE s1.name < s2.name
WITH s1.name AS skill1, s2.name AS skill2, count(DISTINCT j) AS co_occurrence
WHERE co_occurrence >= 5
RETURN skill1, skill2, co_occurrence
ORDER BY co_occurrence DESC
LIMIT 100
```

**Purpose**: Find skills that frequently appear together

---

### 9.2 Most In-Demand Skills Globally
```cypher
MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill)
WITH s.name AS skill_name, count(DISTINCT j) AS job_count
RETURN skill_name, job_count
ORDER BY job_count DESC
LIMIT 50
```

**Purpose**: Global skill demand analysis

---

### 9.3 Candidate Skill Distribution
```cypher
MATCH (p:Person)-[:HAS_SKILL]->(s:Skill)
WITH p, count(DISTINCT s) AS skill_count
RETURN skill_count, count(p) AS candidate_count
ORDER BY skill_count
```

**Purpose**: Analyze candidate skill diversity

---

## 10. Testing & Debugging Queries

### 10.1 Sample Candidate with Rich Evidence
```cypher
MATCH (p:Person)-[:HAS_SKILL]->(s1:Skill)
WITH p, count(DISTINCT s1) AS has_skill_count
WHERE has_skill_count >= 5
MATCH (p)-[:WORKED_AT]->(w)-[:USED_SKILL]->(s2:Skill)
WITH p, has_skill_count, count(DISTINCT s2) AS used_skill_count
WHERE used_skill_count >= 3
RETURN p.candidate_id, has_skill_count, used_skill_count
LIMIT 5
```

**Purpose**: Find candidates with diverse evidence for testing

---

### 10.2 Sample Role with Many Skills
```cypher
MATCH (r:Role)<-[:BELONGS_TO_ROLE]-(j:Job)-[:REQUIRES_SKILL]->(s:Skill)
WITH r, count(DISTINCT s) AS skill_count, count(DISTINCT j) AS job_count
WHERE skill_count >= 20 AND job_count >= 10
RETURN r.role_key, r.name, skill_count, job_count
LIMIT 5
```

**Purpose**: Find roles with rich skill requirements for testing

---

## Query Optimization Tips

1. **Use Parameters**: Always use `$parameter` syntax for security and caching
2. **Add LIMIT**: Prevent runaway queries with LIMIT clauses
3. **Index Properties**: Create indexes on frequently queried properties
4. **Avoid Cartesian Products**: Use OPTIONAL MATCH carefully
5. **Profile Queries**: Use PROFILE to identify bottlenecks
6. **Batch Operations**: Process multiple items in single queries when possible

---

## Common Issues & Solutions

### Issue: Query Timeout
**Solution**: Add LIMIT, create indexes, or split into smaller queries

### Issue: No Results
**Solution**: Check property names match exactly (case-sensitive)

### Issue: Slow Performance
**Solution**: Run PROFILE, check for missing indexes, optimize WHERE clauses

### Issue: Memory Errors
**Solution**: Reduce LIMIT, process in batches, increase Neo4j heap size
