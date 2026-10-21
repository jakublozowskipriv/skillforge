{#
  TODO(learn) #1 — napisz ten model sam (ok. 30–45 min).

  Cel: fakt o podjazdach kurierów (first mile). Grain: jeden wiersz na zaplanowane okno odbioru
  (magazyn × przewoźnik × dzień) — czyli jeden wiersz na wiersz z stg_raw__courier_pickups.

  Wymagane kolumny (testy i unit test w _marts.yml już czekają):
    pickup_id, warehouse_id, carrier_id,
    pickup_date          -- data okna (z window_start_at)
    window_start_at, window_end_at, arrived_at, departed_at,
    is_no_show,
    is_on_time_pickup    -- przyjazd najpóźniej na koniec okna; no-show nigdy nie jest on time
    minutes_late         -- minuty po window_end_at; 0 gdy na czas, NULL dla no-show
    parcels_collected    -- 0 zamiast NULL? Zdecyduj i uzasadnij w komentarzu.
    dwell_minutes        -- ile kurier był na miejscu (departed - arrived)

  Pytania do przemyślenia (odpowiedz w komentarzu w modelu):
    1. Czy no-show ma mieć parcels_collected = 0 czy NULL? Jak to wpływa na avg() w BI?
    2. Czy fakt powinien mieć wiersze dla no-show? (Podpowiedź: co mierzy „no-show rate”?)
    3. Jaka jest addytywność kolumn: które można sumować po dniach, a które tylko uśredniać?

  Uruchom: `uv run skillforge data build` albo w katalogu dbt:
    uv run dbt build --select fct_courier_pickups --profiles-dir .
  Po napisaniu usuń `enabled=false` poniżej.
#}
{{ config(enabled=false) }}

select 1 as pickup_id
