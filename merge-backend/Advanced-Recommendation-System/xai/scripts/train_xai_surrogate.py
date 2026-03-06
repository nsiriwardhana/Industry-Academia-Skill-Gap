"""
Train XAI Surrogate Model Script.

Trains XGBoost surrogate to approximate the missing skill ranking function.
Validates with R² threshold and generates feature importance plot.

Usage:
    python -m xai.scripts.train_xai_surrogate
"""
import sys
from pathlib import Path
import logging
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from xai.services.xai_surrogate_trainer import XAISurrogateTrainer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main execution."""
    logger.info("=" * 80)
    logger.info("Training XAI Surrogate Model")
    logger.info("=" * 80)
    
    # Configuration
    dataset_path = "xai/output/xai_missing_skill_dataset.csv"
    output_model_path = "xai/output/xai_surrogate.pkl"
    test_size = 0.2
    quality_threshold = 0.85
    
    logger.info(f"Dataset: {dataset_path}")
    logger.info(f"Output model: {output_model_path}")
    logger.info(f"Test size: {test_size}")
    logger.info(f"Quality threshold: R² >= {quality_threshold}")
    
    # Load dataset
    logger.info("Loading dataset...")
    try:
        df = pd.read_csv(dataset_path)
        logger.info(f"Loaded {len(df)} rows from dataset")
    except FileNotFoundError:
        logger.error(f"Dataset not found: {dataset_path}")
        logger.info("Please run build_xai_dataset.py first")
        return
    
    # Verify required columns
    required_cols = [
        'candidate_id', 'role_key', 'skill', 'final_score',
        'P_has', 'importance', 'P_gnn', 'gap_magnitude',
        'category', 'category_coverage', 'project_support',
        'neighbor_overlap', 'skill_popularity',
        'num_candidate_skills', 'num_candidate_projects',
        'num_candidate_categories'
    ]
    
    missing_cols = set(required_cols) - set(df.columns)
    if missing_cols:
        logger.error(f"Missing required columns: {missing_cols}")
        return
    
    logger.info(f"Dataset has {df['candidate_id'].nunique()} unique candidates")
    logger.info(f"Dataset has {df['role_key'].nunique()} unique roles")
    
    # Train surrogate
    logger.info("Initializing trainer...")
    trainer = XAISurrogateTrainer()
    
    logger.info("Training surrogate model...")
    try:
        model_info = trainer.train(
            df=df,
            test_size=test_size,
            output_model_path=output_model_path
        )
        
        # Report results
        logger.info("")
        logger.info("=" * 80)
        logger.info("Training Complete!")
        logger.info("=" * 80)
        logger.info(f"Model saved to: {output_model_path}")
        logger.info("")
        logger.info("Performance Metrics:")
        logger.info(f"  Train R²: {model_info['train_r2']:.4f}")
        logger.info(f"  Test R²:  {model_info['test_r2']:.4f}")
        logger.info(f"  Train RMSE: {model_info['train_rmse']:.6f}")
        logger.info(f"  Test RMSE:  {model_info['test_rmse']:.6f}")
        logger.info(f"  Train MAE: {model_info['train_mae']:.6f}")
        logger.info(f"  Test MAE:  {model_info['test_mae']:.6f}")
        logger.info("")
        
        # Quality check
        if model_info['test_r2'] >= quality_threshold:
            logger.info(f"✅ Quality check PASSED: R² ({model_info['test_r2']:.4f}) >= {quality_threshold}")
        else:
            logger.warning(f"⚠️  Quality check FAILED: R² ({model_info['test_r2']:.4f}) < {quality_threshold}")
            logger.warning("Consider:")
            logger.warning("  - Adding more training data")
            logger.warning("  - Engineering better features")
            logger.warning("  - Tuning hyperparameters")
        
        logger.info("")
        logger.info("Top 10 Features by Importance:")
        for i, (feat, imp) in enumerate(model_info['top_features'][:10], 1):
            logger.info(f"  {i:2d}. {feat:30s} {imp:.4f}")
        
        logger.info("=" * 80)
        logger.info("Feature importance plot saved: xai/output/feature_importance.png")
        logger.info("Next step: Generate SHAP explanations with run_shap_and_generate_text.py")
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return


if __name__ == "__main__":
    main()
