-- One row per country for the newest year in the country-year mart.
-- Looker Studio's map, top-10 bar, and headline table read this table.
-- The line chart reads mart_ice_cream_country_year so a country can move through time.

select mart.*
from {{ ref('mart_ice_cream_country_year') }} as mart
inner join (
    select max(year) as snapshot_year
    from {{ ref('mart_ice_cream_country_year') }}
) as snapshot
    on mart.year = snapshot.snapshot_year
