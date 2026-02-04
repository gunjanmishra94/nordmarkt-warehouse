"""SQL shared by both dashboard builds.

`app.py`/`pages/*.py` run these live, against a DuckDB connection, for the
Streamlit Community Cloud deploy. `static/build_data.py` runs the same
queries once at CI build time and dumps the results as JSON for the
account-free stlite (in-browser) build on GitHub Pages. One set of SQL,
two ways of serving the result — see DECISIONS.md for why there are two.
"""

REVENUE_TOTALS = """
    select
        sum(net_revenue_eur) as total_net_revenue_eur,
        count(distinct order_id) as total_orders
    from main.fct_order_lines
"""

REVENUE_BY_MONTH = """
    select date_trunc('month', order_date) as month, sum(net_revenue_eur) as net_revenue_eur
    from main.fct_order_lines
    group by 1
    order by 1
"""

REVENUE_BY_CURRENCY = """
    select currency, sum(net_revenue_eur) as net_revenue_eur, count(distinct order_id) as orders
    from main.fct_order_lines
    group by 1
    order by 2 desc
"""

CATEGORY_REVENUE = """
    select
        dim_product.category,
        sum(fct_order_lines.net_revenue_eur) as net_revenue_eur,
        count(distinct fct_order_lines.order_id) as orders
    from main.fct_order_lines
    inner join main.dim_product on fct_order_lines.product_id = dim_product.product_id
    group by 1
    order by 2 desc
"""

CATEGORY_REVENUE_BY_MONTH = """
    select
        date_trunc('month', fct_order_lines.order_date) as month,
        dim_product.category,
        sum(fct_order_lines.net_revenue_eur) as net_revenue_eur
    from main.fct_order_lines
    inner join main.dim_product on fct_order_lines.product_id = dim_product.product_id
    group by 1, 2
    order by 1, 2
"""

FULFILMENT_SUMMARY = """
    select
        avg(hours_placed_to_shipped) as avg_hours_placed_to_shipped,
        avg(hours_shipped_to_delivered) as avg_hours_shipped_to_delivered,
        avg(case when is_refunded then 1.0 else 0.0 end) as refund_rate
    from main.fct_order_fulfilment
"""

FULFILMENT_BY_MONTH = """
    select
        date_trunc('month', placed_at) as month,
        avg(hours_placed_to_delivered) as avg_hours_placed_to_delivered
    from main.fct_order_fulfilment
    where hours_placed_to_delivered is not null
    group by 1
    order by 1
"""

FULFILMENT_BY_STATUS = """
    select
        order_status,
        count(*) as orders,
        avg(hours_placed_to_shipped) as avg_hours_placed_to_shipped,
        avg(hours_shipped_to_delivered) as avg_hours_shipped_to_delivered
    from main.fct_order_fulfilment
    group by 1
    order by 2 desc
"""
