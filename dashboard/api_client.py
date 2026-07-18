"""Thin HTTP wrappers around the Bandit Brain API, used by the Experiment page."""

from datetime import date, datetime, timedelta

import polars as pl
import requests
import streamlit as st
from config import API_URL


def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state['jwt_token']}"}


def ingest_batch(events: list[dict]) -> bool:
    """POST one batch of events to /ingest. Returns True on success."""
    try:
        resp = requests.post(f"{API_URL}/ingest", json=events, headers=_auth_headers(), timeout=10)
        if resp.status_code == 200:
            return True
        st.error(f"Failed to send batch: {resp.text}")
    except Exception as e:
        st.error(f"Error sending batch: {e}")
    return False


def fetch_allocations(exp_name, exp_date, method, epsilon=None, c=None, tau=None):
    if not isinstance(exp_date, date | datetime):
        exp_date_obj = date.fromisoformat(str(exp_date))
    else:
        exp_date_obj = exp_date.date() if isinstance(exp_date, datetime) else exp_date
    prediction_date = exp_date_obj + timedelta(days=1)
    payload = {"experiment_name": exp_name, "date": str(prediction_date), "method": method}
    if method == "eg" and epsilon is not None:
        payload["epsilon"] = epsilon
    if method == "ucb" and c is not None:
        payload["c"] = c
    if method == "softmax" and tau is not None:
        payload["tau"] = tau
    try:
        resp = requests.post(f"{API_URL}/recommend", json=payload, headers=_auth_headers(), timeout=10)
        if resp.status_code == 200:
            return pl.DataFrame(resp.json())
    except Exception as e:
        st.error(f"Error fetching allocations: {e}")
    return pl.DataFrame()


def fetch_metrics(exp_name, exp_date, group_by_context=False):
    params = {"experiment_name": exp_name, "date": str(exp_date), "group_by_context": str(group_by_context).lower()}
    try:
        resp = requests.get(f"{API_URL}/metrics", params=params, headers=_auth_headers(), timeout=10)
        if resp.status_code == 200:
            return pl.DataFrame(resp.json())
    except Exception as e:
        st.error(f"Error fetching metrics: {e}")
    return pl.DataFrame()


def fetch_experiments(exp_name, exp_date=None, limit=None):
    params = {"experiment_name": exp_name, "limit": limit}
    if exp_date:
        params["date"] = str(exp_date)
    try:
        resp = requests.get(f"{API_URL}/experiments", params=params, headers=_auth_headers(), timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Error fetching experiments: {e}")
    return []


def load_data(exp_name, exp_date, method, epsilon=None, c=None, tau=None):
    allocations = fetch_allocations(exp_name, exp_date, method, epsilon, c, tau)
    metrics = fetch_metrics(exp_name, exp_date)
    metrics_by_context = fetch_metrics(exp_name, exp_date, group_by_context=True)
    logs = fetch_experiments(exp_name, exp_date)
    decision_log_df = pl.DataFrame(logs) if logs else pl.DataFrame()
    return allocations, metrics, metrics_by_context, decision_log_df


def clear_data():
    """Remove all experiment and allocation data from backend."""
    try:
        delete_allocations = requests.delete(f"{API_URL}/allocations", headers=_auth_headers(), timeout=10)
        delete_experiments = requests.delete(f"{API_URL}/experiments", headers=_auth_headers(), timeout=10)
        if delete_allocations.status_code not in [200, 204]:
            st.warning(f"Failed to delete allocations: {delete_allocations.text}")
        if delete_experiments.status_code not in [200, 204]:
            st.warning(f"Failed to delete experiments: {delete_experiments.text}")
    except Exception as e:
        st.warning(f"Error calling deletion routes: {e}")

    # Clear local session data (always exclude)
    keys_to_reset = [
        "allocations_df",
        "metrics_df",
        "metrics_by_context_df",
        "decision_log_df",
        "is_watching",
        "remaining_events",
        "last_batch_sent",
        "refresh_key",
    ]
    for key in keys_to_reset:
        if key in st.session_state:
            if key.endswith("_df") or "allocations" in key or "metrics" in key or key == "decision_log_df":
                st.session_state[key] = pl.DataFrame()
            elif key == "is_watching":
                st.session_state[key] = False
            else:
                st.session_state[key] = 0
