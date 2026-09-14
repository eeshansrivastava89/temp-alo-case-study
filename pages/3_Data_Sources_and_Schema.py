from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from repository import AnalyticsRepository
from semantic_model import CONTEXT_LABELS, DIMENSIONS, METRICS

DB_PATH = ROOT / "data" / "analytics.db"


@st.cache_resource
def repository() -> AnalyticsRepository:
    return AnalyticsRepository(DB_PATH)


repo = repository()
inventory = repo.source_inventory()

st.title("Data Sources & Schema")
st.caption("Generated from the deployed SQLite database and metric registry")

st.header("Source files")
source_frame = pd.DataFrame(inventory).rename(
    columns={
        "source_file": "Excel file",
        "sheet": "Worksheet",
        "fact_table": "SQLite fact table",
        "metric_view": "Metric view",
        "rows": "Rows",
        "date_min": "Start date",
        "date_max": "End date",
    }
)
st.dataframe(source_frame, hide_index=True, width="stretch")

st.header("Data flow")
st.graphviz_chart(
    """
    digraph {
        rankdir=LR
        node [shape=box]
        excel [label="Excel files"]
        facts [label="Clean fact tables"]
        views [label="SQL metric views"]
        registry [label="Metric registry"]
        tools [label="Validated tools"]
        agent [label="AI analyst"]
        excel -> facts -> views -> registry -> tools -> agent
    }
    """,
    width="stretch",
)

st.header("Approved metric catalog")
metric_rows = []
for metric in METRICS.values():
    if metric.is_ratio:
        calculation = f"SUM({metric.numerator_ty}) / SUM({metric.denominator_ty})"
    else:
        calculation = f"SUM({metric.ty_column})"
    metric_rows.append(
        {
            "Metric ID": metric.id,
            "Display label": metric.label,
            "Context": CONTEXT_LABELS[metric.context],
            "Metric view": metric.view,
            "Calculation": calculation,
            "Allowed dimensions": ", ".join(DIMENSIONS[metric.context]),
        }
    )
st.dataframe(pd.DataFrame(metric_rows), hide_index=True, width="stretch")

st.header("Schema explorer")
selected_object = st.selectbox("SQLite table or view", repo.database_objects())
schema = pd.DataFrame(repo.object_schema(selected_object))
st.dataframe(schema, hide_index=True, width="stretch", height=420)

with st.expander("Reporting restrictions"):
    st.markdown(
        """
- The Digital country/state workbook owns top-line Digital metrics.
- The channel/device workbook contains GA metrics and remains a separately labeled diagnostic source.
- The Retail daily/store workbook owns Store metrics.
- The Retail product-category workbook is retained but excluded from the metric registry because its totals do not reconcile with Store Revenue.
- Combined Digital + Store revenue remains unavailable until currency and gross-versus-net definitions are confirmed.
"""
    )
