from ee_init import EarthEngine

import ee
import os
import datetime
from datetime import datetime, timezone
import csv
import sys
import pandas as pd

# Get the instance (initializes only if not already done)
ee_instance = EarthEngine()

# Create an empty list to store the output data for each iteration
output_data_list = []

# Function to check if data already exists in the CSV
def is_data_in_csv(field_name, acquisition_date, sensor_type):
    csv_path = 'check_sentinel_available.csv'
    if os.path.isfile(csv_path):
        existing_data = pd.read_csv(csv_path)
        return ((existing_data['Field Name'] == field_name) & 
                (existing_data['acquisition_date'] == acquisition_date) &
                (existing_data['sensor_type'] == sensor_type)).any()
    return False

def process_s2(bounding_box, start_date, end_date, shp_name):
    global output_data_list  # Use global to access the list outside
    # Get the initial number of scenes in the collection
    print('initialization of the collection......')
    #initial_count = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(bounding_box).size().getInfo()
    #initial_count = ee.ImageCollection('COPERNICUS/S2').filterBounds(bounding_box).size().getInfo()
    
    # Create an empty list to store all new data
    all_new_data = []

    collection = (
        #ee.ImageCollection('COPERNICUS/S2')
        #ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        #ee.ImageCollection('COPERNICUS/S2_SR')
        ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
        .filterBounds(bounding_box)
        .filterDate(ee.Date(start_date), ee.Date(end_date))
        .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10)
    )
    
    # Get the number of scenes after applying filters
    filtered_count = collection.size().getInfo()

    # Check if there are scenes that meet the specified criteria
    if filtered_count > 0:
        #print(f'Number of scenes before filtering: {initial_count}')
        print(f'Number of scenes after filtering: {filtered_count}')
        
        # Print the dates of each capture that meets the criteria
        captured_dates = collection.aggregate_array('system:time_start').getInfo()
        #formatted_dates = [datetime.utcfromtimestamp(date / 1000).strftime('%Y-%m-%d') for date in captured_dates]
        formatted_dates = [datetime.fromtimestamp(date / 1000).strftime('%Y-%m-%d') for date in captured_dates]

        print(f'Dates of captures that meet the specified criteria for Sentinel 2: {formatted_dates}')

        # Set to store unique acquisition dates
        unique_dates = set()

        # Dictionary to store duplicate scenes grouped by acquisition date
        duplicate_images_by_date = {}

        # List to store individual images
        individual_images = []
        
        output_data_list = []

        # Iterate over each image in the collection
        images = collection.toList(filtered_count)
        for i in range(filtered_count):
            image = ee.Image(images.get(i))

            # Get acquisition date
            timestamp_ms = image.date().getInfo()['value']
            timestamp_s = timestamp_ms / 1000
            dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
                
            acquisition_date = dt.strftime('%Y-%m-%d')
                
            #acquisition_date = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%Y-%m-%d')
            
            # Check for duplicates
            if acquisition_date in unique_dates:
                print('Duplicate scene found!')
                # Add the duplicate scene to the dictionary based on acquisition date
                if acquisition_date not in duplicate_images_by_date:
                    duplicate_images_by_date[acquisition_date] = []
                # Select bands
                selected_bands = ['B2', 'B3', 'B4', 'B5', 'B8']
                image = image.select(selected_bands)
                duplicate_images_by_date[acquisition_date].append(image)
            else:
                # Add the acquisition date to the set
                unique_dates.add(acquisition_date)
                print(f'The date of capture is: {acquisition_date}')

                # Select bands
                selected_bands = ['B2', 'B3', 'B4', 'B5', 'B8']
                image = image.select(selected_bands)

                # Append image to the list for individual downloading
                individual_images.append(image)
                
        # Perform individual summary for non-duplicate images
        for ind_image in individual_images:
            
            try:
                timestamp_ms = ind_image.date().getInfo()['value']
                timestamp_s = timestamp_ms / 1000
                dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
                
                acquisition_date = dt.strftime('%Y-%m-%d')
                acquisition_year = dt.strftime('%Y')
                acquisition_month = dt.strftime('%m')
                acquisition_day = dt.strftime('%d')
            except (KeyError, TypeError, AttributeError) as e:
                acquisition_date = acquisition_year = acquisition_month = acquisition_day = None
                print(f"Error extracting acquisition date: {e}")

            # acquisition_date = datetime.utcfromtimestamp(ind_image.date().getInfo()['value'] / 1000).strftime('%Y-%m-%d')
            # acquisition_year = datetime.utcfromtimestamp(ind_image.date().getInfo()['value'] / 1000).strftime('%Y')
            # acquisition_month = datetime.utcfromtimestamp(ind_image.date().getInfo()['value'] / 1000).strftime('%m')
            # acquisition_day = datetime.utcfromtimestamp(ind_image.date().getInfo()['value'] / 1000).strftime('%d')
            cloud_coverage = ind_image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo() if ind_image.get('CLOUDY_PIXEL_PERCENTAGE') else None
            sensor_type = ind_image.get('SPACECRAFT_NAME').getInfo() if ind_image.get('SPACECRAFT_NAME') else None
            #sensor_quality = ind_image.get('SENSOR_QUALITY_FLAG').getInfo() if ind_image.get('SENSOR_QUALITY_FLAG') else None
            #datataken_id = ind_image.get('DATATAKE_IDENTIFIER').getInfo() if ind_image.get('SENSOR_QUALITY_FLAG') else None
            
            shp_name = shp_name.split('_')[0]
            full_name = f'{shp_name}_{acquisition_date}_{start_date}_{end_date}.tif'
            
            # Check if the data already exists in the CSV
            if not is_data_in_csv(shp_name, acquisition_date, sensor_type):
                # Append the output data to the list
            
                # Append the output data to the list
                output_data_list.append({
                    'Field Name': shp_name,
                    'acquisition_date': acquisition_date,
                    'acquisition_year': acquisition_year,
                    'acquisition_month': acquisition_month,
                    'acquisition_day': acquisition_day,
                    'cloud_coverage': cloud_coverage,
                    'sensor_type': sensor_type
                })
                # Print a message if new scenes were found
                print(f'New Sentinel 2 scenes found for {shp_name} on {acquisition_date} that are not available locally.')

            else:
                # Print a message if scenes found in the local CSV are not being further considered
                print(f'Sentinel 2 scenes for {shp_name} on {acquisition_date} found locally, they are not further considered.')
            
        return output_data_list

    else:
        print('No scenes found that meet the specified criteria. Exiting.')
        
        
