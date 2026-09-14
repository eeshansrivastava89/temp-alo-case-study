from __future__ import annotations

from pathlib import Path

import streamlit as st
from nbconvert import HTMLExporter

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "01_data_audit_and_semantic_contract.ipynb"


@st.cache_data(show_spinner=False)
def notebook_html(path: str, modified_ns: int) -> str:
    del modified_ns
    exporter = HTMLExporter(template_name="classic")
    html, _ = exporter.from_filename(path)
    return html


st.title("Analysis Notebook")
st.caption("The executed notebook is rendered directly; this page contains no copied analysis or curated output.")

st.download_button(
    "Download notebook",
    data=NOTEBOOK_PATH.read_bytes(),
    file_name=NOTEBOOK_PATH.name,
    mime="application/x-ipynb+json",
)

html = notebook_html(str(NOTEBOOK_PATH), NOTEBOOK_PATH.stat().st_mtime_ns)
st.iframe(html, width="stretch", height="content")
