{# Fractional hours between two timestamps (NULL-safe: NULL in → NULL out). #}
{% macro hours_between(start_ts, end_ts) -%}
    (date_diff('second', {{ start_ts }}, {{ end_ts }}) / 3600.0)
{%- endmacro %}
