import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from warehouse import query

st.set_page_config(page_title="Nordmarkt — Category trends", page_icon="📦", layout="wide")

st.title("Category trends")

category_revenue = query("""
    select
        dim_product.category,
        sum(fct_order_lines.net_revenue_eur) as net_revenue_eur,
        count(distinct fct_order_lines.order_id) as orders
    from main.fct_order_lines
    inner join main.dim_product on fct_order_lines.product_id = dim_product.product_id
    group by 1
    order by 2 desc
""")
category_revenue["avg_order_value_eur"] = (
    category_revenue["net_revenue_eur"] / category_revenue["orders"]
)

st.subheader("Net revenue by category")
st.bar_chart(category_revenue.set_index("category")["net_revenue_eur"])

category_revenue_by_month = query("""
    select
        date_trunc('month', fct_order_lines.order_date) as month,
        dim_product.category,
        sum(fct_order_lines.net_revenue_eur) as net_revenue_eur
    from main.fct_order_lines
    inner join main.dim_product on fct_order_lines.product_id = dim_product.product_id
    group by 1, 2
    order by 1, 2
""")
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
    width="stretch",
)
