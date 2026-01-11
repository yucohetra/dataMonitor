import streamlit as st
import asyncio
import pandas as pd
from datetime import datetime

from ui.api_client import get, post_json, put_json, delete, upload_csv, download
from ui.auth_state import is_logged_in


st.set_page_config(page_title="Records Manager", layout="wide")
st.title("Records Manager")

if not is_logged_in():
    st.warning("Login is required.")
    st.stop()

token = st.session_state["token"]
role = (st.session_state.get("role") or "").upper()


def _parse_iso_dt(s: str | None):
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    # Expect: 2026-01-11T08:34:14+00:00 or 2026-01-11 08:34:14
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


# -------------------------
# Shared query controls
# -------------------------
st.subheader("Query")
c1, c2, c3, c4 = st.columns(4)

category = c1.text_input("category (optional)")
is_anomaly = c2.selectbox("is_anomaly", ["(any)", "true", "false"])
sort_by = c3.selectbox("sort_by", ["timestamp", "value", "category", "id"])
order = c4.selectbox("order", ["desc", "asc"])

c5, c6, c7 = st.columns(3)
page = c5.number_input("page", min_value=1, value=1)
size = c6.number_input("size", min_value=1, max_value=200, value=50)
start_time = c7.text_input("start_time (ISO, optional)", value="")

c8, c9 = st.columns(2)
end_time = c8.text_input("end_time (ISO, optional)", value="")
# reserve c9 for future

params = {
    "page": int(page),
    "size": int(size),
    "sort_by": sort_by,
    "order": order,
}

if category.strip():
    params["category"] = category.strip()

if is_anomaly == "true":
    params["is_anomaly"] = True
elif is_anomaly == "false":
    params["is_anomaly"] = False

st_dt = _parse_iso_dt(start_time)
en_dt = _parse_iso_dt(end_time)
if start_time.strip() and st_dt is None:
    st.warning("start_time format invalid. Example: 2026-01-11T08:00:00+00:00")
elif st_dt is not None:
    params["start_time"] = st_dt.isoformat()

if end_time.strip() and en_dt is None:
    st.warning("end_time format invalid. Example: 2026-01-11T10:00:00+00:00")
elif en_dt is not None:
    params["end_time"] = en_dt.isoformat()


tabs = st.tabs(["Browse", "Create", "Update", "Delete", "Import CSV", "Export Excel"])

# -------------------------
# Browse
# -------------------------
with tabs[0]:
    st.subheader("Read (pagination / filter / sort)")
    if st.button("Search", key="btn_search"):
        async def do_search():
            return await get("/records", token=token, params=params)

        resp = asyncio.run(do_search())
        if resp.status_code == 200:
            data = resp.json()
            df = pd.DataFrame(data["items"])

            # Admin: try to show created_by -> username (best-effort)
            if not df.empty and "created_by" in df.columns and role == "ADMIN":
                try:
                    async def fetch_users():
                        return await get("/admin/users", token=token)

                    uresp = asyncio.run(fetch_users())
                    if uresp.status_code == 200:
                        users = uresp.json()
                        id_to_name = {u["id"]: u["username"] for u in users}
                        df["created_by_username"] = df["created_by"].map(lambda x: id_to_name.get(x, f"id={x}"))
                except Exception:
                    pass

            st.dataframe(df, use_container_width=True)
            st.caption(f"Total: {data['total']} | Page: {data['page']} | Size: {data['size']}")
        else:
            st.error(resp.text)

