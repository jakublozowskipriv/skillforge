{#
  TODO(learn) #2 — napisz ten generic test sam (ok. 20–30 min).

  Uogólnij singular test tests/assert_delivered_after_pickup.sql na test wielokrotnego użytku:

    - timestamp_order:
        arguments:
          earlier: picked_up_at
          later: delivered_at

  Test ma zwracać wiersze łamiące regułę „earlier <= later”. Wiersze, gdzie któraś kolumna jest
  NULL, nie są błędem (przesyłka mogła jeszcze nie dojechać).

  Pamiętaj: generic test to makro `{% test nazwa(model, ...) %} ... {% endtest %}`, które zwraca
  *błędne* wiersze; 0 wierszy = test zielony. Po napisaniu odkomentuj użycie w models/marts/_marts.yml.
  Bonus: dodaj opcjonalny argument `allow_equal=true`.
#}
{% test timestamp_order(model, earlier, later) %}
    {{ exceptions.raise_compiler_error("TODO(learn) #2: implement the timestamp_order test") }}
{% endtest %}
