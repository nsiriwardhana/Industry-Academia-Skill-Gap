"""
Graded Skill Matching Module for Research-Grade Gap Analysis.

Implements fuzzy/graded matching using:
1. Exact name match (1.0)
2. Cluster membership (0.7) - skills in same semantic cluster
3. Similarity edges (0.4-0.6) - graph-based skill relationships

This replaces binary matching with graded scores, improving:
- Gap analysis accuracy (fewer false negatives)
- Course recommendations (better coverage understanding)
- GNN training labels (richer signal than 0/1)

Performance: Batch queries to avoid N+1 problem.
"""
import logging
from typing import List, Dict, Set, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURABLE MATCHING THRESHOLDS & WEIGHTS
# ============================================================================

class MatchConfig:
    """
    Tunable parameters for graded skill matching.
    
    Adjust these based on domain expertise and validation results.
    """
    # Match strength scores
    EXACT_MATCH_SCORE = 1.0          # Perfect match
    CLUSTER_MATCH_SCORE = 0.7        # Same skill family (e.g., Python3 → Python)
    HIGH_SIMILARITY_SCORE = 0.6      # Strong similarity edge (>= 0.80)
    MED_SIMILARITY_SCORE = 0.4       # Moderate similarity edge (>= 0.68)
    
    # Similarity edge thresholds (tuned for avg similarity 0.775)
    HIGH_SIMILARITY_THRESHOLD = 0.80  # Very similar skills (top ~30%)
    MED_SIMILARITY_THRESHOLD = 0.68   # Moderately similar skills (next ~40%)
    
    # Query limits (prevent graph explosions)
    MAX_SIMILAR_SKILLS_PER_QUERY = 50
    
    # String normalization (optional, for exact match)
    NORMALIZE_SKILL_NAMES = True  # Convert to lowercase, strip whitespace


# ============================================================================
# CANDIDATE SKILL PROFILE LOADER
# ============================================================================

def load_candidate_skill_profile(session, candidate_id: str) -> Dict:
    """
    Efficiently load all candidate skills with metadata in ONE query.
    
    Returns:
        {
            'skill_names': set of skill names,
            'skill_ids': set of skill node IDs,
            'cluster_ids': set of cluster IDs,
            'skills_by_cluster': {cluster_id: [skill_names]},
            'skill_name_to_id': {name: node_id}
        }
    
    Strategy: Single Cypher query aggregates HAS_SKILL, USED_SKILL, USES_TECHNOLOGY.
    """
    query = """
    MATCH (p:Person {candidate_id: $candidate_id})
    
    // Aggregate all skill sources
    OPTIONAL MATCH (p)-[:HAS_SKILL]->(s1:Skill)
    OPTIONAL MATCH (p)-[:WORKED_AT]->(w:WorkExperience)-[:USED_SKILL]->(s2:Skill)
    OPTIONAL MATCH (p)-[:WORKED_ON]->(pr:Project)-[:USES_TECHNOLOGY]->(s3:Skill)
    
    WITH p, 
         collect(DISTINCT s1) + collect(DISTINCT s2) + collect(DISTINCT s3) AS all_skills
    
    UNWIND all_skills AS s
    WITH DISTINCT s
    WHERE s IS NOT NULL
    
    RETURN id(s) AS skill_id,
           s.name AS skill_name,
           s.cluster_id AS cluster_id
    """
    
    result = session.run(query, candidate_id=candidate_id)
    
    skill_names = set()
    skill_ids = set()
    cluster_ids = set()
    skills_by_cluster = {}
    skill_name_to_id = {}
    
    for record in result:
        skill_id = record["skill_id"]
        skill_name = record["skill_name"]
        cluster_id = record.get("cluster_id")
        
        if not skill_name:
            continue
        
        # Normalize if configured
        if MatchConfig.NORMALIZE_SKILL_NAMES:
            skill_name_normalized = skill_name.lower().strip()
        else:
            skill_name_normalized = skill_name
        
        skill_names.add(skill_name_normalized)
        skill_ids.add(skill_id)
        skill_name_to_id[skill_name_normalized] = skill_id
        
        if cluster_id is not None:
            cluster_ids.add(cluster_id)
            if cluster_id not in skills_by_cluster:
                skills_by_cluster[cluster_id] = []
            skills_by_cluster[cluster_id].append(skill_name_normalized)
    
    logger.info(f"Loaded {len(skill_names)} skills, {len(cluster_ids)} clusters for candidate {candidate_id}")
    
    return {
        'skill_names': skill_names,
        'skill_ids': skill_ids,
        'cluster_ids': cluster_ids,
        'skills_by_cluster': skills_by_cluster,
        'skill_name_to_id': skill_name_to_id
    }


