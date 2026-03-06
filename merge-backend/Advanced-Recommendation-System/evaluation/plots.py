"""
Visualization functions for evaluation results.

Generates plots comparing OLD vs NEW ranking.
"""
import logging
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


def plot_quality_comparison(
    results: List[Dict],
    output_dir: Path,
    k: int = 10
):
    """
    Bar chart comparing OLD vs NEW evidence-weighted quality.
    
    Shows overall and per-role comparison.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Overall comparison
    old_quality = [r[f'old_quality{k}'] for r in results]
    new_quality = [r[f'new_quality{k}'] for r in results]
    new_quality_gnn = [r[f'new_quality_gnn{k}'] for r in results]
    
    overall_data = {
        'OLD': np.mean(old_quality),
        'NEW': np.mean(new_quality),
        'NEW+GNN': np.mean(new_quality_gnn)
    }
    
    ax1.bar(overall_data.keys(), overall_data.values(), color=['#d62728', '#2ca02c', '#1f77b4'])
    ax1.set_ylabel(f'Mean Quality@{k}')
    ax1.set_title(f'Overall Quality Comparison (N={len(results)})')
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for i, (label, value) in enumerate(overall_data.items()):
        ax1.text(i, value + 0.5, f'{value:.1f}', ha='center', va='bottom', fontsize=10)
    
    # Per-role comparison
    from collections import defaultdict
    role_data = defaultdict(lambda: {'old': [], 'new': [], 'new_gnn': []})
    
    for r in results:
        role_data[r['role_key']]['old'].append(r[f'old_quality{k}'])
        role_data[r['role_key']]['new'].append(r[f'new_quality{k}'])
        role_data[r['role_key']]['new_gnn'].append(r[f'new_quality_gnn{k}'])
    
    roles = sorted(role_data.keys())
    old_means = [np.mean(role_data[role]['old']) for role in roles]
    new_gnn_means = [np.mean(role_data[role]['new_gnn']) for role in roles]
    
    x = np.arange(len(roles))
    width = 0.35
    
    ax2.bar(x - width/2, old_means, width, label='OLD', color='#d62728')
    ax2.bar(x + width/2, new_gnn_means, width, label='NEW+GNN', color='#1f77b4')
    
    ax2.set_xlabel('Role')
    ax2.set_ylabel(f'Mean Quality@{k}')
    ax2.set_title(f'Quality Comparison by Role')
    ax2.set_xticks(x)
    ax2.set_xticklabels(roles, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / f'quality_comparison_k{k}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved quality comparison plot: {output_path}")


def plot_entropy_comparison(
    results: List[Dict],
    output_dir: Path,
    k: int = 10
):
    """
    Bar chart comparing category entropy (lower = more focused).
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    
    old_entropy = [r[f'old_entropy{k}'] for r in results]
    new_entropy = [r[f'new_entropy{k}'] for r in results]
    
    data = {
        'OLD': np.mean(old_entropy),
        'NEW': np.mean(new_entropy)
    }
    
    colors = ['#d62728', '#1f77b4']
    bars = ax.bar(data.keys(), data.values(), color=colors)
    
    ax.set_ylabel(f'Mean Category Entropy@{k}')
    ax.set_title(f'Category Coherence (Lower = More Focused)')
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels and percentage improvement
    for i, (label, value) in enumerate(data.items()):
        ax.text(i, value + 0.05, f'{value:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    if data['OLD'] > 0:
        improvement = (data['OLD'] - data['NEW']) / data['OLD'] * 100
        ax.text(0.5, max(data.values()) * 0.5, 
                f'Entropy reduction:\n{improvement:.1f}%',
                ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    output_path = output_dir / f'entropy_comparison_k{k}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved entropy comparison plot: {output_path}")


def plot_overlap_distribution(
    results: List[Dict],
    output_dir: Path,
    k: int = 10
):
    """
    Histogram of Jaccard overlap between OLD and NEW rankings.
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    overlaps = [r[f'overlap{k}'] for r in results]
    
    ax.hist(overlaps, bins=20, color='#1f77b4', alpha=0.7, edgecolor='black')
    ax.axvline(np.mean(overlaps), color='red', linestyle='--', linewidth=2, 
               label=f'Mean: {np.mean(overlaps):.2f}')
    ax.axvline(np.median(overlaps), color='green', linestyle='--', linewidth=2,
               label=f'Median: {np.median(overlaps):.2f}')
    
    ax.set_xlabel(f'Jaccard Overlap@{k}')
    ax.set_ylabel('Frequency')
    ax.set_title(f'Distribution of Ranking Overlap (N={len(results)})')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add interpretation text
    mean_overlap = np.mean(overlaps)
    interpretation = "High personalization" if mean_overlap < 0.5 else "Moderate personalization" if mean_overlap < 0.7 else "Low personalization"
    ax.text(0.95, 0.95, f'Interpretation:\n{interpretation}',
            transform=ax.transAxes, ha='right', va='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8),
            fontsize=10)
    
    plt.tight_layout()
    output_path = output_dir / f'overlap_distribution_k{k}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved overlap distribution plot: {output_path}")


def plot_quality_scatter(
    results: List[Dict],
    output_dir: Path,
    k: int = 10
):
    """
    Scatter plot: OLD quality vs NEW GNN quality.
    
    Points above diagonal = NEW is better.
    """
    fig, ax = plt.subplots(figsize=(8, 8))
    
    old_quality = [r[f'old_quality{k}'] for r in results]
    new_quality_gnn = [r[f'new_quality_gnn{k}'] for r in results]
    
    ax.scatter(old_quality, new_quality_gnn, alpha=0.5, s=50, color='#1f77b4')
    
    # Add diagonal line (equal quality)
    max_val = max(max(old_quality), max(new_quality_gnn))
    ax.plot([0, max_val], [0, max_val], 'r--', linewidth=2, label='Equal quality')
    
    # Fill region where NEW is better
    ax.fill_between([0, max_val], [0, max_val], max_val, alpha=0.1, color='green', 
                    label='NEW better')
    
    ax.set_xlabel(f'OLD Quality@{k}')
    ax.set_ylabel(f'NEW+GNN Quality@{k}')
    ax.set_title(f'Quality Comparison (Each point = one candidate-role pair)')
    ax.legend()
    ax.grid(alpha=0.3)
    
    # Add statistics
    better_count = sum(1 for old, new in zip(old_quality, new_quality_gnn) if new > old)
    pct_better = better_count / len(results) * 100
    
    ax.text(0.05, 0.95, f'NEW better: {better_count}/{len(results)} ({pct_better:.1f}%)',
            transform=ax.transAxes, ha='left', va='top',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8),
            fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    output_path = output_dir / f'quality_scatter_k{k}.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved quality scatter plot: {output_path}")


def generate_all_plots(results: List[Dict], output_dir: Path):
    """Generate all evaluation plots."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Generating plots in {output_dir}...")
    
    plot_quality_comparison(results, output_dir, k=10)
    plot_entropy_comparison(results, output_dir, k=10)
    plot_overlap_distribution(results, output_dir, k=10)
    plot_quality_scatter(results, output_dir, k=10)
    
    # Generate for k=20 as well
    plot_quality_comparison(results, output_dir, k=20)
    plot_entropy_comparison(results, output_dir, k=20)
    
    logger.info("All plots generated successfully")
