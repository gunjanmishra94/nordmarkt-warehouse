import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from data_source import load

st.set_page_config(page_title="Nordmarkt — Category trends", page_icon="📦", layout="wide")

st.title("Category trends")

category_revenue = load("category-revenue.json")
category_revenue["avg_order_value_eur"] = (
    category_revenue["net_revenue_eur"] / category_revenue["orders"]
)

st.subheader("Net revenue by category")
st.bar_chart(category_revenue.set_index("category")["net_revenue_eur"])

category_revenue_by_month = load("category-revenue-by-month.json")
pivoted = category_revenue_by_month.pivot(
    index="month", columns="category", values="net_revenue_eur"
)

st.subheader("Revenue by category, over time")
st.line_chart(pivoted)

st.subheader("Category detail")
st.dataframe(
    category_revenue.rename(
        columns={
            "category": "Category",
            "net_revenue_eur": "Net revenue (EUR)",
            "orders": "Orders",
            "avg_order_value_eur": "Avg order value (EUR)",
        }
    ),
    hide_index=True,
    use_container_width=True,
)
