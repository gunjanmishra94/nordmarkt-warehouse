{#
    Raw timestamps arrive as ISO-8601 strings with an explicit UTC offset,
    but different sources use different offsets (Europe/Berlin, Europe/Zurich,
    UTC). Converting an offset-aware string to a UTC instant is spelled
    differently on DuckDB vs Snowflake, so that difference is isolated here
    instead of being scattered through the staging models.
#}
{% macro to_utc_timestamp(column) %}
    {{ return(adapter.dispatch("to_utc_timestamp", "kiezkauf")(column)) }}
{% endmacro %}

{% macro default__to_utc_timestamp(column) %}
    cast({{ column }} as timestamptz) at time zone 'UTC'
{% endmacro %}

{% macro snowflake__to_utc_timestamp(column) %}
    convert_timezone('UTC', to_timestamp_tz({{ column }}))
{% endmacro %}
