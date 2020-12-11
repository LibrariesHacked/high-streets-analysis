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


### Add Starbucks data


```SQL
CREATE TABLE starbucks (
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

Then add a column to store the geometry single field.

```SQL
SELECT AddGeometryColumn ('public', 'starbucks', 'geom', 27700, 'POINT', 2);
UPDATE starbucks s SET geom = ST_Transform(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), 27700);
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

How many libraries are rural or urban?

```
SELECT "Rural urban classification" as classification, COUNT(*) as libraries, Round(COUNT(*) * 100.0/ SUM(COUNT(*)) over ()) as percent
FROM Libraries
GROUP BY "Rural urban classification"
ORDER BY "Rural urban classification";
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

How many libraries are on the high street? (Share postcodes with buildings on the high street)

```
SELECT COUNT(*)
FROM Libraries
WHERE "Postcode" IN 
(SELECT postcode from high_street_201903_id2postcode_lookup);
```

| Count |
| ----- |
| 717 |


How many libraries are on the high street? (Grouped by rural/urban classification)

```
SELECT "Rural urban classification", COUNT(*)
FROM Libraries
WHERE "Postcode" IN 
(SELECT postcode from high_street_201903_id2postcode_lookup)
GROUP BY "Rural urban classification"
ORDER BY "Rural urban classification";
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


How many libraries are near the high street? (Within 400 metres)

```
SELECT COUNT(DISTINCT("Local authority", "Library name"))
FROM libraries l
JOIN high_street_201903_centreline_geom h ON ST_DWithin(l.geom, h.geom, 400);
```

| Count |
| ----- |
| 1820 |



### Starbucks

How many Starbucks are rural or urban?

```
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