import streamlit as st
from config import API_URL
from session import require_login

st.set_page_config(page_title="Bandit Brain", layout="wide", page_icon="🧠")

require_login(API_URL)

st.title("🧠 Bandit Brain")
ROADMAP_URL = "https://github.com/tzpereira/bandit-brain/blob/main/ROADMAP.md"
st.write(
    "Multi-armed bandit traffic allocation, with a proof-of-value layer: off-policy "
    f"evaluation validated against known ground truth. See [ROADMAP.md]({ROADMAP_URL}) for the methodology."
)

col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/1_🧪_Experiment.py", label="Run an experiment", icon="🧪")
    st.caption("Upload historical data or simulate live traffic, and watch recommended allocations update.")
with col2:
    st.page_link("pages/2_📊_Results.py", label="View simulation results", icon="📊")
    st.caption("Regret curves, algorithm comparison, and OPE validation against known ground truth.")
