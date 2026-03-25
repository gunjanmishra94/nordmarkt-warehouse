-- Grain: one row per calendar day, 2015-01-01 through 2031-12-31.
with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2015-01-01' as date)",
        end_date="cast('2032-01-01' as date)"
    ) }}
),

holidays as (
    select
        holiday_date,
        count(distinct federal_state) as states_observing,
        min(holiday_name) as holiday_name
    from {{ ref('dim_public_holiday_de') }}
    group by holiday_date
)

select
    cast(spine.date_day as date) as date_day,
    extract(year from spine.date_day) as calendar_year,
    extract(month from spine.date_day) as calendar_month,
    extract(day from spine.date_day) as day_of_month,
    {{ iso_day_of_week('spine.date_day') }} as iso_day_of_week,
    case ({{ iso_day_of_week('spine.date_day') }})
        when 1 then 'Monday'
        when 2 then 'Tuesday'
        when 3 then 'Wednesday'
        when 4 then 'Thursday'
        when 5 then 'Friday'
        when 6 then 'Saturday'
        else 'Sunday'
    end as day_name,
    ({{ iso_day_of_week('spine.date_day') }}) in (6, 7) as is_weekend,
    extract(year from spine.date_day) as fiscal_year,
    cast(floor((extract(month from spine.date_day) - 1) / 3.0) as integer)
    + 1 as fiscal_quarter,
    holidays.holiday_date is not null as is_public_holiday_de,
    holidays.holiday_name,
    coalesce(holidays.states_observing, 0) as public_holiday_states_observing
from spine
left join holidays on spine.date_day = holidays.holiday_date
