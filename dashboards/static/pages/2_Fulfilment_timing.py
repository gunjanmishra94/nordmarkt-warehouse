import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from data_source import load

st.set_page_config(page_title="Nordmarkt — Fulfilment timing", page_icon="📦", layout="wide")

st.title("Fulfilment timing")
st.caption(
    "Hours between lifecycle stages. Null until an order reaches that stage — there's no "
    '"picked" stage, see the main README\'s "What the numbers mean".'
)

summary = load("fulfilment-summary.json").iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric("Avg hours: placed to shipped", f"{summary.avg_hours_placed_to_shipped:.1f}")
col2.metric("Avg hours: shipped to delivered", f"{summary.avg_hours_shipped_to_delivered:.1f}")
col3.metric("Refund rate", f"{summary.refund_rate:.1%}")

by_month = load("fulfilment-by-month.json").set_index("month")

st.subheader("Avg hours placed to delivered, by month")
st.line_chart(by_month["avg_hours_placed_to_delivered"])

st.subheader("Fulfilment by status")
by_status = load("fulfilment-by-status.json")
st.dataframe(
    by_status.rename(
        columns={
            "order_status": "Status",
            "orders": "Orders",
            "avg_hours_placed_to_shipped": "Avg hrs to ship",
            "avg_hours_shipped_to_delivered": "Avg hrs to deliver",
        }
    ),
    hide_index=True,
    use_container_width=True,
)
