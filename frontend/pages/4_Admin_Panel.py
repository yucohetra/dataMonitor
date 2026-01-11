import streamlit as st
import asyncio
import pandas as pd

from ui.api_client import get, patch_json
from ui.auth_state import is_logged_in


st.set_page_config(page_title="Admin Panel", layout="wide")
st.title("Admin Panel")

if not is_logged_in():
    st.warning("Login is required.")
    st.stop()

token = st.session_state["token"]
role = (st.session_state.get("role") or "").upper()

if role != "ADMIN":
    st.error("ADMIN role is required.")
    st.stop()

tabs = st.tabs(["Users", "Role Management", "Logs", "System Status", "DB Status"])


# -------------------------
# Helpers
# -------------------------
def fetch_users_and_cache():
    async def do_users():
        return await get("/admin/users", token=token)

    resp = asyncio.run(do_users())
    if resp.status_code == 200:
        st.session_state["admin_users_cache"] = resp.json()
        st.session_state["admin_users_last_error"] = None
    else:
        st.session_state["admin_users_last_error"] = resp.text


def get_users_cache() -> list[dict]:
    return st.session_state.get("admin_users_cache") or []


# -------------------------
# Users
# -------------------------
with tabs[0]:
    st.subheader("User list")

    # Auto-load once on first entry or missing cache to avoid manual refresh.
    if "admin_users_cache" not in st.session_state and "admin_users_last_error" not in st.session_state:
        fetch_users_and_cache()

    col1, col2 = st.columns([1, 4])
    if col1.button("Refresh Users", key="admin_refresh_users"):
        fetch_users_and_cache()
        st.rerun()

    err = st.session_state.get("admin_users_last_error")
    if err:
        st.error(err)

    users_cache = get_users_cache()
    if users_cache:
        df = pd.DataFrame(users_cache)

        # Hide id column for UI display.
        if "id" in df.columns:
            df_view = df.drop(columns=["id"])
        else:
            df_view = df

        st.dataframe(df_view, use_container_width=True)
        st.caption(f"Total users: {len(users_cache)}")
    else:
        st.info("No users loaded yet.")


# -------------------------
# Role management
# -------------------------
with tabs[1]:
    st.subheader("Update user role")

    users_cache = get_users_cache()
    if not users_cache:
        st.info("No users cache. Please refresh users in the Users tab first.")
    else:
        # Use username selector and display "username (email)" to reduce ambiguity.
        option_to_user = {}
        options = []
        for u in users_cache:
            label = f'{u.get("username", "")} ({u.get("email", "")})'
            options.append(label)
            option_to_user[label] = u

        selected_label = st.selectbox("Select user (by username)", options=options, key="admin_select_user_by_name")
        selected_user = option_to_user[selected_label]
        selected_id = int(selected_user["id"])

        st.write(
            f'email: {selected_user.get("email")} | '
            f'username: {selected_user.get("username")} | '
            f'current role: {selected_user.get("role")}'
        )

        current_role = (selected_user.get("role") or "").upper()
        new_role = st.selectbox(
            "New role",
            ["ADMIN", "USER"],
            index=0 if current_role == "ADMIN" else 1,
            key="admin_new_role",
        )

        if st.button("Update Role", key="admin_update_role"):
            async def do_patch():
                return await patch_json(f"/admin/users/{selected_id}/role", {"role": new_role}, token=token)

            resp = asyncio.run(do_patch())
            if resp.status_code == 200:
                st.success("Role updated.")
                # Refresh cache after update to avoid stale UI data.
                fetch_users_and_cache()
                st.rerun()
            else:
                st.error(resp.text)


# -------------------------
# Logs
# -------------------------
with tabs[2]:
    st.subheader("System logs")

    limit = st.number_input("limit", min_value=1, max_value=2000, value=200, step=50)
    if st.button("Refresh Logs", key="admin_refresh_logs"):
        async def do_logs():
            return await get("/admin/logs", token=token, params={"limit": int(limit)})

        resp = asyncio.run(do_logs())
        if resp.status_code == 200:
            logs = resp.json()
            df = pd.DataFrame(logs)
            st.dataframe(df, use_container_width=True)
            st.caption(f"Total logs shown: {len(logs)}")
        else:
            st.error(resp.text)


# -------------------------
# System Status
# -------------------------
with tabs[3]:
    st.subheader("Runtime status (generator / ws / buffer / flush)")

    if st.button("Refresh System Status", key="admin_refresh_system"):
        async def do_status():
            return await get("/admin/system/status", token=token)

        resp = asyncio.run(do_status())
        if resp.status_code == 200:
            st.json(resp.json())
        else:
            st.error(resp.text)


# -------------------------
# DB Status
# -------------------------
with tabs[4]:
    st.subheader("DB status")

    if st.button("Refresh DB Status", key="admin_refresh_db"):
        async def do_db():
            return await get("/admin/db/status", token=token)

        resp = asyncio.run(do_db())
        if resp.status_code == 200:
            st.json(resp.json())
        else:
            st.error(resp.text)
