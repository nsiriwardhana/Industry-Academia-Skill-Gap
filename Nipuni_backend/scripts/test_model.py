"""
Quick Model Testing Script
==========================

Test the trained Random Forest model with sample data.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
backend_src_path = Path(__file__).parent.parent / 'src'
sys.path.append(str(backend_src_path))

import pickle
import numpy as np

# Model path
MODEL_PATH = Path(__file__).parent.parent / 'models' / 'skill_score_model.pkl'


def load_model():
    """Load the trained model."""
    if not MODEL_PATH.exists():
        print(f"❌ Model not found at {MODEL_PATH}")
        print("Run model_training.py first to train the model.")
        return None
    
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    
    print(f"✅ Model loaded from {MODEL_PATH}")
    return model


def test_predictions():
    """Test model with sample data."""
    model = load_model()
    
    if model is None:
        return
    
    print("\n" + "="*60)
    print("TESTING MODEL WITH SAMPLE DATA")
    print("="*60)
    
    # Sample test cases
    test_cases = [
        {
            'description': 'Excellent student, recent course, high mapping',
            'features': [0.95, 3.0, 0.90, 0.40],  # grade, credits, recency, map_weight
            'expected': '~90-95'
        },
        {
            'description': 'Average student, moderate recency',
            'features': [0.75, 3.0, 0.60, 0.30],
            'expected': '~70-75'
        },
        {
            'description': 'Good student, old course (less recent)',
            'features': [0.85, 3.0, 0.30, 0.35],
            'expected': '~65-75'
        },
        {
            'description': 'Poor performance, low mapping weight',
            'features': [0.50, 3.0, 0.60, 0.15],
            'expected': '~40-50'
        },
        {
            'description': 'High credits course with excellent grade',
            'features': [1.00, 4.0, 0.85, 0.50],
            'expected': '~95-100'
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['description']}")
        print(f"   Features: {test['features']}")
        print(f"   (grade_norm={test['features'][0]}, credits={test['features'][1]}, "
              f"recency={test['features'][2]}, map_weight={test['features'][3]})")
        
        X = np.array([test['features']])
        prediction = model.predict(X)[0]
        
        print(f"   Expected Range: {test['expected']}")
        print(f"   Predicted Score: {prediction:.2f}")
    
    print("\n" + "="*60)
    
    # Batch prediction example
    print("\n📊 BATCH PREDICTION EXAMPLE")
    print("="*60)
    
    batch_data = np.array([
        [0.85, 3.0, 0.70, 0.35],
        [0.90, 3.0, 0.65, 0.40],
        [0.80, 3.0, 0.50, 0.30],
    ])
    
    predictions = model.predict(batch_data)
    
    print("Batch input (3 students):")
    for i, row in enumerate(batch_data, 1):
        print(f"  Student {i}: grade={row[0]:.2f}, credits={row[1]}, "
              f"recency={row[2]:.2f}, weight={row[3]:.2f}")
    
    print("\nPredictions:")
    for i, pred in enumerate(predictions, 1):
        print(f"  Student {i}: {pred:.2f}/100")
    
    print("="*60)


def interactive_test():
    """Interactive prediction mode."""
    model = load_model()
    
    if model is None:
        return
    
    print("\n" + "="*60)
    print("INTERACTIVE PREDICTION MODE")
    print("="*60)
    print("Enter feature values to get skill score prediction")
    print("(Enter 'q' to quit)\n")
    
    while True:
        try:
            print("\nEnter values:")
            grade = input("  Grade (0-4.0 GPA): ")
            if grade.lower() == 'q':
                break
            
            credits = input("  Credits (2-4): ")
            if credits.lower() == 'q':
                break
            
            recency = input("  Recency (0-1): ")
            if recency.lower() == 'q':
                break
            
            map_weight = input("  Map Weight (0-1): ")
            if map_weight.lower() == 'q':
                break
            
            # Convert to features
            grade_norm = float(grade) / 4.0
            X = np.array([[
                grade_norm,
                float(credits),
                float(recency),
                float(map_weight)
            ]])
            
            # Predict
            prediction = model.predict(X)[0]
            
            print(f"\n🎯 Predicted Skill Score: {prediction:.2f}/100")
            
            # Classify level
            if prediction >= 75:
                level = "Advanced"
            elif prediction >= 50:
                level = "Intermediate"
            else:
                level = "Beginner"
            
            print(f"   Skill Level: {level}")
            
        except ValueError as e:
            print(f"❌ Invalid input: {e}")
        except KeyboardInterrupt:
            break
    
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        interactive_test()
    else:
        test_predictions()
        print("\n💡 Tip: Run with --interactive flag for interactive mode")
        print("   python test_model.py --interactive")
