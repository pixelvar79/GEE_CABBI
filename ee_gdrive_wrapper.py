import ee
import os
import datetime
from datetime import datetime, timezone
import csv
import sys
import ast

ee.Initialize()

# Function to create or update the CSV file
def update_csv(csv_path, new_data):
    header = ["File_Name", "Field_Name", "Acquisition_Date", "Cloud_Coverage", "Sensor_Type", "Sensor_Quality", "Datataken_ID", "Downloaded"]

    # Check if the CSV file exists
    if not os.path.isfile(csv_path):
        # Create a new CSV file with the header
        with open(csv_path, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)

    # Append new data to the CSV file
    with open(csv_path, 'a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        for data in new_data:
            writer.writerow([str(data)])
        writer.writerow(new_data)
        
# Function to check if a file name already exists in the CSV
def file_name_exists(csv_path, file_name):
    if not os.path.isfile(csv_path):
        return False
    with open(csv_path, 'r', newline='') as csv_file:
        reader = csv.reader(csv_file)
        next(reader)  # Skip the header
        for row in reader:
            for cell in row:
                file_info = ast.literal_eval(cell)
                if file_info[0] == file_name:
                    return True
    return False

#def function to add cloud probability to ee collection
def get_s2_sr_cld_col(aoi, start_date, end_date):
    # Import and filter S2 SR.
        s2_sr_col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            .filterBounds(aoi)
            .filterDate(ee.Date(start_date), ee.Date(end_date))
            .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', 10)))

        # Import and filter s2cloudless.
        s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
            .filterBounds(aoi)
            .filterDate(ee.Date(start_date),ee.Date(end_date)))

        # Join the filtered s2cloudless collection to the SR collection by the 'system:index' property.
        return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
            'primary': s2_sr_col,
            'secondary': s2_cloudless_col,
            'condition': ee.Filter.equals(**{
                'leftField': 'system:index',
                'rightField': 'system:index'
            })
        }))
    

#Define a function to add the s2cloudless probability layer and derived cloud mask as bands to an S2 SR image input.
def add_cloud_bands(img):
        # Get s2cloudless image, subset the probability band.
        cld_prb = ee.Image(img.get('s2cloudless')).select('probability')

        # Condition s2cloudless by the probability threshold value.
        is_cloud = cld_prb.gt(50).rename('clouds')

        # Add the cloud probability layer and cloud mask as image bands.
        return img.addBands(ee.Image([cld_prb, is_cloud]))
    
#Define a function to add dark pixels, cloud projection, and identified shadows as bands to an S2 SR image input.
def add_shadow_bands(img):
    # Identify water pixels from the SCL band.
    not_water = img.select('SCL').neq(6)

    # Identify dark NIR pixels that are not water (potential cloud shadow pixels).
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(0.15*SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')

    # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')));

    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, 1*10)
        .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
        .select('distance')
        .mask()
        .rename('cloud_transform'))

    # Identify the intersection of dark pixels with cloud shadow projection.
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')

    # Add dark pixels, cloud projection, and identified shadows as image bands.
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

#alternative for S2 L1C since there's no SCL band
def add_shadow_bands_L1C(img):
    # Calculate the Normalized Difference Water Index (NDWI)
    ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI')
    
    # Identify water pixels using NDWI
    water_threshold = 0.3  # Adjust this threshold as needed
    not_water = ndwi.lt(water_threshold)
    
    # Identify dark NIR pixels that are not water (potential cloud shadow pixels)
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(0.15 * SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')
    
    # Determine the direction to project cloud shadow from clouds (assumes UTM projection)
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')))
    
    # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, 1 * 10)
                .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
                .select('distance')
                .mask()
                .rename('cloud_transform'))
    
    # Identify the intersection of dark pixels with cloud shadow projection
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')
    
    # Add dark pixels, cloud projection, and identified shadows as image bands
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

#Define a function to assemble all of the cloud and cloud shadow components and produce the final mask.
def add_cld_shdw_mask(img):
    # Add cloud component bands.
    img_cloud = add_cloud_bands(img)

    # Add cloud shadow component bands.
    img_cloud_shadow = add_shadow_bands(img_cloud)

    # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)

    # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
    # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
    is_cld_shdw = (is_cld_shdw.focalMin(2).focalMax(50*2/20)
        .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
        .rename('cloudmask'))

    # Add the final cloud-shadow mask to the image.
    #return img_cloud_shadow.addBands(is_cld_shdw)
    return img.addBands(is_cld_shdw)

    
