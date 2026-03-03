"""
XAI Surrogate Model Trainer.

Trains interpretable surrogate model (XGBoost/LightGBM) to mimic the decision function.
Uses proper train-test split by candidate_id to avoid data leakage.
"""
import logging
import pickle
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)


class XAISurrogateTrainer:
    """Trains and evaluates surrogate model for XAI."""
    
    def __init__(self, random_state: int = 42):
        """Initialize trainer with deterministic seed."""
        self.random_state = random_state
        self.model = None
        self.feature_names = None
        self.train_metrics = {}
        self.test_metrics = {}
        
        logger.info(f"XAI Surrogate Trainer initialized (seed={random_state})")
    
    def train(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
        output_model_path: str = "xai/output/xai_surrogate.pkl"
    ) -> Dict:
        """
        Train surrogate model on explanation dataset.
        
        Args:
            df: DataFrame with features and 'final_score' label
            test_size: Fraction for test set
            output_model_path: Path to save trained model
            
        Returns:
            Dict with training metrics
        """
        logger.info(f"Training surrogate model on {len(df)} samples")
        
        # Prepare features and label
        X, y, feature_names = self._prepare_data(df)
        self.feature_names = feature_names
        
        # Split by candidate_id to avoid leakage
        train_idx, test_idx = self._split_by_candidate(df, test_size)
        
        X_train, y_train = X[train_idx], y[train_idx]
        X_test, y_test = X[test_idx], y[test_idx]
        
        logger.info(f"Train set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")
        
        # Train XGBoost model
        # Use base_score as float to ensure SHAP compatibility
        base_score = float(y_train.mean())
        
        self.model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            base_score=base_score,  # Explicit base_score for SHAP compatibility
            random_state=self.random_state,
            n_jobs=-1
        )
        
        logger.info("Training XGBoost surrogate...")
        self.model.fit(X_train, y_train, verbose=False)
        
        # Evaluate
        self.train_metrics = self._evaluate(X_train, y_train, "Train")
        self.test_metrics = self._evaluate(X_test, y_test, "Test")
        
        # Report
        logger.info("\n" + "="*60)
        logger.info("SURROGATE MODEL PERFORMANCE")
        logger.info("="*60)
        logger.info(f"Train R²: {self.train_metrics['r2']:.4f}")
        logger.info(f"Test R²:  {self.test_metrics['r2']:.4f}")
        logger.info(f"Test RMSE: {self.test_metrics['rmse']:.4f}")
        logger.info(f"Test MAE:  {self.test_metrics['mae']:.4f}")
        logger.info("="*60)
        
        # Check quality
        if self.test_metrics['r2'] < 0.85:
            logger.warning(f"⚠️  Test R² ({self.test_metrics['r2']:.4f}) is below 0.85 threshold!")
            logger.warning("Consider adding more features or debugging data quality.")
        else:
            logger.info(f"✅ Test R² ({self.test_metrics['r2']:.4f}) meets 0.85 threshold")
        
        # Save model
        self._save_model(output_model_path)
        
        # Plot feature importance
        self._plot_feature_importance()
        
        # Get top features for reporting
        feature_importance = self.model.feature_importances_
        top_features = sorted(
            zip(self.feature_names, feature_importance),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'train_r2': self.train_metrics['r2'],
            'train_rmse': self.train_metrics['rmse'],
            'train_mae': self.train_metrics['mae'],
            'test_r2': self.test_metrics['r2'],
            'test_rmse': self.test_metrics['rmse'],
            'test_mae': self.test_metrics['mae'],
            'feature_names': self.feature_names,
            'num_features': len(self.feature_names),
            'top_features': top_features
        }
    
    def _prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, list]:
        """
        Prepare feature matrix and target vector.
        
        Returns:
            X (features), y (label), feature_names
        """
        # Feature columns (exclude identifiers and label)
        feature_cols = [
            'P_has',
            'importance',
            'P_gnn',
            'gap_magnitude',
            'category_coverage',
            'project_support',
            'neighbor_overlap',
            'skill_popularity',
            'num_candidate_skills',
            'num_candidate_projects',
            'num_candidate_categories'
        ]
        
        # Handle categorical 'category' feature
        df_encoded = df.copy()
        df_encoded = pd.get_dummies(df_encoded, columns=['category'], prefix='category')
        
        # Get category dummy columns
        category_cols = [col for col in df_encoded.columns if col.startswith('category_')]
        feature_cols_final = feature_cols + category_cols
        
        # Extract features
        X = df_encoded[feature_cols_final].values
        y = df_encoded['final_score'].values
        
        logger.info(f"Prepared {len(feature_cols_final)} features: {feature_cols_final}")
        
        return X, y, feature_cols_final
    
    def _split_by_candidate(self, df: pd.DataFrame, test_size: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Split dataset by candidate_id to avoid data leakage.
        
        Returns:
            train_indices, test_indices
        """
        groups = df['candidate_id'].values
        
        splitter = GroupShuffleSplit(
            n_splits=1,
            test_size=test_size,
            random_state=self.random_state
        )
        
        train_idx, test_idx = next(splitter.split(df, groups=groups))
        
        train_candidates = set(df.iloc[train_idx]['candidate_id'].unique())
        test_candidates = set(df.iloc[test_idx]['candidate_id'].unique())
        
        # Verify no overlap
        overlap = train_candidates & test_candidates
        if overlap:
            logger.warning(f"⚠️  Train-test candidate overlap: {overlap}")
        else:
            logger.info("✅ No train-test candidate overlap (proper split)")
        
        return train_idx, test_idx
    
    def _evaluate(self, X: np.ndarray, y: np.ndarray, set_name: str) -> Dict:
        """Evaluate model performance."""
        y_pred = self.model.predict(X)
        
        metrics = {
            'r2': r2_score(y, y_pred),
            'rmse': np.sqrt(mean_squared_error(y, y_pred)),
            'mae': mean_absolute_error(y, y_pred)
        }
        
        return metrics
    
    def _save_model(self, output_path: str):
        """Save trained model to disk."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'train_metrics': self.train_metrics,
            'test_metrics': self.test_metrics
        }
        
        with open(output_file, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Saved model to {output_file}")
    
    def _plot_feature_importance(self):
        """Plot and save feature importance."""
        importances = self.model.feature_importances_
        feature_importance_df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        
        # Plot
        plt.figure(figsize=(10, 8))
        sns.barplot(
            data=feature_importance_df.head(20),
            x='importance',
            y='feature',
            palette='viridis'
        )
        plt.title('Surrogate Model Feature Importance (Top 20)', fontsize=14, fontweight='bold')
        plt.xlabel('Importance Score')
        plt.ylabel('Feature')
        plt.tight_layout()
        
        output_path = Path("xai/output/feature_importance.png")
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved feature importance plot to {output_path}")
        
        # Log top features
        logger.info("\nTop 10 Features:")
        for idx, row in feature_importance_df.head(10).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")
    
    @staticmethod
    def load_model(model_path: str = "xai/output/xai_surrogate.pkl"):
        """Load trained model from disk."""
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        trainer = XAISurrogateTrainer()
        trainer.model = model_data['model']
        trainer.feature_names = model_data['feature_names']
        trainer.train_metrics = model_data['train_metrics']
        trainer.test_metrics = model_data['test_metrics']
        
        logger.info(f"Loaded model from {model_path}")
        logger.info(f"Test R²: {trainer.test_metrics['r2']:.4f}")
        
        return trainer
