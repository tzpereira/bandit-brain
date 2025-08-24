import random
import requests
import polars as pl
import streamlit as st
from datetime import date
import plotly.express as px
from streamlit_tags import st_tags
from streamlit_autorefresh import st_autorefresh

API_URL = "http://backend:8000"

st.set_page_config(page_title="Bandit Brain Dashboard", layout="wide")
st.title("Bandit Brain Dashboard")

# ---------------------------
# API FUNCTIONS 
# ---------------------------
def fetch_allocations(exp_name, exp_date, method, epsilon=None, c=None, tau=None):
    payload = {"experiment_name": exp_name, "date": str(exp_date), "method": method}
    if method == "eg" and epsilon is not None:
        payload["epsilon"] = epsilon
    if method == "ucb" and c is not None:
        payload["c"] = c
    if method == "softmax" and tau is not None:
        payload["tau"] = tau
    try:
        resp = requests.post(f"{API_URL}/recommend", json=payload, timeout=10)
        if resp.status_code == 200:
            return pl.DataFrame(resp.json())
    except Exception as e:
        st.error(f"Error fetching allocations: {e}")
    return pl.DataFrame()

def fetch_metrics(exp_name, exp_date, group_by_context=False):
    params = {"experiment_name": exp_name, "date": str(exp_date), "group_by_context": str(group_by_context).lower()}
    try:
        resp = requests.get(f"{API_URL}/metrics", params=params, timeout=10)
        if resp.status_code == 200:
            return pl.DataFrame(resp.json())
    except Exception as e:
        st.error(f"Error fetching metrics: {e}")
    return pl.DataFrame()

def load_data(exp_name, exp_date, method, epsilon=None, c=None, tau=None):
    allocations = fetch_allocations(exp_name, exp_date, method, epsilon, c, tau)
    metrics = fetch_metrics(exp_name, exp_date)
    metrics_by_context = fetch_metrics(exp_name, exp_date, group_by_context=True)
    return allocations, metrics, metrics_by_context

# ---------------------------
# SIDEBAR CONTROLS
# ---------------------------
st.sidebar.header("Experiment Configuration")

# Track any parameter that should reset the data if changed
param_tracker = st.session_state.get("param_tracker", {})

experiment_name = st.sidebar.text_input("Experiment Name", "homepage_test")
date_selected = st.sidebar.date_input("Date", date.today())
algorithm = st.sidebar.selectbox("Algorithm", ["eg", "ucb", "ts", "softmax"])
epsilon = st.sidebar.slider("Epsilon (EG)", 0.0, 1.0, 0.1) if algorithm == "eg" else None
c_param = st.sidebar.slider("C (UCB)", 0.0, 5.0, 2.0) if algorithm == "ucb" else None
tau = st.sidebar.slider("Tau (Softmax)", 0.01, 2.0, 0.1) if algorithm == "softmax" else None
batch_size = st.sidebar.number_input("Batch Size", min_value=10, max_value=10000, value=100)
total_events = st.sidebar.number_input("Total Events to Simulate", min_value=100, max_value=100000, value=1000)

# ---------------------------
# VARIANTS SELECTION IN SIDEBAR
# ---------------------------
with st.sidebar:
    if "allocations_df" in st.session_state and isinstance(st.session_state.allocations_df, pl.DataFrame) and st.session_state.allocations_df.height > 0:
        unique_variants = st.session_state.allocations_df["variant_name"].unique().to_list()
    elif "metrics_df" in st.session_state and isinstance(st.session_state.metrics_df, pl.DataFrame) and st.session_state.metrics_df.height > 0:
        unique_variants = st.session_state.metrics_df["variant_name"].unique().to_list()
    else:
        unique_variants = ["A", "B"]

    variants = st_tags(
        label="Variants",
        text="Press enter to add",
        value=st.session_state.get("variants", unique_variants),
        suggestions=unique_variants,
        maxtags=10,
        key="variants",
    )

