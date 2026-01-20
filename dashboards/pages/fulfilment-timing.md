# Fulfilment timing

[Revenue overview](/) · [Category trends](/category-trends)

Hours between lifecycle stages. Null until an order reaches that stage — there's no "picked" stage, see the main README's "What the numbers mean".

{% big_value
    data="main.fct_order_fulfilment"
    value="avg(hours_placed_to_shipped)"
    fmt="num1"
    title="Avg hours: placed to shipped"
/%}

{% big_value
    data="main.fct_order_fulfilment"
    value="avg(hours_shipped_to_delivered)"
    fmt="num1"
    title="Avg hours: shipped to delivered"
/%}

{% big_value
    data="main.fct_order_fulfilment"
    value="avg(case when is_refunded then 1.0 else 0.0 end)"
    fmt="pct1"
    title="Refund rate"
/%}

{% line_chart
    data="main.fct_order_fulfilment"
    x="placed_at"
    y="avg(hours_placed_to_delivered)"
    date_grain="month"
    y_fmt="num1"
    title="Avg hours placed to delivered, by month"
/%}

{% table
    data="main.fct_order_fulfilment"
    title="Fulfilment by status"
%}
    {% dimension value="order_status" /%}
    {% measure value="count(*)" title="Orders" /%}
    {% measure value="avg(hours_placed_to_shipped)" fmt="num1" title="Avg hrs to ship" /%}
    {% measure value="avg(hours_shipped_to_delivered)" fmt="num1" title="Avg hrs to deliver" /%}
{% /table %}
