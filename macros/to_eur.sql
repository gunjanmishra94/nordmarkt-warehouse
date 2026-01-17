{#
    Converts a local-currency amount to EUR using the EUR->CHF rate that
    applied on the relevant date. EUR amounts pass through unchanged; the
    rate is only needed for CHF.
#}
{% macro to_eur(local_amount_column, currency_column, rate_column) %}
    case
        when {{ currency_column }} = 'EUR' then {{ local_amount_column }}
        else {{ local_amount_column }} / {{ rate_column }}
    end
{% endmacro %}
