-- Grain: one row per rate_date for the EUR->CHF pair.
with source as (
    select * from {{ source('raw', 'fx_rates') }}
),

renamed as (
    select
        cast(rate_date as date) as rate_date,
        base_currency,
        quote_currency,
        rate,
        _dlt_load_id,
        _dlt_id
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by rate_date, base_currency, quote_currency
            order by _dlt_load_id desc, _dlt_id desc
        ) as _rn
    from renamed
)

select
    rate_date,
    base_currency,
    quote_currency,
    rate
from deduped
where _rn = 1