def export_s2(bounding_box, start_date, end_date, shp_name):
    # Get the initial number of scenes in the collection
    #initial_count = ee.ImageCollection('COPERNICUS/S2_HARMONIZED').filterBounds(bounding_box).size().getInfo()
    initial_count = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(bounding_box).size().getInfo()
    
    #print(f'Number of scenes before filtering: {initial_count}')
    # Set up CSV path for all bounding boxes
    csv_path = 'ee_s2_l1c_downloaded_info1.csv'
    
    # Create an empty list to store all new data
    all_new_data = []

    # Get the Sentinel-2 SR and cloud probability collection
    s2_sr_cld_col = get_s2_sr_cld_col(bounding_box, start_date, end_date)

    # # Apply the add_cloud_bands function to each image in the collection
    s2_sr_cld_col_with_clouds = s2_sr_cld_col.map(add_cloud_bands)

    # # Print the result to verify
    # #print(s2_sr_cld_col_with_clouds.getInfo())
    
    # # Apply the add_cloud_bands function to each image in the collection
    s2_sr_cld_col_with_clouds_masks = s2_sr_cld_col_with_clouds.map(add_cld_shdw_mask)
    
    # Print the result to verify
    #print(s2_sr_cld_col_with_clouds_masks.getInfo())
    
    # Get the number of scenes after applying filters
    #filtered_count = s2_sr_cld_col_with_clouds_masks.size().getInfo()
    filtered_count = s2_sr_cld_col_with_clouds_masks.size().getInfo()

    # Check if there are scenes that meet the specified criteria
    if filtered_count > 0:
        print(f'Number of scenes before filtering: {initial_count}')
        print(f'Number of scenes after filtering: {filtered_count}')
        
        # Print the dates of each capture that meets the criteria
        #captured_dates = s2_sr_cld_col_with_clouds_masks.aggregate_array('system:time_start').getInfo()
        
        captured_dates = s2_sr_cld_col_with_clouds_masks.aggregate_array('system:time_start').getInfo()
        
        
        #formatted_dates = [datetime.utcfromtimestamp(date / 1000).strftime('%Y-%m-%d') for date in captured_dates]
        formatted_dates = [datetime.fromtimestamp(date / 1000).strftime('%Y-%m-%d') for date in captured_dates]
        #print(f'Dates of captures that meet the specified criteria: {formatted_dates}')

        # Set to store unique acquisition dates
        unique_dates = set()
        # Dictionary to store duplicate scenes grouped by acquisition date
        duplicate_images_by_date = {}
        # List to store individual images
        individual_images = []
        # Iterate over each image in the collection
        #images = s2_sr_cld_col_with_clouds_masks.toList(filtered_count)
        
        images = s2_sr_cld_col_with_clouds_masks.toList(filtered_count)
        
        
        for i in range(filtered_count):
            image = ee.Image(images.get(i))
            
            # Get acquisition date
            timestamp_ms = image.date().getInfo()['value']
            timestamp_s = timestamp_ms / 1000
            dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
                
            acquisition_date = dt.strftime('%Y-%m-%d')

            # Check for duplicates
            if acquisition_date in unique_dates:
                print(f'Duplicate scene found for {acquisition_date}!')
                # Add the duplicate scene to the dictionary based on acquisition date
                if acquisition_date not in duplicate_images_by_date:
                    duplicate_images_by_date[acquisition_date] = []
                # Select bands
                selected_bands = ['B2', 'B3', 'B4', 'B5', 'B8', 'probability','clouds','cloudmask']
                image = image.select(selected_bands)
                duplicate_images_by_date[acquisition_date].append(image)
            else:
                # Add the acquisition date to the set
                unique_dates.add(acquisition_date)
                print(f'Single scene found for: {acquisition_date}!')

                # Select bands
                selected_bands = ['B2', 'B3', 'B4', 'B5', 'B8', 'probability','clouds','cloudmask']
                image = image.select(selected_bands)

                # Append image to the list for individual downloading
                individual_images.append(image)

        # Perform individual downloading for non-duplicate images
        for ind_image in individual_images:
            # Get acquisition date
            #acquisition_date = datetime.utcfromtimestamp(ind_image.date().getInfo()['value'] / 1000).strftime('%Y-%m-%d')
            try:
                timestamp_ms = ind_image.date().getInfo()['value']
                timestamp_s = timestamp_ms / 1000
                dt = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
                
                acquisition_date = dt.strftime('%Y-%m-%d')
                # acquisition_year = dt.strftime('%Y')
                # acquisition_month = dt.strftime('%m')
                # acquisition_day = dt.strftime('%d')
            except (KeyError, TypeError, AttributeError) as e:
                acquisition_date = acquisition_year = acquisition_month = acquisition_day = None
                print(f"Error extracting acquisition date: {e}")
                
            full_name = f'S2_SR_HARM_{shp_name}_{acquisition_date}.tif'
            
            # Check if the file name already exists in the CSV
            if file_name_exists(csv_path, full_name):
                print(f"File {full_name} already exists in the CSV. Skipping export and adding to the csv.")
                continue
            
            print(f'Adding {full_name} to the csv and summarizing its metadata for exporting to gdrive..')
            # Additional information to monitor
            cloud_coverage = ind_image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo() if ind_image.get('CLOUDY_PIXEL_PERCENTAGE') else None
            sensor_type = ind_image.get('SPACECRAFT_NAME').getInfo() if ind_image.get('SPACECRAFT_NAME') else None
            sensor_quality = ind_image.get('SENSOR_QUALITY_FLAG').getInfo() if ind_image.get('SENSOR_QUALITY_FLAG') else None
            datataken_id = ind_image.get('DATATAKE_IDENTIFIER').getInfo() if ind_image.get('SENSOR_QUALITY_FLAG') else None
        
   
            all_new_data.append([full_name, shp_name, acquisition_date, cloud_coverage, sensor_type, sensor_quality, datataken_id, 'Yes'])

            output_directory = 'S2_SR_HARM_2015_2023'
            #os.makedirs(output_directory, exist_ok=True)

            # Set up output path
            #output_path_individual = os.path.join(output_directory, f'{shp_name}_{acquisition_date}_{start_date}_{end_date}.tif')
            output_path_individual = os.path.join(output_directory, full_name)

            # Export individual image
            ind_image = ind_image.toFloat()
            task_individual = ee.batch.Export.image.toDrive(
                image=ind_image,
                #description=f'S2_SR_HARM_{shp_name}_{acquisition_date}',
                description=full_name,
                folder=output_directory,
                scale=10,
                region=bounding_box
                #timeout=120  # Increase the timeout duration
            )
            task_individual.start()

            while task_individual.status()['state'] in ['READY', 'RUNNING']:
                pass

            print(f'Individual image exported to: {output_path_individual}!')

        update_csv(csv_path, all_new_data)
    else:
        print('No scenes found that meet the specified criteria. Exiting.')
        

        
