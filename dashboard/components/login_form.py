import requests
import streamlit as st

def login_form(API_URL: str):
    st.title("Login or Sign Up to Bandit Brain 🧠")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        login_clicked = st.button("Sign In", key="login", width="stretch")
    with col2:
        signup_clicked = st.button("Sign Up", key="signup", width="stretch")

    if login_clicked:
        login_payload = {"email": email, "password": password}
        resp = requests.post(f"{API_URL}/login", json=login_payload)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["jwt_token"] = data["access_token"]
            st.success("Successfully signed in!")
            st.rerun()
        else:
            st.error("Invalid credentials or login error.")
            st.session_state["jwt_token"] = None
            
    if signup_clicked:
        signup_payload = {"email": email, "password": password}
        resp = requests.post(f"{API_URL}/signup", json=signup_payload)
        if resp.status_code == 200:
            st.success("Sign up successful! Please sign in to continue.")
        elif resp.status_code == 400:
            st.error("Email already registered.")
        else:
            st.error("Error signing up user.")