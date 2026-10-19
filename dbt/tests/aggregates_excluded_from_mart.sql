-- World (5000) and the China aggregate (351) would double-count countries if they were summed.
select area_code
from {{ ref('mart_ice_cream_country_year') }}
where area_code in (351, 5000)
