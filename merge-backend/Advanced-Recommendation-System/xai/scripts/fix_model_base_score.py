"""
Fix XGBoost Base Score Format for SHAP Compatibility.

XGBoost 1.6+ saves base_score as '[value]' instead of 'value', which causes issues
with older SHAP versions. This script fixes the saved model.

Usage:
    python -m xai.scripts.fix_model_base_score
"""
import pickle
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_model_base_score(model_path: str = "xai/output/xai_surrogate.pkl"):
    """Fix base_score format in saved XGBoost model."""
    
    logger.info(f"Loading model from {model_path}")
    
    # Load model
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data['model']
    
    # Get booster and config
    booster = model.get_booster()
    config = booster.save_config()
    config_dict = json.loads(config)
    
    # Check base_score format
    base_score_str = config_dict['learner']['learner_model_param']['base_score']
    logger.info(f"Current base_score: {base_score_str}")
    
    # Fix if in array format
    if base_score_str.startswith('[') and base_score_str.endswith(']'):
        base_score_float = float(base_score_str.strip('[]'))
        logger.info(f"Fixing base_score: {base_score_str} → {base_score_float}")
        
        # Update config
        config_dict['learner']['learner_model_param']['base_score'] = str(base_score_float)
        booster.load_config(json.dumps(config_dict))
        
        # Verify fix
        new_config = booster.save_config()
        new_config_dict = json.loads(new_config)
        new_base_score = new_config_dict['learner']['learner_model_param']['base_score']
        logger.info(f"New base_score: {new_base_score}")
        
        # Save fixed model
        backup_path = model_path + ".backup"
        logger.info(f"Backing up original to {backup_path}")
        
        import shutil
        shutil.copy2(model_path, backup_path)
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"✅ Fixed model saved to {model_path}")
        logger.info(f"Original model backed up to {backup_path}")
    else:
        logger.info("✅ base_score is already in correct format, no fix needed")


if __name__ == "__main__":
    fix_model_base_score()