# ---------------------------
# RESET SESSION IF PARAMETERS CHANGE
# ---------------------------
current_params = {
    "experiment_name": experiment_name,
    "date": str(date_selected),
    "algorithm": algorithm,
    "epsilon": epsilon,
    "c_param": c_param,
    "tau": tau,
    "variants": variants,
}

if param_tracker != current_params:
    # Remove/reset all data related to the simulation from st.session_state
    keys_to_reset = [
        "allocations_df", "metrics_df", "metrics_by_context_df",
        "decision_log", "is_watching", "remaining_events",
        "last_batch_sent", "refresh_key"
    ]
    for key in keys_to_reset:
        if key in st.session_state:
            if key.endswith("_df") or "allocations" in key or "metrics" in key:
                st.session_state[key] = pl.DataFrame()
            elif key == "decision_log":
                st.session_state[key] = []
            elif key == "is_watching":
                st.session_state[key] = False
            else:
                st.session_state[key] = 0

    # Clear backend deletion routes
    try:
        r1 = requests.delete(f"{API_URL}/allocations", timeout=10)
        r2 = requests.delete(f"{API_URL}/experiments", timeout=10)
        if r1.status_code not in [200, 204]:
            st.warning(f"Failed to delete allocations: {r1.text}")
        if r2.status_code not in [200, 204]:
            st.warning(f"Failed to delete experiments: {r2.text}")
    except Exception as e:
        st.warning(f"Error calling deletion routes: {e}")

    # Reinitialize session state variables
    st.session_state["allocations_df"] = st.session_state.get("allocations_df", pl.DataFrame())
    st.session_state["metrics_df"] = st.session_state.get("metrics_df", pl.DataFrame())
    st.session_state["metrics_by_context_df"] = st.session_state.get("metrics_by_context_df", pl.DataFrame())
    st.session_state["decision_log"] = st.session_state.get("decision_log", [])
    st.session_state["is_watching"] = False
    st.session_state["remaining_events"] = 0
    st.session_state["last_batch_sent"] = 0
    st.session_state["refresh_key"] = st.session_state.get("refresh_key", 0) + 1

    st.session_state["param_tracker"] = current_params

    allocations_df = pl.DataFrame()
    metrics_df = pl.DataFrame()
    metrics_by_context_df = pl.DataFrame()
    decision_log = []

# ---------------------------
# INITIALIZATION
# ---------------------------
for key in ["is_watching", "remaining_events", "last_batch_sent", "refresh_key"]:
    if key not in st.session_state:
        st.session_state[key] = 0 if "remaining" in key or "last_batch" in key else False

# ---------------------------
# LOAD INITIAL DATA
# ---------------------------
# If the session does not have allocations/metrics loaded (or they are empty), fetch them
need_load = False
if "allocations_df" not in st.session_state:
    need_load = True
else:
    try:
        if isinstance(st.session_state.allocations_df, pl.DataFrame) and st.session_state.allocations_df.height == 0:
            need_load = True
    except Exception:
        need_load = True

if need_load:
    a, m, mbc = load_data(experiment_name, date_selected, algorithm, epsilon, c_param, tau)
    st.session_state["allocations_df"] = a if isinstance(a, pl.DataFrame) else pl.DataFrame()
    st.session_state["metrics_df"] = m if isinstance(m, pl.DataFrame) else pl.DataFrame()
    st.session_state["metrics_by_context_df"] = mbc if isinstance(mbc, pl.DataFrame) else pl.DataFrame()
    st.session_state["simulation_enabled"] = True

# ---------------------------
# Local Variables
# ---------------------------
allocations_df = st.session_state.get("allocations_df", pl.DataFrame())
metrics_df = st.session_state.get("metrics_df", pl.DataFrame())
metrics_by_context_df = st.session_state.get("metrics_by_context_df", pl.DataFrame())
decision_log = st.session_state.get("decision_log", [])

# Remove unwanted columns
if isinstance(allocations_df, pl.DataFrame):
    for col in ["id", "created_at"]:
        if col in allocations_df.columns:
            allocations_df = allocations_df.drop(col)

