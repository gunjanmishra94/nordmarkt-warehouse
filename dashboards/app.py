import streamlit as st
from warehouse import query

st.set_page_config(page_title="Nordmarkt — Revenue overview", page_icon="📦", layout="wide")

st.title("Revenue overview")
st.caption(
    "Net revenue = quantity × unit price, minus this line's share of the order's discount. "
    'Shipping is excluded — see the main README\'s "What the numbers mean".'
)

totals = query("""
    select
        sum(net_revenue_eur) as total_net_revenue_eur,
        count(distinct order_id) as total_orders
    from main.fct_order_lines
""").iloc[0]

col1, col2 = st.columns(2)
col1.metric("Total net revenue", f"€{totals.total_net_revenue_eur:,.0f}")
col2.metric("Total orders", f"{totals.total_orders:,.0f}")

revenue_by_month = query("""
    select date_trunc('month', order_date) as month, sum(net_revenue_eur) as net_revenue_eur
    from main.fct_order_lines
    group by 1
    order by 1
""").set_index("month")

st.subheader("Net revenue by month")
st.line_chart(revenue_by_month["net_revenue_eur"])

st.subheader("Revenue by currency")
revenue_by_currency = query("""
    select currency, sum(net_revenue_eur) as net_revenue_eur, count(distinct order_id) as orders
    from main.fct_order_lines
    group by 1
    order by 2 desc
""")
st.dataframe(revenue_by_currency, hide_index=True, width="stretch")
