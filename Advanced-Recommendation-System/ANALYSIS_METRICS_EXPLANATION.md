# End-to-End Analysis Metrics Explanation

## Overview
The dashboard shows **Analysis for: Data Analyst** with metrics like "31% Readiness", "Matched Skills: 5", "Skill Gaps: 18", and strengths with percentages. Here's how each metric is calculated.

---

## 1. READINESS SCORE (31% in the image)

### What is it?
The **Readiness Score** represents the candidate's overall preparedness for the target role, expressed as a percentage (0-100%).

### Formula
```
readiness = 1.0 - skill_gap_index
skill_gap_index = sum(all_deficits) / sum(all_importances)

Final percentage = readiness × 100
```

### How it Works (Step-by-Step)

**Step 1: Calculate Deficit for Each Skill**
```
deficit = importance × (1 - match_strength)
```

Where:
- **importance** = How critical this skill is for the role (0-1 scale)
- **match_strength** = How well candidate has this skill (0-1 scale)
  - 1.0 = Exact match (candidate has the skill)
  - 0.7 = Cluster match (similar skill, e.g., Python3 vs Python)
  - 0.4-0.6 = Partial match (related skill)
  - 0.0 = No match (candidate lacks this skill)

**Step 2: Sum All Deficits**
```
total_deficit = sum of all deficits across skills
total_importance = sum of all importances across skills
```

**Step 3: Calculate Readiness**
```
readiness_index = total_deficit / total_importance
readiness_score = 1 - readiness_index

Example:
- Total deficit: 5.2
- Total importance: 10.0
- readiness_index = 5.2 / 10.0 = 0.52
- readiness = 1 - 0.52 = 0.48 (48%)
```