# ---------------------------
# SIMULATION FUNCTION
# ---------------------------

def simulate_events(n_events=1000):
    # Use local variables (already aligned with session_state)
    variant_list = [row["variant_name"] for row in allocations_df.iter_rows(named=True)] if isinstance(allocations_df, pl.DataFrame) and allocations_df.height > 0 else variants
    if not variant_list:
        return False

    DEVICES = ["desktop", "mobile", "tablet"]
    LOCATIONS = ["USA", "CAN", "BRA", "FRA", "DEU"]
    USER_SEGMENTS = ["new_user", "returning_user", "vip"]
    BASE_CTR = {v: random.uniform(0.04, 0.07) for v in variant_list}

    if "decision_log" not in st.session_state:
        st.session_state.decision_log = []
    batch = []

    for _ in range(n_events):
        variant = random.choice(variant_list)
        device = random.choice(DEVICES)
        location = random.choice(LOCATIONS)
        segment = random.choice(USER_SEGMENTS)
        hour = random.randint(0, 23)
        impressions = random.randint(1, 5)
        ctr = BASE_CTR[variant]
        ctr *= 1.1 if device == "mobile" else 0.9 if device == "tablet" else 1.0
        ctr *= 1.5 if segment == "vip" else 0.8 if segment == "new_user" else 1.0
        ctr *= 1.2 if 18 <= hour <= 21 else 0.7 if 0 <= hour <= 6 else 1.0
        clicks = sum([1 if random.random() < ctr else 0 for _ in range(impressions)])
        base_cpc = 0.25 if clicks else 0.05
        cost = round(base_cpc * (1.2 if device == "mobile" else 0.9 if device == "tablet" else 1.0) *
                     (1.5 if segment == "vip" else 0.8 if segment == "new_user" else 1.0) *
                     (1.3 if location == "US" else 1.1 if location == "CA" else 0.7 if location == "BR" else 1.0), 4)

        batch.append({
            "experiment_name": experiment_name,
            "variant_name": variant,
            "impressions": impressions,
            "clicks": clicks,
            "event_date": str(date_selected),
            "cost": cost,
            "context": {"device": device, "location": location, "user_segment": segment, "hour": hour},
        })

        # Add decision log entry
        st.session_state.decision_log.append({
            "time_step": len(st.session_state.decision_log) + 1,
            "algorithm": algorithm,
            "variant_name": variant,
            "reward": clicks / impressions if impressions > 0 else 0,
            "impressions": impressions,
            "clicks": clicks,
            "context": {"device": device, "location": location, "user_segment": segment, "hour": hour}
        })

    if batch:
        try:
            resp = requests.post(f"{API_URL}/ingest", json=batch, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            st.error(f"Error sending events: {e}")
    return False

# ---------------------------
# LIVE SIMULATION CONTROL
# ---------------------------

# Flag to control if the button should be enabled
simulation_enabled = False
if param_tracker != current_params:
    simulation_enabled = True
    st.session_state["simulation_enabled"] = True
else:
    simulation_enabled = st.session_state.get("simulation_enabled", False)

with st.sidebar:
    if st.button(f"▶️ Start Simulation for {algorithm}", disabled=not simulation_enabled):
        st.session_state.is_watching = True
        st.session_state.remaining_events = int(total_events)
        st.session_state.last_batch_sent = 0
        st.session_state.refresh_key = st.session_state.get("refresh_key", 0) + 1
        st.session_state["simulation_enabled"] = False

if st.session_state.is_watching:
    st_autorefresh(interval=1000, limit=None, key=f"live_watch_{st.session_state.refresh_key}")
    if st.session_state.remaining_events > 0:
        events_to_send = min(int(batch_size), int(st.session_state.remaining_events))
        if simulate_events(events_to_send):
            st.session_state.remaining_events -= events_to_send
            st.session_state.last_batch_sent += events_to_send
            # Update data from API after sending batch
            a, m, mbc = load_data(experiment_name, date_selected, algorithm, epsilon, c_param, tau)
            st.session_state["allocations_df"] = a if isinstance(a, pl.DataFrame) else pl.DataFrame()
            st.session_state["metrics_df"] = m if isinstance(m, pl.DataFrame) else pl.DataFrame()
            st.session_state["metrics_by_context_df"] = mbc if isinstance(mbc, pl.DataFrame) else pl.DataFrame()
            # Update local variables
            allocations_df = st.session_state.get("allocations_df", pl.DataFrame())
            metrics_df = st.session_state.get("metrics_df", pl.DataFrame())
            metrics_by_context_df = st.session_state.get("metrics_by_context_df", pl.DataFrame())
    else:
        st.session_state.is_watching = False
        st.sidebar.success("✅ Simulation completed.")

# ---------------------------
# DASHBOARD DISPLAY
# ---------------------------

# 1. KPIs by Variant
if isinstance(metrics_df, pl.DataFrame) and metrics_df.height > 0:
    kpi_df = metrics_df.to_pandas()
    st.subheader("KPIs by Variant")
    st.caption("Quick performance summary for each variant.")

    kpi_cols = st.columns([2, 1, 1, 1, 1])
    with kpi_cols[0]:
        st.markdown("**Variant**")
    with kpi_cols[1]:
        st.markdown("**Impressions**")
    with kpi_cols[2]:
        st.markdown("**Clicks**")
    with kpi_cols[3]:
        st.markdown("**CTR**")
    with kpi_cols[4]:
        st.markdown("**Cost**")

    for i, row in kpi_df.iterrows():
        kpi_cols = st.columns([2, 1, 1, 1, 1])
        with kpi_cols[0]:
            st.markdown(f"{row['variant_name']}")
        with kpi_cols[1]:
            st.markdown(f"{row['impressions']}")
        with kpi_cols[2]:
            st.markdown(f"{row['clicks']}")
        with kpi_cols[3]:
            st.markdown(f"{row['ctr']*100:.2f}%")
        total_cost = row.get("total_cost", row.get("cost", 0.0))
        with kpi_cols[4]:
            st.markdown(f"${float(total_cost):.2f}")

# 2. Allocation Evolution Over Time
if "decision_log" in st.session_state and len(st.session_state.decision_log) > 0:
    df_log = pl.DataFrame(st.session_state.decision_log).to_pandas()
    n_bins = 10
    bin_size = total_events // n_bins
    df_log["time_bin"] = (df_log["time_step"] // bin_size) * bin_size

    df_alloc_evol = (
        df_log.groupby(["time_bin", "variant_name"])
        .size()
        .reset_index(name="allocations")
    )

    # Normalize within each bin so it shows proportions
    df_alloc_evol["total"] = df_alloc_evol.groupby("time_bin")["allocations"].transform("sum")
    df_alloc_evol["share"] = df_alloc_evol["allocations"] / df_alloc_evol["total"]

    st.subheader("Allocation Evolution Over Time")
    st.caption(f"Traffic allocation aggregated in bins of {bin_size} steps.")

    fig_alloc = px.area(
        df_alloc_evol,
        x="time_bin",
        y="share",
        color="variant_name",
        title="Traffic Allocation by Variant Over Time",
        groupnorm=None  # already normalized manually
    )
    st.plotly_chart(fig_alloc, use_container_width=True)
    
# 3. Decision Log / Cumulative Reward
if "decision_log" in st.session_state and len(st.session_state.decision_log) > 0:
    df_log["cumulative_mean_reward"] = df_log.groupby("variant_name")["reward"].transform(lambda x: x.expanding().mean())
    st.subheader("Cumulative Reward by Variant (Simulation)")
    st.caption("Performance over time for each variant.")
    fig_reward = px.line(df_log, x="time_step", y="cumulative_mean_reward", color="variant_name", title="Cumulative Reward by Variant")
    st.plotly_chart(fig_reward, use_container_width=True)

# 4. Experiment Metrics
if isinstance(metrics_df, pl.DataFrame) and metrics_df.height > 0:
    st.subheader("Experiment Metrics")
    st.caption("Summary by variant: impressions, clicks, CTR, cost.")
    st.dataframe(metrics_df, use_container_width=True)

# 5. Recommended Allocations
if isinstance(allocations_df, pl.DataFrame) and allocations_df.height > 0:
    st.subheader("Recommended Allocations")
    st.caption("Budget distribution among variants.")
    st.dataframe(allocations_df, use_container_width=True)

# 6. Cost-benefit Visualizations
if isinstance(metrics_by_context_df, pl.DataFrame) and metrics_by_context_df.height > 0:
    df_ctx = metrics_by_context_df.to_pandas()
    st.subheader("Cost vs CTR by Variant, Segment, Device")
    fig_ctx = px.scatter(df_ctx, x="total_cost", y="ctr", color="variant_name", symbol="device",
                         size="impressions", hover_data=["clicks", "user_segment", "device"],
                         facet_col="user_segment", title="CTR vs Cost by Variant, Segment, Device")
    st.plotly_chart(fig_ctx, use_container_width=True)

    st.subheader("Average CTR by Segment and Device")
    fig_bar = px.bar(df_ctx, x="user_segment", y="ctr", color="device", barmode="group", title="Average CTR by Segment and Device")
    st.plotly_chart(fig_bar, use_container_width=True)

# 7. Geographic Performance
if isinstance(metrics_by_context_df, pl.DataFrame) and metrics_by_context_df.height > 0:
    df_geo = metrics_by_context_df.to_pandas()
    st.subheader("Geographic Performance")
    st.caption("Performance metrics by geographic location.")
    # Agrupa por país e soma cliques/impressões
    df_geo_grouped = df_geo.groupby("location").agg({
        "impressions": "sum",
        "clicks": "sum"
    }).reset_index()
    df_geo_grouped["ctr"] = df_geo_grouped["clicks"] / df_geo_grouped["impressions"]
    fig_geo = px.choropleth(
        df_geo_grouped,
        locations="location",
        color="ctr",
        hover_data=["impressions", "clicks"],
        color_continuous_scale=px.colors.sequential.Viridis,
        title="CTR by Geographic Location",
        scope="world",
        projection="natural earth"
    )
    fig_geo.update_geos(
        showcountries=True,
        showcoastlines=True,
        showland=True,
        landcolor="#f7f7f7",
        countrycolor="#333"
    )
    fig_geo.update_traces(marker_line_width=1, marker_line_color="#333")
    fig_geo.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig_geo, use_container_width=True)

# 8. CTR Heatmap: Device x Segment
if isinstance(metrics_by_context_df, pl.DataFrame) and metrics_by_context_df.height > 0:
    df_ctx = metrics_by_context_df.to_pandas()
    if set(["device", "user_segment", "ctr"]).issubset(df_ctx.columns):
        pivot = df_ctx.pivot_table(index="device", columns="user_segment", values="ctr", aggfunc="mean")
        fig_heatmap = px.imshow(
            pivot,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Viridis",
            labels=dict(x="User Segment", y="Device", color="CTR")
        )
        st.subheader("CTR Heatmap: Device x Segment")
        st.plotly_chart(fig_heatmap, use_container_width=True)

# 9. Impressions & Clicks by Hour of Day
if "decision_log" in st.session_state and len(st.session_state.decision_log) > 0:
    df_log = pl.DataFrame(st.session_state.decision_log).to_pandas()
    if "context" in df_log.columns and set(["impressions", "clicks"]).issubset(df_log.columns):
        df_log["hour"] = df_log["context"].apply(lambda x: x.get("hour") if isinstance(x, dict) else None)
        hourly = df_log.groupby("hour")[["impressions", "clicks"]].sum().reset_index()
        fig_hour = px.bar(
            hourly,
            x="hour",
            y=["impressions", "clicks"],
            barmode="group",
            title="Impressions & Clicks by Hour of Day"
        )
        st.subheader("Impressions & Clicks by Hour of Day")
        st.plotly_chart(fig_hour, use_container_width=True)