{#
    ISO day-of-week (1 = Monday .. 7 = Sunday). Plain EXTRACT(dow ...)
    semantics depend on session settings on Snowflake but not on DuckDB, so
    this uses each adapter's ISO-specific function instead.
#}
{% macro iso_day_of_week(column) %}
    {{ return(adapter.dispatch("iso_day_of_week", "kiezkauf")(column)) }}
{% endmacro %}

{% macro default__iso_day_of_week(column) %}
    extract(isodow from {{ column }})
{% endmacro %}

{% macro snowflake__iso_day_of_week(column) %}
    dayofweekiso({{ column }})
{% endmacro %}
