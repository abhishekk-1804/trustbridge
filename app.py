import streamlit as st
import pandas as pd
import qrcode
from io import BytesIO
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import get_session_direct, init_db
from database.models import User, Transaction, TransactionType, TransactionStatus
from engine.trust_score import calculate_trust_score, get_user_transactions, get_all_users
from engine.fraud_rules import get_flagged_transactions, detect_amount_spike
from engine.ml_fraud import (
    evaluate_model, compare_rule_vs_ml, explain_anomaly,
    train_isolation_forest, load_model, score_all_transactions
)

st.set_page_config(page_title="TrustBridge", layout="wide")

def clean(name):
    return re.sub(r'[^a-zA-Z0-9]', '', name)

@st.cache_resource
def get_db_session():
    init_db()
    return get_session_direct()

def load_users():
    session = get_db_session()
    try:
        return get_all_users(session)
    finally:
        session.close()

def load_user_data(user_id):
    session = get_db_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        trust_data = calculate_trust_score(user_id, session)
        transactions = get_user_transactions(user_id, session, limit=100)
        flagged = get_flagged_transactions(user_id, session, multiplier=3.0)
        
        return {
            "user": user,
            "trust_data": trust_data,
            "transactions": transactions,
            "flagged_transactions": flagged
        }
    finally:
        session.close()

