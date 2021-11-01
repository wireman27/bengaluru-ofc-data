# Bengaluru Optical Fibre Cables Data

## Data

When an entity wants to run optical-fibre cables under roads in Bengaluru it needs to make an application to the Bruhat Bengaluru Mahanara Palike (BBMP) and get the necessary permissions. The BBMP makes data about such applications accessible on the [Citizen View section of its website](https://site.bbmp.gov.in/Citizenview.html).

This data in its raw form:
  - is slow to access (activate the OFC layer [here](http://bbmp.oasisweb.in/RoadHistory/CitizenView/CitizenViewDemo.aspx))
  - has a convoluted structure that makes interpreting features tricky

This repository exposes two transformed datasets. 

### `bbmp_ofc_segments.csv`

A segment is a group of roads/portions of roads that an entity wants to lay cables under. This table is just a list of all the segments with the following columns:
  1. `segment_id`: The unique id of the segment (string)
  2. `company`: The name of the company laying the cabling under this segment (string)
  3. `ofc_cable_length`: The total length of the optical-fibre cable under the segment, in metres (float)
  4. `segment_length`: The total length of the segment, in metres (float)
  5. `application_submitted_time`: Time the application was submitted by the company (iso datetime)
  6. `number_of_pits`: The number of pits requested to be dug (integer)
  7. `ward_name`: The name of the BBMP ward the segment is in (string)

### `bbmp_ofc_segment_portions.gpkg`

As noted above, each segment is made up of a road/portion of a road. This file contains shapes for all of these portions of segments with information about the company that wants to lay cabling under those portions. Each shape contains the following attributes:
  1. `segment_id`: Same as above
  2. `company`: Same as above
  3. `application_submitted_time`: Same as above
  4. `street_name`: The name of the street (string)

## Generating the data from scratch

After cloning this repository

```
$ mkdir data_raw                   # Create a directory to house the raw data
$ virtualenv -p python3.8 .venv    # Setup a virtual environment
$ source ./.venv/bin/activate      # Activate the virtual environment
$ pip3 install -r requirements.txt # Install the requirements
$ python3 do.py                    # Run the script (might take anywhere between 1 and 2 hours depending on the BBMP servers)
```