def export_3dem_to_drive(bounding_box, shp_name):
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
    
    # Set up CSV path for all bounding boxes
    csv_path = 'ee_3DEM_downloaded_info.csv'

    # Check if there are scenes in the specified bounding box
    if scene_count > 0:
        print(f'Number of scenes in the bounding box for {shp_name}: {scene_count}')
        
        # Mosaic the images in the collection
        mosaicked_image = collection.mosaic()

        # Get acquisition date (Note: DEMs may not have a specific acquisition date like optical imagery)
        acquisition_date = 'Not Applicable'
        
        # Additional information to monitor (customize as needed)
        sensor_type = '3DEP'
        
        full_name = f'3DEP1M_{shp_name}.tif'
        
        # Check if the file name already exists in the CSV
        if file_name_exists(csv_path, full_name):
            print(f"File {full_name} already exists in the CSV. Skipping export and adding to the csv.")
        else:
            all_new_data.append([full_name, shp_name, acquisition_date, sensor_type, 'Yes'])

            output_directory = 'FULL_3DEP1M_ee'
            os.makedirs(output_directory, exist_ok=True)

            # Set up output path
            output_path_individual = os.path.join(output_directory, f'3DEP1M_{shp_name}.tif')

            # Export the mosaicked DEM
            task_individual = ee.batch.Export.image.toDrive(
                image=mosaicked_image,
                description=f'3DEP1M_{shp_name}',
                folder=output_directory,
                scale=1,  # Adjust scale as needed
                region=bounding_box
            )
            task_individual.start()

            while task_individual.status()['state'] in ['READY', 'RUNNING']:
                pass

            print(f'Individual 3DEP DEM exported to: {output_path_individual}')

        update_csv(csv_path, all_new_data)
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
        
        # Check if the file name already exists in the CSV
        if file_name_exists(csv_path, full_name):
            print(f"File {full_name} already exists in the CSV. Skipping export and adding to the csv.")
            return

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
            scale=10,  # Adjust scale as needed
            region=bounding_box
            #timeout=120  # Increase the timeout duration
        )
        task_individual.start()

        while task_individual.status()['state'] in ['READY', 'RUNNING']:
            pass

        print(f'Individual 10M 3DEP DEM exported to: {output_path_individual}')

        update_csv(csv_path, all_new_data)
    else:
        print('No 10M 3DEP DEMs found in the specified bounding box. Exiting.')
        


