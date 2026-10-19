-- One row per country and year. The long FAO element list is pivoted into columns.
-- is_country drops World, continents, economic groups, and FAO area 351 (China),
-- which repeats China mainland plus Hong Kong, Macao, and Taiwan.

with measures as (
    select * from {{ ref('stg_ice_cream') }}
),

countries as (
    select area_code, area_name, iso2, iso3
    from {{ ref('fao_area_iso3') }}
    where is_country
),

pivoted as (
    select
        measures.area_code,
        max(measures.area_name) as area_name,
        countries.iso2,
        countries.iso3,
        measures.year,
        max(if(measures.element_code = 5510, measures.value, null)) as production_tonnes,
        max(if(measures.element_code = 5610, measures.value, null)) as import_tonnes,
        max(if(measures.element_code = 5910, measures.value, null)) as export_tonnes,
        max(if(measures.element_code = 5141, measures.value, null)) as food_supply_tonnes,
        max(if(measures.element_code = 665, measures.value, null)) as food_supply_g_per_capita_day
    from measures
    inner join countries
        on measures.area_code = countries.area_code
    group by measures.area_code, countries.iso2, countries.iso3, measures.year
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
    export_tonnes - import_tonnes as trade_balance_tonnes,
    food_supply_tonnes,
    food_supply_g_per_capita_day,
    food_supply_g_per_capita_day * 365 / 1000 as kg_per_person_year,
    food_supply_tonnes = 0
        and (coalesce(import_tonnes, 0) > 0 or coalesce(export_tonnes, 0) > 0)
        as food_supply_estimated_zero
from pivoted
