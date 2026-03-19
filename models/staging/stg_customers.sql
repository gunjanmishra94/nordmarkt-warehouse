-- Grain: one row per customer_id (latest load wins if a row was re-ingested).
with source as (
    select * from {{ source('raw', 'customers') }}
),

renamed as (
    select
        customer_id,
        first_name,
        last_name,
        email,
        country,
        city,
        address_line,
        coalesce(postal_code, zip_code) as postal_code,
        tier,
        cast(signup_date as date) as signup_date,
        {{ to_utc_timestamp('created_at') }} as created_at_utc,
        _dlt_load_id,
        _dlt_id
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by customer_id
            order by _dlt_load_id desc, _dlt_id desc
        ) as _rn
    from renamed
)

select
    customer_id,
    first_name,
    last_name,
    email,
    country,
    city,
    address_line,
    postal_code,
    tier,
    signup_date,
    created_at_utc
from deduped
where _rn = 1
