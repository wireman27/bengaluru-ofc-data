"""
Extracts and structures Optical Fibre Cabling (OFC) data 
from the Bruhat Bengaluru Mahanagara Palike (BBMP)
"""

import csv
import json
import logging
import os
import requests

import geopandas as gpd
import imageio
from matplotlib import pyplot as plt

headers = {
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Mobile Safari/537.36',
    'Origin': 'http://bbmp.oasisweb.in',
    'Referer': 'http://bbmp.oasisweb.in/RoadHistory/CitizenView/CitizenViewDemo.aspx'
}

def write_to_csv(list_of_dicts, filename):
	
	keys = list_of_dicts[0].keys()
	
	with open(filename, 'w', newline='') as f:
		dict_writer = csv.DictWriter(f, keys)
		dict_writer.writeheader()
		dict_writer.writerows(list_of_dicts)

def clean_data_derive_insights(path_to_full_data):

	"""
	The final GeoJSON can be made better by:
		1. Removing duplicates
		2. Assigning a company to the email addresses

	This then allows us to derive some insights.

	Some assumptions:
		1. A segment_id represents a certain area within the city (it can contain multiple line strings)
		2. An application_id does NOT correspond to the company making the application.

	To figure out:
		1. What does it mean when the ofc cable length for a segment is larger than the segment length?

	Given these complexities we:
		1. Do total cabling length and company analyses based purely on application_id, segment_id, ofc_cable_length totally ignoring shapes
			- The table is called gdf_segments
			- view_1: view_total_ofc_length
		2. Do spread analysis (color-coding by company based purely on shapes and application_id/company)
			- The table is called gdf_spread
			- We see the densest areas in terms of cables by the number of cables running under the road
			- We create a GIF of the spread of individual companies
	"""

	email_mappings = {
		"ril.com": "Reliance Jio",
		"acttv.in": "ACT TV",
		"vodafone.com": "Vodafone Idea",
		"airtel.com": "Bharti Airtel",
		"vodafoneidea.com": "Vodafone Idea",
		"idea.adityabirla.com": "Vodafone Idea",
		"tatadocomo.com": "TATA Docomo",
		"relianceada.com": "Reliance ADA",
		"tatacommunications.com": "TATA Communications",
		"tataskybb.com": "TATA Sky Broadband",
		"tatatel.co.in": "TATA Teleservices",
		"i-on.in": "i-on",
		"spectranet.in": "Spectra",
		"actcorp.in": "ACT Fibernet"
	}

	def parse_email_domain(row):

		email_id = row['application_email_id']

		try:
			domain = email_id.split('@')[1]
			company = email_mappings[domain]
			return company
		except:
			return None

	def generate_spread_gif(path_to_gpkg):

		"""
		Helper function to spin up the GIF on the repo
		"""

		images = []
		
		# Generate the images first
		gdf_spread = gpd.read_file(path_to_gpkg)
		companies = [x for x in gdf_spread['company'].unique().tolist() if x is not None]
		
		for company in companies:
			plot_data = gdf_spread[gdf_spread['company'] == company]
			ax = plot_data.plot()

			# Configure the plot
			ax.set_title(company, fontdict={'fontsize': 18})
			ax.set_xlim(77.40, 77.85)
			ax.set_ylim(12.78, 13.25)

			filename = f"{company.lower().replace(' ', '_')}.png"
			plt.savefig(filename)

			images.append(imageio.imread(filename))
			os.remove(filename)
		
		imageio.mimsave('company_spread.gif', images, duration=1)

	gdf = gpd.read_file(path_to_full_data)
	gdf_segments = gdf.drop_duplicates(subset=['segment_id', 'application_id'])
	
	# Remove the geometry column because it's useless here
	gdf_segments = gdf_segments.drop(['geometry'], axis = 1)

	# Prepare for analysis
	gdf_segments['company'] = gdf_segments.apply(lambda row: parse_email_domain(row), axis = 1)
	gdf_segments['ofc_cable_length'] = gdf_segments['ofc_cable_length'].astype('float')
	gdf_segments['segment_length'] = gdf_segments['segment_length'].astype('float')
	gdf_segments['number_of_pits'] = gdf_segments['number_of_pits'].astype('int')
	gdf_segments['application_submitted_time'] = gdf_segments.apply(
		lambda row: datetime.strptime(row['application_submitted_date'], '%m/%d/%Y %I:%M:%S %p').isoformat(), 
		axis = 1
	)

	gdf_segments = gdf_segments[[
		'segment_id', 
		'application_submitted_time',
		'segment_length',
		'ofc_cable_length',
		'company',
		'number_of_pits',
		'ward_name'
		]]

	# A unique list of all the segments with the companies who made applications for them.
	gdf_segments.to_csv('bbmp_ofc_segments.csv', index=False)
	view_total_ofc_length = gdf_segments.groupby('company').sum()['ofc_cable_length']
	print(view_total_ofc_length)
	
	# For the spread analysis, we discard duplicate portions of segments
	gdf_spread = gdf.drop_duplicates(subset=['geometry', 'segment_id'])
	gdf_spread['company'] = gdf_spread.apply(lambda row: parse_email_domain(row), axis = 1)
	gdf_spread['application_submitted_time'] = gdf_spread.apply(
        lambda row: datetime.strptime(row['application_submitted_date'], '%m/%d/%Y %I:%M:%S %p').isoformat(),
        axis = 1
    )
	
	# Cleaning up the columns to avoid confusion
	gdf_spread = gdf_spread[[
		'geometry', 
		'company', 
		'street_name', 
		'application_submitted_time',
		'segment_id'
	]]
	
	# A segment differs from a segment portion. Each linestring in this file is a portion of a segment
	gdf_spread.to_file('bbmp_ofc_segment_portions.gpkg', layer='ofc_segment_portions', driver="GPKG")

	generate_spread_gif('bbmp_ofc_segment_portions.gpkg')