# -------------------------
# Create
# -------------------------
with tabs[1]:
    st.subheader("Create record")
    c1, c2, c3 = st.columns(3)
    title = c1.text_input("title", key="create_title")
    value = c2.number_input("value", value=0.0, step=0.1, key="create_value")
    category_c = c3.text_input("category", value="A", key="create_category")

    ts = st.text_input("timestamp (ISO, optional)", value="", key="create_ts")
    ts_dt = _parse_iso_dt(ts)

    payload = {
        "title": title.strip(),
        "value": float(value),
        "category": category_c.strip(),
        "timestamp": ts_dt.isoformat() if ts_dt else None,
    }

    if st.button("Create", key="btn_create"):
        if not payload["title"] or not payload["category"]:
            st.error("title and category are required.")
        elif ts.strip() and ts_dt is None:
            st.error("timestamp format invalid. Example: 2026-01-11T08:34:14+00:00")
        else:
            async def do_create():
                return await post_json("/records", payload, token=token)

            resp = asyncio.run(do_create())
            if resp.status_code == 200:
                st.success("Created.")
                st.json(resp.json())
            else:
                st.error(resp.text)

# -------------------------
# Update
# -------------------------
with tabs[2]:
    st.subheader("Update record (creator or ADMIN only)")
    record_id = st.number_input("record_id", min_value=1, value=1, step=1, key="upd_id")

    st.caption("Only provide fields you want to change. Leave blank to keep as-is.")
    u1, u2, u3 = st.columns(3)
    new_title = u1.text_input("title (optional)", value="", key="upd_title")
    new_value_str = u2.text_input("value (optional)", value="", key="upd_value")
    new_category = u3.text_input("category (optional)", value="", key="upd_category")

    new_ts = st.text_input("timestamp (ISO, optional)", value="", key="upd_ts")
    new_ts_dt = _parse_iso_dt(new_ts) if new_ts.strip() else None

    update_payload = {}
    if new_title.strip():
        update_payload["title"] = new_title.strip()
    if new_value_str.strip():
        try:
            update_payload["value"] = float(new_value_str.strip())
        except Exception:
            st.error("value must be a number.")
    if new_category.strip():
        update_payload["category"] = new_category.strip()
    if new_ts.strip():
        if new_ts_dt is None:
            st.error("timestamp format invalid.")
        else:
            update_payload["timestamp"] = new_ts_dt.isoformat()

    if st.button("Update", key="btn_update"):
        if not update_payload:
            st.warning("Nothing to update.")
        else:
            async def do_update():
                return await put_json(f"/records/{int(record_id)}", update_payload, token=token)

            resp = asyncio.run(do_update())
            if resp.status_code == 200:
                st.success("Updated.")
                st.json(resp.json())
            else:
                st.error(resp.text)

# -------------------------
# Delete
# -------------------------
with tabs[3]:
    st.subheader("Delete record (creator or ADMIN only)")
    del_id = st.number_input("record_id", min_value=1, value=1, step=1, key="del_id")
    st.warning("Delete is irreversible.")

    if st.button("Delete", key="btn_delete"):
        async def do_delete():
            return await delete(f"/records/{int(del_id)}", token=token)

        resp = asyncio.run(do_delete())
        if resp.status_code == 200:
            st.success("Deleted.")
            st.json(resp.json())
        else:
            st.error(resp.text)

# -------------------------
# Import CSV
# -------------------------
with tabs[4]:
    st.subheader("Batch import (CSV)")
    st.caption("CSV columns: title, value, category, timestamp(optional ISO).")

    up = st.file_uploader("Upload CSV", type=["csv"])
    if st.button("Import", key="btn_import"):
        if up is None:
            st.error("Please upload a CSV file.")
        else:
            file_bytes = up.getvalue()
            async def do_import():
                return await upload_csv("/records/import", file_bytes, up.name, token=token)

            resp = asyncio.run(do_import())
            if resp.status_code == 200:
                st.success("Import done.")
                st.json(resp.json())
            else:
                st.error(resp.text)

# -------------------------
# Export Excel
# -------------------------
with tabs[5]:
    st.subheader("Export Excel")
    st.caption("Export uses current query params (page/size/filter/sort/time range).")

    if st.button("Download Excel", key="btn_export"):
        async def do_export():
            return await download("/records/export", token=token, params=params)

        try:
            content = asyncio.run(do_export())
            st.download_button(
                "Download records_export.xlsx",
                data=content,
                file_name="records_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(str(e))
