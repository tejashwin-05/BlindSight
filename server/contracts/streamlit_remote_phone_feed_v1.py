"""
EcoSight Remote Phone Feed Viewer (v1)
Simple Streamlit app that shows phone camera feed from v1 stream endpoint.
"""

from __future__ import annotations

import streamlit as st


st.set_page_config(page_title="Remote Phone Feed v1", layout="wide")
st.title("Remote Phone Feed v1")
st.caption("Simple test viewer for phone → laptop feed via remote_camera_server_v1")

base_url = st.text_input("Server Base URL", value="http://127.0.0.1:8080")
api_key = st.text_input("API Key (optional)", value="", type="password")

normalized = base_url.rstrip("/")
stream_url = f"{normalized}/v1/stream.mjpg"
if api_key:
    stream_url = f"{stream_url}?api_key={api_key}"

st.markdown(
    f"""
    <div style=\"border-radius:12px;overflow:hidden;border:1px solid #ddd;\">
      <img src=\"{stream_url}\" style=\"width:100%;height:auto;display:block;\" />
    </div>
    """,
    unsafe_allow_html=True,
)

st.info("If blank, start phone stream first and verify base URL/API key.")
st.code(stream_url, language="text")
