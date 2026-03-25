-- Grain: one row per holiday_date x federal_state. See DECISIONS.md for the
-- simplifications baked into which states observe which regional holidays.
select
    cast(holiday_date as date) as holiday_date,
    holiday_name,
    federal_state,
    cast(nationwide as boolean) as nationwide
from {{ ref('de_public_holidays') }}
