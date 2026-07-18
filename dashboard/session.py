"""Shared login gate. Every page (app.py and each file under pages/) calls this
first — Streamlit runs each page as an independent script, so the check can't
live in just one place."""

import streamlit as st
from components.login_form import login_form


def require_login(api_url: str) -> None:
    if "jwt_token" not in st.session_state:
        login_form(api_url)
        st.stop()
