import streamlit as st
import asyncio

from ui.api_client import post_json
from ui.auth_state import is_logged_in, set_auth, clear_auth


st.set_page_config(page_title="Realtime Monitoring System", layout="wide")
st.title("Realtime Monitoring System")

if is_logged_in():
    st.success(f"Logged in as role: {st.session_state.get('role')}")
    if st.button("Logout"):
        clear_auth()
        st.rerun()

else:
    tabs = st.tabs(["Login", "Register"])

    # -----------------------
    # Login tab
    # -----------------------
    with tabs[0]:
        st.subheader("Login")
        email = st.text_input("Email", value="admin@example.com", key="login_email")
        password = st.text_input("Password", type="password", value="Password123!", key="login_password")

        if st.button("Login", key="login_btn"):
            async def do_login():
                return await post_json("/auth/login", {"email": email, "password": password})

            resp = asyncio.run(do_login())
            if resp.status_code == 200:
                data = resp.json()
                set_auth(data["access_token"], data["role"])
                st.rerun()
            else:
                st.error(resp.text)

    # -----------------------
    # Register tab
    # -----------------------
    with tabs[1]:
        st.subheader("Register")

        reg_email = st.text_input("Email", key="reg_email")
        reg_username = st.text_input("Username", key="reg_username")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        reg_password2 = st.text_input("Confirm Password", type="password", key="reg_password2")

        # Optional: basic client-side validation to fail fast before API calls.
        if st.button("Create Account", key="register_btn"):
            # basic validation
            if not reg_email.strip():
                st.error("Email is required.")
                st.stop()
            if not reg_username.strip():
                st.error("Username is required.")
                st.stop()
            if not reg_password:
                st.error("Password is required.")
                st.stop()
            if reg_password != reg_password2:
                st.error("Passwords do not match.")
                st.stop()

            async def do_register():
                return await post_json(
                    "/auth/register",
                    {"email": reg_email.strip(), "username": reg_username.strip(), "password": reg_password},
                )

            resp = asyncio.run(do_register())

            if resp.status_code == 200:
                st.success("Registration successful. Logging you in...")

                # Auto-login after registration because /auth/register returns no token.
                async def do_login_after_register():
                    return await post_json("/auth/login", {"email": reg_email.strip(), "password": reg_password})

                login_resp = asyncio.run(do_login_after_register())
                if login_resp.status_code == 200:
                    data = login_resp.json()
                    set_auth(data["access_token"], data["role"])
                    st.rerun()
                else:
                    # Fallback for registration success but auto-login failure.
                    st.warning("Registered, but auto-login failed. Please login manually.")
                    st.error(login_resp.text)

            else:
                # Register returns 400 + detail (e.g., email/username already exists).
                st.error(resp.text)
