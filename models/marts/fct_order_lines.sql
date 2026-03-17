-- Grain: one row per order line, i.e. one product within one order (not one
-- row per order — see README.md for why). Shipping and discount are charged
-- once per order, converted to EUR using the FX rate on the order's date,
-- then allocated across that order's lines by each line's share of gross
-- value. tests/assert_*_allocation_sums_correctly.sql prove the allocation
-- adds back up to the order-level amount.
--
-- Incremental: reprocesses a trailing lookback window of order_date_utc on
-- every run (not just rows newer than the last max), so upstream rows that
-- arrive late still get picked up.
{{
    config(
        materialized='incremental',
        unique_key='order_line_id',
        incremental_strategy='delete+insert',
    )
}}

with lines as (
    select * from {{ ref('stg_order_lines') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
    {% if is_incremental() %}
        where order_date_utc > (
            select
                coalesce(
                    max(prior_run.order_date_utc), timestamp '1900-01-01'
                )
            from {{ this }} as prior_run
        ) - interval '{{ var("late_arrival_lookback_days", 7) }} days'
    {% endif %}
),

fx_rates as (
    select * from {{ ref('stg_fx_rates') }}
),

line_values as (
    select
        lines.order_line_id,
        lines.order_id,
        lines.product_id,
        lines.quantity,
        lines.unit_price_eur,
        orders.customer_id,
        orders.order_date_utc,
        orders.status as order_status,
        orders.currency,
        orders.shipping_amount_local,
        orders.discount_amount_local,
        fx_rates.rate as eur_chf_rate,
        lines.quantity * lines.unit_price_eur as gross_amount_eur
    from lines
    inner join orders on lines.order_id = orders.order_id
    left join
        fx_rates
        on cast(orders.order_date_utc as date) = fx_rates.rate_date
),

order_totals as (
    select
        order_id,
        sum(gross_amount_eur) as order_gross_amount_eur,
        max({{ to_eur('shipping_amount_local', 'currency', 'eur_chf_rate') }})
            as order_shipping_amount_eur,
        max({{ to_eur('discount_amount_local', 'currency', 'eur_chf_rate') }})
            as order_discount_amount_eur
    from line_values
    group by order_id
)

select
    line_values.order_line_id,
    line_values.order_id,
    line_values.product_id,
    line_values.customer_id,
    cast(line_values.order_date_utc as date) as order_date,
    line_values.order_date_utc,
    line_values.order_status,
    line_values.currency,
    line_values.quantity,
    line_values.unit_price_eur,
    round(line_values.gross_amount_eur, 2) as gross_amount_eur,
    round(order_totals.order_shipping_amount_eur, 2)
        as order_shipping_amount_eur,
    round(order_totals.order_discount_amount_eur, 2)
        as order_discount_amount_eur,
    round(
        order_totals.order_shipping_amount_eur
        * (
            line_values.gross_amount_eur
            / nullif(order_totals.order_gross_amount_eur, 0)
        ),
        2
    ) as allocated_shipping_eur,
    round(
        order_totals.order_discount_amount_eur
        * (
            line_values.gross_amount_eur
            / nullif(order_totals.order_gross_amount_eur, 0)
        ),
        2
    ) as allocated_discount_eur,
    round(
        line_values.gross_amount_eur
        - (
            order_totals.order_discount_amount_eur
            * (
                line_values.gross_amount_eur
                / nullif(order_totals.order_gross_amount_eur, 0)
            )
        ),
        2
    ) as net_revenue_eur
from line_values
inner join order_totals on line_values.order_id = order_totals.order_id
