{#
    Raw timestamps arrive as ISO-8601 strings with an explicit UTC offset,
    but different sources use different offsets (Europe/Berlin, Europe/Zurich,
    UTC). This converts an offset-aware string to a UTC instant.
#}
{% macro to_utc_timestamp(column) %}
    cast({{ column }} as timestamptz) at time zone 'UTC'
{% endmacro %}
