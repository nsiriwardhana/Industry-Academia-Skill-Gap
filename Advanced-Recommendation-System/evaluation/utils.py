"""
Utility functions for ranking evaluation.

Provides API client, data loading, and helper functions.
"""
import logging
import time
from typing import Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class RankingAPIClient:
    """Client for interacting with ranking endpoints."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        
        # Setup session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get_old_ranking(
        self, 
        candidate_id: str, 
        role_key: str, 
        top_k: int = 25
    ) -> Tuple[Optional[Dict], float]:
        """
        Call OLD symbolic deficit ranking endpoint.
        
        Returns:
            (response_data, latency_ms)
        """
        url = f"{self.base_url}/candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced"
        params = {'top_k': top_k}
        
        start = time.perf_counter()
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            latency_ms = (time.perf_counter() - start) * 1000
            
            if response.status_code == 200:
                return response.json(), latency_ms
            else:
                logger.warning(f"OLD endpoint failed for {candidate_id}/{role_key}: {response.status_code}")
                return None, latency_ms
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error(f"OLD endpoint error for {candidate_id}/{role_key}: {e}")
            return None, latency_ms
    
    def get_gnn_ranking(
        self, 
        candidate_id: str, 
        role_key: str, 
        top_k: int = 25
    ) -> Tuple[Optional[Dict], float]:
        """
        Call NEW GNN-based ranking endpoint.
        
        Returns:
            (response_data, latency_ms)
        """
        url = f"{self.base_url}/candidates/{candidate_id}/roles/{role_key}/missing-skills-gnn"
        params = {'top_k': top_k}
        
        start = time.perf_counter()
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            latency_ms = (time.perf_counter() - start) * 1000
            
            if response.status_code == 200:
                return response.json(), latency_ms
            else:
                logger.warning(f"GNN endpoint failed for {candidate_id}/{role_key}: {response.status_code}")
                return None, latency_ms
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error(f"GNN endpoint error for {candidate_id}/{role_key}: {e}")
            return None, latency_ms
    
    def get_roles(self) -> List[str]:
        """Get list of available roles."""
        try:
            response = self.session.get(f"{self.base_url}/roles", timeout=self.timeout)
            if response.status_code == 200:
                roles = response.json()
                return [r['role_key'] for r in roles]
            else:
                logger.error(f"Failed to fetch roles: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching roles: {e}")
            return []


def load_candidate_role_pairs(csv_path: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Load candidate-role pairs from CSV or generate from database query.
    
    Args:
        csv_path: Path to CSV with columns: candidate_id, role_key
        
    Returns:
        List of (candidate_id, role_key) tuples
    """
    if csv_path:
        import pandas as pd
        try:
            df = pd.read_csv(csv_path)
            if 'candidate_id' not in df.columns or 'role_key' not in df.columns:
                logger.error(f"CSV must have 'candidate_id' and 'role_key' columns")
                return []
            
            pairs = list(zip(df['candidate_id'], df['role_key']))
            logger.info(f"Loaded {len(pairs)} candidate-role pairs from {csv_path}")
            return pairs
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            return []
    else:
        # Fallback: query Neo4j directly
        try:
            from neo4j import GraphDatabase
            import os
            
            uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
            user = os.getenv('NEO4J_USER', 'neo4j')
            password = os.getenv('NEO4J_PASSWORD')
            
            if not password:
                logger.error("NEO4J_PASSWORD environment variable not set")
                return []
            
            driver = GraphDatabase.driver(uri, auth=(user, password))
            
            query = """
            MATCH (p:Person)
            MATCH (r:Role)
            WHERE rand() < 0.1  // Sample ~10% of all combinations
            RETURN DISTINCT p.candidate_id AS candidate_id, r.role_key AS role_key
            LIMIT 500
            """
            
            with driver.session() as session:
                result = session.run(query)
                pairs = [(record['candidate_id'], record['role_key']) for record in result]
            
            driver.close()
            logger.info(f"Loaded {len(pairs)} candidate-role pairs from Neo4j")
            return pairs
        except Exception as e:
            logger.error(f"Failed to query Neo4j: {e}")
            return []


def sample_pairs(
    pairs: List[Tuple[str, str]], 
    n_samples: int, 
    stratify_by_role: bool = True
) -> List[Tuple[str, str]]:
    """
    Sample n pairs, optionally stratifying by role for balanced evaluation.
    
    Args:
        pairs: List of (candidate_id, role_key) tuples
        n_samples: Number of samples to take
        stratify_by_role: If True, sample proportionally from each role
        
    Returns:
        Sampled list of pairs
    """
    import random
    
    if len(pairs) <= n_samples:
        return pairs
    
    if not stratify_by_role:
        return random.sample(pairs, n_samples)
    
    # Group by role
    from collections import defaultdict
    role_pairs = defaultdict(list)
    for candidate_id, role_key in pairs:
        role_pairs[role_key].append((candidate_id, role_key))
    
    # Sample proportionally from each role
    samples_per_role = max(1, n_samples // len(role_pairs))
    sampled = []
    
    for role_key, role_pair_list in role_pairs.items():
        n = min(samples_per_role, len(role_pair_list))
        sampled.extend(random.sample(role_pair_list, n))
    
    # If we didn't reach n_samples, add more randomly
    if len(sampled) < n_samples:
        remaining = [p for p in pairs if p not in sampled]
        additional = random.sample(remaining, min(n_samples - len(sampled), len(remaining)))
        sampled.extend(additional)
    
    return sampled[:n_samples]


def extract_skills_list(response_data: Dict, endpoint_type: str) -> List[Dict]:
    """
    Extract skills list from API response.
    
    Args:
        response_data: API response JSON
        endpoint_type: 'old' or 'new'
        
    Returns:
        List of skill dicts with normalized fields
    """
    if endpoint_type == 'old':
        # OLD format: {deficits: [{skill_name, category, importance, p_has, deficit}, ...]}
        skills = response_data.get('deficits', [])
        return [{
            'skill': s.get('skill_name', s.get('skill', '')),
            'category': s.get('category', 'Unknown'),
            'importance': s.get('importance', 0.0),
            'p_has': s.get('p_has', 0.0),
            'deficit': s.get('deficit', 0.0),
        } for s in skills]
    else:
        # NEW format: {top_missing_skills: [{skill, category, final_score, P_gnn, P_has, importance}, ...]}
        skills = response_data.get('top_missing_skills', [])
        return [{
            'skill': s.get('skill', ''),
            'category': s.get('category', 'Unknown'),
            'importance': s.get('importance', 0.0),
            'p_has': s.get('P_has', s.get('p_has', 0.0)),
            'p_gnn': s.get('P_gnn', s.get('p_gnn', 0.0)),
            'final_score': s.get('final_score', 0.0),
        } for s in skills]
