-- Grain: one row per order_line_id, i.e. one row per product within an order.
with source as (
    select * from {{ source('raw', 'order_lines') }}
),

renamed as (
    select
        order_line_id,
        order_id,
        product_id,
        quantity,
        unit_price_eur,
        _dlt_load_id,
        _dlt_id
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by order_line_id
            order by _dlt_load_id desc, _dlt_id desc
        ) as _rn
    from renamed
)

select
    order_line_id,
    order_id,
    product_id,
    quantity,
    unit_price_eur
from deduped
where _rn = 1
