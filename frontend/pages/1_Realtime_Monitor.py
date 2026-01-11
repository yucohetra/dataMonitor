import streamlit as st
import asyncio
import json
import pandas as pd
import plotly.express as px
import websockets
import os
import threading
import time
from collections import deque
from queue import Queue, Empty

from ui.auth_state import is_logged_in


st.set_page_config(page_title="Realtime Monitor", layout="wide")
st.title("Realtime Monitor")

# -----------------------
# Auth
# -----------------------
if not is_logged_in():
    st.warning("Login is required.")
    st.stop()

token = st.session_state["token"]
api_base = (
    os.getenv("API_BASE_URL", "http://localhost:8000")
    .replace("http://", "ws://")
    .replace("https://", "wss://")
    .rstrip("/")
)
ws_url = f"{api_base}/ws/realtime?token={token}"

# -----------------------
# Session-state init (UI thread only)
# -----------------------
if "rt_points" not in st.session_state:
    st.session_state["rt_points"] = deque(maxlen=200)

if "rt_freeze_view" not in st.session_state:
    st.session_state["rt_freeze_view"] = False

if "rt_refresh_sec" not in st.session_state:
    st.session_state["rt_refresh_sec"] = 1.0

if "rt_category_labels" not in st.session_state:
    st.session_state["rt_category_labels"] = {
        "A": "Category A",
        "B": "Category B",
        "C": "Category C",
    }

# Thread-safe queue for thread/UI data transfer.
if "rt_queue" not in st.session_state:
    st.session_state["rt_queue"] = Queue(maxsize=2000)

# Thread control objects.
if "rt_stop_event" not in st.session_state:
    st.session_state["rt_stop_event"] = threading.Event()

if "rt_thread" not in st.session_state:
    st.session_state["rt_thread"] = None


# -----------------------
# Background WebSocket receiver (NO session_state access inside)
# -----------------------
async def _ws_consumer(url: str, stop_event: threading.Event, out_q: Queue):
    """
    Receives realtime data from WebSocket and pushes into out_q.
    IMPORTANT: Do NOT touch st/session_state inside this function.
    """
    while not stop_event.is_set():
        try:
            async with websockets.connect(url) as ws:
                while not stop_event.is_set():
                    msg = await ws.recv()
                    payload = json.loads(msg)
                    if payload.get("event") != "realtime_data":
                        continue
                    event = payload["data"]

                    # non-blocking: if queue full, drop oldest then try again
                    try:
                        out_q.put_nowait(event)
                    except Exception:
                        try:
                            _ = out_q.get_nowait()
                        except Exception:
                            pass
                        try:
                            out_q.put_nowait(event)
                        except Exception:
                            pass
        except Exception:
            # reconnect backoff
            await asyncio.sleep(1.0)


def _ensure_ws_thread_running(url: str):
    """
    Starts WS background thread once. Safe to call every rerun.
    """
    t = st.session_state.get("rt_thread")
    if t is not None and t.is_alive():
        return

    stop_event = st.session_state["rt_stop_event"]
    out_q = st.session_state["rt_queue"]

    stop_event.clear()

    def runner(stop_event: threading.Event, out_q: Queue, url: str):
        asyncio.run(_ws_consumer(url, stop_event, out_q))

    t = threading.Thread(target=runner, args=(stop_event, out_q, url), daemon=True)
    st.session_state["rt_thread"] = t
    t.start()


# -----------------------
# Queue drain (UI thread only)
# -----------------------
def drain_queue_to_points(out_q: Queue, points: deque, max_drain: int = 1000) -> int:
    drained = 0
    while drained < max_drain:
        try:
            event = out_q.get_nowait()
        except Empty:
            break
        points.append(event)
        drained += 1
    return drained


# -----------------------
# Auto connect on page load
# -----------------------
_ensure_ws_thread_running(ws_url)

# -----------------------
# Sidebar controls (Freeze/Resume only)
# -----------------------
with st.sidebar:
    st.subheader("Controls")

    if not st.session_state["rt_freeze_view"]:
        if st.button("Freeze"):
            st.session_state["rt_freeze_view"] = True
            st.rerun()
    else:
        st.warning("Frozen (UI paused; background data intake continues).")
        if st.button("Resume"):
            st.session_state["rt_freeze_view"] = False
            st.rerun()

    st.session_state["rt_refresh_sec"] = st.slider(
        "UI refresh interval (seconds)",
        0.5,
        5.0,
        float(st.session_state["rt_refresh_sec"]),
        0.5,
        help="UI refresh rate (not the data generation rate).",
    )

    st.divider()
    st.subheader("What are A / B / C?")
    labels = st.session_state["rt_category_labels"].copy()
    labels["A"] = st.text_input("Label for A", value=labels.get("A", "A"))
    labels["B"] = st.text_input("Label for B", value=labels.get("B", "B"))
    labels["C"] = st.text_input("Label for C", value=labels.get("C", "C"))
    st.session_state["rt_category_labels"] = labels

    st.info(
        "A/B/C updating at different times does not necessarily indicate missing data; "
        "it can reflect different sources or frequencies."
    )

# -----------------------
# Update points from queue unless frozen
# -----------------------
if not st.session_state["rt_freeze_view"]:
    drain_queue_to_points(st.session_state["rt_queue"], st.session_state["rt_points"])

st.caption(f"WebSocket URL: {ws_url}")

# -----------------------
# Render chart + table
# -----------------------
points = list(st.session_state["rt_points"])
if not points:
    st.warning("No data yet. (WebSocket connected; waiting for first messages.)")
else:
    df = pd.DataFrame(points)
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")

    # Stable colors (avoid red)
    color_map = {
        "A": "#1f77b4",  # blue
        "B": "#2ca02c",  # green
        "C": "#9467bd",  # purple
    }

    # Ensure stable ordering
    df = df.sort_values("timestamp")

    fig = px.line(
        df,
        x="timestamp",
        y="value",
        color="category",
        category_orders={"category": ["A", "B", "C"]},
        color_discrete_map=color_map,
    )
    st.plotly_chart(fig, use_container_width=True)

    anomalies = df[df.get("is_anomaly") == True]
    st.write(f"Anomaly count (last {len(df)} points): {len(anomalies)}")

    show_n = st.selectbox("Show last N rows", [20, 50, 100, 200], index=0)
    st.dataframe(df.tail(int(show_n)), use_container_width=True)

# -----------------------
# Auto rerun
# - When NOT frozen: keep rerunning to update UI
# - When frozen: do NOT rerun; user can scroll/annotate
# -----------------------
if not st.session_state["rt_freeze_view"]:
    time.sleep(float(st.session_state["rt_refresh_sec"]))
    st.rerun()
