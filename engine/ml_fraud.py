import os
import joblib
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from engine.ml_features import build_ml_dataset, prepare_training_data, extract_transaction_features, build_categorical_mappings
from database.db import get_session_direct, init_db


MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "isolation_forest_model.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "feature_scaler.pkl")
FEATURE_COLS_PATH = os.path.join(MODEL_DIR, "feature_columns.pkl")

DEFAULT_CONTAMINATION = 0.01
DEFAULT_N_ESTIMATORS = 200
DEFAULT_RANDOM_STATE = 42


def ensure_model_dir():
    os.makedirs(MODEL_DIR, exist_ok=True)


def train_isolation_forest(
    contamination: float = DEFAULT_CONTAMINATION,
    n_estimators: int = DEFAULT_N_ESTIMATORS,
    random_state: int = DEFAULT_RANDOM_STATE,
    max_samples: str = "auto"
) -> Dict[str, Any]:
    ensure_model_dir()
    init_db()
    
    session = get_session_direct()
    try:
        df = build_ml_dataset(session)
    finally:
        session.close()
    
    X, y, feature_cols = prepare_training_data(df)
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = IsolationForest(
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=random_state,
        max_samples=max_samples,
        n_jobs=-1
    )
    
    model.fit(X_scaled)
    
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(feature_cols, FEATURE_COLS_PATH)
    
    anomaly_scores = model.decision_function(X_scaled)
    predictions = model.predict(X_scaled)
    predictions_binary = (predictions == -1).astype(int)
    
    results = {
        "model_path": MODEL_PATH,
        "n_samples": len(X),
        "n_features": len(feature_cols),
        "contamination": contamination,
        "n_estimators": n_estimators,
        "anomaly_score_range": (float(anomaly_scores.min()), float(anomaly_scores.max())),
        "predicted_anomalies": int(predictions_binary.sum()),
    }
    
    if y is not None and y.sum() > 0:
        precision = precision_score(y, predictions_binary, zero_division=0)
        recall = recall_score(y, predictions_binary, zero_division=0)
        f1 = f1_score(y, predictions_binary, zero_division=0)
        cm = confusion_matrix(y, predictions_binary)
        
        results.update({
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "confusion_matrix": cm.tolist(),
            "true_anomalies": int(y.sum()),
        })
    
    return results


def load_model() -> Tuple[IsolationForest, StandardScaler, List[str]]:
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Run train_isolation_forest() first.")
    
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    feature_cols = joblib.load(FEATURE_COLS_PATH)
    
    return model, scaler, feature_cols


def predict_anomaly(transaction_features: Dict[str, Any]) -> Dict[str, Any]:
    model, scaler, feature_cols = load_model()
    
    X = pd.DataFrame([transaction_features])[feature_cols].fillna(0)
    X_scaled = scaler.transform(X)
    
    anomaly_score = model.decision_function(X_scaled)[0]
    is_anomaly = model.predict(X_scaled)[0] == -1
    
    return {
        "anomaly_score": float(anomaly_score),
        "is_anomaly": bool(is_anomaly),
        "risk_level": "HIGH" if is_anomaly else "LOW"
    }