# def export_chirp_to_drive(bounding_box, start_date, end_date,shp_name):
#     # Set up CSV path for all bounding boxes
#     csv_path = 'ee_CHIRPS_downloaded_info.csv'
    
#     # Create an empty list to store all new data
#     all_new_data = []

#     collection = (
#         ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
#         .filterBounds(bounding_box)
#         .filterDate(start_date, end_date)
#     )
    
#     # Get the number of scenes in the collection
#     scene_count = collection.size().getInfo()
    
#     # Check if there are scenes in the specified bounding box and time period
#     if scene_count > 0:
#         print(f'Number of scenes in the bounding box for {shp_name} from {start_date} to {end_date}: {scene_count}')
        
#         # Iterate over each image in the collection
#         images = collection.toList(scene_count)
#         for i in range(scene_count):
#             image = ee.Image(images.get(i))

#             # Get acquisition date
#             acquisition_date = image.date().format('YYYY-MM-dd').getInfo()
            
#             # Additional information to monitor (customize as needed)
#             sensor_type = 'CHIRPS'
            
#             full_name = f'CHIRPS_{acquisition_date}.tif'
            
#             # Check if the file name already exists in the CSV
#             if file_name_exists(csv_path, full_name):
#                 print(f"File {full_name} already exists in the CSV. Skipping export and adding to the csv.")
#                 continue

#             all_new_data.append([full_name, acquisition_date, sensor_type, 'Yes'])

#             output_directory = 'FULL_CHIRPS_ee'
            
#             os.makedirs(output_directory, exist_ok=True)

#             # Set up output path
#             output_path_individual = os.path.join(output_directory, full_name)

#             # Export individual CHIRPS image
#             task_individual = ee.batch.Export.image.toDrive(
#                 image=image,
#                 description=full_name,
#                 folder=output_directory,
#                 scale=5000,  # Adjust scale as needed
#                 region=bounding_box
#             )
#             task_individual.start()

#             while task_individual.status()['state'] in ['READY', 'RUNNING']:
#                 pass

#             print(f'Individual CHIRPS image exported to: {output_path_individual}')

#         update_csv(csv_path, all_new_data)
#     else:
#         print(f'No CHIRPS data found in the specified bounding box and time period from {start_date} to {end_date}. Exiting.')

# # Helper functions (assuming they are defined elsewhere in your code)
# def file_name_exists(csv_path, file_name):
#     # Implement the logic to check if the file name exists in the CSV
#     pass

# def update_csv(csv_path, data):
#     # Implement the logic to update the CSV with new data



