import streamlit as st
import matplotlib.pyplot as plt
import time
import pandas as pd
import numpy as np
import qrcode
from io import BytesIO
import re

st.set_page_config(page_title="TrustBridge", layout="wide")

# ---------- USERS DATABASE ----------
users = {
    "Raj – Delivery Partner": {"tasks": 82, "rating": 4.6, "punctuality": 91},
    "Priya – Freelancer": {"tasks": 64, "rating": 4.8, "punctuality": 95},
    "Anil – Student": {"tasks": 40, "rating": 4.2, "punctuality": 80}
}

def clean(name):
    return re.sub(r'[^a-zA-Z0-9]', '', name)

# ---------- QUERY PARAM ----------
query = st.query_params
auto_user = query.get("user", None)

default_index = 0
if auto_user:
    for i,u in enumerate(users.keys()):
        if clean(u) == auto_user:
            default_index = i

# ---------- STYLE ----------
st.markdown("""
<style>
.big-title { font-size:42px; font-weight:bold; color:#4CAF50; }
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown('<p class="big-title">TrustBridge</p>', unsafe_allow_html=True)
st.subheader("Portable Trust Score System")

st.markdown("""
<div style="background:#1E293B;padding:20px;border-radius:14px;">
<h3 style="color:#FFD966;">Meet Raj — 2000+ deliveries, perfect ratings, zero credit score.</h3>
<p style="color:#E5E7EB;">
TrustBridge converts real-world reliability into a portable trust identity.
</p>
</div>
""", unsafe_allow_html=True)

# ---------- SIDEBAR ----------
page = st.sidebar.selectbox("Select View", ["User Dashboard","Company Verification"])

st.sidebar.markdown("---")
st.sidebar.markdown("### 💼 Business Model")

st.sidebar.markdown("""
<div style="background:#111827;padding:18px;border-radius:12px">

<b>🏢 Platform API (Primary)</b><br>
Companies pay to integrate TrustBridge scoring<br>
into hiring, onboarding and screening systems.<br><br>

<b>🛡 Enterprise Licensing</b><br>
Organizations deploy TrustBridge internally<br>
for vendor trust + workforce verification.<br><br>

<b>✔ Verification Layer</b><br>
₹49 per proof verification<br>
<small>Used for authentication & fraud prevention</small>

</div>
""", unsafe_allow_html=True)

st.sidebar.caption("Scalable across hiring, lending, rentals and gig and other platforms.")

# ---------- SESSION ----------
if "bonus" not in st.session_state:
    st.session_state.bonus = 0

if "verified" not in st.session_state:
    st.session_state.verified = False

# ======================================================
# USER DASHBOARD
# ======================================================
if page == "User Dashboard":

    st.header("User Dashboard")

    selected = st.selectbox(
        "Select Demo User",
        list(users.keys()),
        index=default_index
    )

    data = users[selected]

    tasks = st.slider("Tasks Completed",0,100,data["tasks"])
    rating = st.slider("Peer Rating",0.0,5.0,data["rating"])
    punctuality = st.slider("On-time %",0,100,data["punctuality"])

    # ---------- SCORE ----------
    score = (
        tasks/100*0.4 +
        rating/5*0.35 +
        punctuality/100*0.25
    )*100 + st.session_state.bonus

    # ---------- AI RISK METER ----------
    st.markdown("### AI Reliability Engine")

    risk = 100-score
    color = "#16A34A" if score>85 else "#FACC15" if score>70 else "#DC2626"
    verdict = "Highly Reliable" if score>85 else "Moderate Risk" if score>70 else "High Risk"

    st.markdown(f"""
    <div style="text-align:center;">
        <div style="font-size:80px;font-weight:bold;color:{color};">{round(score,1)}%</div>
        <div style="font-size:22px;">AI Trust Probability</div>
        <div style="font-size:20px;color:{color};"><b>{verdict}</b></div>
    </div>
    """, unsafe_allow_html=True)

    # ---------- HISTORY ----------
    if "history" not in st.session_state:
        base = score-10
        st.session_state.history=[max(0,base+np.random.randint(-5,15)) for _ in range(6)]

    st.subheader("Trust Growth History")
    st.line_chart(pd.DataFrame({"Score":st.session_state.history}))

    # ---------- METRICS ----------
    col1,col2,col3 = st.columns(3)
    col1.metric("Tasks",tasks)
    col2.metric("Rating",rating)
    col3.metric("Punctuality",f"{punctuality}%")

    # ---------- CHART ----------
    st.markdown("### Reliability Analytics")
    fig, ax = plt.subplots()
    ax.bar(["Tasks","Rating","Punctuality"],[tasks,rating,punctuality])
    st.pyplot(fig)

    # ---------- VERIFY ----------
    st.markdown("### Verification")

    if st.button("Verify Work Proof"):
        with st.spinner("Checking platform records..."):
            time.sleep(2)
        st.session_state.bonus += 5
        st.success("+5 Trust Points Added")

    if st.button("Get Verified Badge"):
        st.session_state.verified=True

    if st.session_state.verified:
        st.success("🏅 Verified Professional")

    # ---------- DOWNLOAD REPORT ----------
    st.markdown("### Download Professional Report")

    report=f"""
TRUSTBRIDGE VERIFIED REPORT
----------------------------
Name: {selected}
Tasks Completed: {tasks}
Rating: {rating}
Punctuality: {punctuality}%

Trust Score: {round(score,1)}
AI Verdict: {verdict}
Verification: {"Verified" if st.session_state.verified else "Not Verified"}

Generated by TrustBridge Engine
"""

    st.download_button(
        "Download Report",
        report,
        file_name=f"{clean(selected)}_TrustReport.txt"
    )

    # ---------- QR ----------
    st.markdown("### Share Profile")

    if st.button("Generate QR"):
        url=f"http://localhost:8501/?user={clean(selected)}"
        img=qrcode.make(url)
        buf=BytesIO()
        img.save(buf)
        st.image(buf,width=170)
        st.code(url)

# ======================================================
# COMPANY VIEW
# ======================================================
else:

    st.header("Company Verification Portal")

    db={
        "raj123":{"name":"Raj – Delivery Partner","score":88,"tasks":82,"rating":4.6,"punctuality":91},
        "priya456":{"name":"Priya – Freelancer","score":93,"tasks":64,"rating":4.8,"punctuality":95},
        "anil789":{"name":"Anil – Student","score":67,"tasks":40,"rating":4.2,"punctuality":80}
    }

    uid=st.text_input("Enter User ID")

    if uid in db:
        d=db[uid]

        st.success("User Found")
        st.subheader(d["name"])
        st.metric("Trust Score",d["score"])

        c1,c2,c3=st.columns(3)
        c1.metric("Tasks",d["tasks"])
        c2.metric("Rating",d["rating"])
        c3.metric("Punctuality",f'{d["punctuality"]}%')

        st.bar_chart({
            "Tasks":[d["tasks"]],
            "Rating":[d["rating"]],
            "Punctuality":[d["punctuality"]]
        })

        if d["score"]>85:
            st.success("Strongly Recommended")
        elif d["score"]>70:
            st.info("Recommended")
        else:
            st.warning("Needs Review")

# ---------- FOOTER ----------
st.markdown("---")
st.markdown("<center>Built with ❤️ by Team StratNova | Hackathon 2026</center>",unsafe_allow_html=True)