def get_all_ofc_data(zones_wards):

	"""
	NOTE: Time consuming function.

	Gets all of the raw data and logs progress along the way.
	"""

	logging.basicConfig(
		filename='get_all_ofc_data.log', 
		filemode='a', 
		format='%(asctime)s - %(message)s',
		level=logging.INFO
	)

	url = "http://bbmp.oasisweb.in/RoadHistory/CitizenView/CitizenViewDemo.aspx/GetOFCData"
	session = requests.Session()
	
	for ward in zones_wards:
		
		zone_id = str(ward['zone_id'])
		ward_id = str(ward['ward_id'])
		
		logging.info(f'Attempting ward_id {ward_id}')

		data = f'{{\'zoneid\':\'{zone_id}\',\'wardid\':\'{ward_id}\',\'streetid\':\'0\'}}'
		page = session.post(url, data=data, headers=headers)
		
		filename = f'data_raw/{ward_id}.txt'
		with open(filename, 'w') as f:
			f.write(page.text)
		
		logging.info(f"Saved ward_id {ward_id} to {filename}")
		
def get_wards():

	"""
	Given the zones, get the wards corresponding to them.
	"""

	url = 'http://bbmp.oasisweb.in/RoadHistory/CitizenView/CitizenViewDemo.aspx/LoadWardByZone'
	final_data = []	

	for i in range(1, 9):
		print("Starting zone ", i)
		page = requests.post(
			url, 
			data=f"{{\'zoneid\':\'{str(i)}\'}}", 
			headers=headers
		)
		page_json = json.loads(page.content)
		data = json.loads(page_json['d'])
		
		for ward in data:
			row = {
				"zone_id": str(i),
				"zone_name": ward['Zone_Name'],
				"ward_id": ward['Ward_Id'],
				"ward_name": ward['Ward_Name']
			}
			final_data.append(row)
	
	write_to_csv(final_data, 'zones_wards.csv')

def create_behemoth_geojson(path_to_raw_data):

	"""
	Parses the raw data into a single GeoJSON file.
	"""
	
	features = []
	files = os.listdir(path_to_raw_data)
	
	for f in files:
		full_path = os.path.join(path_to_raw_data, f)
		with open(full_path, 'r') as f:
			data = json.loads(f.read())
		
			# Weird quirk where the value is a string
			try:
				rows = json.loads(data['d'])
			except:
				print("Could not parse data for ", full_path)
				continue
		
			for row in rows:
				feature = {
					"type": "Feature",
					"properties": {
						"segment_id": row['SegmentID'],
						"street_name": row['StreetName'],
						"application_id": row['ApplicationId'],
						"application_submitted_date": row['ApplicationsubmittedDate'],
						"application_email_id": row['EmailId'],
						"ofc_cable_length": row['OFCcableLength'],
						"number_of_pits": row['NumberOfPits'],
						"authorized_person": row['NameofAuthorizedPerson'],
						"segment_length": row['SegmentLength'],
						"ward_name": row['WardName'],
						"zone_name": row['ZoneName']
					},
					"geometry": {
						"type": "LineString",
						"coordinates": json.loads(row['Shape_Coordinates'])
					}
				}

				features.append(feature)
	
	# Make GeoJSON complete

	final_geojson = {"type": "FeatureCollection", "features": features}

	with open('bbmp_ofc_data.geojson', 'w') as f:
		json.dump(final_geojson, f)
	

def main():
	
	"""
	First, get the wards.
	"""

	get_wards()

	"""
	Then, use the zone_wards combinations to save the data in their raw form.
	"""
	
	with open('zones_wards.csv') as f:
		reader = csv.DictReader(f)
		data = list(reader)

	get_all_ofc_data(data)
	
	"""
	Parse the data to create the behemoth GeoJSON
	"""
	
	create_behemoth_geojson('data_raw')

	"""
	Clean further and derive insights
	"""

	clean_data_derive_insights("bbmp_ofc_data.geojson")	

if __name__ == "__main__":
	main()
