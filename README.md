# High street analysis

Process for analysing locations of libraries alongside high streets definitions from Ordnance Survey.

## Set up the database

These steps provide the process used to create a database that will then be used for the libraries on the high streets research.

(Sorry - this is not #OpenData)

### Initial setup

Ordnance Survey data (available to the public sector via the [Public sector geospatial agreement](https://www.ordnancesurvey.co.uk/business-government/public-sector-geospatial-agreement)) is available as a PostGIS database dump. 

```
high_street_201903.dump.gz
```

With a local (or remote) PostgreSQL server this can be refreshed into a new database. This provides the following tables.

### Extract libraries from librarydata DB

This refers to a separate database, the details for which are in the Libraries Hacked [librarydata-db](https://github.com/LibrariesHacked/librarydata-db) GitHub repository.

Save a CSV file of the results from the following query which extracts a list of libraries.

```SQL
select
	"Local authority",
	"Local authority code",
	"Library name",
	"Address 1",
	"Address 2",
	"Address 3",
	"Postcode",
	"Library type",
	"Unique property reference number",
	"Co-located",
	"Easting",
	"Northing",
	"OA Code",
	"Rural urban classification",
	"IMD"
from vw_libraries_geo
where "Year closed" is null
and "Country Code" = 'E92000001'
order by "Local authority", "Library name";
```

Also save a CSV file of the following query which extracts rural/urban classifications for all postcodes.

```SQL
select postcode, rural_urban_classification from geo_postcode_lookup;
```

### Create a new table for libraries

Back on the High Streets database, create a new table to store libraries.

```SQL
CREATE TABLE libraries (
  "Local authority" text,
	"Local authority code" text,
	"Library name" text,
	"Address 1" text,
	"Address 2" text,
	"Address 3" text,
	"Postcode" text,
	"Library type" text,
	"Unique property reference number" text,
	"Co-located" text,
	"Easting" numeric,
	"Northing" numeric,
	"OA Code" text,
	"Rural urban classification" character (2),
	"IMD" integer
);
```

Then import the data from the previous CSV (change the path to be whatever is the one for you).

```SQL
copy libraries from 'C:\Development\LibrariesHacked\high-streets-analysis\libraries.csv' csv header;
```

Then add a column to store the geometry single field.

```SQL
SELECT AddGeometryColumn ('public', 'libraries', 'geom', 27700, 'POINT', 2);
UPDATE libraries l SET geom = ST_SetSRID(ST_MakePoint("Easting", "Northing"), 27700);
```


### Create a new table for classifications

The rural/urban classifications can then be entered into a new table. First create the tables.

```SQL
CREATE TABLE classifications (
  postcode text,
	rural_urban_classification text
);
CREATE TABLE classification_description (
  code text,
	description text
);
```

Then import the following classifications file held in this repository.

```SQL
copy classifications from 'C:\Development\LibrariesHacked\high-streets-analysis\classifications.csv' csv header;
```

Then import the classification descriptions. These aren't fully necessary but are quite useful to see.

```SQL
INSERT INTO classification_description VALUES
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

At that point we have enough data in the database to run the queries.


## Queries

### Urban/rural classifications

Which urban/rural classifications are applicable to high streets in England?

```SQL
SELECT DISTINCT c.rural_urban_classification, d.description
FROM classifications c
JOIN classification_description d ON c.rural_urban_classification = d.code
WHERE c.postcode in (
	select p.postcode from high_street_201903_id2postcode_lookup p join high_street_201903_address_geom a on a.id = p.id where a.country_name = 'ENGLAND'
)
ORDER by c.rural_urban_classification;
```

| Code | Rural/urban description |
| ---- | ----------------------- |
| A1 | Urban - Major Conurbation |
| B1 | Urban - Minor Conurbation |
| C1 | Urban - City and Town |
| C2 | Urban - City and Town in a sparse setting |
| D1 | Rural - Town and Fringe |
| D2 | Rural - Town and Fringe in a sparse setting |
| E1 | Rural - Village |
| E2 | Rural - Village in a sparse setting |
| F1 | Rural - Hamlets and Isolated Dwellings |

All except F2 (Rural - Hamlets and Isolated Dwellings in a sparse setting) are returned.


### High streets

How many high streets are there in England?

```
select count(*) from high_street_201903_centreline_geom where country_name = 'ENGLAND'
```

| Count |
| ----- |
| 6136 |


How many high street clusters are there in England? (Clustering high streets within 100m)

```SQL
SELECT COUNT(*) FROM (SELECT UNNEST(ST_ClusterWithin(geom, 100)) FROM high_street_201903_centreline_geom WHERE country_name = 'ENGLAND')C;
```

| Count |
| ----- |
| 3367 |


### Libraries

```
select distinct "Local authority", "Library name" from libraries l
join high_street_201903_centreline_geom h
on ST_DWithin(l.geom, h.geom, 400);
```
