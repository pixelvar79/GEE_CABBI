import ee
import os
import datetime
from datetime import datetime
import csv
import sys

ee.Initialize()

# Function to create or update the CSV file
def update_csv(csv_path, new_data):
    header = ["File_Name","Field_Name", "Acquisition_Date", "Cloud_Coverage", "Sensor_Type", "Sensor_Quality", "Datataken_ID", "Downloaded"]

    # Check if the CSV file exists
    if not os.path.isfile(csv_path):
        # Create a new CSV file with the header
        with open(csv_path, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)

    # Append new data to the CSV file
    with open(csv_path, 'a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(new_data)
    
def export_s2(bounding_box, start_date, end_date, shp_name):
    # Get the initial number of scenes in the collection
    initial_count = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(bounding_box).size().getInfo()
    # Set up CSV path for all bounding boxes
    csv_path = 'ee_downloaded_info.csv'
    
    # Create an empty list to store all new data
    all_new_data = []

    collection = (
        #ee.ImageCollection('COPERNICUS/S2')
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(bounding_box)
        .filterDate(ee.Date(start_date), ee.Date(end_date))
        .filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10)
    )
    
    # Get the number of scenes after applying filters
    filtered_count = collection.size().getInfo()

    # Check if there are scenes that meet the specified criteria
    if filtered_count > 0:
        print(f'Number of scenes before filtering: {initial_count}')
        print(f'Number of scenes after filtering: {filtered_count}')
        
        # Print the dates of each capture that meets the criteria
        captured_dates = collection.aggregate_array('system:time_start').getInfo()
        formatted_dates = [datetime.utcfromtimestamp(date / 1000).strftime('%Y-%m-%d') for date in captured_dates]
        print(f'Dates of captures that meet the specified criteria: {formatted_dates}')

        # Set to store unique acquisition dates
        unique_dates = set()

        # Dictionary to store duplicate scenes grouped by acquisition date
        duplicate_images_by_date = {}

        # List to store individual images
        individual_images = []

        # Iterate over each image in the collection
        images = collection.toList(filtered_count)
        for i in range(filtered_count):
            image = ee.Image(images.get(i))

            # Get acquisition date
            acquisition_date = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%Y-%m-%d')
            
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

        # Perform individual downloading for non-duplicate images
        for ind_image in individual_images:
            # Get acquisition date
            acquisition_date = datetime.utcfromtimestamp(ind_image.date().getInfo()['value'] / 1000).strftime('%Y-%m-%d')
            
            # Additional information to monitor
            cloud_coverage = ind_image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo() if ind_image.get('CLOUDY_PIXEL_PERCENTAGE') else None
            sensor_type = ind_image.get('SPACECRAFT_NAME').getInfo() if ind_image.get('SPACECRAFT_NAME') else None
            sensor_quality = ind_image.get('SENSOR_QUALITY_FLAG').getInfo() if ind_image.get('SENSOR_QUALITY_FLAG') else None
            datataken_id = ind_image.get('DATATAKE_IDENTIFIER').getInfo() if ind_image.get('SENSOR_QUALITY_FLAG') else None
            
            full_name = f'S2_{shp_name}_{acquisition_date}.tif'
   
            all_new_data.append([full_name, shp_name, acquisition_date, cloud_coverage, sensor_type, sensor_quality, datataken_id, 'Yes'])

            output_directory = 'FULL_sentinel_ee'
            #os.makedirs(output_directory, exist_ok=True)

            # Set up output path
            #output_path_individual = os.path.join(output_directory, f'{shp_name}_{acquisition_date}_{start_date}_{end_date}.tif')
            output_path_individual = os.path.join(output_directory, f'{shp_name}_{acquisition_date}.tif')

            # Export individual image
            ind_image = ind_image.toFloat()
            task_individual = ee.batch.Export.image.toDrive(
                image=ind_image,
                description=f'S2_{shp_name}_{acquisition_date}',
                folder=output_directory,
                scale=10,
                region=bounding_box
                #timeout=120  # Increase the timeout duration
            )
            task_individual.start()

            while task_individual.status()['state'] in ['READY', 'RUNNING']:
                pass

            print(f'Individual image exported to: {output_path_individual}')

        update_csv(csv_path, all_new_data)
    else:
        print('No scenes found that meet the specified criteria. Exiting.')
        