# ============================================================================
# BATCH SIMILARITY QUERY (Avoid N+1)
# ============================================================================

def batch_query_similar_skills(
    session, 
    required_skill_names: List[str]
) -> Dict[str, List[Tuple[str, float]]]:
    """
    For multiple required skills, fetch SIMILAR_TO neighbors in ONE query.
    
    Args:
        session: Neo4j session
        required_skill_names: List of required skill names
    
    Returns:
        {
            'Python': [('Python3', 0.92), ('Python2', 0.85), ...],
            'TensorFlow': [('PyTorch', 0.78), ...],
            ...
        }
    
    Strategy: UNWIND required skills, fetch neighbors, filter by threshold.
    """
    # Normalize skill names
    if MatchConfig.NORMALIZE_SKILL_NAMES:
        required_skill_names = [s.lower().strip() for s in required_skill_names]
    
    query = """
    UNWIND $required_skills AS req_skill_name
    
    MATCH (req:Skill)
    WHERE toLower(trim(req.name)) = req_skill_name
    
    OPTIONAL MATCH (req)-[sim:SIMILAR_TO]->(neighbor:Skill)
    WHERE sim.similarity >= $threshold
    
    WITH req.name AS required_skill,
         neighbor.name AS similar_skill,
         sim.similarity AS similarity
    WHERE similar_skill IS NOT NULL
    
    RETURN required_skill,
           collect({name: similar_skill, similarity: similarity}) AS neighbors
    ORDER BY required_skill
    LIMIT $limit
    """
    
    result = session.run(
        query, 
        required_skills=required_skill_names,
        threshold=MatchConfig.MED_SIMILARITY_THRESHOLD,  # Fetch all >= 0.75
        limit=MatchConfig.MAX_SIMILAR_SKILLS_PER_QUERY
    )
    
    similar_skills_map = {}
    
    for record in result:
        req_skill = record["required_skill"]
        neighbors = record["neighbors"]
        
        # Normalize
        if MatchConfig.NORMALIZE_SKILL_NAMES:
            req_skill_normalized = req_skill.lower().strip()
        else:
            req_skill_normalized = req_skill
        
        similar_list = []
        for neighbor in neighbors:
            neighbor_name = neighbor["name"]
            similarity = neighbor["similarity"]
            
            if MatchConfig.NORMALIZE_SKILL_NAMES:
                neighbor_name = neighbor_name.lower().strip()
            
            similar_list.append((neighbor_name, similarity))
        
        similar_skills_map[req_skill_normalized] = similar_list
    
    return similar_skills_map


def batch_query_skill_clusters(
    session,
    required_skill_names: List[str]
) -> Dict[str, int]:
    """
    Fetch cluster_id for required skills in ONE query.
    
    Returns:
        {'Python': 5, 'TensorFlow': 12, ...}
    """
    if MatchConfig.NORMALIZE_SKILL_NAMES:
        required_skill_names = [s.lower().strip() for s in required_skill_names]
    
    query = """
    UNWIND $required_skills AS req_skill_name
    
    MATCH (s:Skill)
    WHERE toLower(trim(s.name)) = req_skill_name
    
    RETURN s.name AS skill_name, s.cluster_id AS cluster_id
    """
    
    result = session.run(query, required_skills=required_skill_names)
    
    cluster_map = {}
    for record in result:
        skill_name = record["skill_name"]
        cluster_id = record.get("cluster_id")
        
        if MatchConfig.NORMALIZE_SKILL_NAMES:
            skill_name = skill_name.lower().strip()
        
        if cluster_id is not None:
            cluster_map[skill_name] = cluster_id
    
    return cluster_map


# ============================================================================
# GRADED MATCHING LOGIC
# ============================================================================