def export_gridmet_to_drive(bounding_box, start_date, end_date, shp_name):
    # Set up CSV path for all bounding boxes
    csv_path = 'ee_GRIDMET_downloaded_info.csv'
    
    # Create an empty list to store all new data
    all_new_data = []

    collection = (
        ee.ImageCollection('IDAHO_EPSCOR/GRIDMET')
        .filterBounds(bounding_box)
        .filterDate(start_date, end_date)
    )
    
    # Get the number of scenes in the collection
    scene_count = collection.size().getInfo()
    
    # Check if there are scenes in the specified bounding box and time period
    if scene_count > 0:
        print(f'Number of scenes in the bounding box for {shp_name} from {start_date} to {end_date}: {scene_count}')
        
        # Iterate over each image in the collection
        images = collection.toList(scene_count)
        for i in range(scene_count):
            image = ee.Image(images.get(i))

            # Get acquisition date
            acquisition_date = image.date().format('YYYY-MM-dd').getInfo()
            
            # Get the band names for the image
            band_names = image.bandNames().getInfo()
            
            # Additional information to monitor (customize as needed)
            sensor_type = 'GRIDMET'
            
            full_name = f'GRIDMET_{acquisition_date}.tif'
            
            # Check if the file name already exists in the CSV
            if file_name_exists(csv_path, full_name):
                print(f"File {full_name} already exists in the CSV. Skipping export and adding to the csv.")
                continue

            # Append to the list the filename, acquisition date, sensor type, and band names
            all_new_data.append([full_name, acquisition_date, sensor_type, band_names])

            output_directory = 'FULL_GRIDMET_ee'
            
            os.makedirs(output_directory, exist_ok=True)

            # Set up output path
            output_path_individual = os.path.join(output_directory, full_name)
            
            # Select and rename the bands explicitly
            image = ee.Image(images.get(i)).select(
                ['pr', 'rmax', 'rmin', 'sph', 'srad', 'th', 'tmmn', 'tmmx', 'vs', 'erc', 'eto', 'bi', 'fm100', 'fm1000', 'etr', 'vpd'],
                ['Precipitation', 'MaxRelHumidity', 'MinRelHumidity', 'SpecificHumidity', 'SolarRadiation', 'WindDirection', 'MinTemp', 'MaxTemp', 'WindSpeed', 'EnergyReleaseComponent', 'RefEvapotranspiration', 'BurningIndex', 'FuelMoisture100', 'FuelMoisture1000', 'ActualEvapotranspiration', 'VaporPressureDeficit']
            )

            # Proceed with the export as usual
            task_individual = ee.batch.Export.image.toDrive(
                image=image,
                description=full_name,
                folder=output_directory,
                region=bounding_box
            )


            # # Export individual GRIDMET image
            # task_individual = ee.batch.Export.image.toDrive(
            #     image=image,
            #     description=full_name,
            #     folder=output_directory,
            #     #scale=5000,  # Adjust scale as needed
            #     region=bounding_box
            # )
            
            task_individual.start()

            # Wait for the task to complete before proceeding to the next
            while task_individual.status()['state'] in ['READY', 'RUNNING']:
                pass

            print(f'Individual GRIDMET image exported to: {output_path_individual}')
            print(f'Band names for {acquisition_date}: {band_names}')


# Helper functions (assuming they are defined elsewhere in your code)
def file_name_exists(csv_path, file_name):
    # Implement the logic to check if the file name exists in the CSV
    pass

def update_csv(csv_path, data):
    # Implement the logic to update the CSV with new data
    pass


        
