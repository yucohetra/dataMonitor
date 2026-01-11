import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px

from ui.api_client import get
from ui.auth_state import is_logged_in


st.set_page_config(page_title="Analytics", layout="wide")
st.title("Analytics")

if not is_logged_in():
    st.warning("Login is required.")
    st.stop()

token = st.session_state["token"]

if st.button("Load Summary"):
    async def do_summary():
        return await get("/analytics/summary", token=token)

    resp = asyncio.run(do_summary())
    if resp.status_code == 200:
        s = resp.json()
        st.metric("count", s["count"])
        st.metric("avg", s["avg"])
        st.metric("min", s["min"])
        st.metric("max", s["max"])
    else:
        st.error(resp.text)

if st.button("Load By Category"):
    async def do_cat():
        return await get("/analytics/by-category", token=token)

    resp = asyncio.run(do_cat())
    if resp.status_code == 200:
        rows = resp.json()
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        fig = px.bar(df, x="category", y="avg")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(resp.text)
