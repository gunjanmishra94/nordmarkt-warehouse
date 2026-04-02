{#
    Deletes an incremental model's rows in [start_date, end_date] so a
    following run reprocesses that window instead of relying on the model's
    usual trailing lookback filter. For a historical fix older than what the
    lookback normally reaches.

    The model's own filter is always anchored at `max(date_column) in the
    table, minus late_arrival_lookback_days` — deleting the window is not
    enough on its own if start_date is further back than that. Widen the var
    so the anchor reaches start_date (e.g. today minus start_date, in days).

    Usage:
      dbt run-operation backfill_incremental_model \
        --args '{model_name: fct_order_lines, date_column: order_date, start_date: 2024-01-01, end_date: 2024-01-31}'
      dbt run --select fct_order_lines --vars '{late_arrival_lookback_days: 1500}'
#}
{% macro backfill_incremental_model(model_name, date_column, start_date, end_date) %}
    {% set relation = ref(model_name) %}
    {% set query %}
        delete from {{ relation }}
        where {{ date_column }} between '{{ start_date }}' and '{{ end_date }}'
    {% endset %}
    {% if execute %}
        {% do run_query(query) %}
        {{
            log(
                "Deleted "
                ~ model_name
                ~ " rows where "
                ~ date_column
                ~ " is between "
                ~ start_date
                ~ " and "
                ~ end_date
                ~ ". Run `dbt run --select "
                ~ model_name
                ~ "` to reprocess that window.",
                info=true,
            )
        }}
    {% endif %}
{% endmacro %}