def export_polaris_to_drive(bounding_box, start_date, end_date, shp_name):
    
    
    # Create an empty list to store all new data
    all_new_data = []

    # Define the POLARIS datasets
    datasets = {
        
        'clay_mean': 'projects/sat-io/open-datasets/polaris/clay_mean',
        'sand_mean': 'projects/sat-io/open-datasets/polaris/sand_mean',
        'silt_mean': 'projects/sat-io/open-datasets/polaris/silt_mean',
        
        'om_mean': 'projects/sat-io/open-datasets/polaris/om_mean',
        'ph_mean': 'projects/sat-io/open-datasets/polaris/ph_mean',
        
        'bd_mean': 'projects/sat-io/open-datasets/polaris/bd_mean',
        'ksat_mean': 'projects/sat-io/open-datasets/polaris/ksat_mean',
        'n_mean': 'projects/sat-io/open-datasets/polaris/n_mean',
        
        'theta_r_mean': 'projects/sat-io/open-datasets/polaris/theta_r_mean',
        'theta_s_mean': 'projects/sat-io/open-datasets/polaris/theta_s_mean',
        'lambda_mean': 'projects/sat-io/open-datasets/polaris/lambda_mean',
        'hb_mean': 'projects/sat-io/open-datasets/polaris/hb_mean',
        'alpha_mean': 'projects/sat-io/open-datasets/polaris/alpha_mean'
    }

    for dataset_name, dataset_path in datasets.items():
        collection = (
            ee.ImageCollection(dataset_path)
            .filterBounds(bounding_box)
            #.filterDate(start_date, end_date)
        )
        
        # Get the number of scenes in the collection
        scene_count = collection.size().getInfo()
        
        # Set up CSV path for all bounding boxes
        csv_path = 'ee_POLARIS_downloaded_info.csv'
        
        # Print the size of the image collection
        print(f'Number of scenes in {dataset_name}: {scene_count}')
        
        # Check if there are scenes in the specified bounding box and time period
        if scene_count > 0:
            print(f'Number of scenes in the bounding box for {shp_name} in {dataset_name}: {scene_count}')
            
            # Iterate over each image in the collection
            images = collection.toList(scene_count)
            for i in range(scene_count):
                image = ee.Image(images.get(i))
                # Initialize an empty image to add bands to
                #combined_image = ee.Image()
                
                # # Add all images in the collection as bands to the combined image
                # images = collection.toList(scene_count)
                # for i in range(scene_count):
                #     image = ee.Image(images.get(i))
                #     combined_image = combined_image.addBands(image.rename(f'{dataset_name}_{i}'))
                    
            # Get acquisition date (Note: DEMs may not have a specific acquisition date like optical imagery)
            acquisition_date = 'Not Applicable'
            
            # Additional information to monitor (customize as needed)
            sensor_type = '3DEP'
        
            # print(f'Number of bands in combined image for {dataset_name}: {combined_image.bandNames().size().getInfo()}')


            # Split dataset_name to remove .tif if it exists
            #dataset_name = dataset_name.split('.tif')[0]
            
            # Construct full_name without adding .tif to dataset_name
            full_name = f'POLARIS_{shp_name}_{dataset_name}.tif'
            
            # Check if the file name already exists in the CSV
            if file_name_exists(csv_path, full_name):
                print(f"File {full_name} already exists in the CSV. Skipping export and adding to the csv.")
                continue
                
            # Append new data to the list
            all_new_data.append([full_name, acquisition_date, sensor_type, 'Yes'])

            output_directory = 'FULL_POLARIS_ee'
            
            os.makedirs(output_directory, exist_ok=True)

            # Set up output path
            output_path_individual = os.path.join(output_directory, full_name)
            
            # Define the export task
            task = ee.batch.Export.image.toDrive(
                image=image,
                description=f'POLARIS_{shp_name}_{dataset_name}',
                folder=output_directory,
                #fileNamePrefix=f'{shp_name}_{dataset_name}',
                region=bounding_box,
                scale=30,
                #maxPixels=1e13
            )
            
                # Start the export task
            task.start()
            
            
            
            # Wait for the task to complete
            while task.status()['state'] in ['READY', 'RUNNING']:
                pass
            
            print(f'POLARIS {dataset_name} data for {shp_name} exported to Google Drive.')
            
        # Update the CSV with the new data
        update_csv(csv_path, all_new_data)
    else:
        print(f'No POLARIS {dataset_name} data found in the specified bounding box for {shp_name}.')
        
        
#     # Export SSURGO soil data
#     # ssurgo_collection = (
#     #     ee.FeatureCollection('users/databasin/ssurgo')
#     #     .filterBounds(bounding_box)
#     # )
    
#     # # Export SSURGO soil data using the official asset ID
#     # ssurgo_collection = (
#     #     ee.FeatureCollection('projects/soils-revealed/ssurgo')
#     #     .filterBounds(bounding_box)
#     # )

#     # # Get the number of SSURGO features in the collection
#     # ssurgo_feature_count = ssurgo_collection.size().getInfo()

#     # # Check if there are SSURGO features in the specified bounding box
#     # if ssurgo_feature_count > 0:
#     #     print(f'Number of SSURGO features in the bounding box for {shp_name}: {ssurgo_feature_count}')

#     #     # Iterate over each SSURGO feature in the collection
#     #     ssurgo_features = ssurgo_collection.toList(ssurgo_feature_count)
#     #     for j in range(ssurgo_feature_count):
#     #         ssurgo_feature = ee.Feature(ssurgo_features.get(j))

#     #         # Get acquisition date (Note: SSURGO features don't have acquisition dates)
#     #         acquisition_date_ssurgo = 'Not Applicable'
            
#     #         # Additional information to monitor (customize as needed)
#     #         feature_type = 'SSURGO'
            
#     #         ssurgo_full_name = f'SSURGO_{shp_name}.shp'
   
#     #         all_new_data.append([ssurgo_full_name, shp_name, acquisition_date_ssurgo, feature_type, 'Yes'])

#     #         output_directory_ssurgo = 'GEE/ssurgo_ee'
#     #         os.makedirs(output_directory_ssurgo, exist_ok=True)

