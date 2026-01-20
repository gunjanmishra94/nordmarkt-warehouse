{#
    Hours between two timestamps (end - start), null if either side is null.
    DuckDB's function is spelled `date_diff`; Snowflake's is `datediff` — same
    (part, start, end) argument order in both, but the name differs, so it's
    isolated here per the convention in docs/STACK.md.
#}
{% macro date_diff_hours(start_column, end_column) %}
    {{ return(adapter.dispatch("date_diff_hours", "kiezkauf")(start_column, end_column)) }}
{% endmacro %}

{% macro default__date_diff_hours(start_column, end_column) %}
    date_diff('hour', {{ start_column }}, {{ end_column }})
{% endmacro %}

{% macro snowflake__date_diff_hours(start_column, end_column) %}
    datediff('hour', {{ start_column }}, {{ end_column }})
{% endmacro %}
