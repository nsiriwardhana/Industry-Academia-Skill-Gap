"""
Generate SHAP Explanations Script.

Applies SHAP to trained surrogate model and generates:
- Global explanations (summary plots, dependence plots)
- Local explanations for sample candidate-role pairs
- Natural language explanations

Usage:
    python -m xai.scripts.run_shap_and_generate_text
"""
import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from xai.services.xai_explainer import XAIExplainer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main execution."""
    logger.info("=" * 80)
    logger.info("Generating SHAP Explanations")
    logger.info("=" * 80)
    
    # Configuration
    dataset_path = "xai/output/xai_missing_skill_dataset.csv"
    model_path = "xai/output/xai_surrogate.pkl"
    output_dir = "xai/output"
    n_background = 100  # Samples for SHAP background
    n_local_examples = 3  # Number of candidate-role pairs to explain locally
    
    logger.info(f"Dataset: {dataset_path}")
    logger.info(f"Model: {model_path}")
    logger.info(f"Output directory: {output_dir}")
    
    # Load dataset
    logger.info("Loading dataset...")
    try:
        df = pd.read_csv(dataset_path)
        logger.info(f"Loaded {len(df)} rows")
    except FileNotFoundError:
        logger.error(f"Dataset not found: {dataset_path}")
        logger.info("Please run build_xai_dataset.py first")
        return
    
    # Initialize explainer
    logger.info("Initializing XAI explainer...")
    try:
        explainer = XAIExplainer(model_path=model_path)
    except FileNotFoundError:
        logger.error(f"Model not found: {model_path}")
        logger.info("Please run train_xai_surrogate.py first")
        return
    
    # Prepare features for SHAP
    logger.info("Preparing features...")
    X, y, feature_names = explainer._prepare_features(df)
    logger.info(f"Feature matrix shape: {X.shape}")
    
    # Sample background data for TreeExplainer
    logger.info(f"Sampling {n_background} background instances...")
    np.random.seed(42)
    background_idx = np.random.choice(len(X), size=min(n_background, len(X)), replace=False)
    X_background = X[background_idx]
    
    # Initialize SHAP explainer
    explainer.initialize_shap(X_background)
    
    # Generate global explanations
    logger.info("")
    logger.info("=" * 80)
    logger.info("Generating Global Explanations")
    logger.info("=" * 80)
    explainer.generate_global_explanations(X, y, output_dir=output_dir)
    
    logger.info("")
    logger.info("Global plots generated:")
    logger.info("  - shap_summary.png (beeswarm)")
    logger.info("  - shap_summary_bar.png (feature importance)")
    logger.info("  - shap_dependence_importance.png")
    logger.info("  - shap_dependence_pgnn.png")
    logger.info("  - shap_dependence_phas.png")
    
    # Generate local explanations for sample pairs
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"Generating Local Explanations ({n_local_examples} examples)")
    logger.info("=" * 80)
    
    # Select diverse candidate-role pairs
    pairs = df[['candidate_id', 'role_key']].drop_duplicates()
    
    if len(pairs) > n_local_examples:
        # Sample diverse pairs
        sample_pairs = pairs.sample(n=n_local_examples, random_state=42)
    else:
        sample_pairs = pairs
    
    for idx, (_, row) in enumerate(sample_pairs.iterrows(), 1):
        candidate_id = row['candidate_id']
        role_key = row['role_key']
        
        logger.info(f"\nExample {idx}: {candidate_id} / {role_key}")
        explainer.generate_local_explanation(
            candidate_id=candidate_id,
            role_key=role_key,
            df=df,
            top_k=5,
            output_dir=output_dir
        )
    
    logger.info("")
    logger.info("Local waterfall plots generated:")
    for idx, (_, row) in enumerate(sample_pairs.iterrows(), 1):
        filename = f"shap_local_{row['candidate_id']}_{row['role_key']}.png"
        logger.info(f"  - {filename}")
    
    # Generate text explanations for sample skills
    logger.info("")
    logger.info("=" * 80)
    logger.info("Generating Natural Language Explanations")
    logger.info("=" * 80)
    
    for idx, (_, pair_row) in enumerate(sample_pairs.iterrows(), 1):
        candidate_id = pair_row['candidate_id']
        role_key = pair_row['role_key']
        
        # Get top 2 skills for this pair
        mask = (df['candidate_id'] == candidate_id) & (df['role_key'] == role_key)
        top_skills = df[mask].nlargest(2, 'final_score')
        
        logger.info(f"\nExample {idx}: {candidate_id} / {role_key}")
        logger.info("-" * 80)
        
        for skill_idx, (_, skill_row) in enumerate(top_skills.iterrows(), 1):
            skill = skill_row['skill']
            
            explanation = explainer.explain_skill(
                candidate_id=candidate_id,
                role_key=role_key,
                skill=skill,
                df=df
            )
            
            if 'error' in explanation:
                logger.warning(f"  Skill {skill_idx}: {skill} - {explanation['error']}")
                continue
            
            logger.info(f"  Skill {skill_idx}: {skill}")
            logger.info(f"    Score: {explanation['final_score']:.4f}")
            logger.info(f"    Explanation: {explanation['explanation_text']}")
            logger.info(f"    Top factors:")
            for factor in explanation['top_factors'][:3]:
                logger.info(f"      - {factor['feature']:20s} (SHAP: {factor['shap']:+.4f}): {factor['meaning']}")
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("SHAP Generation Complete!")
    logger.info("=" * 80)
    logger.info(f"All outputs saved to: {output_dir}/")
    logger.info("")
    logger.info("Generated files:")
    logger.info("  Global explanations:")
    logger.info("    - shap_summary.png")
    logger.info("    - shap_summary_bar.png")
    logger.info("    - shap_dependence_importance.png")
    logger.info("    - shap_dependence_pgnn.png")
    logger.info("    - shap_dependence_phas.png")
    logger.info("  Local explanations:")
    for _, row in sample_pairs.iterrows():
        logger.info(f"    - shap_local_{row['candidate_id']}_{row['role_key']}.png")
    logger.info("")
    logger.info("Next step: Integrate XAI endpoint into FastAPI (xai/api/xai_routes.py)")


if __name__ == "__main__":
    main()
