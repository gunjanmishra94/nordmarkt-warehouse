-- Fails (returns rows) if an order's total refunded amount exceeds the
-- gross value of what was actually ordered.
with order_value as (
    select
        order_id,
        sum(gross_amount_eur) as order_gross_amount_eur
    from {{ ref('fct_order_lines') }}
    group by order_id
),

refunds as (
    select
        order_id,
        sum(amount_eur) as total_refunded_eur
    from {{ ref('stg_refunds') }}
    group by order_id
)

select
    refunds.order_id,
    refunds.total_refunded_eur,
    order_value.order_gross_amount_eur
from refunds
inner join order_value on refunds.order_id = order_value.order_id
where refunds.total_refunded_eur > order_value.order_gross_amount_eur + 0.01