def match_strength(
    required_skill_name: str,
    candidate_profile: Dict,
    required_skill_cluster_id: int = None,
    similar_skills: List[Tuple[str, float]] = None
) -> float:
    """
    Compute graded match strength for a required skill.
    
    Args:
        required_skill_name: The skill required by role/job
        candidate_profile: Output from load_candidate_skill_profile()
        required_skill_cluster_id: Cluster ID of required skill (optional)
        similar_skills: List of (skill_name, similarity) from SIMILAR_TO edges
    
    Returns:
        Match strength in [0.0, 1.0]:
        - 1.0: Exact match (candidate has this skill)
        - 0.7: Cluster match (candidate has skill in same cluster)
        - 0.6: High similarity edge (>= 0.85)
        - 0.4: Medium similarity edge (>= 0.75)
        - 0.0: No match
    
    Example:
        >>> profile = {
        ...     'skill_names': {'python3', 'pandas', 'numpy'},
        ...     'cluster_ids': {5},
        ...     'skills_by_cluster': {5: ['python3']},
        ... }
        >>> match_strength('python', profile, required_skill_cluster_id=5)
        0.7  # Cluster match
    """
    # Normalize
    if MatchConfig.NORMALIZE_SKILL_NAMES:
        required_skill_name = required_skill_name.lower().strip()
    
    # 1. EXACT MATCH
    if required_skill_name in candidate_profile['skill_names']:
        return MatchConfig.EXACT_MATCH_SCORE
    
    # 2. CLUSTER MATCH
    if required_skill_cluster_id is not None:
        if required_skill_cluster_id in candidate_profile['cluster_ids']:
            logger.debug(f"Cluster match: {required_skill_name} (cluster {required_skill_cluster_id})")
            return MatchConfig.CLUSTER_MATCH_SCORE
    
    # 3. SIMILARITY EDGE MATCH
    if similar_skills:
        max_similarity_score = 0.0
        
        for similar_name, similarity in similar_skills:
            # Check if candidate has this similar skill
            if similar_name in candidate_profile['skill_names']:
                # Determine score based on similarity threshold
                if similarity >= MatchConfig.HIGH_SIMILARITY_THRESHOLD:
                    score = MatchConfig.HIGH_SIMILARITY_SCORE
                elif similarity >= MatchConfig.MED_SIMILARITY_THRESHOLD:
                    score = MatchConfig.MED_SIMILARITY_SCORE
                else:
                    score = 0.0
                
                max_similarity_score = max(max_similarity_score, score)
        
        if max_similarity_score > 0:
            logger.debug(f"Similarity match: {required_skill_name} -> {max_similarity_score}")
            return max_similarity_score
    
    # 4. NO MATCH
    return 0.0


# ============================================================================
# BATCH MATCHING FOR ALL REQUIRED SKILLS
# ============================================================================

def compute_graded_matches(
    session,
    candidate_id: str,
    required_skill_names: List[str]
) -> Dict[str, float]:
    """
    Compute graded match strengths for all required skills efficiently.
    
    Args:
        session: Neo4j session
        candidate_id: Candidate identifier
        required_skill_names: List of required skill names
    
    Returns:
        {
            'Python': 1.0,      # Exact match
            'TensorFlow': 0.7,  # Cluster match
            'Docker': 0.6,      # High similarity match
            'Kubernetes': 0.0,  # No match
            ...
        }
    
    Strategy:
        1. Load candidate profile (1 query)
        2. Batch query clusters for required skills (1 query)
        3. Batch query similarities for required skills (1 query)
        4. Compute match strengths for all (in memory)
    
    Total: 3 Neo4j queries regardless of # required skills.
    """
    logger.info(f"Computing graded matches for {len(required_skill_names)} required skills")
    
    # Step 1: Load candidate skills
    candidate_profile = load_candidate_skill_profile(session, candidate_id)
    
    if not candidate_profile['skill_names']:
        logger.warning(f"Candidate {candidate_id} has no skills - all matches will be 0.0")
        return {skill: 0.0 for skill in required_skill_names}
    
    # Step 2: Batch query required skill clusters
    required_clusters = batch_query_skill_clusters(session, required_skill_names)
    
    # Step 3: Batch query required skill similarities
    required_similarities = batch_query_similar_skills(session, required_skill_names)
    
    # Step 4: Compute match strengths
    match_strengths = {}
    
    for required_skill in required_skill_names:
        # Normalize
        if MatchConfig.NORMALIZE_SKILL_NAMES:
            required_skill_normalized = required_skill.lower().strip()
        else:
            required_skill_normalized = required_skill
        
        cluster_id = required_clusters.get(required_skill_normalized)
        similar_skills = required_similarities.get(required_skill_normalized, [])
        
        strength = match_strength(
            required_skill_normalized,
            candidate_profile,
            cluster_id,
            similar_skills
        )
        
        match_strengths[required_skill] = strength
    
    # Log statistics
    exact_matches = sum(1 for s in match_strengths.values() if s == 1.0)
    cluster_matches = sum(1 for s in match_strengths.values() if s == 0.7)
    similarity_matches = sum(1 for s in match_strengths.values() if 0.0 < s < 0.7)
    no_matches = sum(1 for s in match_strengths.values() if s == 0.0)
    
    logger.info(
        f"Match distribution: {exact_matches} exact, {cluster_matches} cluster, "
        f"{similarity_matches} similarity, {no_matches} no match"
    )
    
    return match_strengths


