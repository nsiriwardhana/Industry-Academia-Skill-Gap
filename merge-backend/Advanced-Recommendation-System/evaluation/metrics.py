"""
Metrics for evaluating ranking quality.

Implements: Overlap, Category coherence, Evidence-weighted quality, Personalization.
"""
import math
from collections import Counter
from typing import Dict, List, Tuple


def compute_overlap(list1: List[str], list2: List[str], k: int = 10) -> float:
    """
    Compute Jaccard overlap between top-K skills from two lists.
    
    Args:
        list1: First skill list
        list2: Second skill list
        k: Number of top items to consider
        
    Returns:
        Jaccard similarity [0, 1]
    """
    set1 = set(list1[:k])
    set2 = set(list2[:k])
    
    if not set1 and not set2:
        return 1.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def compute_category_entropy(skills: List[Dict], k: int = 10) -> float:
    """
    Compute Shannon entropy of category distribution in top-K skills.
    
    Lower entropy = more focused (better coherence)
    
    Args:
        skills: List of skill dicts with 'category' field
        k: Number of top items to consider
        
    Returns:
        Entropy value (0 = single category, higher = more diverse)
    """
    if not skills or k == 0:
        return 0.0
    
    categories = [s['category'] for s in skills[:k]]
    counter = Counter(categories)
    total = len(categories)
    
    entropy = 0.0
    for count in counter.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    
    return entropy


def compute_dominant_category_share(skills: List[Dict], k: int = 10) -> float:
    """
    Compute fraction of top-K skills in the dominant category.
    
    Higher share = more focused (better coherence)
    
    Args:
        skills: List of skill dicts with 'category' field
        k: Number of top items to consider
        
    Returns:
        Dominant category share [0, 1]
    """
    if not skills or k == 0:
        return 0.0
    
    categories = [s['category'] for s in skills[:k]]
    counter = Counter(categories)
    
    max_count = max(counter.values()) if counter else 0
    return max_count / len(categories)


def compute_evidence_weighted_quality(skills: List[Dict], k: int = 10) -> float:
    """
    Compute evidence-weighted quality for OLD ranking.
    
    quality = Σ (importance * (1 - p_has))
    
    Args:
        skills: List of skill dicts
        k: Number of top items to consider
        
    Returns:
        Quality score
    """
    quality = 0.0
    for skill in skills[:k]:
        importance = skill.get('importance', 0.0)
        p_has = skill.get('p_has', 0.0)
        quality += importance * (1 - p_has)
    
    return quality


def compute_gnn_weighted_quality(skills: List[Dict], k: int = 10) -> float:
    """
    Compute GNN-weighted quality for NEW ranking.
    
    quality_gnn = Σ (importance * (1 - p_has) * p_gnn)
    
    Args:
        skills: List of skill dicts with 'p_gnn' field
        k: Number of top items to consider
        
    Returns:
        GNN-weighted quality score
    """
    quality = 0.0
    for skill in skills[:k]:
        importance = skill.get('importance', 0.0)
        p_has = skill.get('p_has', 0.0)
        p_gnn = skill.get('p_gnn', 0.0)
        quality += importance * (1 - p_has) * p_gnn
    
    return quality


def compute_all_metrics(
    old_skills: List[Dict],
    new_skills: List[Dict],
    k_values: List[int] = [10, 20]
) -> Dict:
    """
    Compute all metrics for a candidate-role pair.
    
    Args:
        old_skills: Skills from OLD endpoint
        new_skills: Skills from NEW endpoint
        k_values: List of K values to evaluate
        
    Returns:
        Dict with all metrics
    """
    metrics = {}
    
    old_skill_names = [s['skill'] for s in old_skills]
    new_skill_names = [s['skill'] for s in new_skills]
    
    for k in k_values:
        # Overlap
        metrics[f'overlap{k}'] = compute_overlap(old_skill_names, new_skill_names, k)
        
        # Category coherence for OLD
        metrics[f'old_entropy{k}'] = compute_category_entropy(old_skills, k)
        metrics[f'old_dom_share{k}'] = compute_dominant_category_share(old_skills, k)
        
        # Category coherence for NEW
        metrics[f'new_entropy{k}'] = compute_category_entropy(new_skills, k)
        metrics[f'new_dom_share{k}'] = compute_dominant_category_share(new_skills, k)
        
        # Evidence-weighted quality
        metrics[f'old_quality{k}'] = compute_evidence_weighted_quality(old_skills, k)
        metrics[f'new_quality{k}'] = compute_evidence_weighted_quality(new_skills, k)
        metrics[f'new_quality_gnn{k}'] = compute_gnn_weighted_quality(new_skills, k)
    
    return metrics


def analyze_personalization_sensitivity(
    results: List[Dict],
    role_key: str,
    candidate_feature: str = 'num_projects'
) -> Dict:
    """
    Analyze how much rankings vary by candidate profile (personalization).
    
    Hypothesis: NEW should show more variation than OLD (more personalized).
    
    Args:
        results: List of evaluation results for a specific role
        role_key: Role being analyzed
        candidate_feature: Feature to split candidates (not implemented - placeholder)
        
    Returns:
        Dict with personalization metrics
    """
    # This is a simplified version - in practice you'd split by actual features
    # For now, compute variance in rankings as a proxy for personalization
    
    if len(results) < 2:
        return {
            'role': role_key,
            'n_candidates': len(results),
            'old_list_diversity': 0.0,
            'new_list_diversity': 0.0,
            'note': 'Insufficient samples'
        }
    
    # Compute pairwise Jaccard dissimilarity (1 - Jaccard) as diversity measure
    old_lists = [r['old_top10_skills'] for r in results]
    new_lists = [r['new_top10_skills'] for r in results]
    
    old_diversity = []
    new_diversity = []
    
    for i in range(len(results)):
        for j in range(i+1, len(results)):
            old_jaccard = compute_overlap(old_lists[i], old_lists[j], 10)
            new_jaccard = compute_overlap(new_lists[i], new_lists[j], 10)
            
            old_diversity.append(1 - old_jaccard)
            new_diversity.append(1 - new_jaccard)
    
    return {
        'role': role_key,
        'n_candidates': len(results),
        'n_comparisons': len(old_diversity),
        'old_list_diversity': sum(old_diversity) / len(old_diversity) if old_diversity else 0.0,
        'new_list_diversity': sum(new_diversity) / len(new_diversity) if new_diversity else 0.0,
        'diversity_increase': (sum(new_diversity) - sum(old_diversity)) / len(old_diversity) if old_diversity else 0.0
    }


def compute_aggregate_stats(results: List[Dict], metric_name: str) -> Dict:
    """
    Compute aggregate statistics (mean, median, std) for a metric.
    
    Args:
        results: List of evaluation results
        metric_name: Name of metric field
        
    Returns:
        Dict with mean, median, std, min, max
    """
    import numpy as np
    
    values = [r[metric_name] for r in results if metric_name in r and r[metric_name] is not None]
    
    if not values:
        return {
            'mean': 0.0,
            'median': 0.0,
            'std': 0.0,
            'min': 0.0,
            'max': 0.0,
            'count': 0
        }
    
    return {
        'mean': float(np.mean(values)),
        'median': float(np.median(values)),
        'std': float(np.std(values)),
        'min': float(np.min(values)),
        'max': float(np.max(values)),
        'count': len(values)
    }