def predict_batch(features_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    model, scaler, feature_cols = load_model()
    
    X = pd.DataFrame(features_list)[feature_cols].fillna(0)
    X_scaled = scaler.transform(X)
    
    anomaly_scores = model.decision_function(X_scaled)
    predictions = model.predict(X_scaled)
    
    results = []
    for i, (score, pred) in enumerate(zip(anomaly_scores, predictions)):
        results.append({
            "transaction_id": features_list[i].get("transaction_id"),
            "anomaly_score": float(score),
            "is_anomaly": bool(pred == -1),
            "risk_level": "HIGH" if pred == -1 else "LOW"
        })
    
    return results


def score_all_transactions(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    from database.models import Transaction
    from engine.ml_features import extract_transaction_features, build_categorical_mappings
    
    session = get_session_direct()
    try:
        model, scaler, feature_cols = load_model()
        categorical_mappings = build_categorical_mappings(session)
        
        # Use same transaction scope as training (all transaction types) for consistency
        query = session.query(Transaction)
        if user_id:
            query = query.filter(Transaction.user_id == user_id)
        
        transactions = query.order_by(Transaction.timestamp.asc()).all()
        
        results = []
        for txn in transactions:
            features = extract_transaction_features(txn, session, categorical_mappings)
            txn_id = features.pop("transaction_id")
            
            X = pd.DataFrame([features])[feature_cols].fillna(0)
            X_scaled = scaler.transform(X)
            
            anomaly_score = model.decision_function(X_scaled)[0]
            is_anomaly = model.predict(X_scaled)[0] == -1
            
            results.append({
                "transaction_id": txn_id,
                "user_id": txn.user_id,
                "amount": txn.amount,
                "timestamp": txn.timestamp,
                "anomaly_score": float(anomaly_score),
                "is_anomaly": bool(is_anomaly),
                "risk_level": "HIGH" if is_anomaly else "LOW",
                "ground_truth_anomaly": txn.is_anomaly,
                "ground_truth_type": txn.anomaly_type
            })
        
        return results
    finally:
        session.close()


def evaluate_model() -> Dict[str, Any]:
    from database.models import Transaction
    
    session = get_session_direct()
    try:
        model, scaler, feature_cols = load_model()
        categorical_mappings = build_categorical_mappings(session)
        
        # Evaluates across all transaction types (DEBIT + CREDIT) to match
        # train_isolation_forest() and the feature-engineering population.
        transactions = session.query(Transaction).order_by(Transaction.timestamp.asc()).all()
        
        all_features = []
        y_true = []
        txn_ids = []
        
        for txn in transactions:
            features = extract_transaction_features(txn, session, categorical_mappings)
            txn_ids.append(features.pop("transaction_id"))
            all_features.append(features)
            y_true.append(1 if txn.is_anomaly else 0)
        
        X = pd.DataFrame(all_features)[feature_cols].fillna(0)
        X_scaled = scaler.transform(X)
        
        anomaly_scores = model.decision_function(X_scaled)
        y_pred = (model.predict(X_scaled) == -1).astype(int)
        
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        cm = confusion_matrix(y_true, y_pred)
        
        anomalies_detected = []
        false_positives = []
        false_negatives = []
        
        for i, (tid, true_label, pred_label, score) in enumerate(zip(txn_ids, y_true, y_pred, anomaly_scores)):
            if true_label == 1 and pred_label == 1:
                anomalies_detected.append({"transaction_id": tid, "anomaly_score": float(score)})
            elif true_label == 0 and pred_label == 1:
                false_positives.append({"transaction_id": tid, "anomaly_score": float(score)})
            elif true_label == 1 and pred_label == 0:
                false_negatives.append({"transaction_id": tid, "anomaly_score": float(score)})
        
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "confusion_matrix": cm.tolist(),
            "total_transactions": len(y_true),
            "true_anomalies": sum(y_true),
            "predicted_anomalies": sum(y_pred),
            "anomalies_detected": len(anomalies_detected),
            "false_positives": len(false_positives),
            "false_negatives": len(false_negatives),
            "anomaly_score_stats": {
                "min": float(anomaly_scores.min()),
                "max": float(anomaly_scores.max()),
                "mean": float(anomaly_scores.mean()),
                "std": float(anomaly_scores.std())
            },
            "detected_details": anomalies_detected,
            "false_positive_details": false_positives[:10],
            "false_negative_details": false_negatives
        }
    finally:
        session.close()


def compare_rule_vs_ml(user_id: Optional[int] = None, multiplier: float = 3.0, limit: int = 100) -> Dict[str, Any]:
    from engine.fraud_rules import check_all_transactions
    from database.models import Transaction
    
    session = get_session_direct()
    try:
        model, scaler, feature_cols = load_model()
        categorical_mappings = build_categorical_mappings(session)
        
        # Use same transaction scope as training (all transaction types) for consistency
        query = session.query(Transaction)
        if user_id:
            query = query.filter(Transaction.user_id == user_id)
        
        transactions = query.order_by(Transaction.timestamp.asc()).limit(limit).all()
        
        rule_results = {}
        for txn in transactions:
            rule_result = check_all_transactions(txn.user_id, session, multiplier)
            for r in rule_result:
                if r["transaction_id"] == txn.id:
                    rule_results[txn.id] = r
                    break
        
        ml_results = {}
        for txn in transactions:
            features = extract_transaction_features(txn, session, categorical_mappings)
            txn_id = features.pop("transaction_id")
            
            X = pd.DataFrame([features])[feature_cols].fillna(0)
            X_scaled = scaler.transform(X)
            
            anomaly_score = model.decision_function(X_scaled)[0]
            is_anomaly = model.predict(X_scaled)[0] == -1
            
            ml_results[txn_id] = {
                "anomaly_score": float(anomaly_score),
                "is_anomaly": bool(is_anomaly),
                "risk_level": "HIGH" if is_anomaly else "LOW"
            }
        
        comparison = {
            "both": [],
            "rule_only": [],
            "ml_only": [],
            "neither": []
        }
        
        for txn in transactions:
            rule_flagged = rule_results.get(txn.id, {}).get("flagged", False)
            ml_flagged = ml_results.get(txn.id, {}).get("is_anomaly", False)
            
            entry = {
                "transaction_id": txn.id,
                "amount": txn.amount,
                "timestamp": txn.timestamp,
                "ground_truth": txn.is_anomaly
            }
            
            if rule_flagged and ml_flagged:
                comparison["both"].append(entry)
            elif rule_flagged and not ml_flagged:
                comparison["rule_only"].append(entry)
            elif not rule_flagged and ml_flagged:
                comparison["ml_only"].append(entry)
            else:
                comparison["neither"].append(entry)
        
        return {
            "comparison": comparison,
            "counts": {
                "both": len(comparison["both"]),
                "rule_only": len(comparison["rule_only"]),
                "ml_only": len(comparison["ml_only"]),
                "neither": len(comparison["neither"])
            },
            "total_analyzed": len(transactions)
        }
    finally:
        session.close()


def explain_anomaly(transaction_id: int) -> Dict[str, Any]:
    from engine.ml_features import extract_transaction_features, build_categorical_mappings
    from database.models import Transaction
    
    session = get_session_direct()
    try:
        model, scaler, feature_cols = load_model()
        categorical_mappings = build_categorical_mappings(session)
        
        txn = session.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not txn:
            return {"error": "Transaction not found"}
        
        features = extract_transaction_features(txn, session, categorical_mappings)
        txn_id = features.pop("transaction_id")
        
        X = pd.DataFrame([features])[feature_cols].fillna(0)
        X_scaled = scaler.transform(X)
        
        anomaly_score = model.decision_function(X_scaled)[0]
        is_anomaly = model.predict(X_scaled)[0] == -1
        
        feature_contributions = {}
        for i, col in enumerate(feature_cols):
            feature_contributions[col] = float(X_scaled[0, i])
        
        key_indicators = []
        if features.get("amount_to_hist_avg_ratio", 0) > 3:
            key_indicators.append(f"Amount is {features['amount_to_hist_avg_ratio']:.1f}x historical average")
        if features.get("amount_zscore_20", 0) > 3:
            key_indicators.append(f"Amount is {features['amount_zscore_20']:.1f} standard deviations from rolling average")
        if features.get("txn_count_last_7d", 0) == 0 and features.get("days_since_last_txn", 0) > 7:
            key_indicators.append("Unusual timing: long gap since last transaction")
        if features.get("merchant_category_encoded", -1) != -1:
            key_indicators.append("Unusual merchant category for this user")
        if features.get("city_encoded", -1) != -1:
            key_indicators.append("Transaction from unusual location")
        if features.get("hour_of_day", 12) < 6 or features.get("hour_of_day", 12) > 22:
            key_indicators.append("Unusual transaction time (late night/early morning)")
        
        return {
            "transaction_id": transaction_id,
            "anomaly_score": float(anomaly_score),
            "is_anomaly": bool(is_anomaly),
            "risk_level": "HIGH" if is_anomaly else "LOW",
            "contributing_indicators": key_indicators,
            "feature_values": {k: float(v) for k, v in features.items() if k in feature_cols}
        }
    finally:
        session.close()