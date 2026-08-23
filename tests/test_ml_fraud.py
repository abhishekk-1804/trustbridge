import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import numpy as np
from engine.ml_fraud import (
    train_isolation_forest,
    load_model,
    predict_anomaly,
    predict_batch,
    score_all_transactions,
    evaluate_model,
    compare_rule_vs_ml,
    explain_anomaly,
    MODEL_PATH,
    SCALER_PATH,
    FEATURE_COLS_PATH
)
from database.db import get_session_direct, reset_db, init_db
from database.models import User, Account, Transaction, UserRole, TransactionType, TransactionStatus, PaymentMethod
from datetime import datetime, timedelta
import os


@pytest.fixture(scope="function")
def db_session():
    reset_db()
    init_db()
    session = get_session_direct()
    yield session
    session.close()
    reset_db()


@pytest.fixture(scope="module")
def trained_model():
    reset_db()
    init_db()
    from data.generator import generate_synthetic_data
    generate_synthetic_data()
    
    result = train_isolation_forest(contamination=0.01, n_estimators=50, random_state=42)
    
    yield result
    
    reset_db()


def test_train_isolation_forest_creates_model(trained_model):
    assert os.path.exists(MODEL_PATH)
    assert os.path.exists(SCALER_PATH)
    assert os.path.exists(FEATURE_COLS_PATH)
    
    assert trained_model["n_samples"] > 0
    assert trained_model["n_features"] > 0
    assert trained_model["predicted_anomalies"] >= 0


def test_load_model(trained_model):
    model, scaler, feature_cols = load_model()
    
    assert model is not None
    assert scaler is not None
    assert len(feature_cols) > 0


def test_predict_anomaly(trained_model):
    from engine.ml_features import extract_transaction_features, build_categorical_mappings
    from database.models import Transaction
    
    session = get_session_direct()
    try:
        txn = session.query(Transaction).filter(Transaction.transaction_type == "DEBIT").first()
        
        mappings = build_categorical_mappings(session)
        features = extract_transaction_features(txn, session, mappings)
        
        result = predict_anomaly(features)
        
        assert "anomaly_score" in result
        assert "is_anomaly" in result
        assert "risk_level" in result
        assert isinstance(result["anomaly_score"], float)
        assert isinstance(result["is_anomaly"], bool)
        assert result["risk_level"] in ["HIGH", "LOW"]
    finally:
        session.close()


def test_predict_batch(trained_model):
    from engine.ml_features import extract_transaction_features, build_categorical_mappings
    from database.models import Transaction
    
    session = get_session_direct()
    try:
        txns = session.query(Transaction).filter(Transaction.transaction_type == "DEBIT").limit(5).all()
        
        mappings = build_categorical_mappings(session)
        features_list = []
        for txn in txns:
            features = extract_transaction_features(txn, session, mappings)
            features_list.append(features)
        
        results = predict_batch(features_list)
        
        assert len(results) == 5
        for r in results:
            assert "transaction_id" in r
            assert "anomaly_score" in r
            assert "is_anomaly" in r
            assert "risk_level" in r
    finally:
        session.close()


def test_score_all_transactions(trained_model):
    results = score_all_transactions()
    
    assert len(results) > 0
    for r in results:
        assert "transaction_id" in r
        assert "anomaly_score" in r
        assert "is_anomaly" in r
        assert "risk_level" in r
        assert "ground_truth_anomaly" in r
        assert "ground_truth_type" in r


def test_evaluate_model(trained_model):
    eval_result = evaluate_model()
    
    assert "precision" in eval_result
    assert "recall" in eval_result
    assert "f1" in eval_result
    assert "confusion_matrix" in eval_result
    assert "total_transactions" in eval_result
    assert "true_anomalies" in eval_result
    assert "predicted_anomalies" in eval_result
    assert "anomalies_detected" in eval_result
    assert "false_positives" in eval_result
    assert "false_negatives" in eval_result
    assert "anomaly_score_stats" in eval_result
    
    assert 0 <= eval_result["precision"] <= 1
    assert 0 <= eval_result["recall"] <= 1
    assert 0 <= eval_result["f1"] <= 1
    assert eval_result["total_transactions"] > 0


def test_compare_rule_vs_ml(trained_model):
    comparison = compare_rule_vs_ml()
    
    assert "comparison" in comparison
    assert "counts" in comparison
    assert "total_analyzed" in comparison
    
    comp = comparison["comparison"]
    counts = comparison["counts"]
    
    assert "both" in comp
    assert "rule_only" in comp
    assert "ml_only" in comp
    assert "neither" in comp
    
    total = sum(counts.values())
    assert total == comparison["total_analyzed"]


def test_explain_anomaly(trained_model):
    session = get_session_direct()
    try:
        from database.models import Transaction
        anomaly_txn = session.query(Transaction).filter(Transaction.is_anomaly == True).first()
        
        if anomaly_txn:
            explanation = explain_anomaly(anomaly_txn.id)
            
            assert "transaction_id" in explanation
            assert "anomaly_score" in explanation
            assert "is_anomaly" in explanation
            assert "risk_level" in explanation
            assert "contributing_indicators" in explanation
            assert "feature_values" in explanation
            
            assert isinstance(explanation["contributing_indicators"], list)
            assert len(explanation["feature_values"]) > 0
    finally:
        session.close()


def test_model_reproducibility():
    reset_db()
    init_db()
    from data.generator import generate_synthetic_data
    generate_synthetic_data()
    
    result1 = train_isolation_forest(contamination=0.01, n_estimators=50, random_state=42)
    
    reset_db()
    init_db()
    generate_synthetic_data()
    
    result2 = train_isolation_forest(contamination=0.01, n_estimators=50, random_state=42)
    
    assert result1["n_samples"] == result2["n_samples"]
    assert result1["n_features"] == result2["n_features"]
    assert result1["predicted_anomalies"] == result2["predicted_anomalies"]


def test_anomaly_detection_on_known_spike(trained_model):
    session = get_session_direct()
    try:
        from database.models import Transaction
        anomaly_txn = session.query(Transaction).filter(Transaction.is_anomaly == True, Transaction.transaction_type == "DEBIT").first()
        
        if anomaly_txn:
            from engine.ml_features import extract_transaction_features, build_categorical_mappings
            mappings = build_categorical_mappings(session)
            features = extract_transaction_features(anomaly_txn, session, mappings)
            
            result = predict_anomaly(features)
            
            assert result["anomaly_score"] < 0
    finally:
        session.close()