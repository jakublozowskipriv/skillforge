{#
  Hash-based surrogate key, same semantics as dbt_utils.generate_surrogate_key:
  md5 of the columns cast to text, NULL replaced by a placeholder, joined with '-'.
  The placeholder matters: without it ('a', NULL) and (NULL, 'a') could collide, and
  concat with NULL would yield NULL for the whole key.
#}
{% macro surrogate_key(columns) -%}
    md5(
        {%- for col in columns %}
        coalesce(cast({{ col }} as varchar), '_dbt_utils_surrogate_key_null_')
        {%- if not loop.last %} || '-' || {% endif -%}
        {%- endfor %}
    )
{%- endmacro %}
