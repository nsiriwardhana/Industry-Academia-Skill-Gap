"""
XAI Explainer Service.

Applies SHAP to surrogate model and generates:
- Global explanations (summary plots, dependence plots)
- Local explanations for specific candidate-role-skill triples
- Natural language explanations
"""
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shap

logger = logging.getLogger(__name__)


class XAIExplainer:
    """SHAP-based explainer for missing skill rankings."""
    
    def __init__(self, model_path: str = "xai/output/xai_surrogate.pkl"):
        """
        Initialize explainer with trained surrogate model.
        
        Args:
            model_path: Path to saved model pickle file
        """
        self.model_path = model_path
        self.model = None
        self.feature_names = None
        self.explainer = None
        
        self._load_model()
        logger.info("XAI Explainer initialized")
    
    def _load_model(self):
        """Load trained surrogate model."""
        with open(self.model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        
        logger.info(f"Loaded model from {self.model_path}")
        logger.info(f"Features: {len(self.feature_names)}")
    
    def initialize_shap(self, X_background: np.ndarray):
        """
        Initialize SHAP explainer with background dataset.
        
        Args:
            X_background: Representative sample for TreeExplainer background
        """
        logger.info(f"Initializing SHAP TreeExplainer with {len(X_background)} background samples")
        
        # Fix XGBoost 1.6+ base_score format compatibility with SHAP
        # XGBoost now returns base_score as '[value]' instead of 'value'
        try:
            import xgboost as xgb
            if isinstance(self.model, xgb.XGBRegressor):
                booster = self.model.get_booster()
                config = booster.save_config()
                import json
                config_dict = json.loads(config)
                base_score_str = config_dict['learner']['learner_model_param']['base_score']
                
                # Check if base_score is in array format '[value]'
                if base_score_str.startswith('[') and base_score_str.endswith(']'):
                    # Extract the numeric value
                    base_score_float = float(base_score_str.strip('[]'))
                    logger.info(f"Fixed base_score format: {base_score_str} → {base_score_float}")
                    
                    # Update the model's base_score in config
                    config_dict['learner']['learner_model_param']['base_score'] = str(base_score_float)
                    
                    # Create a new booster with fixed config
                    booster.load_config(json.dumps(config_dict))
                    
                    # IMPORTANT: Pass the booster instead of the model to SHAP
                    model_for_shap = booster
                else:
                    model_for_shap = self.model
            else:
                model_for_shap = self.model
        except Exception as e:
            logger.warning(f"Could not apply base_score fix: {e}")
            model_for_shap = self.model
        
        # Use TreeExplainer with potentially fixed model
        self.explainer = shap.TreeExplainer(model_for_shap, X_background)
        logger.info("SHAP explainer ready")
    
    def generate_global_explanations(
        self,
        X: np.ndarray,
        y: np.ndarray,
        output_dir: str = "xai/output"
    ):
        """
        Generate global SHAP explanations and plots.
        
        Creates:
        - Summary plot (bar + beeswarm)
        - Dependence plots for key features
        
        Args:
            X: Feature matrix for dataset
            y: True labels
            output_dir: Directory for output plots
        """
        logger.info(f"Generating global explanations for {len(X)} samples")
        
        # Compute SHAP values
        shap_values = self.explainer.shap_values(X)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 1. Summary plot (feature importance)
        logger.info("Generating summary plot...")
        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            shap_values,
            X,
            feature_names=self.feature_names,
            max_display=20,
            show=False
        )
        plt.tight_layout()
        plt.savefig(output_path / "shap_summary.png", dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved: {output_path / 'shap_summary.png'}")
        
        # 2. Summary plot (bar chart)
        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            shap_values,
            X,
            feature_names=self.feature_names,
            plot_type='bar',
            max_display=20,
            show=False
        )
        plt.tight_layout()
        plt.savefig(output_path / "shap_summary_bar.png", dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"Saved: {output_path / 'shap_summary_bar.png'}")
        
        # 3. Dependence plot: importance
        if 'importance' in self.feature_names:
            logger.info("Generating dependence plot for 'importance'...")
            importance_idx = self.feature_names.index('importance')
            
            plt.figure(figsize=(10, 6))
            shap.dependence_plot(
                importance_idx,
                shap_values,
                X,
                feature_names=self.feature_names,
                show=False
            )
            plt.title('SHAP Dependence: Importance', fontsize=14, fontweight='bold')
            plt.tight_layout()
            plt.savefig(output_path / "shap_dependence_importance.png", dpi=300, bbox_inches='tight')
            plt.close()
            logger.info(f"Saved: {output_path / 'shap_dependence_importance.png'}")
        
        # 4. Dependence plot: P_gnn
        if 'P_gnn' in self.feature_names:
            logger.info("Generating dependence plot for 'P_gnn'...")
            pgnn_idx = self.feature_names.index('P_gnn')
            
            plt.figure(figsize=(10, 6))
            shap.dependence_plot(
                pgnn_idx,
                shap_values,
                X,
                feature_names=self.feature_names,
                show=False
            )
            plt.title('SHAP Dependence: P_gnn (GNN Prediction)', fontsize=14, fontweight='bold')
            plt.tight_layout()
            plt.savefig(output_path / "shap_dependence_pgnn.png", dpi=300, bbox_inches='tight')
            plt.close()
            logger.info(f"Saved: {output_path / 'shap_dependence_pgnn.png'}")
        
        # 5. Dependence plot: P_has
        if 'P_has' in self.feature_names:
            logger.info("Generating dependence plot for 'P_has'...")
            phas_idx = self.feature_names.index('P_has')
            
            plt.figure(figsize=(10, 6))
            shap.dependence_plot(
                phas_idx,
                shap_values,
                X,
                feature_names=self.feature_names,
                show=False
            )
            plt.title('SHAP Dependence: P_has (Current Proficiency)', fontsize=14, fontweight='bold')
            plt.tight_layout()
            plt.savefig(output_path / "shap_dependence_phas.png", dpi=300, bbox_inches='tight')
            plt.close()
            logger.info(f"Saved: {output_path / 'shap_dependence_phas.png'}")
        
        logger.info("Global explanations complete")
    
    def generate_local_explanation(
        self,
        candidate_id: str,
        role_key: str,
        df: pd.DataFrame,
        top_k: int = 5,
        output_dir: str = "xai/output"
    ):
        """
        Generate local SHAP explanation for one candidate-role pair.
        
        Creates waterfall plots for top-K ranked skills.
        
        Args:
            candidate_id: Candidate identifier
            role_key: Role identifier
            df: Full dataset with features
            top_k: Number of top skills to explain
            output_dir: Directory for output plots
        """
        logger.info(f"Generating local explanation for {candidate_id}/{role_key}")
        
        # Filter to this candidate-role pair
        mask = (df['candidate_id'] == candidate_id) & (df['role_key'] == role_key)
        df_pair = df[mask].copy()
        
        if len(df_pair) == 0:
            logger.warning(f"No data found for {candidate_id}/{role_key}")
            return
        
        # Sort by final_score (top ranked skills)
        df_pair = df_pair.sort_values('final_score', ascending=False).head(top_k)
        
        # Prepare features
        X_pair, _, _ = self._prepare_features(df_pair)
        
        # Compute SHAP values
        shap_values = self.explainer.shap_values(X_pair)
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate waterfall plot for each skill
        fig, axes = plt.subplots(top_k, 1, figsize=(12, 4*top_k))
        if top_k == 1:
            axes = [axes]
        
        for idx, (row_idx, row) in enumerate(df_pair.iterrows()):
            ax = axes[idx]
            
            # Create SHAP explanation object
            explanation = shap.Explanation(
                values=shap_values[idx],
                base_values=self.explainer.expected_value,
                data=X_pair[idx],
                feature_names=self.feature_names
            )
            
            # Waterfall plot
            plt.sca(ax)
            shap.plots.waterfall(explanation, max_display=10, show=False)
            ax.set_title(
                f"Rank {idx+1}: {row['skill']} (score={row['final_score']:.4f})",
                fontsize=12,
                fontweight='bold'
            )
        
        plt.tight_layout()
        output_file = output_path / f"shap_local_{candidate_id}_{role_key}.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Saved local explanation: {output_file}")
    
    def explain_skill(
        self,
        candidate_id: str,
        role_key: str,
        skill: str,
        df: pd.DataFrame
    ) -> Dict:
        """
        Generate explanation for specific candidate-role-skill triple.
        
        Returns dict with:
        - skill, final_score
        - top_factors: List of top SHAP contributors with meanings
        - explanation_text: Natural language summary
        
        Args:
            candidate_id: Candidate identifier
            role_key: Role identifier
            skill: Skill name
            df: Full dataset
            
        Returns:
            Explanation dict
        """
        # Find row
        mask = (
            (df['candidate_id'] == candidate_id) &
            (df['role_key'] == role_key) &
            (df['skill'] == skill)
        )
        
        if not mask.any():
            return {
                'error': f'No data for {candidate_id}/{role_key}/{skill}'
            }
        
        row = df[mask].iloc[0]
        
        # Prepare features
        X, _, _ = self._prepare_features(df[mask])
        
        # Compute SHAP values
        shap_values = self.explainer.shap_values(X)[0]
        
        # Get top positive contributors
        feature_impacts = list(zip(self.feature_names, shap_values))
        feature_impacts.sort(key=lambda x: abs(x[1]), reverse=True)
        
        top_factors = []
        for feat_name, shap_val in feature_impacts[:5]:
            if abs(shap_val) < 0.001:  # Skip negligible
                continue
            
            meaning = self._generate_meaning(
                feat_name,
                shap_val,
                row[feat_name] if feat_name in row else None
            )
            
            top_factors.append({
                'feature': feat_name,
                'shap': float(shap_val),
                'value': float(row[feat_name]) if feat_name in row else None,
                'meaning': meaning
            })
        
        # Generate natural language explanation
        explanation_text = self._generate_explanation_text(top_factors, row)
        
        return {
            'candidate_id': candidate_id,
            'role_key': role_key,
            'skill': skill,
            'final_score': float(row['final_score']),
            'top_factors': top_factors,
            'explanation_text': explanation_text
        }
    
    def _prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, list]:
        """Prepare feature matrix (same as trainer)."""
        feature_cols = [
            'P_has', 'importance', 'P_gnn', 'gap_magnitude',
            'category_coverage', 'project_support', 'neighbor_overlap',
            'skill_popularity', 'num_candidate_skills',
            'num_candidate_projects', 'num_candidate_categories'
        ]
        
        df_encoded = df.copy()
        df_encoded = pd.get_dummies(df_encoded, columns=['category'], prefix='category')
        
        category_cols = [col for col in df_encoded.columns if col.startswith('category_')]
        feature_cols_final = feature_cols + category_cols
        
        # Ensure all features are numeric (float64) for SHAP compatibility
        X = df_encoded[feature_cols_final].astype('float64').values
        y = df_encoded['final_score'].astype('float64').values
        
        return X, y, feature_cols_final
    
    def _generate_meaning(self, feature_name: str, shap_value: float, feature_value: Optional[float]) -> str:
        """Generate human-readable meaning for feature contribution."""
        direction = "increases" if shap_value > 0 else "decreases"
        
        # Feature-specific templates
        if feature_name == 'importance':
            if shap_value > 0:
                return "This skill is critical for the role (high TF-IDF importance)"
            else:
                return "This skill is less critical for the role"
        
        elif feature_name == 'P_has':
            if shap_value > 0:
                # Higher P_has means lower gap, but could still increase score if other factors dominate
                return f"Current proficiency level ({feature_value:.2f}) influences ranking"
            else:
                return "You currently lack this skill (low proficiency)"
        
        elif feature_name == 'P_gnn':
            if shap_value > 0:
                return f"Strong graph alignment ({feature_value:.2f}) - GNN predicts high learning potential"
            else:
                return "Lower graph-based learning potential"
        
        elif feature_name == 'gap_magnitude':
            if shap_value > 0:
                return f"Large skill gap ({feature_value:.2f}) - significant learning needed"
            else:
                return "Smaller skill gap"
        
        elif feature_name == 'category_coverage':
            if shap_value > 0:
                return f"Good coverage in skill category ({feature_value:.1%})"
            else:
                return f"Low category coverage ({feature_value:.1%}) - unfamiliar domain"
        
        elif feature_name == 'project_support':
            if shap_value > 0:
                return f"Project experience in related category ({int(feature_value)} projects)"
            else:
                return "Limited project evidence in this category"
        
        elif feature_name == 'neighbor_overlap':
            if shap_value > 0:
                return f"Your existing skills are highly related ({feature_value:.1%} overlap)"
            else:
                return "Limited skill overlap with your profile"
        
        elif feature_name == 'skill_popularity':
            if shap_value > 0:
                return f"Popular skill ({int(feature_value)} mentions) - widely adopted"
            else:
                return "Niche skill with limited adoption"
        
        elif feature_name.startswith('category_'):
            category_name = feature_name.replace('category_', '').replace('_', ' ').title()
            if shap_value > 0:
                return f"Skill belongs to {category_name} category (positive signal)"
            else:
                return f"Category effect ({category_name})"
        
        else:
            return f"Feature {feature_name} {direction} score by {abs(shap_value):.3f}"
    
    def _generate_explanation_text(self, top_factors: List[Dict], row: pd.Series) -> str:
        """Generate natural language explanation from top factors."""
        if not top_factors:
            return "No significant factors identified."
        
        parts = []
        
        # Introduction
        parts.append(f"This skill ranks with a score of {row['final_score']:.3f}.")
        
        # Top factor
        top = top_factors[0]
        parts.append(f"Primary driver: {top['meaning']} (SHAP contribution: {top['shap']:+.3f}).")
        
        # Secondary factors
        if len(top_factors) > 1:
            secondary = [f['meaning'].lower() for f in top_factors[1:3]]
            parts.append(f"Additional factors: {'; '.join(secondary)}.")
        
        return " ".join(parts)
