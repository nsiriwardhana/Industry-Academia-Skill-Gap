"""Simple analysis utilities for validation CSVs.

Computes:
- Question-level averages and % good (>=4)
- For answers: Pearson/Spearman correlation and MAE between human_score and system_score

Usage:
    python analyze.py

Outputs summary to stdout and writes `validation/summary.json` and `validation/answer_metrics.csv`.
"""
import os
import json
import sys
from pathlib import Path

try:
    import pandas as pd
    from scipy.stats import pearsonr, spearmanr
    from sklearn.metrics import mean_absolute_error
except Exception as e:
    print("Missing dependencies for analysis. Install pandas, scipy, scikit-learn.")
    raise


BASE = Path(__file__).resolve().parent
QPATH = BASE / "question_ratings.csv"
APATH = BASE / "answer_ratings.csv"


def analyze_questions():
    if not QPATH.exists():
        print("No question_ratings.csv found; skipping question analysis")
        return None

    df = pd.read_csv(QPATH)
    metrics = (
        df.groupby(["question_id", "question_text"]).agg(
            relevance_mean=("relevance", "mean"),
            clarity_mean=("clarity", "mean"),
            realism_mean=("realism", "mean"),
            n_ratings=("relevance", "count"),
        )
    )
    metrics["overall_mean"] = metrics[["relevance_mean", "clarity_mean", "realism_mean"]].mean(axis=1)
    metrics["pct_good"] = (metrics[["relevance_mean", "clarity_mean", "realism_mean"]] >= 4).mean(axis=1)

    out = metrics.reset_index()
    out.to_csv(BASE / "question_metrics.csv", index=False)
    return out


def analyze_answers():
    if not APATH.exists():
        print("No answer_ratings.csv found; skipping answer analysis")
        return None

    df = pd.read_csv(APATH)
    # Ensure numeric
    df = df.dropna(subset=["human_score", "system_score"]) 
    df["human_score"] = pd.to_numeric(df["human_score"], errors="coerce")
    df["system_score"] = pd.to_numeric(df["system_score"], errors="coerce")
    df = df.dropna(subset=["human_score", "system_score"]) 

    pearson = pearsonr(df["system_score"], df["human_score"]) if len(df) > 1 else (float("nan"), float("nan"))
    spearman = spearmanr(df["system_score"], df["human_score"]) if len(df) > 1 else (float("nan"), float("nan"))
    mae = mean_absolute_error(df["human_score"], df["system_score"]) if len(df) > 0 else float("nan")

    summary = {
        "n": len(df),
        "pearson_r": float(pearson[0]) if not pd.isna(pearson[0]) else None,
        "pearson_p": float(pearson[1]) if not pd.isna(pearson[1]) else None,
        "spearman_r": float(spearman[0]) if not pd.isna(spearman[0]) else None,
        "spearman_p": float(spearman[1]) if not pd.isna(spearman[1]) else None,
        "mae": float(mae),
    }

    df.to_csv(BASE / "answer_metrics.csv", index=False)
    return summary


def main():
    q = analyze_questions()
    a = analyze_answers()

    summary = {"questions": None, "answers": a}
    if q is not None:
        summary["questions"] = {
            "n_questions": int(q["question_id"].nunique()),
            "n_rows": len(q),
        }

    with open(BASE / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("Analysis complete. Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