### Code Implementation
**File**: [Agent-Runtime/agents/gap_analyzer.py](Agent-Runtime/agents/gap_analyzer.py#L230-L240)

```python
@staticmethod
def _compute_readiness(deficits: List[SkillDeficitResult]) -> float:
    """Readiness = 1 - (sum(deficits) / sum(importances))"""
    if not deficits:
        return 1.0
    
    total_deficit = sum(d.deficit for d in deficits)
    total_importance = sum(d.importance for d in deficits)
    
    if total_importance == 0:
        return 1.0
    
    skill_gap_index = total_deficit / total_importance
    readiness = 1 - skill_gap_index
    return max(0.0, min(1.0, readiness))  # Clamp to [0, 1]
```

---

## 2. MATCHED SKILLS (5 skills in the image)

### What is it?
**Matched Skills** = Count of skills where the candidate has sufficient proficiency for the role.

### Threshold
A skill is **matched** if:
```
match_strength >= 0.5
```

### How Match Strength is Calculated

The system uses **3-level graded matching**:

#### Level 1: Exact Match (1.0)
```
IF candidate_skills.contains(required_skill):
    match_strength = 1.0
```

#### Level 2: Cluster Match (0.7)
Skills are grouped into clusters (e.g., "Machine Learning" cluster contains: TensorFlow, PyTorch, Scikit-learn)
```
IF required_skill_in_cluster AND candidate_has_any_skill_in_cluster:
    match_strength = 0.7
```

#### Level 3: Similarity Match (0.4-0.6)
Graph-based similarity using Neo4j edges
```
IF required_skill_has_similarity_edge_to_candidate_skill:
    match_strength = 0.4 to 0.6 (based on edge weight)
```

#### Level 4: No Match (0.0)
```
IF no_match_found:
    match_strength = 0.0
```

### Code Implementation
**File**: [Advanced-Recommendation-System/services/skill_matching.py](Advanced-Recommendation-System/services/skill_matching.py#L336-L390)

```python
def compute_graded_matches(session, candidate_id, required_skill_names):
    """
    Returns: {'Python': 1.0, 'TensorFlow': 0.7, 'Docker': 0.6, 'Kubernetes': 0.0}
    """
    # Step 1: Load candidate skills
    candidate_profile = load_candidate_skill_profile(session, candidate_id)
    
    # Step 2: Batch query clusters for required skills (1 query)
    required_clusters = batch_query_skill_clusters(session, required_skill_names)
    
    # Step 3: Batch query similarities (1 query)
    required_similarities = batch_query_similar_skills(session, required_skill_names)
    
    # Step 4: Compute match strength for each skill
    match_strengths = {}
    for required_skill in required_skill_names:
        strength = match_strength(
            required_skill,
            candidate_profile,
            required_clusters.get(required_skill),
            required_similarities.get(required_skill, [])
        )
        match_strengths[required_skill] = strength
    
    return match_strengths
```

### Summary of Matched Skills
```
Example for "Data Analyst" role:

Candidate has these skills:
✅ Python (exact match 1.0) → MATCHED
✅ SQL (exact match 1.0) → MATCHED
✅ Power BI (cluster match 0.7 - similar to Tableau) → MATCHED
✅ Excel (exact match 1.0) → MATCHED
✅ Pandas (cluster match 0.8 - ML/Data tools) → MATCHED
❌ Tableau (no match 0.0) → NOT MATCHED
❌ Statistics (no match 0.0) → NOT MATCHED

Matched Skills Count = 5 (all with match_strength >= 0.5)
```

---

## 3. SKILL GAPS (18 skills in the image)

### What is it?
**Skill Gaps** = List of skills the candidate lacks but are important for the target role, ranked by priority.

### How Gaps are Ranked

#### Primary Formula (Symbolic Method - TF-IDF Based)
```
deficit = importance × (1 - match_strength)
```

#### Secondary Formula (Hybrid Method - GNN-Enhanced)
```
final_score = deficit × P_gnn
```

Where:
- **P_gnn** = Probability the skill can be learned (0-1, from Graph Neural Network)
- Skills with higher P_gnn (easier to learn) rank higher despite larger deficit

#### Tertiary Formula (Additive GNN)
```
final_score = 0.3 × gap + 0.4 × importance + 0.3 × P_gnn
```

### Detailed Calculation Example

**For "Tableau" skill in "Data Analyst" role:**

```
Step 1: Get skill importance
- Role requires Tableau in 84% of job postings
- importance = 0.84

Step 2: Check candidate match
- Candidate has no Power BI experience
- match_strength = 0.0 (no match)

Step 3: Calculate deficit
- deficit = 0.84 × (1 - 0.0) = 0.84

Step 4: Rank (if using GNN)
- P_gnn = 0.75 (high probability to learn visualization tools)
- final_score = 0.84 × 0.75 = 0.63 (HIGH PRIORITY)
```

### Code Implementation
**File**: [Advanced-Recommendation-System/services/deficit_service.py](Advanced-Recommendation-System/services/deficit_service.py#L126-L160)

```python
@staticmethod
def compute_deficits_with_graded_matching(session, candidate_id, role_importance, top_k=25):
    """
    Compute deficit scores using GRADED skill matching.
    
    Returns top_k deficits sorted by deficit descending:
    [
        {
            "skill_name": "TensorFlow",
            "match_strength": 0.6,
            "importance": 0.76,
            "deficit": 0.304,  # 0.76 × (1 - 0.6)
            "P_gnn": 0.81,
            "final_score": 0.246,  # 0.304 × 0.81
            "reason": "Important ML framework, learnable"
        },
        ...
    ]
    """
    # Get graded match strengths
    match_strengths = compute_graded_matches(session, candidate_id, role_importance.keys())
    
    deficits = []
    for skill_name, importance_data in role_importance.items():
        match_strength = match_strengths.get(skill_name, 0.0)
        importance = importance_data["importance"]
        
        # FORMULA: deficit = importance × (1 - match_strength)
        deficit = importance * (1 - match_strength)
        
        deficits.append({
            "skill_name": skill_name,
            "match_strength": match_strength,
            "importance": importance,
            "deficit": deficit,
        })
    
    # Sort by deficit descending
    deficits.sort(key=lambda x: x["deficit"], reverse=True)
    return deficits[:top_k]
```

### API Endpoints
- **Symbolic**: `/candidates/{id}/roles/{role}/skill-gap-advanced`
- **Hybrid (GNN)**: `/candidates/{id}/roles/{role}/missing-skills-gnn`

---

## 4. STRENGTHS PERCENTAGES (Python 99%, Flutter 99%, etc.)

### What is it?
**Strengths** = Candidate's proficiency in specific skills, shown as confidence percentages.

### Source of Percentages

The percentages come from **Skill Confidence Scores**, which are extracted from the candidate's profile/CV using multiple evidence sources:

```
confidence = number_of_evidence_sources / total_evidence_weight

Evidence sources can be:
- CV text mentions
- Work experience
- Projects
- Certifications
- Social profiles (GitHub, etc.)
```

### Calculation Example

**For "Python" skill:**
```
Evidence sources:
1. CV mention: 5 projects using Python
2. Work experience: 8 years of Python development
3. GitHub: 50+ Python repositories
4. Certifications: Python Developer Certification

Combined confidence calculation:
- Maximum evidence weight: 100
- Actual evidence: 95 (strong evidence across all sources)
- confidence = 95/100 = 0.95 = 95%

Display: "Python 95%"
```

### Code Implementation
**File**: [Agent-Runtime/agents/gap_analyzer.py](Agent-Runtime/agents/gap_analyzer.py#L100-L140)

```python
def _get_skill_confidence(self, candidate_id: str, top_n: int = 25) -> List[SkillConfidenceResult]:
    """
    Get candidate skill confidence from recommendation API.
    
    Endpoint: GET /candidates/{candidate_id}/skill-confidence?top_n={top_n}
    
    Returns:
    [
        {
            "skill_name": "Python",
            "confidence": 0.99,  # 99%
            "evidence_count": 25,  # 25 evidence pieces
            "evidence_sources": ["cv", "github", "projects", "work_experience"]
        },
        {
            "skill_name": "Flutter",
            "confidence": 0.99,
            "evidence_count": 18,
            "evidence_sources": ["cv", "projects", "work_experience"]
        },
        ...
    ]
    """
    url = f"{self.api_base_url}/candidates/{candidate_id}/skill-confidence"
    response = requests.get(url, params={"top_n": top_n}, timeout=30)
    
    confidence_results = []
    for skill in response.json().get("skills", []):
        confidence_results.append(SkillConfidenceResult(
            skill_name=skill["skill_name"],
            confidence=skill["confidence"],  # This is the percentage
            evidence_count=skill["evidence_count"],
            evidence_sources=skill["evidence_sources"]
        ))
    return confidence_results
```

### Category-Based Strength Analysis

**File**: [Advanced-Recommendation-System/services/category_service.py](Advanced-Recommendation-System/services/category_service.py#L283-L290)

For category-based analysis (e.g., "Data Analysis", "Machine Learning"):

```python
# Coverage: average match strength for category skills
avg_match = sum(match_strengths) / len(match_strengths)

# Gap score: importance × (1 - coverage)
gap_score = importance_sum × (1 - avg_match)

# Coverage percentage
coverage_percent = (avg_match) × 100

Example for "Machine Learning" category:
- Matched strengths: [1.0, 0.7, 0.6, 0.4] (Python, TensorFlow, PyTorch, Scikit-learn)
- Average: (1.0 + 0.7 + 0.6 + 0.4) / 4 = 0.675
- Coverage: 67.5%
```

---

## 5. COMPLETE DATA FLOW (End-to-End)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND REQUEST                             │
│         "Analyze candidate for Data Analyst role"              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 1: LOAD ROLE REQUIREMENTS                        │
│  File: role_importance_service.py                              │
│                                                                 │
│  Query Neo4j:                                                   │
│  - Get all skills required for "Data Analyst" role             │
│  - Calculate TF (skill frequency in role): 38, 45, 12, ...     │
│  - Calculate DF (document frequency): roles with this skill    │
│  - Calculate IDF = log(total_roles / DF)                       │
│  - Calculate Importance = TF × IDF                             │
│                                                                 │
│  Result: {                                                      │
│    "Python": {"importance": 0.89, "tf": 120, "df": 5},        │
│    "SQL": {"importance": 0.84, "tf": 110, "df": 8},           │
│    "Tableau": {"importance": 0.76, "tf": 98, "df": 12},       │
│    ... (15 more skills)                                         │
│  }                                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 2: LOAD CANDIDATE PROFILE                        │
│  File: skill_matching.py                                       │
│                                                                 │
│  Query Neo4j:                                                   │
│  - Get all skills candidate has/mentioned                      │
│  - Get confidence score for each skill                         │
│  - Extract skill clusters and categories                       │
│                                                                 │
│  Result: {                                                      │
│    "skills": ["Python", "Pandas", "SQL", "Excel", "Power BI"] │
│    "confidence": {"Python": 0.95, "SQL": 0.88, ...}            │
│  }                                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 3: COMPUTE GRADED MATCHING                       │
│  File: skill_matching.py → compute_graded_matches()            │
│                                                                 │
│  For each required skill:                                       │
│  1. Check exact match (candidate has exact skill)              │
│  2. Check cluster match (similar skill in same cluster)         │
│  3. Check similarity edges (Neo4j similarity relationships)     │
│                                                                 │
│  Results: {                                                     │
│    "Python": 1.0,        ← Exact match                         │
│    "SQL": 1.0,           ← Exact match                         │
│    "Tableau": 0.0,       ← No match                            │
│    "Statistics": 0.0,    ← No match                            │
│    "R": 0.6,             ← Similarity match (similar to Python)│
│    "Excel": 0.7,         ← Cluster match                       │
│  }                                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 4: COMPUTE DEFICITS                              │
│  File: deficit_service.py → compute_deficits_with_...()        │
│                                                                 │
│  For each required skill:                                       │
│  deficit = importance × (1 - match_strength)                   │
│                                                                 │
│  Results (top 5 sorted by deficit):                             │
│  [                                                              │
│    {                                                            │
│      "skill": "Tableau",                                        │
│      "importance": 0.76,                                        │
│      "match_strength": 0.0,                                     │
│      "deficit": 0.76  ← 0.76 × (1 - 0.0)                      │
│    },                                                           │
│    {                                                            │
│      "skill": "Statistics",                                     │
│      "importance": 0.68,                                        │
│      "match_strength": 0.0,                                     │
│      "deficit": 0.68                                            │
│    },                                                           │
│    ...                                                          │
│  ]                                                              │
│                                                                 │
│  Total deficit across all skills: 5.2                          │
│  Total importance across all skills: 10.0                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 5: RANK GAPS (Optional GNN Enhancement)          │
│  File: gnn_ranking_service.py                                  │
│                                                                 │
│  If using Hybrid mode:                                         │
│  - Run GNN to get P_gnn (learning probability)                 │
│  - final_score = deficit × P_gnn                               │
│  - Re-sort by final_score                                      │
│                                                                 │
│  Example:                                                       │
│  Tableau: deficit=0.76, P_gnn=0.75 → final_score=0.57 ✓       │
│  Statistics: deficit=0.68, P_gnn=0.92 → final_score=0.63 ↑    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 6: COMPUTE READINESS SCORE                       │
│  File: gap_analyzer.py → _compute_readiness()                  │
│                                                                 │
│  Formula: readiness = 1 - (total_deficit / total_importance)   │
│                                                                 │
│  Calculation:                                                   │
│  total_deficit = 5.2                                            │
│  total_importance = 10.0                                        │
│  skill_gap_index = 5.2 / 10.0 = 0.52                           │
│  readiness = 1 - 0.52 = 0.48                                   │
│  percentage = 0.48 × 100 = 48%                                 │
│                                                                 │
│  ✓ Final Readiness Score: 48%                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 7: COUNT MATCHED SKILLS                          │
│  File: skill_matching.py & SkillGap.tsx                        │
│                                                                 │
│  Filter: skill where match_strength >= 0.5                     │
│                                                                 │
│  From Step 3 results:                                           │
│  - Python: 1.0 ✓ MATCHED                                       │
│  - SQL: 1.0 ✓ MATCHED                                          │
│  - Excel: 0.7 ✓ MATCHED                                        │
│  - R: 0.6 ✓ MATCHED                                            │
│  - Pandas: 0.55 ✓ MATCHED                                      │
│  - Tableau: 0.0 ✗ NOT MATCHED                                  │
│  - Statistics: 0.0 ✗ NOT MATCHED                               │
│                                                                 │
│  ✓ Final Matched Skills Count: 5                               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 8: DISPLAY STRENGTHS                             │
│  File: NewFrontend/SkillGap.tsx                                │
│                                                                 │
│  From candidate profile:                                        │
│  - Python: 99% (evidence: CV, GitHub, experience)              │
│  - Flutter: 99% (evidence: CV, projects)                       │
│  - Machine Learning: 94%                                        │
│  - Firebase: 94%                                                │
│  - Next.js: 94%                                                │
│                                                                 │
│  Display in "Your Strengths" section                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              FRONTEND DISPLAY                                   │
│                                                                 │
│  Analysis for: Data Analyst                                    │
│  GNN-Powered Recommendations (AI Learning Potential)           │
│                                                                 │
│  [31%] Readiness ← From Step 6                                 │
│  [5] Matched Skills ← From Step 7                              │
│  [18] Skill Gaps ← Count of deficits from Step 4/5             │
│  [1%] Project Score ← Separate calculation                     │
│                                                                 │
│  Your Strengths:                                                │
│  Python 99% ← From Step 8                                      │
│  Flutter 99%                                                    │
│  Machine Learning 94%                                           │
│  ...                                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. KEY FILES REFERENCE

| Component | File Path | Key Function |
|-----------|-----------|--------------|
| **Readiness Score** | [Agent-Runtime/agents/gap_analyzer.py](Agent-Runtime/agents/gap_analyzer.py) | `_compute_readiness()` |
| **Matched Skills** | [Advanced-Recommendation-System/services/skill_matching.py](Advanced-Recommendation-System/services/skill_matching.py) | `compute_graded_matches()` |
| **Skill Gaps** | [Advanced-Recommendation-System/services/deficit_service.py](Advanced-Recommendation-System/services/deficit_service.py) | `compute_deficits_with_graded_matching()` |
| **GNN Enhancement** | [Advanced-Recommendation-System/services/gnn_ranking_service.py](Advanced-Recommendation-System/services/gnn_ranking_service.py) | `rank_with_gnn()` |
| **Strengths %** | [Agent-Runtime/agents/gap_analyzer.py](Agent-Runtime/agents/gap_analyzer.py) | `_get_skill_confidence()` |
| **Role Importance** | [Advanced-Recommendation-System/services/role_importance_service.py](Advanced-Recommendation-System/services/role_importance_service.py) | `get_role_importance()` |
| **Frontend Display** | [NewFrontend/src/pages/SkillGap.tsx](NewFrontend/src/pages/SkillGap.tsx) | Renders metrics |

---

## 7. SUMMARY TABLE

| Metric | Formula | Data Source | Example |
|--------|---------|-------------|---------|
| **Readiness %** | `(1 - Σdeficit / Σimportance) × 100` | Deficits + Importance scores | 31% = Good readiness |
| **Matched Skills** | `Count(match_strength ≥ 0.5)` | Graded skill matching | 5 skills |
| **Skill Gaps** | `Σ(importance × (1 - match_strength))` | Deficit ranking | 18 top deficits |
| **Strengths %** | `Evidence count / Max weight × 100` | Candidate profile | Python 99% |

---

## 8. ADDITIONAL NOTES

### Why GNN (Graph Neural Network)?
- **GNN calculates P_gnn**: Probability that candidate can learn a skill based on:
  - Similar skills they already have
  - Historical learning patterns
  - Skill graph structure
  
- **Hybrid ranking = More intelligent prioritization**:
  - Skills easy to learn rank higher (even if large deficit)
  - Example: "Tableau" (easier) ranks before "Advanced Statistics" (harder)

### Why Graded Matching?
- **Reduces false negatives**: Recognizes "Python3" candidate can work with "Python" jobs
- **Better than binary (0/1) confidence**: Provides nuanced signal (0.6, 0.7, 0.8, etc.)
- **3 Neo4j queries only**: Efficient batch processing regardless of skill count

### Performance Optimization
- **Caching**: Role importance computed once per role_key
- **Batch queries**: All Neo4j queries use BATCH operations
- **Top-K limiting**: Only top 25-50 results returned (not all skills)