def process_s1(bounding_box, start_date, end_date, shp_name):
    global output_data_list  # Use global to access the list outside
    # Create an empty list to store all new data
    initial_count = ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(bounding_box).size().getInfo()

    all_new_data = []

    collection = (
        ee.ImageCollection('COPERNICUS/S1_GRD')
        .filterBounds(bounding_box)
        .filterDate(ee.Date(start_date), ee.Date(end_date))
        .filter(ee.Filter.eq('instrumentMode', 'IW'))
        #.filter(ee.Filter.rangeContains('system:incidence_angle', min_incidence_angle, max_incidence_angle))
        #.select(['HH', 'VV'])  # Select HH and VV polarizations
    )
    
    # Get the number of scenes in the collection
    filtered_count = collection.size().getInfo()
    
    output_data_list = []
    
    # Check if there are scenes in the collection
    if filtered_count > 0:
        print(f'Number of scenes before filtering: {initial_count}')
        print(f'Number of scenes after filtering: {filtered_count}')
        
        # Print the dates of each capture that meets the criteria
        captured_dates = collection.aggregate_array('system:time_start').getInfo()
        formatted_dates = [datetime.utcfromtimestamp(date / 1000).strftime('%Y-%m-%d') for date in captured_dates]
        print(f'Dates of captures that meet the specified criteria for Sentinel 1: {formatted_dates}')
        
        # Iterate over each image in the collection
        images = collection.toList(filtered_count)
        
        for i in range(filtered_count):
            image = ee.Image(images.get(i))

            acquisition_date = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%Y-%m-%d')
            acquisition_year = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%Y')
            acquisition_month = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%m')
            acquisition_day = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%d')
            cloud_coverage = 0.0
            sensor_type = 'Sentinel-1'
            
            shp_name_modified = shp_name.split('_')[0]
            
            full_name = f'{shp_name_modified}_{acquisition_date}_{start_date}_{end_date}.tif'
            
            # Check if the data already exists in the CSV
            if not is_data_in_csv(shp_name_modified, acquisition_date, sensor_type):
            # Append the output data to the list
                output_data_list.append({
                    'Field Name': shp_name_modified,
                    'acquisition_date': acquisition_date,
                    'acquisition_year': acquisition_year,
                    'acquisition_month': acquisition_month,
                    'acquisition_day': acquisition_day,
                    'cloud_coverage': cloud_coverage,
                    'sensor_type': sensor_type
                })
                
                # Print a message if new scenes were found
                print(f'New Sentinel 1 scenes found for {shp_name_modified} on {acquisition_date} that are not available locally.')

            else:
                # Print a message if scenes found in the local CSV are not being further considered
                print(f'Sentinel 1 scenes for {shp_name_modified} on {acquisition_date} found locally, they are not further considered.')

        return output_data_list

    else:
        print('No Sentinel-1 scenes found in the specified date range. Exiting.')

if __name__ == "__main__":
    # This script is intended to be imported as a module, so there's no main execution here.
    pass
    # After all iterations are complete, concatenate the lists into a DataFrame
    