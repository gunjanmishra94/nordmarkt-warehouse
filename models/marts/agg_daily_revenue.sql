-- Grain: one row per order_date. Exists purely to give dbt_expectations a
-- distribution to bound, a sanity check, not real anomaly detection.
select
    order_date,
    count(distinct order_id) as order_count,
    sum(net_revenue_eur) as net_revenue_eur
from {{ ref('fct_order_lines') }}
group by order_date
