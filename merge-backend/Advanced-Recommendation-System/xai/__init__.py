"""
XAI Module for Missing Skill Ranking Explanations.

Provides surrogate model + SHAP-based explanations for the decision function:
    final_score(p,s,r) = (1 - P_has) × importance × P_gnn

Components:
- Dataset builder: Creates explanation dataset from system outputs
- Surrogate trainer: Trains interpretable model mimicking the decision function
- SHAP explainer: Generates local/global explanations with visualizations
- API routes: FastAPI endpoints for explanation serving
"""

__version__ = "1.0.0"
__author__ = "CV Parser Agent Team"

from .services.xai_dataset_builder import XAIDatasetBuilder
from .services.xai_surrogate_trainer import XAISurrogateTrainer
from .services.xai_explainer import XAIExplainer

__all__ = [
    'XAIDatasetBuilder',
    'XAISurrogateTrainer',
    'XAIExplainer'
]