def export_s1(bounding_box, start_date, end_date, shp_name):
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
            
            full_name = f'S1_{shp_name}_{acquisition_date}.tif'
   
            #all_new_data.append([full_name, shp_name, acquisition_date, cloud_coverage, sensor_type, sensor_quality, datataken_id, 'Yes'])

            output_directory = 'FULL_sentinel1_ee'
            #os.makedirs(output_directory, exist_ok=True)

            # Set up output path
            #output_path_individual = os.path.join(output_directory, f'{shp_name}_{acquisition_date}_{start_date}_{end_date}.tif')
            output_path_individual = os.path.join(output_directory, f'S1_{shp_name}_{acquisition_date}.tif')

            # Export individual image
            image = image.toFloat()
            task_individual = ee.batch.Export.image.toDrive(
                image=image,
                description=f'S1_{shp_name}_{acquisition_date}',
                folder=output_directory,
                scale=10,
                region=bounding_box
                #timeout=120  # Increase the timeout duration
            )
            task_individual.start()

            while task_individual.status()['state'] in ['READY', 'RUNNING']:
                pass

            print(f'Individual image exported to: {output_path_individual}')

        #update_csv(csv_path, all_new_data)
    # else:
    #     print('No scenes found that meet the specified criteria. Exiting.')

    else:
        print('No Sentinel-1 scenes found in the specified date range. Exiting.')
        
        
