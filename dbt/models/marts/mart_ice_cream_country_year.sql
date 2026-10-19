-- Dashboard grain: one country, one year, with population, year-over-year change, and ranks.
-- Summing import_tonnes or export_tonnes across countries is a country total.
-- Do not add the FAO World row on top of that sum.

with base as (
    select
        ice.area_code,
        ice.area_name,
        ice.iso2,
        ice.iso3,
        ice.year,
        ice.production_tonnes,
        ice.import_tonnes,
        ice.export_tonnes,
        ice.trade_balance_tonnes,
        ice.food_supply_tonnes,
        ice.food_supply_g_per_capita_day,
        ice.kg_per_person_year,
        ice.food_supply_estimated_zero,
        population.population_persons
    from {{ ref('int_ice_cream_country_year') }} as ice
    left join {{ ref('stg_population') }} as population
        on ice.area_code = population.area_code
        and ice.year = population.year
)

select
    area_code,
    area_name,
    iso2,
    iso3,
    year,
    production_tonnes,
    import_tonnes,
    export_tonnes,
    trade_balance_tonnes,
    food_supply_tonnes,
    food_supply_g_per_capita_day,
    kg_per_person_year,
    food_supply_estimated_zero,
    population_persons,
    import_tonnes - lag(import_tonnes) over (
        partition by area_code order by year
    ) as import_tonnes_yoy,
    export_tonnes - lag(export_tonnes) over (
        partition by area_code order by year
    ) as export_tonnes_yoy,
    rank() over (
        partition by year order by import_tonnes desc nulls last
    ) as import_rank,
    rank() over (
        partition by year order by export_tonnes desc nulls last
    ) as export_rank
from base
