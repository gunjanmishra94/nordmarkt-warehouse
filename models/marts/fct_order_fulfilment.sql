-- Grain: one row per order, updated as it moves through its lifecycle
-- (accumulating snapshot). Tracks placed -> shipped -> delivered -> refunded.
-- There's no "picked" stage: the generator never produces one, only orders,
-- shipments (shipped/delivered) and refunds — see DECISIONS.md.
--
-- Incremental like fct_order_lines: reprocesses a trailing lookback window,
-- but on recorded_at (when the source system learned about the event) rather
-- than occurred_at, since shipment/refund events can be recorded days after
-- they actually happened. That's what actually needs a lookback: an order's
-- row can need updating well after it was first placed.
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='delete+insert',
    )
}}

with orders as (
    select * from {{ ref('stg_orders') }}
),

shipments as (
    select * from {{ ref('stg_shipments') }}
),

refunds as (
    select * from {{ ref('stg_refunds') }}
),

shipped as (
    select
        order_id,
        min(occurred_at_utc) as shipped_at,
        max(recorded_at_utc) as shipped_recorded_at
    from shipments
    where status in ('shipped', 'delivered')
    group by order_id
),

delivered as (
    select
        order_id,
        min(occurred_at_utc) as delivered_at,
        max(recorded_at_utc) as delivered_recorded_at
    from shipments
    where status = 'delivered'
    group by order_id
),

refunded as (
    select
        order_id,
        min(occurred_at_utc) as refunded_at,
        max(recorded_at_utc) as refunded_recorded_at
    from refunds
    group by order_id
),

joined as (
    select
        orders.order_id,
        orders.customer_id,
        orders.status as order_status,
        orders.order_date_utc as placed_at,
        shipped.shipped_at,
        delivered.delivered_at,
        refunded.refunded_at,
        greatest(
            orders.order_date_utc,
            coalesce(shipped.shipped_recorded_at, orders.order_date_utc),
            coalesce(delivered.delivered_recorded_at, orders.order_date_utc),
            coalesce(refunded.refunded_recorded_at, orders.order_date_utc)
        ) as last_recorded_at
    from orders
    left join shipped on orders.order_id = shipped.order_id
    left join delivered on orders.order_id = delivered.order_id
    left join refunded on orders.order_id = refunded.order_id
    {% if is_incremental() %}
        where
            greatest(
                orders.order_date_utc,
                coalesce(shipped.shipped_recorded_at, orders.order_date_utc),
                coalesce(
                    delivered.delivered_recorded_at, orders.order_date_utc
                ),
                coalesce(refunded.refunded_recorded_at, orders.order_date_utc)
            )
            > (
                select
                    coalesce(
                        max(prior_run.last_recorded_at), timestamp '1900-01-01'
                    )
                from {{ this }} as prior_run
            ) - interval '{{ var("late_arrival_lookback_days", 7) }} days'
    {% endif %}
)

select
    order_id,
    customer_id,
    order_status,
    placed_at,
    shipped_at,
    delivered_at,
    refunded_at,
    last_recorded_at,
    refunded_at is not null as is_refunded,
    {{ date_diff_hours('placed_at', 'shipped_at') }}
        as hours_placed_to_shipped,
    {{ date_diff_hours('shipped_at', 'delivered_at') }}
        as hours_shipped_to_delivered,
    {{ date_diff_hours('placed_at', 'delivered_at') }}
        as hours_placed_to_delivered
from joined