def export_dem_and_ssurgodata_to_drive(bounding_box, shp_name):
    # Set up CSV path for all bounding boxes
    #csv_path = 'ee_downloaded_info.csv'
    
    # Create an empty list to store all new data
    all_new_data = []

    collection = (
        ee.ImageCollection('USGS/3DEP/1m')
        .filterBounds(bounding_box)
    )
    
    # Get the number of scenes in the collection
    scene_count = collection.size().getInfo()

    # Check if there are scenes in the specified bounding box
    if scene_count > 0:
        print(f'Number of scenes in the bounding box for {shp_name}: {scene_count}')
        
        # Iterate over each image in the collection
        images = collection.toList(scene_count)
        for i in range(scene_count):
            image = ee.Image(images.get(i))

            # Get acquisition date (Note: DEMs may not have a specific acquisition date like optical imagery)
            acquisition_date = 'Not Applicable'
            
            # Additional information to monitor (customize as needed)
            sensor_type = '3DEP'
            
            #full_name = f'3DEP_{shp_name}_{acquisition_date}_{i}.tif'
            full_name = f'3DEP1M_{shp_name}.tif'
   
            all_new_data.append([full_name, shp_name, acquisition_date, sensor_type, 'Yes'])

            output_directory = 'FULL_3DEP1M_ee'
            os.makedirs(output_directory, exist_ok=True)

            # Set up output path
            #output_path_individual = os.path.join(output_directory, f'3DEP_{shp_name}_{acquisition_date}_{i}.tif')
            output_path_individual = os.path.join(output_directory, f'3DEP1M_{shp_name}.tif')

            # Export individual DEM
            task_individual = ee.batch.Export.image.toDrive(
                image=image,
                #description=f'3DEP_{shp_name}_{acquisition_date}_{i}',
                description=f'3DEP1M_{shp_name}',
                folder=output_directory,
                scale=1,  # Adjust scale as needed
                region=bounding_box
                #timeout=120  # Increase the timeout duration
            )
            task_individual.start()

            while task_individual.status()['state'] in ['READY', 'RUNNING']:
                pass

            print(f'Individual 3DEP DEM exported to: {output_path_individual}')

        #update_csv(csv_path, all_new_data)
    else:
        print('No 1M 3DEP DEMs found in the specified bounding box. Exiting.')
        
        
    
    # Create an empty list to store all new data
    all_new_data = []

    # collection = (
    #     ee.Image('USGS/3DEP/10m')
    #     .filterBounds(bounding_box)
    # )
    
    #collection = ee.ImageCollection('USGS/3DEP/10m').filterBounds(bounding_box)
    
    # Load an example image
    image = ee.Image('USGS/3DEP/10m')

    # Clip the image to the bounding box
    image = image.clip(bounding_box)

    
    # Get the number of scenes in the collection
    #scene_count = collection.size().getInfo()

    # Check if there are scenes in the specified bounding box
    if scene_count > 0:
        print(f'Scene found for bounding box {shp_name}')
        
        # # Iterate over each image in the collection
        # images = collection.toList(scene_count)
        # for i in range(scene_count):
        # image = ee.Image(images.get(i))

        # Get acquisition date (Note: DEMs may not have a specific acquisition date like optical imagery)
        acquisition_date = 'Not Applicable'
        
        # Additional information to monitor (customize as needed)
        sensor_type = '3DEP'
        
        #full_name = f'3DEP_{shp_name}_{acquisition_date}_{i}.tif'
        full_name = f'3DEP10M_{shp_name}.tif'

        all_new_data.append([full_name, shp_name, acquisition_date, sensor_type, 'Yes'])

        output_directory = 'FULL_3DEP10m_ee'
        os.makedirs(output_directory, exist_ok=True)

        # Set up output path
        #output_path_individual = os.path.join(output_directory, f'3DEP_{shp_name}_{acquisition_date}_{i}.tif')
        output_path_individual = os.path.join(output_directory, f'3DEP10M_{shp_name}.tif')

        # Export individual DEM
        task_individual = ee.batch.Export.image.toDrive(
            image=image,
            #description=f'3DEP_{shp_name}_{acquisition_date}_{i}',
            description=f'3DEP10M_{shp_name}',
            folder=output_directory,
            scale=1,  # Adjust scale as needed
            region=bounding_box
            #timeout=120  # Increase the timeout duration
        )
        task_individual.start()

        while task_individual.status()['state'] in ['READY', 'RUNNING']:
            pass

        print(f'Individual 10M 3DEP DEM exported to: {output_path_individual}')

        #update_csv(csv_path, all_new_data)
    else:
        print('No 10M 3DEP DEMs found in the specified bounding box. Exiting.')
        
    # Export SSURGO soil data
    # ssurgo_collection = (
    #     ee.FeatureCollection('users/databasin/ssurgo')
    #     .filterBounds(bounding_box)
    # )
    
    # # Export SSURGO soil data using the official asset ID
    # ssurgo_collection = (
    #     ee.FeatureCollection('projects/soils-revealed/ssurgo')
    #     .filterBounds(bounding_box)
    # )

    # # Get the number of SSURGO features in the collection
    # ssurgo_feature_count = ssurgo_collection.size().getInfo()

    # # Check if there are SSURGO features in the specified bounding box
    # if ssurgo_feature_count > 0:
    #     print(f'Number of SSURGO features in the bounding box for {shp_name}: {ssurgo_feature_count}')

    #     # Iterate over each SSURGO feature in the collection
    #     ssurgo_features = ssurgo_collection.toList(ssurgo_feature_count)
    #     for j in range(ssurgo_feature_count):
    #         ssurgo_feature = ee.Feature(ssurgo_features.get(j))

    #         # Get acquisition date (Note: SSURGO features don't have acquisition dates)
    #         acquisition_date_ssurgo = 'Not Applicable'
            
    #         # Additional information to monitor (customize as needed)
    #         feature_type = 'SSURGO'
            
    #         ssurgo_full_name = f'SSURGO_{shp_name}.shp'
   
    #         all_new_data.append([ssurgo_full_name, shp_name, acquisition_date_ssurgo, feature_type, 'Yes'])

    #         output_directory_ssurgo = 'GEE/ssurgo_ee'
    #         os.makedirs(output_directory_ssurgo, exist_ok=True)

    #         # Set up output path for SSURGO
    #         output_path_ssurgo_individual = os.path.join(output_directory_ssurgo, f'SSURGO_{shp_name}.shp')

    #         # Export individual SSURGO feature
    #         task_ssurgo_individual = ee.batch.Export.table.toDrive(
    #             collection=ee.FeatureCollection(ssurgo_feature),
    #             description=f'SSURGO_{shp_name}',
    #             folder=output_directory_ssurgo,
    #             fileFormat='SHP',
    #         )
    #         task_ssurgo_individual.start()

    #         while task_ssurgo_individual.status()['state'] in ['READY', 'RUNNING']:
    #             pass

    #         print(f'Individual SSURGO feature exported to: {output_path_ssurgo_individual}')

    # else:
    #     print('No SSURGO features found in the specified bounding box. Exiting.')



if __name__ == "__main__":
    # This script is intended to be imported as a module, so there's no main execution here.
    pass
