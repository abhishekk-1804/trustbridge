#!/usr/bin/env python3
"""
TrustBridge External Fraud Benchmark Runner

Evaluates Isolation Forest on the Kaggle Credit Card Fraud Detection dataset.
This is an ISOLATED benchmark - completely separate from the operational
TrustBridge ML pipeline.

Run from project root: D:\TrustBridge
$env:PYTHONPATH="D:\TrustBridge"
.venv\Scripts\python ml_benchmark/benchmark_runner.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
    roc_auc_score,
    confusion_matrix,
)


def main():
    # Configuration
    DATASET_PATH = Path("ml_benchmark/creditcard.csv")
    RESULTS_DIR = Path("ml_benchmark/results")
    RESULTS_FILE = RESULTS_DIR / "benchmark_results.json"
    RANDOM_STATE = 42
    TEST_SIZE = 0.3
    CONTAMINATION = "auto"  # Let sklearn estimate from data

    print("=" * 60)
    print("TrustBridge External Fraud Benchmark")
    print("Kaggle Credit Card Fraud Detection Dataset")
    print("=" * 60)
    print()

    # Check dataset exists
    if not DATASET_PATH.exists():
        print("ERROR: Dataset not found.")
        print(f"Expected: {DATASET_PATH.resolve()}")
        print()
        print("Please download the Kaggle Credit Card Fraud dataset from:")
        print("  https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud")
        print()
        print("Place 'creditcard.csv' in the ml_benchmark/ directory.")
        print()
        print("Benchmark skipped - dataset unavailable.")
        print("=" * 60)

        # Write a "dataset unavailable" marker result (not fabricated metrics)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        unavailable_result = {
            "dataset": "kaggle_creditcard_fraud",
            "dataset_path": str(DATASET_PATH),
            "status": "dataset_unavailable",
            "message": "creditcard.csv not found. Download from Kaggle to run benchmark.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        with open(RESULTS_FILE, "w") as f:
            json.dump(unavailable_result, f, indent=2)
        print(f"Status written to {RESULTS_FILE}")
        sys.exit(0)  # Clean exit, not an error

    print(f"Loading dataset: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {list(df.columns)}")
    print()

    # Validate required columns
    required_cols = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "Class"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"ERROR: Missing required columns: {missing}")
        sys.exit(1)

    # Check for missing/invalid values
    print("Checking data quality...")
    null_counts = df.isnull().sum().sum()
    if null_counts > 0:
        print(f"  WARNING: {null_counts} null values found - dropping rows")
        df = df.dropna()
    else:
        print("  No missing values")

    # Separate features and target
    X = df.drop(columns=["Class"])
    y = df["Class"].astype(int)

    print(f"  Total samples: {len(df)}")
    print(f"  Fraud samples: {y.sum()} ({y.mean()*100:.4f}%)")
    print(f"  Legitimate samples: {(y==0).sum()} ({(y==0).mean()*100:.4f}%)")
    print()

    # Train/test split - stratified to preserve class distribution
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Train size: {len(X_train)} (fraud: {y_train.sum()})")
    print(f"Test size:  {len(X_test)} (fraud: {y_test.sum()})")
    print()

    # Train Isolation Forest on training data only (no leakage)
    # Use only normal transactions for training? No - IF is unsupervised,
    # but we fit on all training data. This is standard for IF benchmarking.
    print("Training Isolation Forest...")
    model = IsolationForest(
        n_estimators=200,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train)

    # Predict on test set
    # IF returns -1 for anomalies, 1 for normal
    y_pred_raw = model.predict(X_test)
    y_pred = (y_pred_raw == -1).astype(int)  # 1 = predicted fraud, 0 = normal

    # Anomaly scores (lower = more anomalous)
    anomaly_scores = -model.decision_function(X_test)

    print("Evaluating...")
    print()

    # Calculate metrics
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    pr_auc = average_precision_score(y_test, anomaly_scores)
    roc_auc = roc_auc_score(y_test, anomaly_scores)
    cm = confusion_matrix(y_test, y_pred)

    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(f"PR-AUC:    {pr_auc:.4f}")
    print(f"ROC-AUC:   {roc_auc:.4f}")
    print()
    print("Confusion Matrix:")
    print(f"  TN: {cm[0,0]}  FP: {cm[0,1]}")
    print(f"  FN: {cm[1,0]}  TP: {cm[1,1]}")
    print()

    # Prepare results
    results = {
        "dataset": "kaggle_creditcard_fraud",
        "dataset_path": str(DATASET_PATH),
        "dataset_samples": int(len(df)),
        "fraud_samples": int(y.sum()),
        "fraud_prevalence": float(y.mean()),
        "model": "IsolationForest",
        "model_params": {
            "n_estimators": 200,
            "contamination": CONTAMINATION,
            "random_state": RANDOM_STATE,
        },
        "evaluation": {
            "test_size": TEST_SIZE,
            "train_samples": int(len(X_train)),
            "test_samples": int(len(X_test)),
            "test_fraud_samples": int(y_test.sum()),
            "random_state": RANDOM_STATE,
        },
        "metrics": {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "pr_auc": float(pr_auc),
            "roc_auc": float(roc_auc),
        },
        "confusion_matrix": {
            "tn": int(cm[0, 0]),
            "fp": int(cm[0, 1]),
            "fn": int(cm[1, 0]),
            "tp": int(cm[1, 1]),
        },
        "status": "completed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "note": "External benchmark on Kaggle PCA features (V1-V28). Not equivalent to TrustBridge production feature pipeline.",
    }

    # Write results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results written to: {RESULTS_FILE}")
    print("=" * 60)
    print("Benchmark completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()