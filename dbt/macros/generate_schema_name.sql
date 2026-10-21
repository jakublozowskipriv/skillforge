{#
  Use the custom schema name as-is (staging / intermediate / marts) instead of dbt's default
  `<target_schema>_<custom_schema>`. With a single local target there is nothing to isolate,
  and clean schema names make exercises readable: `select * from marts.fct_shipments`.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
