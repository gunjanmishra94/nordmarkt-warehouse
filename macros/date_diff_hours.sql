{#
    Hours between two timestamps (end - start), null if either side is null.
#}
{% macro date_diff_hours(start_column, end_column) %}
    date_diff('hour', {{ start_column }}, {{ end_column }})
{% endmacro %}
