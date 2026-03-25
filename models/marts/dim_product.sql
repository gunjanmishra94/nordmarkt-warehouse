-- Grain: one row per product_id.
select
    product_id,
    name,
    category,
    supplier,
    price_eur,
    created_at_utc,
    case
        when price_eur < 25 then 'budget'
        when price_eur < 100 then 'mid'
        else 'premium'
    end as price_band
from {{ ref('stg_products') }}
