-- Grain: one row per product_id (latest load wins if a row was re-ingested).
with source as (
    select * from {{ source('raw', 'products') }}
),

renamed as (
    select
        product_id,
        name,
        category,
        supplier,
        price_eur,
        {{ to_utc_timestamp('created_at') }} as created_at_utc,
        _dlt_load_id,
        _dlt_id
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by product_id
            order by _dlt_load_id desc, _dlt_id desc
        ) as _rn
    from renamed
)

select
    product_id,
    name,
    category,
    supplier,
    price_eur,
    created_at_utc
from deduped
where _rn = 1