st.markdown("""
<style>
.big-title { font-size:42px; font-weight:bold; color:#4CAF50; }
.metric-card { background:#1E293B;padding:15px;border-radius:10px; }
.flagged-high { background:#FEF2F2;border-left:4px solid #DC2626;padding:10px;border-radius:5px;margin:5px 0; }
.flagged-low { background:#F0FDF4;border-left:4px solid #16A34A;padding:10px;border-radius:5px;margin:5px 0; }
.ml-flagged { background:#FEF3C7;border-left:4px solid #F59E0B;padding:10px;border-radius:5px;margin:5px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-title">TrustBridge</p>', unsafe_allow_html=True)
st.subheader("Portable Trust Score & Fraud Intelligence Platform")

st.markdown("""
<div style="background:#1E293B;padding:20px;border-radius:14px;">
<h3 style="color:#FFD966;">TrustBridge converts real-world reliability into a portable trust identity.</h3>
<p style="color:#E5E7EB;">
Trust Score ≠ Fraud Risk. A high-trust user can still have a high-risk transaction.
</p>
</div>
""", unsafe_allow_html=True)

users = load_users()

if not users:
    st.warning("No users found in database. Run data generator first.")
    if st.button("Generate Synthetic Data"):
        from data.generator import generate_synthetic_data
        with st.spinner("Generating synthetic data..."):
            generate_synthetic_data()
        st.success("Data generated! Please refresh the page.")
    st.stop()

st.sidebar.markdown("### Navigation")
page = st.sidebar.selectbox("Select View", ["User Dashboard", "Company Verification", "ML Model Management"])

st.sidebar.markdown("---")
st.sidebar.markdown("### Business Model")
st.sidebar.markdown("""
<div style="background:#111827;padding:18px;border-radius:12px">
<b>🏢 Platform API (Primary)</b><br>
Companies integrate TrustBridge scoring into hiring, onboarding and screening systems.<br><br>
<b>🛡 Enterprise Licensing</b><br>
Organizations deploy TrustBridge internally for vendor trust + workforce verification.<br><br>
<b>✔ Verification Layer</b><br>
₹49 per proof verification<br>
<small>Used for authentication & fraud prevention</small>
</div>
""", unsafe_allow_html=True)
st.sidebar.caption("Scalable across hiring, lending, rentals and gig platforms.")

if "bonus" not in st.session_state:
    st.session_state.bonus = 0
if "verified" not in st.session_state:
    st.session_state.verified = False

if page == "User Dashboard":
    st.header("User Dashboard")
    
    user_options = {f"{u.name} (ID: {u.id})": u.id for u in users}
    selected_key = st.selectbox("Select User", list(user_options.keys()))
    selected_user_id = user_options[selected_key]
    
    data = load_user_data(selected_user_id)
    if not data:
        st.error("User data not found")
        st.stop()
    
    user = data["user"]
    trust_data = data["trust_data"]
    transactions = data["transactions"]
    flagged_txns = data["flagged_transactions"]
    
    flagged_ids = {f["transaction_id"] for f in flagged_txns}
    
    # Load ML scores for this user's transactions
    ml_scores = {}
    try:
        ml_results = score_all_transactions(selected_user_id)
        for r in ml_results:
            ml_scores[r["transaction_id"]] = r
    except Exception as e:
        st.info(f"ML model not available: {e}")
    
    trust_score = trust_data["trust_score"]
    color = "#16A34A" if trust_score > 85 else "#FACC15" if trust_score > 70 else "#DC2626"
    verdict = "Highly Reliable" if trust_score > 85 else "Moderate Risk" if trust_score > 70 else "High Risk"
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### AI Reliability Engine")
        st.markdown(f"""
        <div style="text-align:center;">
            <div style="font-size:80px;font-weight:bold;color:{color};">{trust_score}%</div>
            <div style="font-size:22px;">Trust Score</div>
            <div style="font-size:20px;color:{color};"><b>{verdict}</b></div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### Trust Score Breakdown")
        components = trust_data["components"]
        
        for name, comp in components.items():
            label = name.replace("_", " ").title()
            st.metric(
                label=f"{label}",
                value=f"{comp['score']}%",
                delta=f"Weight: {int(comp['weight']*100)}% | Contribution: {comp['contribution']}"
            )
    
    st.markdown("---")
    
    # FRAUD INTELLIGENCE SECTION
    st.markdown("### Fraud Intelligence")
    
    # Summary metrics
    ml_flagged_count = sum(1 for tid, ms in ml_scores.items() if ms.get("is_anomaly"))
    rule_flagged_count = len(flagged_txns)
    both_flagged = sum(1 for tid in flagged_ids if tid in ml_scores and ml_scores[tid].get("is_anomaly"))
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Trust Score", f"{trust_score}%")
    col2.metric("Rule-based Flags", rule_flagged_count)
    col3.metric("ML Anomaly Flags", ml_flagged_count)
    col4.metric("Both Agree", both_flagged)
    
    # Risk classification
    st.markdown("#### Transaction Risk Classification")
    if transactions:
        txn_data = []
        for txn in transactions:
            is_rule_flagged = txn.id in flagged_ids
            is_ml_flagged = ml_scores.get(txn.id, {}).get("is_anomaly", False)
            
            if is_rule_flagged and is_ml_flagged:
                risk_label = "🔴 BOTH"
                risk_class = "both"
            elif is_rule_flagged:
                risk_label = "🔴 RULE"
                risk_class = "rule"
            elif is_ml_flagged:
                risk_label = "🟡 ML"
                risk_class = "ml"
            else:
                risk_label = "🟢 LOW"
                risk_class = "low"
            
            rule_reason = ""
            for f in flagged_txns:
                if f["transaction_id"] == txn.id:
                    rule_reason = f["reason"]
                    break
            
            ml_reason = ""
            if is_ml_flagged:
                ml_reason = f"Anomaly score: {ml_scores[txn.id]['anomaly_score']:.4f}"
            
            txn_data.append({
                "Date": txn.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Type": txn.transaction_type.value.upper(),
                "Amount (₹)": f"{txn.amount:,.2f}",
                "Status": txn.status.value.upper(),
                "Merchant": txn.merchant_name or "N/A",
                "Category": txn.merchant_category or "N/A",
                "City": txn.location_city or "N/A",
                "Risk": risk_label,
                "Rule Flag": "✓" if is_rule_flagged else "",
                "ML Flag": "✓" if is_ml_flagged else "",
                "Anomaly": "⚠️" if txn.is_anomaly else ""
            })
        
        df = pd.DataFrame(txn_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # RULE-BASED FRAUD ANALYSIS
    st.markdown("#### Rule-based Fraud Analysis (Amount Spike)")
    
    if flagged_txns:
        st.warning(f"⚠️ {len(flagged_txns)} transaction(s) flagged as HIGH RISK by rule engine")
        
        for flag in flagged_txns:
            ml_info = ml_scores.get(flag["transaction_id"], {})
            ml_badge = " 🟡 ML AGREES" if ml_info.get("is_anomaly") else " 🟢 ML: Normal"
            
            st.markdown(f"""
            <div class="flagged-high">
                <strong>Transaction ID:</strong> {flag['transaction_id']}<br>
                <strong>Amount:</strong> Rs.{flag['transaction_amount']:,.2f}<br>
                <strong>Reference Average:</strong> Rs.{flag['reference_average']:,.2f}<br>
                <strong>Ratio:</strong> {flag['ratio']:.1f}x (threshold: {flag['multiplier_used']}x)<br>
                <strong>Risk Level:</strong> {flag['risk_level']}{ml_badge}<br>
                <strong>Reason:</strong> {flag['reason']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No high-risk transactions detected by rule engine")
    
    # ML ANOMALY ANALYSIS
    st.markdown("#### ML Anomaly Detection (Isolation Forest)")
    
    ml_anomalies = [ms for ms in ml_scores.values() if ms.get("is_anomaly")]
    
    if ml_anomalies:
        st.warning(f"⚠️ {len(ml_anomalies)} transaction(s) flagged as ANOMALOUS by ML model")
        
        for ms in ml_anomalies:
            rule_flagged = ms["transaction_id"] in flagged_ids
            rule_badge = " 🔴 RULE AGREES" if rule_flagged else " 🟢 RULE: Normal"
            
            explanation = explain_anomaly(ms["transaction_id"])
            
            st.markdown(f"""
            <div class="ml-flagged">
                <strong>Transaction ID:</strong> {ms['transaction_id']}<br>
                <strong>Amount:</strong> Rs.{ms['amount']:,.2f}<br>
                <strong>Anomaly Score:</strong> {ms['anomaly_score']:.4f}<br>
                <strong>Risk Level:</strong> {ms['risk_level']}{rule_badge}<br>
                <strong>Contributing Indicators:</strong><br>
            """, unsafe_allow_html=True)
            
            for indicator in explanation.get("contributing_indicators", []):
                st.markdown(f"• {indicator}")
            
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.success("✅ No anomalies detected by ML model")
    
    st.markdown("---")
    
    # RULE vs ML COMPARISON
    st.markdown("#### Rule vs ML Comparison")
    
    try:
        comparison = compare_rule_vs_ml(selected_user_id)
        comp = comparison["comparison"]
        counts = comparison["counts"]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Both Flag", counts["both"])
        col2.metric("Rule Only", counts["rule_only"])
        col3.metric("ML Only", counts["ml_only"])
        col4.metric("Neither", counts["neither"])
        
        if comp["rule_only"]:
            st.markdown("**Rule Only (ML says normal):**")
            for e in comp["rule_only"]:
                st.write(f"  Txn {e['transaction_id']}: Rs.{e['amount']:,.2f} (GT: {'Anomaly' if e['ground_truth'] else 'Normal'})")
        
        if comp["ml_only"]:
            st.markdown("**ML Only (Rule says normal):**")
            for e in comp["ml_only"]:
                st.write(f"  Txn {e['transaction_id']}: Rs.{e['amount']:,.2f} (GT: {'Anomaly' if e['ground_truth'] else 'Normal'})")
        
        if comp["both"]:
            st.markdown("**Both Agree:**")
            for e in comp["both"]:
                st.write(f"  Txn {e['transaction_id']}: Rs.{e['amount']:,.2f} (GT: {'Anomaly' if e['ground_truth'] else 'Normal'})")
    except Exception as e:
        st.info(f"Comparison unavailable: {e}")
    
    st.markdown("---")
    
    # KEY INSIGHT
    if flagged_txns or ml_anomalies:
        st.markdown("""
        <div style="background:#FEF3C7;padding:15px;border-radius:10px;border-left:4px solid #F59E0B;">
        <strong>Key Insight:</strong> This user has a <strong>Trust Score of {trust_score}%</strong> but has <strong>flagged transactions</strong>.
        <br>Trust Score reflects long-term behavioural reliability. Fraud Risk evaluates individual transaction anomalies.
        ML adds behavioural pattern detection beyond simple amount thresholds.
        They are separate concepts — all three matter.
        </div>
        """.format(trust_score=trust_score), unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### Verification")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Verify Work Proof"):
            st.session_state.bonus += 5
            st.success("+5 Trust Points Added (Demo)")
    with col2:
        if st.button("Get Verified Badge"):
            st.session_state.verified = True
    
    if st.session_state.verified:
        st.success("🏅 Verified Professional")
    
    st.markdown("---")
    st.markdown("### Download Professional Report")
    
    report = f"""
TRUSTBRIDGE VERIFIED REPORT
----------------------------
Name: {user.name}
Role: {user.role.value}
Account Created: {user.account_created_at.strftime('%Y-%m-%d')}
Verification: {"Verified" if st.session_state.verified else "Not Verified"}

Trust Score: {trust_score}
AI Verdict: {verdict}

Component Breakdown:
- Payment Reliability: {trust_data['payment_reliability']}% (Weight: 40%)
- Transaction Consistency: {trust_data['transaction_consistency']}% (Weight: 35%)
- Account Behaviour: {trust_data['account_behaviour']}% (Weight: 25%)

Rule-based Flags: {len(flagged_txns)}
ML Anomaly Flags: {ml_flagged_count}
Total Transactions: {len(transactions)}

Generated by TrustBridge Engine
"""
    
    st.download_button(
        "Download Report",
        report,
        file_name=f"{clean(user.name)}_TrustReport.txt"
    )
    
    st.markdown("---")
    st.markdown("### Share Profile")
    
    if st.button("Generate QR"):
        url = f"http://localhost:8501/?user={clean(user.name)}"
        img = qrcode.make(url)
        buf = BytesIO()
        img.save(buf)
        st.image(buf, width=170)
        st.code(url)

elif page == "Company Verification":
    st.header("Company Verification Portal")
    
    session = get_db_session()
    try:
        all_users = get_all_users(session)
        
        uid = st.text_input("Enter User ID")
        
        if uid:
            try:
                user_id = int(uid)
                user = session.query(User).filter(User.id == user_id).first()
                
                if user:
                    trust_data = calculate_trust_score(user_id, session)
                    flagged = get_flagged_transactions(user_id, session)
                    
                    # ML scores
                    ml_scores_corp = {}
                    try:
                        ml_results = score_all_transactions(user_id)
                        for r in ml_results:
                            ml_scores_corp[r["transaction_id"]] = r
                    except:
                        pass
                    
                    ml_flagged_count = sum(1 for ms in ml_scores_corp.values() if ms.get("is_anomaly"))
                    
                    st.success("User Found")
                    st.subheader(user.name)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Trust Score", f"{trust_data['trust_score']}%")
                    col2.metric("Rule Flags", len(flagged))
                    col3.metric("ML Anomalies", ml_flagged_count)
                    col4.metric("Both", sum(1 for f in flagged if f["transaction_id"] in ml_scores_corp and ml_scores_corp[f["transaction_id"]].get("is_anomaly")))
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Payment Reliability", f"{trust_data['payment_reliability']}%")
                    col2.metric("Transaction Consistency", f"{trust_data['transaction_consistency']}%")
                    col3.metric("Account Behaviour", f"{trust_data['account_behaviour']}%")
                    
                    st.bar_chart({
                        "Payment Reliability": [trust_data['payment_reliability']],
                        "Transaction Consistency": [trust_data['transaction_consistency']],
                        "Account Behaviour": [trust_data['account_behaviour']]
                    })
                    
                    if flagged:
                        st.error(f"⚠️ {len(flagged)} HIGH-RISK transaction(s) detected by rules")
                        for f in flagged:
                            ml_info = ml_scores_corp.get(f["transaction_id"], {})
                            ml_badge = " | ML: ANOMALY" if ml_info.get("is_anomaly") else " | ML: Normal"
                            st.write(f"Txn {f['transaction_id']}: Rs.{f['transaction_amount']:,.2f} - {f['reason']}{ml_badge}")
                    else:
                        st.success("No high-risk transactions by rules")
                    
                    if ml_flagged_count > 0:
                        st.warning(f"⚠️ {ml_flagged_count} ML anomaly(ies) detected")
                        for tid, ms in ml_scores_corp.items():
                            if ms.get("is_anomaly"):
                                rule_flagged = tid in [f["transaction_id"] for f in flagged]
                                rule_badge = " | Rule: FLAGGED" if rule_flagged else " | Rule: Normal"
                                st.write(f"Txn {tid}: Rs.{ms['amount']:,.2f} (Score: {ms['anomaly_score']:.4f}){rule_badge}")
                    else:
                        st.success("No ML anomalies detected")
                    
                    score = trust_data["trust_score"]
                    if score > 85:
                        st.success("Strongly Recommended")
                    elif score > 70:
                        st.info("Recommended")
                    else:
                        st.warning("Needs Review")
                else:
                    st.error("User not found")
            except ValueError:
                st.error("Invalid User ID")
    finally:
        session.close()

elif page == "ML Model Management":
    st.header("ML Model Management")
    
    st.markdown("### Model Training")
    st.info("Train a new Isolation Forest model on the current transaction dataset.")
    
    col1, col2 = st.columns(2)
    with col1:
        contamination = st.slider("Contamination", 0.001, 0.1, 0.01, 0.001, format="%.3f")
        n_estimators = st.slider("N Estimators", 50, 500, 200, 50)
    with col2:
        random_state = st.number_input("Random State", value=42, step=1)
        max_samples = st.selectbox("Max Samples", ["auto", 100, 200, 256, 512])
    
    if st.button("Train Model"):
        with st.spinner("Training Isolation Forest..."):
            try:
                result = train_isolation_forest(
                    contamination=contamination,
                    n_estimators=n_estimators,
                    random_state=int(random_state),
                    max_samples=max_samples if max_samples != "auto" else "auto"
                )
                st.success("Model trained successfully!")
                st.json(result)
            except Exception as e:
                st.error(f"Training failed: {e}")
    
    st.markdown("---")
    
    st.markdown("### Model Evaluation")
    
    if st.button("Run Evaluation"):
        with st.spinner("Evaluating model..."):
            try:
                eval_result = evaluate_model()
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Precision", f"{eval_result['precision']:.2%}")
                col2.metric("Recall", f"{eval_result['recall']:.2%}")
                col3.metric("F1 Score", f"{eval_result['f1']:.2%}")
                
                st.markdown("#### Confusion Matrix")
                cm = eval_result["confusion_matrix"]
                cm_df = pd.DataFrame(cm, index=["Actual: Normal", "Actual: Anomaly"], columns=["Pred: Normal", "Pred: Anomaly"])
                st.dataframe(cm_df)
                
                st.markdown("#### Details")
                st.write(f"Total Transactions: {eval_result['total_transactions']}")
                st.write(f"True Anomalies (injected): {eval_result['true_anomalies']}")
                st.write(f"Predicted Anomalies: {eval_result['predicted_anomalies']}")
                st.write(f"Correctly Detected: {eval_result['anomalies_detected']}")
                st.write(f"False Positives: {eval_result['false_positives']}")
                st.write(f"False Negatives: {eval_result['false_negatives']}")
                
                st.markdown("#### Anomaly Score Distribution")
                stats = eval_result["anomaly_score_stats"]
                st.write(f"Min: {stats['min']:.4f}, Max: {stats['max']:.4f}, Mean: {stats['mean']:.4f}, Std: {stats['std']:.4f}")
                
                if eval_result["false_positive_details"]:
                    st.markdown("**Sample False Positives:**")
                    for fp in eval_result["false_positive_details"][:5]:
                        st.write(f"  Txn {fp['transaction_id']}: Score={fp['anomaly_score']:.4f}")
                
                if eval_result["false_negative_details"]:
                    st.markdown("**False Negatives (Missed Anomalies):**")
                    for fn in eval_result["false_negative_details"]:
                        st.write(f"  Txn {fn['transaction_id']}: Score={fn['anomaly_score']:.4f}")
                
            except Exception as e:
                st.error(f"Evaluation failed: {e}")
    
    st.markdown("---")
    
    st.markdown("### Rule vs ML Comparison (All Users)")
    
    if st.button("Run Comparison"):
        with st.spinner("Comparing rule vs ML..."):
            try:
                comparison = compare_rule_vs_ml()
                comp = comparison["comparison"]
                counts = comparison["counts"]
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Both Flag", counts["both"])
                col2.metric("Rule Only", counts["rule_only"])
                col3.metric("ML Only", counts["ml_only"])
                col4.metric("Neither", counts["neither"])
                
                st.markdown("#### Both Flagged (High Confidence)")
                for e in comp["both"][:10]:
                    st.write(f"  Txn {e['transaction_id']}: Rs.{e['amount']:,.2f} (GT: {'Anomaly' if e['ground_truth'] else 'Normal'})")
                
                st.markdown("#### Rule Only")
                for e in comp["rule_only"][:10]:
                    st.write(f"  Txn {e['transaction_id']}: Rs.{e['amount']:,.2f} (GT: {'Anomaly' if e['ground_truth'] else 'Normal'})")
                
                st.markdown("#### ML Only (Potential Novel Patterns)")
                for e in comp["ml_only"][:10]:
                    st.write(f"  Txn {e['transaction_id']}: Rs.{e['amount']:,.2f} (GT: {'Anomaly' if e['ground_truth'] else 'Normal'})")
                    
            except Exception as e:
                st.error(f"Comparison failed: {e}")

st.markdown("---")
st.markdown("<center>TrustBridge — Simulated Financial Trust & Fraud Intelligence Platform</center>", unsafe_allow_html=True)
st.markdown("<center>Built with ❤️ by Team StratNova | Hackathon 2026</center>", unsafe_allow_html=True)