-- Grain: one row per order_id. Some orders arrive twice in raw under the same
-- id (a deliberately injected duplicate); the latest load wins.
with source as (
    select * from {{ source('raw', 'orders') }}
),

renamed as (
    select
        order_id,
        customer_id,
        {{ to_utc_timestamp('order_date') }} as order_date_utc,
        currency,
        status,
        shipping_amount_local,
        discount_amount_local,
        _dlt_load_id,
        _dlt_id
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by order_id
            order by _dlt_load_id desc, _dlt_id desc
        ) as _rn
    from renamed
)

select
    order_id,
    customer_id,
    order_date_utc,
    currency,
    status,
    shipping_amount_local,
    discount_amount_local
from deduped
where _rn = 1
