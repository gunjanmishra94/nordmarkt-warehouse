{% snapshot dim_customer_snapshot %}

{{
    config(
        target_schema='snapshots',
        unique_key='customer_id',
        strategy='check',
        check_cols=['address_line', 'city', 'postal_code', 'tier'],
    )
}}

    select * from {{ ref('stg_customers') }}

{% endsnapshot %}
