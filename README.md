# High street analysis

Technical documentation for analysing locations of libraries alongside high streets definition data from Ordnance Survey.

## Set up the database

These steps were used to create a database that was then used for the libraries on the high streets research.

### Initial setup

Ordnance Survey data (available to the public sector via the [Public sector geospatial agreement](https://www.ordnancesurvey.co.uk/business-government/public-sector-geospatial-agreement)) is available as a PostGIS database dump. 

```
high_street_201903.dump.gz
```

With a local PostgreSQL server this was restored into a new database.

### Extract libraries from librarydata DB

Firstly, data on libraries was extracted from a separate database, the details for which are in the Libraries Hacked [librarydata-db](https://github.com/LibrariesHacked/librarydata-db) GitHub repository.

A CSV file of the results from the following query was saved to the ```libraries.csv``` in this repository.

```SQL
select
	local_authority,
	local_authority_code,
	library_name,
	address_1,
	address_2,
	address_3,
	postcode,
	library_type,
	unique_property_reference_number,
	colocated,
	easting,
	northing,
	oa_code,
	rural_urban_classification,
	imd
from vw_libraries_geo
where year_closed is null
and country_code = 'E92000001'
order by local_authority, library_name;
```

CSV file extracted (```classifications.csv```) of the following query which produces rural/urban classifications for all postcodes.

```SQL
select postcode, rural_urban_classification
from geo_postcode_lookup;
```

### Create a new table for libraries

Back on the High Streets database, a new table to store libraries:

```SQL
create table libraries (
  local_authority text,
	local_authority_code text,
	library_name text,
	address_1 text,
	address_2 text,
	address_3 text,
	postcode text,
	library_type text,
	unique_property_reference_number text,
	colocated text,
	easting numeric,
	northing numeric,
	oa_code character (9),
	rural_urban_classification character (2),
	imd integer
);
```

Then data imported from the previous CSV.

```SQL
copy libraries from 'C:\Development\LibrariesHacked\high-streets-analysis\libraries.csv' csv header;
```

Then a column to store the geometry field from Easting and Northing.

```SQL
select AddGeometryColumn ('public', 'libraries', 'geom', 27700, 'POINT', 2);
update libraries l set geom = ST_SetSRID(ST_MakePoint(easting, northing), 27700);
```

### Create a new table for classifications

The rural/urban classifications were then entered into a new table. First, tables created:

```SQL
create table classifications (
  postcode text,
  rural_urban_classification text
);
create table classifications_description (
  code text,
  description text
);
```

Then imported the classifications file from the extract in previous steps.

```SQL
copy classifications from 'C:\Development\LibrariesHacked\high-streets-analysis\classifications.csv' csv header;
```

Then the classification descriptions. These are purely descriptive versions of the codes but are quite useful to see.

```SQL
insert into classifications_description values
('A1', 'Urban - Major Conurbation'),
('B1', 'Urban - Minor Conurbation'),
('C1', 'Urban - City and Town'),
('C2', 'Urban - City and Town in a sparse setting'),
('D1', 'Rural - Town and Fringe'),
('D2', 'Rural - Town and Fringe in a sparse setting'),
('E1', 'Rural - Village'),
('E2', 'Rural - Village in a sparse setting'),
('F1', 'Rural - Hamlets and Isolated Dwellings'),
('F2', 'Rural - Hamlets and Isolated Dwellings in a sparse setting');
```

### Add Starbucks data

A Starbucks file was downloaded from [the Starbucks CSV repository](https://github.com/chrismeller/StarbucksLocations). It is outdated (2017) but should be illustrative.

Table creation script:

```SQL
create table starbucks (
  Id text,
	StarbucksId text,
	Name text,
	BrandName text,
	StoreNumber text,
	PhoneNumber text,
	OwnershipType text,
	Street1 text,
	Street2 text,
	Street3 text,
	City text,
	CountrySubdivisionCode text,
	CountryCode text,
	PostalCode text,
	Longitude numeric,
	Latitude numeric,
	TimezoneOffset text,
	TimezoneId text,
	TimezoneOlsonId text,
	FirstSeen text,
	LastSeen text
);
```

```SQL
copy starbucks from 'C:\Development\LibrariesHacked\high-streets-analysis\starbucks.csv' csv header;
```

Then a column to store the geometry single field.

```SQL
select AddGeometryColumn ('public', 'starbucks', 'geom', 27700, 'POINT', 2);
update starbucks s set geom = ST_Transform(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), 27700);
```

That is all the data that was required for the analysis.

## Queries

### Urban/rural classifications

Which urban/rural classifications are applicable to high streets in England?

```SQL
select c.rural_urban_classification, d.description, count(distinct hsa.id), Round(count(*) * 100.0/ SUM(count(*)) over ()) as percent
from classifications c
join classifications_description d on c.rural_urban_classification = d.code
join high_street_201903_id2postcode_lookup hsp on hsp.postcode = c.postcode
join high_street_201903_address_geom hsa on hsa.id = hsp.id and hsa.country_name = 'ENGLAND'
group by c.rural_urban_classification, d.description
order by c.rural_urban_classification;
```

| Code | Rural/urban description | High streets | Percentage |
| ---- | ----------------------- | ------------ | ---------- |
| A1 | Urban - Major Conurbation | 2437 | 47 |
| B1 | Urban - Minor Conurbation | 235 | 3 |
| C1 | Urban - City and Town | 2905 | 43 |
| C2 | Urban - City and Town in a sparse setting | 27 | 0 |
| D1 | Rural - Town and Fringe | 485 | 6 |
| D2 | Rural - Town and Fringe in a sparse setting | 74 | 1 |
| E1 | Rural - Village | 29 | 0 |
| E2 | Rural - Village in a sparse setting | 6 | 0 |
| F1 | Rural - Hamlets and Isolated Dwellings | 32 | 0 |

All except F2 (Rural - Hamlets and Isolated Dwellings in a sparse setting) are returned. Rural amounts of 7% of high streets, urban is 93%.

### High streets

How many high streets are there in England?

```SQL
select count(*) from high_street_201903_centreline_geom where country_name = 'ENGLAND';
```

| Count |
| ----- |
| 6136 |

How many high street clusters are there in England? (Clustering high streets within 50m)

```SQL
select count(*) from (select unnest(ST_ClusterWithin(geom, 50)) from high_street_201903_centreline_geom where country_name = 'ENGLAND')c;
```

| Count |
| ----- |
| 3732 |

### Libraries

#### How many libraries are there?

```SQL
select count(*) from libraries;
```

| Count |
| ----- |
| 2953 |

#### How many libraries are rural or urban?

```SQL
select rural_urban_classification as classification, count(*) as libraries, round(count(*) * 100.0/ SUM(count(*)) over ()) as percent
from Libraries
group by rural_urban_classification
order by rural_urban_classification;
```

| Classification | Count | Percent |
| -------------- | ----- | ------- |
| A1 | 884 | 30 |
| B1 | 112 | 4 |
| C1 | 1194 | 40 |
| C2 | 8 | 0 |
| D1 | 640 | 22 |
| D2 | 46 | 2 |
| E1 | 34 | 1 |
| E2 | 16 | 1 |
| F1 | 16 | 1 |
| F2 | 3 | 0 |

74% are in urban areas, while 26% are in rural areas. 

#### How many libraries are on the high street? (Share postcodes with buildings on the high street)

```SQL
select count(*)
from Libraries
where postcode in
(select postcode from high_street_201903_id2postcode_lookup);
```

| Count |
| ----- |
| 717 |


#### How many libraries are on the high street? (Grouped by rural/urban classification)

```SQL
select rural_urban_classification, count(*)
from libraries
where postcode in 
(select postcode from high_street_201903_id2postcode_lookup)
group by rural_urban_classification
order by rural_urban_classification;
```

| Code | Count |
| ---- | ----- |
| A1 | 246 |
| B1 | 31 |
| C1 | 301 |
| C2 | 3 |
| D1 | 121 |
| D2 | 11 |
| E1 | 1 |
| E2 | 1 |
| F1 | 2 |


#### How many libraries are near the high street? (Within 400 metres)

```SQL
select count(distinct(local_authority, library_name))
from libraries l
join high_street_201903_centreline_geom h ON ST_DWithin(l.geom, h.geom, 400);
```

| Count |
| ----- |
| 1820 |

This is 62% of libraries.

### Starbucks

How many Starbucks are rural or urban?

```SQL
SELECT c.rural_urban_classification, d.description, COUNT(*) as stores, Round(COUNT(*) * 100.0/ SUM(COUNT(*)) over ()) as percent
FROM starbucks s 
JOIN classifications c on c.postcode = s.postalcode
JOIN classification_description d on d.code = c.rural_urban_classification
WHERE s.countrysubdivisioncode = 'ENG'
GROUP BY c.rural_urban_classification, d.description ORDER BY c.rural_urban_classification;
```

| Classification | Description | Count | Percent |
| -------------- | ----------- | ----- | ------- |
"A1"	"Urban - Major Conurbation"	702	47
"B1"	"Urban - Minor Conurbation"	34	2
"C1"	"Urban - City and Town"	548	37
"D1"	"Rural - Town and Fringe"	24	2
"E1"	"Rural - Village"	102	7
"F1"	"Rural - Hamlets and Isolated Dwellings"	86	6
"F2"	"Rural - Hamlets and Isolated Dwellings in a sparse setting"	4	0

86% of Starbucks stores are in Urban locations. That is also skewed by a large number of those If we take out motorway services and airports that becomes closer to 95%.
