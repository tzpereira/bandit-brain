import base64
from datetime import date

import charts
import polars as pl
import streamlit as st
from api_client import clear_data, ingest_batch, load_data
from config import API_URL
from session import require_login
from simulate import simulate_events
from streamlit_autorefresh import st_autorefresh
from streamlit_tags import st_tags

require_login(API_URL)

st.set_page_config(page_title="Bandit Brain - Experiment", layout="wide")

st.title("🧠 Bandit Brain")

if "expander_open" not in st.session_state:
    st.session_state["expander_open"] = True

with st.expander("Bandit Brain Settings", expanded=st.session_state["expander_open"]):
    # Track any parameter that should reset the data if changed
    param_tracker = st.session_state.get("param_tracker", {})

    col1, col2 = st.columns(2, vertical_alignment="top")

    with col1:
        upload_mode = st.radio(
            "Data Input Mode", ["Upload historical data (CSV)", "Simulate live data"], key="data_mode"
        )

        # Orientation message for each mode
        if upload_mode == "Upload historical data (CSV)":
            st.markdown(
                "<span style='color:gray;'>Upload a CSV file with historical experiment data. Only aggregate visualizations will be shown.</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span style='color:gray;'>Simulate live data for step-by-step bandit learning and visualizations.</span>",
                unsafe_allow_html=True,
            )

        experiment_name = st.text_input(
            "Experiment Name", "homepage_test", disabled=(upload_mode == "Upload historical data (CSV)")
        )

        date_selected = st.date_input("Date", date.today())

        algorithm = st.selectbox("Algorithm", ["eg", "ucb", "ts", "softmax"])

        # Variants selection
        if (
            "allocations_df" in st.session_state
            and isinstance(st.session_state.allocations_df, pl.DataFrame)
            and st.session_state.allocations_df.height > 0
        ):
            unique_variants = st.session_state.allocations_df["variant_name"].unique().to_list()
        elif (
            "metrics_df" in st.session_state
            and isinstance(st.session_state.metrics_df, pl.DataFrame)
            and st.session_state.metrics_df.height > 0
        ):
            unique_variants = st.session_state.metrics_df["variant_name"].unique().to_list()
        else:
            unique_variants = ["A", "B"]

        if upload_mode == "Upload historical data (CSV)":
            st.markdown("<span style='color:gray;'>Variants (from CSV):</span>", unsafe_allow_html=True)
            variants_list = st.session_state.get("variants", unique_variants)
            st.markdown(", ".join([str(v) for v in variants_list]))
            variants = variants_list
        else:
            variants = st_tags(
                label="Variants",
                text="Press enter to add",
                value=st.session_state.get("variants", unique_variants),
                suggestions=unique_variants,
                maxtags=10,
                key="variants",
            )

    with col2:
        colA, colB = st.columns([2.5, 1], vertical_alignment="center")
        with colA:
            uploaded_file = st.file_uploader(
                "Upload CSV file", type=["csv"], key="csv_uploader", disabled=(upload_mode == "Simulate data")
            )
            if uploaded_file is not None:
                try:
                    df_csv = pl.read_csv(uploaded_file)
                except Exception as e:
                    st.error(f"Failed to read CSV: {e}")
        with colB:
            template_df = pl.DataFrame(
                {
                    "variant_name": [],
                    "impressions": [],
                    "clicks": [],
                    "cost": [],
                    "device": [],
                    "location": [],
                    "user_segment": [],
                    "hour": [],
                }
            )

            csv_bytes = template_df.write_csv()
            b64 = base64.b64encode(csv_bytes.encode()).decode()

            href = f"""
                <a href="data:file/csv;base64,{b64}" download="csv_template.csv" style="font-size:1.1em;">Download CSV template ⬇️</a>
            """
            st.markdown(href, unsafe_allow_html=True)

        batch_size = st.number_input(
            "Batch Size",
            min_value=10,
            max_value=10000,
            value=100,
            disabled=(upload_mode == "Upload historical data (CSV)"),
        )
        total_events = st.number_input(
            "Total Events to Simulate",
            min_value=100,
            max_value=100000,
            value=1000,
            disabled=(upload_mode == "Upload historical data (CSV)"),
        )

        epsilon = st.slider("Epsilon (EG)", 0.0, 1.0, 0.1) if algorithm == "eg" else None
        c_param = st.slider("C (UCB)", 0.0, 5.0, 2.0) if algorithm == "ucb" else None
        tau = st.slider("Tau (Softmax)", 0.01, 2.0, 0.1) if algorithm == "softmax" else None

    # Flag to control if the button should be enabled
    run_enabled = False

    current_params = {
        "upload_mode": upload_mode,
        "experiment_name": experiment_name,
        "date": str(date_selected),
        "algorithm": algorithm,
        "epsilon": epsilon,
        "c_param": c_param,
        "tau": tau,
        "variants": variants,
    }

    # Button enabled logic
    if param_tracker != current_params:
        if upload_mode == "Upload historical data (CSV)" and uploaded_file is None:
            run_enabled = False
            st.session_state["run_enabled"] = False
        else:
            run_enabled = True
            st.session_state["run_enabled"] = True
    else:
        run_enabled = st.session_state.get("run_enabled", False)

    col1, col2 = st.columns([1, 1])

    with col1:
        clear_clicked = st.button(
            "🗑️ Clear Data", key="clear_data_btn", help="Delete all experiment and allocation data.", width="stretch"
        )
        if clear_clicked:
            clear_data()

    with col2:
        run_clicked = st.button(
            f"🚀 Run {algorithm} Bandit Brain",
            disabled=not run_enabled,
            key="run_btn",
            help="Start simulation or experiment.",
            width="stretch",
        )

        if run_clicked:
            # Sempre desativa botão e fecha expander após rodar
            st.session_state["run_enabled"] = False
            st.session_state["expander_open"] = False

            if upload_mode == "Upload historical data (CSV)":
                if df_csv is not None:
                    batch = []

                    for row in df_csv.iter_rows(named=True):
                        context = {}
                        for ctx_field in ["device", "location", "user_segment", "hour"]:
                            if ctx_field in row:
                                context[ctx_field] = row[ctx_field]
                        batch.append(
                            {
                                "experiment_name": st.session_state.get("experiment_name", "homepage_test"),
                                "variant_name": row.get("variant_name", "A"),
                                "impressions": int(row.get("impressions", 1)),
                                "clicks": int(row.get("clicks", 0)),
                                "event_date": str(date_selected),
                                "cost": float(row.get("cost", 0.0)),
                                "context": context,
                            }
                        )

                    n_rows = len(batch)
                    batch_size = max(1, n_rows // 10)
                    success = True

                    for i in range(0, n_rows, batch_size):
                        batch_slice = batch[i : i + batch_size]
                        if not ingest_batch(batch_slice):
                            success = False

                    if success:
                        a, m, mbc, decision_log_df = load_data(
                            experiment_name, date_selected, algorithm, epsilon, c_param, tau
                        )
                        st.session_state["allocations_df"] = a if isinstance(a, pl.DataFrame) else pl.DataFrame()
                        st.session_state["metrics_df"] = m if isinstance(m, pl.DataFrame) else pl.DataFrame()
                        st.session_state["metrics_by_context_df"] = (
                            mbc if isinstance(mbc, pl.DataFrame) else pl.DataFrame()
                        )
                        st.session_state["decision_log_df"] = (
                            decision_log_df if isinstance(decision_log_df, pl.DataFrame) else pl.DataFrame()
                        )
                        st.session_state.is_watching = False
                        st.session_state.remaining_events = 0
                        st.session_state.last_batch_sent = n_rows
                        st.session_state.refresh_key = st.session_state.get("refresh_key", 0) + 1
                else:
                    st.error("No CSV file uploaded.")
            elif upload_mode == "Simulate live data":
                st.session_state.is_watching = True
                st.session_state.remaining_events = int(total_events)
                st.session_state.last_batch_sent = 0
                st.session_state.refresh_key = st.session_state.get("refresh_key", 0) + 1

# ---------------------------
# RESET SESSION IF PARAMETERS CHANGE
# ---------------------------
if param_tracker != current_params:
    clear_data()

    # Reinitialize session state variables
    st.session_state["allocations_df"] = st.session_state.get("allocations_df", pl.DataFrame())
    st.session_state["metrics_df"] = st.session_state.get("metrics_df", pl.DataFrame())
    st.session_state["metrics_by_context_df"] = st.session_state.get("metrics_by_context_df", pl.DataFrame())
    st.session_state["is_watching"] = False
    st.session_state["remaining_events"] = 0
    st.session_state["last_batch_sent"] = 0
    st.session_state["refresh_key"] = st.session_state.get("refresh_key", 0) + 1

    st.session_state["param_tracker"] = current_params

    allocations_df = pl.DataFrame()
    metrics_df = pl.DataFrame()
    metrics_by_context_df = pl.DataFrame()

# ---------------------------
# INITIALIZATION
# ---------------------------
for key in ["is_watching", "remaining_events", "last_batch_sent", "refresh_key"]:
    if key not in st.session_state:
        st.session_state[key] = 0 if "remaining" in key or "last_batch" in key else False

# ---------------------------
# Local Variables
# ---------------------------
allocations_df = st.session_state.get("allocations_df", pl.DataFrame())
metrics_df = st.session_state.get("metrics_df", pl.DataFrame())
metrics_by_context_df = st.session_state.get("metrics_by_context_df", pl.DataFrame())
decision_log_df = st.session_state.get("decision_log_df", pl.DataFrame())

# Remove unwanted columns
if isinstance(allocations_df, pl.DataFrame):
    for col in ["id", "created_at"]:
        if col in allocations_df.columns:
            allocations_df = allocations_df.drop(col)

# ---------------------------
# LIVE SIMULATION CONTROL
# ---------------------------

# Flag to control if the button should be enabled
run_enabled = False
if param_tracker != current_params:
    run_enabled = True
    st.session_state["run_enabled"] = True
else:
    run_enabled = st.session_state.get("run_enabled", False)

if st.session_state.is_watching:
    st_autorefresh(interval=1000, limit=None, key=f"live_watch_{st.session_state.refresh_key}")
    if st.session_state.remaining_events > 0:
        events_to_send = min(int(batch_size), int(st.session_state.remaining_events))
        if simulate_events(events_to_send, allocations_df, variants, experiment_name, date_selected, batch_size):
            st.session_state.remaining_events -= events_to_send
            st.session_state.last_batch_sent += events_to_send
            # Update data from API after sending batch
            a, m, mbc, decision_log_df = load_data(experiment_name, date_selected, algorithm, epsilon, c_param, tau)
            st.session_state["allocations_df"] = a if isinstance(a, pl.DataFrame) else pl.DataFrame()
            st.session_state["metrics_df"] = m if isinstance(m, pl.DataFrame) else pl.DataFrame()
            st.session_state["metrics_by_context_df"] = mbc if isinstance(mbc, pl.DataFrame) else pl.DataFrame()
            st.session_state["decision_log_df"] = (
                decision_log_df if isinstance(decision_log_df, pl.DataFrame) else pl.DataFrame()
            )
            # Update local variables
            allocations_df = st.session_state.get("allocations_df", pl.DataFrame())
            metrics_df = st.session_state.get("metrics_df", pl.DataFrame())
            metrics_by_context_df = st.session_state.get("metrics_by_context_df", pl.DataFrame())
            decision_log_df = st.session_state.get("decision_log_df", pl.DataFrame())
    else:
        st.session_state.is_watching = False

# ---------------------------
# DASHBOARD DISPLAY
# ---------------------------
charts.render_kpis(metrics_df)
charts.render_allocation_evolution(decision_log_df, total_events)
charts.render_cumulative_ctr(decision_log_df)
charts.render_metrics_table(metrics_df)
charts.render_allocations_table(allocations_df)
charts.render_cost_ctr_breakdown(metrics_by_context_df)
charts.render_geo(metrics_by_context_df)
charts.render_heatmap(metrics_by_context_df)
charts.render_hourly(decision_log_df)

# Footer
st.markdown(
    """
    <style>
        .footer {
            text-align: center;
            margin-top: 2em;
        }
    </style>
    <div class='footer'>
        <span>Made by <a href='https://github.com/tzpereira' target='_blank' style='color:#FF69B4; text-decoration:none;'><b>Mateus</b></a> &middot; Powered by Streamlit</span>
    </div>
""",
    unsafe_allow_html=True,
)


def on_session_end():
    """Callback to clear all user data when session ends (tab closed or refreshed)."""
    clear_data()


if hasattr(st, "on_session_end"):
    st.on_session_end(on_session_end)
