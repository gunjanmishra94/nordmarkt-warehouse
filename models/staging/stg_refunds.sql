-- Grain: one row per refund_id. occurred_at is when the refund actually
-- happened; recorded_at is when it showed up in the source system, which can
-- be several days later.
with source as (
    select * from {{ source('raw', 'refunds') }}
),

renamed as (
    select
        refund_id,
        order_id,
        amount_eur,
        reason,
        {{ to_utc_timestamp('occurred_at') }} as occurred_at_utc,
        {{ to_utc_timestamp('recorded_at') }} as recorded_at_utc,
        _dlt_load_id,
        _dlt_id
    from source
),

deduped as (
    select
        *,
        row_number() over (
            partition by refund_id
            order by _dlt_load_id desc, _dlt_id desc
        ) as _rn
    from renamed
)

select
    refund_id,
    order_id,
    amount_eur,
    reason,
    occurred_at_utc,
    recorded_at_utc
from deduped
where _rn = 1
