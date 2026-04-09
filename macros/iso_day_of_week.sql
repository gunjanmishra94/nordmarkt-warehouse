{#
    ISO day-of-week (1 = Monday .. 7 = Sunday).
#}
{% macro iso_day_of_week(column) %}
    extract(isodow from {{ column }})
{% endmacro %}
