import streamlit as st


def is_logged_in() -> bool:
    return "token" in st.session_state and bool(st.session_state["token"])


def set_auth(token: str, role: str) -> None:
    # NOTE:
    # - Session state is used to persist authentication across pages.
    st.session_state["token"] = token
    st.session_state["role"] = role


def clear_auth() -> None:
    st.session_state.pop("token", None)
    st.session_state.pop("role", None)
