# TrustBridge External Fraud Benchmark

This module provides an **isolated** evaluation of an Isolation Forest model
against the public **Kaggle Credit Card Fraud Detection dataset**.

## Purpose

- Independent external validation of anomaly detection capability
- Completely separate from the operational TrustBridge ML pipeline
- Uses publicly available benchmark data for transparency

## Dataset Requirements

The benchmark expects the Kaggle Credit Card Fraud dataset:

**File:** `ml_benchmark/creditcard.csv` (NOT bundled in git)

**Columns:**
- `Time` — seconds elapsed between transaction and first transaction
- `V1` ... `V28` — PCA-transformed features (anonymized)
- `Amount` — transaction amount
- `Class` — target label (0 = legitimate, 1 = fraud)

**Source:** https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

## Why This Is NOT a Production Substitute

| Aspect | Kaggle Benchmark | TrustBridge Production |
|--------|------------------|------------------------|
| Features | PCA-derived V1-V28 | 24 behavioural features from raw transactions |
| Data | 284,807 transactions (Sep 2013) | Synthetic demo data (399 transactions) |
| Labels | Real fraud labels | 2 injected anomalies |
| Purpose | External benchmark | Operational risk scoring |

The Kaggle dataset uses anonymized PCA features that have **no semantic
relationship** to TrustBridge's behavioural features (payment reliability,
transaction consistency, account behaviour). This benchmark evaluates
Isolation Forest on a *different feature representation* and *different
data distribution*. It does **not** validate production performance.

## Why PR-AUC / Precision / Recall / F1 > Accuracy

The Kaggle dataset is **extremely imbalanced**:
- ~284,315 legitimate (99.83%)
- ~492 fraud (0.17%)

A dummy model predicting "legitimate" for all transactions achieves
**99.83% accuracy** but detects **zero fraud**.

**Precision** — Of predicted frauds, how many are actually fraud?
**Recall** — Of actual frauds, how many did we catch?
**F1** — Harmonic mean of precision and recall.
**PR-AUC** — Area under the Precision-Recall curve; robust to class imbalance.
**ROC-AUC** — Area under the ROC curve; also informative but can be
optimistic on imbalanced data.

These metrics reflect real fraud detection utility; accuracy does not.

## Running the Benchmark

```bash
cd D:\TrustBridge
$env:PYTHONPATH="D:\TrustBridge"
.venv\Scripts\python ml_benchmark/benchmark_runner.py
```

If `creditcard.csv` is not present, the script exits with a clear message
and **does not generate fabricated results**.

## Output

On successful run with real data:

`ml_benchmark/results/benchmark_results.json`

Contains:
- dataset, dataset_samples, fraud_samples, fraud_prevalence
- model, precision, recall, f1, pr_auc, roc_auc
- confusion_matrix, random_state

## Git Safety

`ml_benchmark/creditcard.csv` and any downloaded archives are ignored
via `.gitignore`. No dataset or credentials are committed.