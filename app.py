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
page = st.sidebar.selectbox("Select View", ["User Dashboard", "Company Verification"])

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
    
    st.markdown("### Transaction History")
    if transactions:
        txn_data = []
        for txn in transactions:
            is_flagged = txn.id in flagged_ids
            risk = "🔴 HIGH" if is_flagged else "🟢 LOW"
            
            txn_data.append({
                "Date": txn.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Type": txn.transaction_type.value.upper(),
                "Amount (₹)": f"{txn.amount:,.2f}",
                "Status": txn.status.value.upper(),
                "Merchant": txn.merchant_name or "N/A",
                "Category": txn.merchant_category or "N/A",
                "City": txn.location_city or "N/A",
                "Fraud Risk": risk,
                "Anomaly": "⚠️" if txn.is_anomaly else ""
            })
        
        df = pd.DataFrame(txn_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions found for this user.")
    
    st.markdown("---")
    
    st.markdown("### Fraud Analysis")
    
    if flagged_txns:
        st.warning(f"⚠️ {len(flagged_txns)} transaction(s) flagged as HIGH RISK")
        
        for flag in flagged_txns:
            st.markdown(f"""
            <div class="flagged-high">
                <strong>Transaction ID:</strong> {flag['transaction_id']}<br>
                <strong>Amount:</strong> Rs.{flag['transaction_amount']:,.2f}<br>
                <strong>Reference Average:</strong> Rs.{flag['reference_average']:,.2f}<br>
                <strong>Ratio:</strong> {flag['ratio']:.1f}x (threshold: {flag['multiplier_used']}x)<br>
                <strong>Risk Level:</strong> {flag['risk_level']}<br>
                <strong>Reason:</strong> {flag['reason']}
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="background:#FEF3C7;padding:15px;border-radius:10px;border-left:4px solid #F59E0B;">
        <strong>Key Insight:</strong> This user has a <strong>HIGH Trust Score</strong> but a <strong>HIGH-RISK Transaction</strong>.
        <br>Trust Score reflects long-term behavioural reliability. Fraud Risk evaluates individual transaction anomalies.
        They are separate concepts — both matter.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("✅ No high-risk transactions detected")
        st.info("All transactions are within normal behavioural patterns for this user.")
    
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

Flagged Transactions: {len(flagged_txns)}
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

else:
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
                    
                    st.success("User Found")
                    st.subheader(user.name)
                    st.metric("Trust Score", trust_data["trust_score"])
                    
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
                        st.error(f"⚠️ {len(flagged)} HIGH-RISK transaction(s) detected")
                        for f in flagged:
                            st.write(f"Txn {f['transaction_id']}: Rs.{f['transaction_amount']:,.2f} - {f['reason']}")
                    else:
                        st.success("No high-risk transactions")
                    
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

st.markdown("---")
st.markdown("<center>TrustBridge — Simulated Financial Trust & Fraud Intelligence Platform</center>", unsafe_allow_html=True)
st.markdown("<center>Built with ❤️ by Team StratNova | Hackathon 2026</center>", unsafe_allow_html=True)