#     #         # Set up output path for SSURGO
#     #         output_path_ssurgo_individual = os.path.join(output_directory_ssurgo, f'SSURGO_{shp_name}.shp')

#     #         # Export individual SSURGO feature
#     #         task_ssurgo_individual = ee.batch.Export.table.toDrive(
#     #             collection=ee.FeatureCollection(ssurgo_feature),
#     #             description=f'SSURGO_{shp_name}',
#     #             folder=output_directory_ssurgo,
#     #             fileFormat='SHP',
#     #         )
#     #         task_ssurgo_individual.start()

#     #         while task_ssurgo_individual.status()['state'] in ['READY', 'RUNNING']:
#     #             pass

#     #         print(f'Individual SSURGO feature exported to: {output_path_ssurgo_individual}')

#     # else:
#     #     print('No SSURGO features found in the specified bounding box. Exiting.')



# if __name__ == "__main__":
#     # This script is intended to be imported as a module, so there's no main execution here.
#     pass

        
# def export_s1(bounding_box, start_date, end_date, shp_name):
#     global output_data_list  # Use global to access the list outside
#     # Create an empty list to store all new data
#     initial_count = ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(bounding_box).size().getInfo()

#     all_new_data = []

#     collection = (
#         ee.ImageCollection('COPERNICUS/S1_GRD')
#         .filterBounds(bounding_box)
#         .filterDate(ee.Date(start_date), ee.Date(end_date))
#         .filter(ee.Filter.eq('instrumentMode', 'IW'))
#         #.filter(ee.Filter.rangeContains('system:incidence_angle', min_incidence_angle, max_incidence_angle))
#         #.select(['HH', 'VV'])  # Select HH and VV polarizations
#     )
    
#     # Get the number of scenes in the collection
#     filtered_count = collection.size().getInfo()
    
#     output_data_list = []
    
#     # Check if there are scenes in the collection
#     if filtered_count > 0:
#         print(f'Number of scenes before filtering: {initial_count}')
#         print(f'Number of scenes after filtering: {filtered_count}')
        
#         # Print the dates of each capture that meets the criteria
#         captured_dates = collection.aggregate_array('system:time_start').getInfo()
#         formatted_dates = [datetime.utcfromtimestamp(date / 1000).strftime('%Y-%m-%d') for date in captured_dates]
#         print(f'Dates of captures that meet the specified criteria for Sentinel 1: {formatted_dates}')
        
#         # Iterate over each image in the collection
#         images = collection.toList(filtered_count)
        
#         for i in range(filtered_count):
#             image = ee.Image(images.get(i))

#             acquisition_date = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%Y-%m-%d')
#             acquisition_year = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%Y')
#             acquisition_month = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%m')
#             acquisition_day = datetime.utcfromtimestamp(image.date().getInfo()['value'] / 1000).strftime('%d')
#             cloud_coverage = 0.0
#             sensor_type = 'Sentinel-1'
            
#             full_name = f'S1_{shp_name}_{acquisition_date}.tif'
   
#             #all_new_data.append([full_name, shp_name, acquisition_date, cloud_coverage, sensor_type, sensor_quality, datataken_id, 'Yes'])

#             output_directory = 'FULL_sentinel1_ee'
#             #os.makedirs(output_directory, exist_ok=True)

#             # Set up output path
#             #output_path_individual = os.path.join(output_directory, f'{shp_name}_{acquisition_date}_{start_date}_{end_date}.tif')
#             output_path_individual = os.path.join(output_directory, f'S1_{shp_name}_{acquisition_date}.tif')

#             # Export individual image
#             image = image.toFloat()
#             task_individual = ee.batch.Export.image.toDrive(
#                 image=image,
#                 description=f'S1_{shp_name}_{acquisition_date}',
#                 folder=output_directory,
#                 scale=10,
#                 region=bounding_box
#                 #timeout=120  # Increase the timeout duration
#             )
#             task_individual.start()

#             while task_individual.status()['state'] in ['READY', 'RUNNING']:
#                 pass

#             print(f'Individual image exported to: {output_path_individual}')

#         #update_csv(csv_path, all_new_data)
#     # else:
#     #     print('No scenes found that meet the specified criteria. Exiting.')

#     else:
#         print('No Sentinel-1 scenes found in the specified date range. Exiting.')
        
        
