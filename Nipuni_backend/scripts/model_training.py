import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from math import exp
import pickle
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression
import xgboost as xgb
import lightgbm as lgb
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt

# Add parent directory to path for imports
backend_src_path = Path(__file__).parent.parent / 'src'
sys.path.append(str(backend_src_path))

# Change working directory to src so database path resolves correctly
os.chdir(str(backend_src_path))

# Constants (matching skill_scoring.py)
GRADE_MAPPING = {
    "A+": 4.0, "A": 4.0, "A-": 3.7,
    "B+": 3.3, "B": 3.0, "B-": 2.7,
    "C+": 2.3, "C": 2.0, "C-": 1.7,
    "D+": 1.3, "D": 1.0, "F": 0.0,
}
RECENCY_DECAY = 0.4
CONFIDENCE_FACTOR = 0.25
CURRENT_ACADEMIC_YEAR = 4

def calculate_recency(academic_year: int) -> float:
    """Calculate recency factor based on academic year."""
    years_since = max(0, CURRENT_ACADEMIC_YEAR - academic_year)
    return exp(-RECENCY_DECAY * years_since)

def get_grade_points(grade: str) -> float:
    """Convert grade to GPA points."""
    grade_upper = grade.strip().upper()
    return GRADE_MAPPING.get(grade_upper, 0.0)

def calculate_skill_score(contributions: list, evidences: list) -> float:
    """Calculate skill score from contributions and evidence weights."""
    total_contribution = sum(contributions)
    total_evidence = sum(evidences)
    
    if total_evidence == 0:
        return 0.0
    
    return (total_contribution / total_evidence) * 100

def extract_training_data():
    """
    Extract training data from CSV file and calculate required features (skill_score).
    
    Returns:
        DataFrame with features and target skill scores
    """
    csv_file_path = Path(r'D:\OneDrive\OneDrive - Sri Lanka Institute of Information Technology\Research\Transcript-Based-Skill-Validation-Quiz\Transcript-Based-Skill-Validation-Quiz\backend\data\transcript_data.csv')

    if not csv_file_path.exists():
        print(f"❌ CSV file not found at: {csv_file_path.absolute()}")
        return pd.DataFrame()
    
    # Load data from CSV with a specified encoding
    print(f"📊 Extracting data from CSV file: {csv_file_path}")
    try:
        df = pd.read_csv(csv_file_path, encoding='ISO-8859-1')  # Use ISO-8859-1 encoding
    except Exception as e:
        print(f"❌ Error loading CSV file: {e}")
        return pd.DataFrame()
    
    if df.empty:
        print("❌ CSV file is empty.")
        return pd.DataFrame()
    
    print(f"✅ Extracted {len(df)} records from the CSV file")
    
    # Ensure that the columns are named correctly
    expected_columns = ['Name', 'RegNo', 'Program', 'Specialization', 'Medium', 'Admission', 
                        'Y1_Code1', 'Y1_Title1', 'Y1_Grade1', 'Y1_Code2', 'Y1_Title2', 'Y1_Grade2', 
                        'Y1_Code3', 'Y1_Title3', 'Y1_Grade3', 'Y1_Code4', 'Y1_Title4', 'Y1_Grade4', 
                        'Y1_Code5', 'Y1_Title5', 'Y1_Grade5', 'Y1_Code6', 'Y1_Title6', 'Y1_Grade6', 
                        'Y1_Code7', 'Y1_Title7', 'Y1_Grade7', 'Y1_Code8', 'Y1_Title8', 'Y1_Grade8', 
                        'Y1_Code9', 'Y1_Title9', 'Y1_Grade9', 'Y1_GPA', 'Y1_Credits']
    
    if not all(col in df.columns for col in expected_columns):
        print(f"❌ Missing required columns in the CSV. Expected columns: {expected_columns}")
        return pd.DataFrame()

    # Process each row of the CSV
    records = []
    for _, row in df.iterrows():
        skills = ['Skill_X', 'Skill_Y', 'Skill_Z']  # Example skills
        map_weights = [0.2, 0.3, 0.5]  # Example weights
        
        for i in range(1, 10):  # Iterating through Year 1 courses
            course_code = row[f'Y1_Code{i}']
            grade = row[f'Y1_Grade{i}']
            if pd.isna(course_code) or pd.isna(grade):
                continue

            grade_points = get_grade_points(grade)
            grade_normalized = grade_points / 4.0  # Normalize GPA to 0-1 scale
            recency = calculate_recency(1)  # Assuming year 1 courses

            credits = row['Y1_Credits'] if pd.notna(row['Y1_Credits']) else 3.0  # Default to 3 credits if missing

            for skill, map_weight in zip(skills, map_weights):
                evidence_weight = map_weight * credits * recency
                contribution = grade_normalized * evidence_weight
                
                # Store the record
                record = {
                    'student_id': row['RegNo'],
                    'course_code': course_code,
                    'skill_name': skill,
                    'grade_normalized': grade_normalized,
                    'credits': credits,
                    'recency': recency,
                    'map_weight': map_weight,
                    'evidence_weight': evidence_weight,
                    'contribution': contribution,
                }
                
                records.append(record)

    df_new = pd.DataFrame(records)
    
    # Aggregate contributions to calculate final skill score per student-skill
    print("\n📈 Calculating aggregated skill scores...")
    skill_scores = []
    
    for (student_id, skill_name), group in df_new.groupby(['student_id', 'skill_name']):
        contributions = group['contribution'].tolist()
        evidences = group['evidence_weight'].tolist()
        
        skill_score = calculate_skill_score(contributions, evidences)
        
        for idx in group.index:
            skill_scores.append({
                'index': idx,
                'skill_score': skill_score
            })
    
    scores_df = pd.DataFrame(skill_scores).set_index('index')
    df_new = df_new.join(scores_df)
    
    print(f"✅ Extracted {len(df_new)} training records")
    print(f"✅ Covering {df_new['skill_name'].nunique()} unique skills")
    print(f"✅ From {df_new['student_id'].nunique()} students")
    
    return df_new