# ============================================================================
# UNIT TEST EXAMPLES
# ============================================================================

def _test_examples():
    """
    Pure Python unit test examples (no Neo4j required).
    
    Run this to validate matching logic.
    """
    print("=" * 70)
    print("GRADED SKILL MATCHING - UNIT TEST EXAMPLES")
    print("=" * 70)
    
    # Mock candidate profile
    candidate_profile = {
        'skill_names': {'python3', 'pandas', 'numpy', 'scikit-learn'},
        'skill_ids': {1, 2, 3, 4},
        'cluster_ids': {5, 8},
        'skills_by_cluster': {
            5: ['python3'],      # Python cluster
            8: ['pandas', 'numpy']  # Data analysis cluster
        },
        'skill_name_to_id': {
            'python3': 1,
            'pandas': 2,
            'numpy': 3,
            'scikit-learn': 4
        }
    }
    
    # Test 1: Exact match
    print("\n[Test 1] Exact Match")
    print("Required: 'pandas', Candidate has: 'pandas'")
    score = match_strength('pandas', candidate_profile)
    print(f"→ Match strength: {score} (expected: 1.0)")
    assert score == 1.0, "Exact match should return 1.0"
    
    # Test 2: Cluster match
    print("\n[Test 2] Cluster Match")
    print("Required: 'python' (cluster 5), Candidate has: 'python3' (cluster 5)")
    score = match_strength('python', candidate_profile, required_skill_cluster_id=5)
    print(f"→ Match strength: {score} (expected: 0.7)")
    assert score == 0.7, "Cluster match should return 0.7"
    
    # Test 3: High similarity match
    print("\n[Test 3] High Similarity Match")
    print("Required: 'pytorch', Candidate has: 'tensorflow' (similarity 0.86)")
    similar_skills = [('tensorflow', 0.86)]  # Pretend candidate has TensorFlow
    # First add tensorflow to candidate profile
    candidate_profile_with_tf = candidate_profile.copy()
    candidate_profile_with_tf['skill_names'] = candidate_profile['skill_names'].copy()
    candidate_profile_with_tf['skill_names'].add('tensorflow')
    
    score = match_strength('pytorch', candidate_profile_with_tf, similar_skills=similar_skills)
    print(f"→ Match strength: {score} (expected: 0.6)")
    assert score == 0.6, "High similarity match should return 0.6"
    
    # Test 4: Medium similarity match
    print("\n[Test 4] Medium Similarity Match")
    print("Required: 'react', Candidate has: 'vue.js' (similarity 0.78)")
    candidate_profile_with_vue = candidate_profile.copy()
    candidate_profile_with_vue['skill_names'] = candidate_profile['skill_names'].copy()
    candidate_profile_with_vue['skill_names'].add('vue.js')
    
    similar_skills = [('vue.js', 0.78)]
    score = match_strength('react', candidate_profile_with_vue, similar_skills=similar_skills)
    print(f"→ Match strength: {score} (expected: 0.4)")
    assert score == 0.4, "Medium similarity match should return 0.4"
    
    # Test 5: No match
    print("\n[Test 5] No Match")
    print("Required: 'blockchain', Candidate has: ['python3', 'pandas', 'numpy', 'scikit-learn']")
    score = match_strength('blockchain', candidate_profile)
    print(f"→ Match strength: {score} (expected: 0.0)")
    assert score == 0.0, "No match should return 0.0"
    
    # Test 6: Multiple similarity edges, take max
    print("\n[Test 6] Multiple Similarity Edges (Max)")
    print("Required: 'java', Candidate has: 'kotlin' (0.82) and 'scala' (0.89)")
    candidate_profile_with_jvm = candidate_profile.copy()
    candidate_profile_with_jvm['skill_names'] = candidate_profile['skill_names'].copy()
    candidate_profile_with_jvm['skill_names'].update(['kotlin', 'scala'])
    
    similar_skills = [('kotlin', 0.82), ('scala', 0.89)]
    score = match_strength('java', candidate_profile_with_jvm, similar_skills=similar_skills)
    print(f"→ Match strength: {score} (expected: 0.6, from scala 0.89 >= 0.85)")
    assert score == 0.6, "Should take max similarity score"
    
    print("\n" + "=" * 70)
    print("✓ ALL TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    # Run unit tests
    _test_examples()
