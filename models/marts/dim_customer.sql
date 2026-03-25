-- Grain: one row per customer_id per version of their address/tier (Type 2
-- SCD, via the dim_customer_snapshot dbt snapshot). A customer who has
-- always had the same address/tier has exactly one row; one who has moved
-- or changed tier has one row per version, with valid_to set on every
-- version except the current one.
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
    dbt_valid_from as valid_from,
    dbt_valid_to as valid_to,
    dbt_valid_to is null as is_current
from {{ ref('dim_customer_snapshot') }}
