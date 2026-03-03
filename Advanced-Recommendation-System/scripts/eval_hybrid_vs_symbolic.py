"""
Evaluation Script: Hybrid vs Symbolic Skill Gap Ranking

Compares two ranking methods:
1. SYMBOLIC: deficit = (1 - P_has) × importance
2. HYBRID: final_score = gap × importance_norm × P_gnn

Methodology:
- Sample N candidates per role
- Hide 20% of their skills (holdout set) to simulate "missing" skills
- Run both ranking methods
- Compute Hits@10, MRR, NDCG@10 for recovering held-out skills
- Compare performance

Usage:
    cd Advanced-Recommendation-System
    python scripts/eval_hybrid_vs_symbolic.py --n_candidates 10 --holdout_ratio 0.2
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import Neo4jConnection
from services.skill_confidence_service import SkillConfidenceService
from services.role_importance_service import RoleImportanceService
from services.deficit_service import DeficitService
from services.hybrid_ranking_service import HybridRankingService
from services.gnn_inference_service import gnn_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def compute_hits_at_k(ranked_predictions: List[str], ground_truth: List[str], k: int) -> float:
    """
    Compute Hits@K metric.
    
    Hits@K = 1 if any ground truth skill appears in top-K predictions, else 0
    
    Args:
        ranked_predictions: List of skill names ranked by score (descending)
        ground_truth: List of ground truth skill names
        k: Top-K cutoff
        
    Returns:
        1.0 if hit, 0.0 otherwise
    """
    if not ground_truth:
        return 0.0
    
    top_k_predictions = set(ranked_predictions[:k])
    ground_truth_set = set(ground_truth)
    
    # Check if any ground truth skill is in top-K
    if top_k_predictions & ground_truth_set:
        return 1.0
    return 0.0


def compute_mrr(ranked_predictions: List[str], ground_truth: List[str]) -> float:
    """
    Compute Mean Reciprocal Rank (MRR).
    
    MRR = 1 / rank_of_first_hit
    
    Args:
        ranked_predictions: List of skill names ranked by score (descending)
        ground_truth: List of ground truth skill names
        
    Returns:
        Reciprocal rank (1/rank) of first hit, or 0 if no hit
    """
    if not ground_truth:
        return 0.0
    
    ground_truth_set = set(ground_truth)
    
    for rank, skill in enumerate(ranked_predictions, start=1):
        if skill in ground_truth_set:
            return 1.0 / rank
    
    return 0.0


def compute_ndcg_at_k(ranked_predictions: List[str], ground_truth: List[str], k: int) -> float:
    """
    Compute Normalized Discounted Cumulative Gain at K (NDCG@K).
    
    DCG@K = Σ (rel_i / log2(i+1)) for i=1 to K
    NDCG@K = DCG@K / IDCG@K
    
    Args:
        ranked_predictions: List of skill names ranked by score (descending)
        ground_truth: List of ground truth skill names
        k: Top-K cutoff
        
    Returns:
        NDCG@K score [0, 1]
    """
    if not ground_truth:
        return 0.0
    
    ground_truth_set = set(ground_truth)
    
    # Compute DCG@K
    dcg = 0.0
    for i, skill in enumerate(ranked_predictions[:k], start=1):
        if skill in ground_truth_set:
            dcg += 1.0 / np.log2(i + 1)
    
    # Compute IDCG@K (ideal DCG with all ground truth at top)
    idcg = sum(1.0 / np.log2(i + 1) for i in range(1, min(len(ground_truth), k) + 1))
    
    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def sample_candidates_per_role(session, n_per_role: int = 10) -> Dict[str, List[str]]:
    """
    Sample N candidates per role that have at least 5 skills.
    
    Args:
        session: Neo4j session
        n_per_role: Number of candidates to sample per role
        
    Returns:
        Dict mapping role_key to list of candidate_ids
    """
    logger.info(f"Sampling {n_per_role} candidates per role...")
    
    query = """
    MATCH (p:Person)-[:HAS_SKILL]->(s:Skill)
    WITH p, count(DISTINCT s) AS skill_count
    WHERE skill_count >= 5
    MATCH (p)-[:HAS_SKILL]->(s:Skill)<-[:REQUIRES_SKILL]-(j:Job)-[:BELONGS_TO_ROLE]->(r:Role)
    WITH r.role_key AS role_key, p.candidate_id AS candidate_id, count(DISTINCT s) AS common_skills
    WHERE common_skills >= 3
    WITH role_key, candidate_id
    ORDER BY role_key, rand()
    WITH role_key, collect(candidate_id)[..$limit] AS candidates
    RETURN role_key, candidates
    """
    
    result = session.run(query, limit=n_per_role)
    
    role_to_candidates = {}
    for record in result:
        role_key = record['role_key']
        candidates = record['candidates']
        if candidates:
            role_to_candidates[role_key] = candidates
    
    logger.info(f"Sampled candidates for {len(role_to_candidates)} roles")
    for role_key, candidates in role_to_candidates.items():
        logger.info(f"  {role_key}: {len(candidates)} candidates")
    
    return role_to_candidates


def get_candidate_skills(session, candidate_id: str) -> List[str]:
    """Get all skills for a candidate."""
    query = """
    MATCH (p:Person {candidate_id: $candidate_id})-[:HAS_SKILL]->(s:Skill)
    RETURN s.name AS skill_name
    """
    result = session.run(query, candidate_id=candidate_id)
    return [record['skill_name'] for record in result]


def hide_skills(session, candidate_id: str, skills_to_hide: List[str]):
    """
    Temporarily remove skills from candidate in Neo4j.
    
    WARNING: This modifies the database. Call restore_skills() after evaluation.
    """
    query = """
    MATCH (p:Person {candidate_id: $candidate_id})-[r:HAS_SKILL]->(s:Skill)
    WHERE s.name IN $skills_to_hide
    DELETE r
    """
    session.run(query, candidate_id=candidate_id, skills_to_hide=skills_to_hide)


def restore_skills(session, candidate_id: str, skills_to_restore: List[str]):
    """Restore previously hidden skills."""
    query = """
    MATCH (p:Person {candidate_id: $candidate_id})
    MATCH (s:Skill)
    WHERE s.name IN $skills_to_restore
    MERGE (p)-[:HAS_SKILL]->(s)
    """
    session.run(query, candidate_id=candidate_id, skills_to_restore=skills_to_restore)


def evaluate_candidate_role_pair(
    session,
    candidate_id: str,
    role_key: str,
    holdout_ratio: float = 0.2
) -> Dict:
    """
    Evaluate symbolic vs hybrid ranking for one candidate-role pair.
    
    Steps:
    1. Get candidate skills
    2. Hide 20% randomly (holdout set)
    3. Run symbolic ranking
    4. Run hybrid ranking
    5. Restore hidden skills
    6. Compute metrics for both methods
    
    Args:
        session: Neo4j session
        candidate_id: Candidate identifier
        role_key: Role identifier
        holdout_ratio: Fraction of skills to hide (default: 0.2)
        
    Returns:
        Dict with metrics for symbolic and hybrid methods
    """
    # Step 1: Get candidate skills
    candidate_skills = get_candidate_skills(session, candidate_id)
    
    if len(candidate_skills) < 5:
        logger.warning(f"Candidate {candidate_id} has only {len(candidate_skills)} skills, skipping")
        return None
    
    # Step 2: Hide skills
    n_holdout = max(1, int(len(candidate_skills) * holdout_ratio))
    np.random.shuffle(candidate_skills)
    holdout_skills = candidate_skills[:n_holdout]
    
    logger.info(f"Hiding {n_holdout} skills from {candidate_id}: {holdout_skills}")
    
    try:
        hide_skills(session, candidate_id, holdout_skills)
        
        # Step 3: Run symbolic ranking (using DeficitService)
        try:
            candidate_confidence = SkillConfidenceService.compute_confidence(session, candidate_id)
            role_importance, total_jobs, role_name = RoleImportanceService.compute_role_importance(
                session, role_key
            )
            
            # Compute deficits
            deficits = DeficitService.compute_deficits_with_graded_matching(
                session, candidate_id, role_importance, top_k=50
            )
            
            symbolic_ranking = [d['skill_name'] for d in deficits]
            
        except Exception as e:
            logger.error(f"Symbolic ranking failed for {candidate_id}, {role_key}: {e}")
            symbolic_ranking = []
        
        # Step 4: Run hybrid ranking
        try:
            hybrid_skills, _, _ = HybridRankingService.rank_missing_skills_hybrid(
                session=session,
                candidate_id=candidate_id,
                role_key=role_key,
                top_k=50,
                p_has_threshold=0.6
            )
            
            hybrid_ranking = [s['skill'] for s in hybrid_skills]
            
        except Exception as e:
            logger.error(f"Hybrid ranking failed for {candidate_id}, {role_key}: {e}")
            hybrid_ranking = []
        
    finally:
        # Step 5: Always restore skills
        restore_skills(session, candidate_id, holdout_skills)
        logger.info(f"Restored {len(holdout_skills)} skills for {candidate_id}")
    
    # Step 6: Compute metrics
    # Filter holdout_skills to only those relevant to role
    role_relevant_holdout = [s for s in holdout_skills if s in role_importance]
    
    if not role_relevant_holdout:
        logger.warning(f"No holdout skills are relevant to role {role_key}, skipping")
        return None
    
    logger.info(f"Evaluating {len(role_relevant_holdout)} role-relevant holdout skills")
    
    # Compute metrics for symbolic
    symbolic_metrics = {
        'hits@10': compute_hits_at_k(symbolic_ranking, role_relevant_holdout, 10),
        'mrr': compute_mrr(symbolic_ranking, role_relevant_holdout),
        'ndcg@10': compute_ndcg_at_k(symbolic_ranking, role_relevant_holdout, 10)
    }
    
    # Compute metrics for hybrid
    hybrid_metrics = {
        'hits@10': compute_hits_at_k(hybrid_ranking, role_relevant_holdout, 10),
        'mrr': compute_mrr(hybrid_ranking, role_relevant_holdout),
        'ndcg@10': compute_ndcg_at_k(hybrid_ranking, role_relevant_holdout, 10)
    }
    
    return {
        'candidate_id': candidate_id,
        'role_key': role_key,
        'n_holdout_skills': len(role_relevant_holdout),
        'holdout_skills': role_relevant_holdout,
        'symbolic': symbolic_metrics,
        'hybrid': hybrid_metrics
    }


def run_evaluation(n_candidates_per_role: int = 10, holdout_ratio: float = 0.2) -> Dict:
    """
    Run full evaluation across roles.
    
    Args:
        n_candidates_per_role: Number of candidates to sample per role
        holdout_ratio: Fraction of skills to hide per candidate
        
    Returns:
        Dict with aggregated results
    """
    logger.info("="*80)
    logger.info("HYBRID vs SYMBOLIC SKILL RANKING EVALUATION")
    logger.info("="*80)
    
    # Check GNN service
    if not gnn_service.is_ready():
        logger.error("GNN model not loaded! Load model first:")
        logger.error("  from services.gnn_inference_service import gnn_service")
        logger.error("  gnn_service.load_model(...)")
        sys.exit(1)
    
    all_results = []
    role_aggregates = defaultdict(lambda: {
        'symbolic': {'hits@10': [], 'mrr': [], 'ndcg@10': []},
        'hybrid': {'hits@10': [], 'mrr': [], 'ndcg@10': []}
    })
    
    with Neo4jConnection.get_session() as session:
        # Sample candidates
        role_to_candidates = sample_candidates_per_role(session, n_candidates_per_role)
        
        # Evaluate each candidate-role pair
        for role_key, candidates in role_to_candidates.items():
            logger.info(f"\n{'='*80}")
            logger.info(f"Evaluating role: {role_key}")
            logger.info(f"{'='*80}")
            
            for candidate_id in candidates:
                logger.info(f"\nCandidate: {candidate_id}")
                
                result = evaluate_candidate_role_pair(
                    session, candidate_id, role_key, holdout_ratio
                )
                
                if result:
                    all_results.append(result)
                    
                    # Aggregate by role
                    for metric in ['hits@10', 'mrr', 'ndcg@10']:
                        role_aggregates[role_key]['symbolic'][metric].append(result['symbolic'][metric])
                        role_aggregates[role_key]['hybrid'][metric].append(result['hybrid'][metric])
                    
                    logger.info(f"  Symbolic: Hits@10={result['symbolic']['hits@10']:.2f}, "
                              f"MRR={result['symbolic']['mrr']:.4f}, NDCG@10={result['symbolic']['ndcg@10']:.4f}")
                    logger.info(f"  Hybrid:   Hits@10={result['hybrid']['hits@10']:.2f}, "
                              f"MRR={result['hybrid']['mrr']:.4f}, NDCG@10={result['hybrid']['ndcg@10']:.4f}")
    
    # Compute per-role averages
    role_summaries = {}
    for role_key, aggregates in role_aggregates.items():
        role_summaries[role_key] = {
            'n_samples': len(aggregates['symbolic']['hits@10']),
            'symbolic': {
                'hits@10': np.mean(aggregates['symbolic']['hits@10']),
                'mrr': np.mean(aggregates['symbolic']['mrr']),
                'ndcg@10': np.mean(aggregates['symbolic']['ndcg@10'])
            },
            'hybrid': {
                'hits@10': np.mean(aggregates['hybrid']['hits@10']),
                'mrr': np.mean(aggregates['hybrid']['mrr']),
                'ndcg@10': np.mean(aggregates['hybrid']['ndcg@10'])
            }
        }
    
    # Compute overall averages
    overall_symbolic = {
        'hits@10': np.mean([r['symbolic']['hits@10'] for r in all_results]),
        'mrr': np.mean([r['symbolic']['mrr'] for r in all_results]),
        'ndcg@10': np.mean([r['symbolic']['ndcg@10'] for r in all_results])
    }
    
    overall_hybrid = {
        'hits@10': np.mean([r['hybrid']['hits@10'] for r in all_results]),
        'mrr': np.mean([r['hybrid']['mrr'] for r in all_results]),
        'ndcg@10': np.mean([r['hybrid']['ndcg@10'] for r in all_results])
    }
    
    return {
        'config': {
            'n_candidates_per_role': n_candidates_per_role,
            'holdout_ratio': holdout_ratio,
            'total_samples': len(all_results)
        },
        'overall': {
            'symbolic': overall_symbolic,
            'hybrid': overall_hybrid
        },
        'per_role': role_summaries,
        'raw_results': all_results
    }


def print_results(results: Dict):
    """Print evaluation results in a readable format."""
    print("\n" + "="*80)
    print("EVALUATION RESULTS")
    print("="*80)
    
    print(f"\nConfiguration:")
    print(f"  Candidates per role: {results['config']['n_candidates_per_role']}")
    print(f"  Holdout ratio: {results['config']['holdout_ratio']}")
    print(f"  Total samples: {results['config']['total_samples']}")
    
    print(f"\n{'='*80}")
    print("OVERALL RESULTS (Averaged Across All Samples)")
    print("="*80)
    
    overall = results['overall']
    
    print(f"\n{'Method':<15} {'Hits@10':>10} {'MRR':>10} {'NDCG@10':>10}")
    print("-" * 50)
    print(f"{'SYMBOLIC':<15} {overall['symbolic']['hits@10']:>10.4f} "
          f"{overall['symbolic']['mrr']:>10.4f} {overall['symbolic']['ndcg@10']:>10.4f}")
    print(f"{'HYBRID':<15} {overall['hybrid']['hits@10']:>10.4f} "
          f"{overall['hybrid']['mrr']:>10.4f} {overall['hybrid']['ndcg@10']:>10.4f}")
    
    # Compute improvements
    hits_improvement = (overall['hybrid']['hits@10'] - overall['symbolic']['hits@10']) / overall['symbolic']['hits@10'] * 100 if overall['symbolic']['hits@10'] > 0 else 0
    mrr_improvement = (overall['hybrid']['mrr'] - overall['symbolic']['mrr']) / overall['symbolic']['mrr'] * 100 if overall['symbolic']['mrr'] > 0 else 0
    ndcg_improvement = (overall['hybrid']['ndcg@10'] - overall['symbolic']['ndcg@10']) / overall['symbolic']['ndcg@10'] * 100 if overall['symbolic']['ndcg@10'] > 0 else 0
    
    print(f"{'IMPROVEMENT (%)':<15} {hits_improvement:>10.2f} {mrr_improvement:>10.2f} {ndcg_improvement:>10.2f}")
    
    print(f"\n{'='*80}")
    print("PER-ROLE RESULTS")
    print("="*80)
    
    for role_key, role_data in sorted(results['per_role'].items()):
        print(f"\n{role_key} (n={role_data['n_samples']})")
        print("-" * 50)
        print(f"{'Method':<15} {'Hits@10':>10} {'MRR':>10} {'NDCG@10':>10}")
        print(f"{'Symbolic':<15} {role_data['symbolic']['hits@10']:>10.4f} "
              f"{role_data['symbolic']['mrr']:>10.4f} {role_data['symbolic']['ndcg@10']:>10.4f}")
        print(f"{'Hybrid':<15} {role_data['hybrid']['hits@10']:>10.4f} "
              f"{role_data['hybrid']['mrr']:>10.4f} {role_data['hybrid']['ndcg@10']:>10.4f}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Hybrid vs Symbolic Skill Gap Ranking"
    )
    parser.add_argument(
        '--n_candidates',
        type=int,
        default=10,
        help="Number of candidates to sample per role (default: 10)"
    )
    parser.add_argument(
        '--holdout_ratio',
        type=float,
        default=0.2,
        help="Fraction of skills to hide per candidate (default: 0.2)"
    )
    parser.add_argument(
        '--output',
        type=str,
        default='evaluation_results/hybrid_vs_symbolic.json',
        help="Output JSON file path (default: evaluation_results/hybrid_vs_symbolic.json)"
    )
    parser.add_argument(
        '--gnn_model',
        type=str,
        default='../GNN-Link-Prediction/models/best_gnn_linkpred.pt',
        help="Path to GNN model checkpoint"
    )
    parser.add_argument(
        '--gnn_data',
        type=str,
        default='../GNN-Link-Prediction/output/heterodata_lp.pt',
        help="Path to GNN graph data"
    )
    parser.add_argument(
        '--id_maps',
        type=str,
        default='../GNN-Link-Prediction/output/id_maps.json',
        help="Path to ID mappings JSON"
    )
    
    args = parser.parse_args()
    
    # Load GNN model
    logger.info("Loading GNN model...")
    gnn_service.load_model(args.gnn_model, args.gnn_data, args.id_maps)
    logger.info("GNN model loaded successfully")
    
    # Run evaluation
    results = run_evaluation(
        n_candidates_per_role=args.n_candidates,
        holdout_ratio=args.holdout_ratio
    )
    
    # Print results
    print_results(results)
    
    # Save to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nResults saved to: {output_path}")


if __name__ == '__main__':
    main()