# Prepare features for model training
def prepare_features(df: pd.DataFrame):
    print("\n🔧 Preparing features...")
    
    feature_cols = ['grade_normalized', 'credits', 'recency', 'map_weight']
    
    X = df[feature_cols].values
    y = df['skill_score'].values
    
    print(f"Feature matrix shape: {X.shape}")
    print(f"Target vector shape: {y.shape}")
    
    return X, y, feature_cols

# Train different models and evaluate their performance
def train_and_evaluate_models(X_train, y_train, X_test, y_test):
    # List of models to test
    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, max_depth=10, random_state=42),
        "Support Vector Regressor": SVR(kernel='rbf', C=1, epsilon=0.1),
        "XGBoost": xgb.XGBRegressor(n_estimators=100, max_depth=10, learning_rate=0.1, random_state=42),
        "LightGBM": lgb.LGBMRegressor(n_estimators=100, max_depth=10, learning_rate=0.1, random_state=42)
    }
    
    results = {}
    
    for name, model in models.items():
        print(f"\n🌲 Training {name}...")
        model.fit(X_train, y_train)
        
        # Predictions
        y_train_pred = model.predict(X_train)
        y_test_pred = model.predict(X_test)
        
        # Evaluate the model
        train_mse = mean_squared_error(y_train, y_train_pred)
        test_mse = mean_squared_error(y_test, y_test_pred)
        
        results[name] = {
            "train_mse": train_mse,
            "test_mse": test_mse,
            "train_r2": r2_score(y_train, y_train_pred),
            "test_r2": r2_score(y_test, y_test_pred)
        }
    
    return results

# Run the training and evaluation
def main():
    print("="*60)
    print("  SKILL SCORE PREDICTION MODEL TRAINING")
    print("  Multiple Model Comparison")
    print("="*60)

    # Step 1: Extract data
    df = extract_training_data()

    if df.empty:
        print("\n❌ No training data available.")
        print("\n" + "="*60)
        return

    # Step 2: Prepare features
    X, y, feature_names = prepare_features(df)

    # Step 3: Split dataset
    print("\n📊 Splitting dataset (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"Training set: {X_train.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")

    # Step 4: Train and evaluate models
    results = train_and_evaluate_models(X_train, y_train, X_test, y_test)

    # Display the results
    print("\n" + "="*60)
    for model_name, metrics in results.items():
        print(f"{model_name}:")
        print(f"  Train MSE: {metrics['train_mse']:.2f}")
        print(f"  Test MSE: {metrics['test_mse']:.2f}")
        print(f"  Train R²: {metrics['train_r2']:.4f}")
        print(f"  Test R²: {metrics['test_r2']:.4f}")
        print("="*60)

    # Optionally, save the best model
    best_model_name = min(results, key=lambda model: results[model]["test_mse"])
    print(f"\nBest Model: {best_model_name} with Test MSE: {results[best_model_name]['test_mse']:.2f}")

if __name__ == "__main__":
    main()
