import streamlit as st
from data_source import load

st.set_page_config(page_title="Nordmarkt — Revenue overview", page_icon="📦", layout="wide")

st.title("Revenue overview")
st.caption(
    "Net revenue = quantity × unit price, minus this line's share of the order's discount. "
    'Shipping is excluded — see the main README\'s "What the numbers mean". '
    "Numbers here are a snapshot from the last build, not live — see the main README."
)

totals = load("revenue-totals.json").iloc[0]

col1, col2 = st.columns(2)
col1.metric("Total net revenue", f"€{totals.total_net_revenue_eur:,.0f}")
col2.metric("Total orders", f"{totals.total_orders:,.0f}")

revenue_by_month = load("revenue-by-month.json").set_index("month")

st.subheader("Net revenue by month")
st.line_chart(revenue_by_month["net_revenue_eur"])

st.subheader("Revenue by currency")
st.dataframe(load("revenue-by-currency.json"), hide_index=True, use_container_width=True)
