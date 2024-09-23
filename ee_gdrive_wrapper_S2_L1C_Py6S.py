
import ee
import os
import datetime
from datetime import datetime, timezone
import csv
import ast
from Py6S import *

# Initialize the Earth Engine API
ee.Initialize()

# Function to create or update the CSV file
def update_csv(csv_path, new_data):
    header = ["File_Name", "Field_Name", "Acquisition_Date", "Cloud_Coverage", "Sensor_Type", "Sensor_Quality", "Datataken_ID", "Downloaded"]
    if not os.path.isfile(csv_path):
        with open(csv_path, 'w', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(header)
    with open(csv_path, 'a', newline='') as csv_file:
        writer = csv.writer(csv_file)
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

# Function to get Sentinel-2 collection with cloud probability
def get_s2_sr_cld_col(aoi, start_date, end_date):
    s2_sr_col = (ee.ImageCollection('COPERNICUS/S2')
                 .filterBounds(aoi)
                 .filterDate(ee.Date(start_date), ee.Date(end_date))
                 .filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE', 10)))

    s2_cloudless_col = (ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY')
                        .filterBounds(aoi)
                        .filterDate(ee.Date(start_date), ee.Date(end_date)))

    return ee.ImageCollection(ee.Join.saveFirst('s2cloudless').apply(**{
        'primary': s2_sr_col,
        'secondary': s2_cloudless_col,
        'condition': ee.Filter.equals(**{
            'leftField': 'system:index',
            'rightField': 'system:index'
        })
    }))

# Function to add cloud bands
def add_cloud_bands(img):
    cld_prb = ee.Image(img.get('s2cloudless')).select('probability')
    is_cloud = cld_prb.gt(50).rename('clouds')
    return img.addBands(ee.Image([cld_prb, is_cloud]))

# Function to add shadow bands
def add_shadow_bands(img):
    ndwi = img.normalizedDifference(['B3', 'B8']).rename('NDWI')
    water_threshold = 0.3
    not_water = ndwi.lt(water_threshold)
    SR_BAND_SCALE = 1e4
    dark_pixels = img.select('B8').lt(0.15 * SR_BAND_SCALE).multiply(not_water).rename('dark_pixels')
    shadow_azimuth = ee.Number(90).subtract(ee.Number(img.get('MEAN_SOLAR_AZIMUTH_ANGLE')))
    cld_proj = (img.select('clouds').directionalDistanceTransform(shadow_azimuth, 1 * 10)
                .reproject(**{'crs': img.select(0).projection(), 'scale': 100})
                .select('distance')
                .mask()
                .rename('cloud_transform'))
    shadows = cld_proj.multiply(dark_pixels).rename('shadows')
    return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

# Function to add cloud and shadow mask
def add_cld_shdw_mask(img):
    print('applying cloud shadows...')
    img_cloud = add_cloud_bands(img)
    img_cloud_shadow = add_shadow_bands(img_cloud)
    is_cld_shdw = img_cloud_shadow.select('clouds').add(img_cloud_shadow.select('shadows')).gt(0)
    is_cld_shdw = (is_cld_shdw.focalMin(2).focalMax(50 * 2 / 20)
                   .reproject(**{'crs': img.select([0]).projection(), 'scale': 20})
                   .rename('cloudmask'))
    return img.addBands(is_cld_shdw)

# Function to run Py6S
def (metadata):
    #print(metadata)
    s = SixS()
    s.geometry = Geometry.User()
    s.geometry.solar_z = metadata['solar_zenith_angle']
    s.geometry.solar_a = metadata['solar_azimuth_angle']
    s.geometry.view_z = 0  # Assume nadir view
    s.geometry.view_a = 0  # Assume nadir view
    s.geometry.month = int(metadata['month'])
    s.geometry.day = int(metadata['day'])
    s.atmos_profile = AtmosProfile.PredefinedType(AtmosProfile.MidlatitudeSummer)
    s.aero_profile = AeroProfile.PredefinedType(AeroProfile.Maritime)
    s.aot550 = 0.1  # Example AOD value
    s.wavelength = Wavelength(0.55)  # Example: Green band
    s.run()
    return s.outputs.transmittance_total_scattering.total / s.outputs.transmittance_global_gas.total

# Function to extract metadata for Py6S
# Function to extract metadata and prepare for Py6S
def extract_metadata(image):
    # Get the solar zenith and azimuth angles
    solar_zenith_angle = ee.Number(image.get('MEAN_SOLAR_ZENITH_ANGLE'))
    solar_azimuth_angle = ee.Number(image.get('MEAN_SOLAR_AZIMUTH_ANGLE'))

    # Get the date in milliseconds and convert to datetime
    date_ms = ee.Date(image.get('system:time_start')).millis()
    dt = ee.Date(date_ms).format('YYYY-MM-dd').split('-')
    
    # Prepare metadata dictionary
    metadata = ee.Dictionary({
        'solar_zenith_angle': solar_zenith_angle,
        'solar_azimuth_angle': solar_azimuth_angle,
        'month': ee.Number.parse(dt.get(1)),
        'day': ee.Number.parse(dt.get(2))
    })
    #print(image.set(metadata))
    
    #return image.set(metadata)
    return metadata

def apply_py6s_correction(image):
    # Fetch metadata in a client-side context
    metadata = extract_metadata(image)
    
    # Ensure to fetch the correction factor on the client-side
    correction_factor = run_py6s(metadata)
    
    # Apply correction
    return image.multiply(correction_factor).copyProperties(image, image.propertyNames())


# Export function
def export_s2(bounding_box, start_date, end_date, shp_name):
    csv_path = 'ee_s2_l1c_downloaded_info1.csv'
    all_new_data = []
    s2_sr_cld_col = get_s2_sr_cld_col(bounding_box, start_date, end_date)
    s2_sr_cld_col_with_clouds = s2_sr_cld_col.map(add_cloud_bands)
    s2_sr_cld_col_with_clouds_masks = s2_sr_cld_col_with_clouds.map(add_cld_shdw_mask)
    s2_sr_cld_col_corrected = s2_sr_cld_col_with_clouds_masks.map(apply_py6s_correction)

    filtered_count = s2_sr_cld_col_corrected.size().getInfo()

    # Check if there are scenes that meet the specified criteria
    if filtered_count > 0:
        #print(f'Number of scenes before filtering: {initial_count}')
        print(f'Number of scenes after filtering: {filtered_count}')
        
        # Print the dates of each capture that meets the criteria
        #captured_dates = s2_sr_cld_col_with_clouds_masks.aggregate_array('system:time_start').getInfo()
        
        captured_dates = s2_sr_cld_col_corrected.aggregate_array('system:time_start').getInfo()
        
        
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
        
        images = s2_sr_cld_col_corrected.toList(filtered_count)
        
        
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
                
            full_name = f'S2_L1C_CORRECTED_{shp_name}_{acquisition_date}.tif'
            
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

            output_directory = 'S2_L1C_CORRECTED_2015_2023'
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
        


def export_chirp_to_drive(bounding_box, start_date, end_date,shp_name):
    # Set up CSV path for all bounding boxes
    csv_path = 'ee_CHIRPS_downloaded_info.csv'
    
    # Create an empty list to store all new data
    all_new_data = []

    collection = (
        ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY')
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
            
            # Additional information to monitor (customize as needed)
            sensor_type = 'CHIRPS'
            
            full_name = f'CHIRPS_{acquisition_date}.tif'
            
            # Check if the file name already exists in the CSV
            if file_name_exists(csv_path, full_name):
                print(f"File {full_name} already exists in the CSV. Skipping export and adding to the csv.")
                continue

            all_new_data.append([full_name, acquisition_date, sensor_type, 'Yes'])

            output_directory = 'FULL_CHIRPS_ee'
            
            os.makedirs(output_directory, exist_ok=True)

            # Set up output path
            output_path_individual = os.path.join(output_directory, full_name)

            # Export individual CHIRPS image
            task_individual = ee.batch.Export.image.toDrive(
                image=image,
                description=full_name,
                folder=output_directory,
                scale=5000,  # Adjust scale as needed
                region=bounding_box
            )
            task_individual.start()

            while task_individual.status()['state'] in ['READY', 'RUNNING']:
                pass

            print(f'Individual CHIRPS image exported to: {output_path_individual}')

        update_csv(csv_path, all_new_data)
    else:
        print(f'No CHIRPS data found in the specified bounding box and time period from {start_date} to {end_date}. Exiting.')

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
        
        
