# import os
# import geopandas as gpd
# import rasterio
# import pandas as pd
# import numpy as np
# from shapely.geometry import Point, MultiPolygon
# from datetime import datetime
# import matplotlib.pyplot as plt
# import gc  # Import garbage collection module
# from tqdm import tqdm  # Import tqdm for progress bar

# shp_folder = '../../data/input_shps_utm11/'
# tif_folder = '../../data/GEE_ANALYSIS_UTM/FULL_GRIDMET11_ee-20240923T025810Z-001/FULL_GRIDMET_ee'

# # Provided band names
# band_short_names = ['pr', 'rmax', 'rmin', 'sph', 'srad', 'th', 'tmmn', 'tmmx', 'vs', 'erc', 'eto', 'bi', 'fm100', 'fm1000', 'etr', 'vpd']
# band_long_names = ['Precipitation', 'MaxRelHumidity', 'MinRelHumidity', 'SpecificHumidity', 'SolarRadiation', 'WindDirection', 'MinTemp', 'MaxTemp', 'WindSpeed', 'EnergyReleaseComponent', 'RefEvapotranspiration', 'BurningIndex', 'FuelMoisture100', 'FuelMoisture1000', 'ActualEvapotranspiration', 'VaporPressureDeficit']

# def extract_date_from_filename(filename):
#     date_str = filename.split('_')[1].split('.')[0]
#     return datetime.strptime(date_str, '%Y-%m-%d').date()

# def get_pixel_value_at_centroid(src, geom):
#     centroid = geom.centroid
#     coords = [(centroid.x, centroid.y)]
#     pixel_values = []
#     for val in src.sample(coords):
#         pixel_values.append(val)
#     return pixel_values

# def process_shapefiles_and_tifs(shp_folder, tif_folder):
#     data = []
#     shp_files = [f for f in os.listdir(shp_folder) if f.endswith('.shp')]
#     tif_files = [f for f in os.listdir(tif_folder) if f.endswith('.tif')]
    
#     for shp_file in tqdm(shp_files, desc="Processing shapefiles"):
#         shp_path = os.path.join(shp_folder, shp_file)
#         gdf = gpd.read_file(shp_path)
#         for tif_file in tqdm(tif_files, desc="Processing TIFF files", leave=False):
#             tif_path = os.path.join(tif_folder, tif_file)
#             date = extract_date_from_filename(tif_file)
#             with rasterio.open(tif_path) as src:
#                 band_names = src.descriptions
#                 if not band_names or all(band_name is None for band_name in band_names):
#                     band_names = band_long_names
#                 for geom in gdf.geometry:
#                     pixel_values = get_pixel_value_at_centroid(src, geom)
#                     if pixel_values:
#                         for band_index, band_name in enumerate(band_names):
#                             data.append({
#                                 'shapefile': shp_file,
#                                 'date': date,
#                                 'band_name': band_name,
#                                 'pixel_value': pixel_values[0][band_index]
#                             })
#             # Free up memory after processing each TIFF file
#             gc.collect()
#     df = pd.DataFrame(data)
#     df.to_csv('extracted_pixel_values_accumulated.csv', index=False)
#     return df

# def accumulate_and_plot(df):
#     # Convert the 'date' column to datetime format
#     df['date'] = pd.to_datetime(df['date'])
#     # Extract month and day from the 'date' column
#     df['month'] = df['date'].dt.month
#     df['day'] = df['date'].dt.day
    
#     # Filter for the months of May, June, July, August, September, and October
#     df_filtered = df[df['month'].isin([5, 6, 7, 8, 9, 10])]

#     # Accumulate pixel values by day for each band
#     accumulated_data = df_filtered.groupby(['shapefile', 'band_name', 'month', 'day']).agg({'pixel_value': 'sum'}).groupby(level=[0, 1, 2]).cumsum().reset_index()
#     accumulated_data.to_csv('accumulated_pixel_values_accumulated.csv', index=False)

#     # Plot the progressive accumulation for each band
#     output_dir = '../../data/GRIDMET_acccumulated_figures1'
#     os.makedirs(output_dir, exist_ok=True)
    
#     for shp_name in tqdm(accumulated_data['shapefile'].unique(), desc="Plotting shapefiles"):
#         for band_name in tqdm(accumulated_data['band_name'].unique(), desc="Plotting bands", leave=False):
#             plt.figure(figsize=(10, 6))
#             for month in [5, 6, 7, 8, 9, 10]:
#                 df_month = accumulated_data[(accumulated_data['shapefile'] == shp_name) & (accumulated_data['band_name'] == band_name) & (accumulated_data['month'] == month)]
#                 plt.plot(df_month['day'], df_month['pixel_value'], label=f'Month {month}')
#             plt.title(f'Progressive Accumulation of {band_name} for {shp_name}', fontsize=14)
#             plt.xlabel('Day of Month', fontsize=16)
#             plt.ylabel('Accumulated Pixel Value', fontsize=16)
#             plt.legend(title='Month', fontsize=16)
#             plt.xticks(fontsize=14)
#             plt.yticks(fontsize=14)
#             plt.tight_layout()
#             plt.savefig(os.path.join(output_dir, f'{shp_name}_{band_name}_accumulation.png'))
#             plt.close()
#             # Free up memory after saving each plot
#             gc.collect()

# # Process shapefiles and TIFFs
# df = process_shapefiles_and_tifs(shp_folder, tif_folder)

# # Accumulate and plot
# accumulate_and_plot(df)

# import os
# import geopandas as gpd
# import rasterio
# import pandas as pd
# import numpy as np
# from shapely.geometry import Point, MultiPolygon
# from datetime import datetime
# import matplotlib.pyplot as plt
# import gc  # Import garbage collection module
# from tqdm import tqdm  # Import tqdm for progress bar

# shp_folder = '../../data/input_shps_utm11/'
# tif_folder = '../../data/GEE_ANALYSIS_UTM/FULL_GRIDMET11_ee-20240923T025810Z-001 - Copy/FULL_GRIDMET_ee'

# # Provided band names
# band_short_names = ['pr', 'rmax', 'rmin', 'sph', 'srad', 'th', 'tmmn', 'tmmx', 'vs', 'erc', 'eto', 'bi', 'fm100', 'fm1000', 'etr', 'vpd']
# band_long_names = ['Precipitation', 'MaxRelHumidity', 'MinRelHumidity', 'SpecificHumidity', 'SolarRadiation', 'WindDirection', 'MinTemp', 'MaxTemp', 'WindSpeed', 'EnergyReleaseComponent', 'RefEvapotranspiration', 'BurningIndex', 'FuelMoisture100', 'FuelMoisture1000', 'ActualEvapotranspiration', 'VaporPressureDeficit']

# def extract_date_from_filename(filename):
#     date_str = filename.split('_')[1].split('.')[0]
#     return datetime.strptime(date_str, '%Y-%m-%d').date()

# def get_pixel_value_at_centroid(src, geom):
#     centroid = geom.centroid
#     coords = [(centroid.x, centroid.y)]
#     pixel_values = []
#     for val in src.sample(coords):
#         pixel_values.append(val)
#     return pixel_values

# def process_shapefiles_and_tifs(shp_folder, tif_folder):
#     data = []
#     shp_files = [f for f in os.listdir(shp_folder) if f.endswith('.shp')]
#     tif_files = [f for f in os.listdir(tif_folder) if f.endswith('.tif')]
    
#     for shp_file in tqdm(shp_files, desc="Processing shapefiles"):
#         shp_path = os.path.join(shp_folder, shp_file)
#         gdf = gpd.read_file(shp_path)
#         for tif_file in tqdm(tif_files, desc="Processing TIFF files", leave=False):
#             tif_path = os.path.join(tif_folder, tif_file)
#             date = extract_date_from_filename(tif_file)
#             with rasterio.open(tif_path) as src:
#                 band_names = src.descriptions
#                 if not band_names or all(band_name is None for band_name in band_names):
#                     band_names = band_long_names
#                 for geom in gdf.geometry:
#                     pixel_values = get_pixel_value_at_centroid(src, geom)
#                     if pixel_values:
#                         for band_index, band_name in enumerate(band_names):
#                             data.append({
#                                 'shapefile': shp_file,
#                                 'date': date,
#                                 'band_name': band_name,
#                                 'pixel_value': pixel_values[0][band_index]
#                             })
#             # Free up memory after processing each TIFF file
#             gc.collect()
#     df = pd.DataFrame(data)
#     df.to_csv('extracted_pixel_values_accumulated.csv', index=False)
#     return df

# def accumulate_and_plot(df):
#     # Convert the 'date' column to datetime format
#     df['date'] = pd.to_datetime(df['date'])
#     # Extract month and day from the 'date' column
#     df['month'] = df['date'].dt.month
#     df['day'] = df['date'].dt.day
    
#     # Filter for the months of May, June, July, August, September, and October
#     df_filtered = df[df['month'].isin([5, 6, 7, 8, 9, 10])]

#     # Accumulate pixel values by day for each band
#     accumulated_data = df_filtered.groupby(['shapefile', 'band_name', 'month', 'day']).agg({'pixel_value': 'sum'}).groupby(level=[0, 1, 2]).cumsum().reset_index()
#     accumulated_data.to_csv('accumulated_pixel_values_accumulated.csv', index=False)

#     # Plot the progressive accumulation for each band
#     output_dir = '../../data/GRIDMET_acccumulated_figures1'
#     os.makedirs(output_dir, exist_ok=True)
    
#     for shp_name in tqdm(accumulated_data['shapefile'].unique(), desc="Plotting shapefiles"):
#         for band_name in tqdm(accumulated_data['band_name'].unique(), desc="Plotting bands", leave=False):
#             plt.figure(figsize=(10, 6))
#             for month in [5, 6, 7, 8, 9, 10]:
#                 df_month = accumulated_data[(accumulated_data['shapefile'] == shp_name) & (accumulated_data['band_name'] == band_name) & (accumulated_data['month'] == month)]
#                 plt.plot(df_month['day'].to_numpy(), df_month['pixel_value'].to_numpy(), label=f'Month {month}')
#             plt.title(f'Progressive Accumulation of {band_name} for {shp_name}', fontsize=14)
#             plt.xlabel('Day of Month', fontsize=16)
#             plt.ylabel('Accumulated Pixel Value', fontsize=16)
#             plt.legend(title='Month', fontsize=16)
#             plt.xticks(fontsize=14)
#             plt.yticks(fontsize=14)
#             plt.tight_layout()
#             plt.savefig(os.path.join(output_dir, f'{shp_name}_{band_name}_accumulation.png'))
#             plt.close()
#             # Free up memory after saving each plot
#             gc.collect()

# # Process shapefiles and TIFFs
# df = process_shapefiles_and_tifs(shp_folder, tif_folder)

# # Accumulate and plot
# accumulate_and_plot(df)


import os
import geopandas as gpd
import rasterio
import pandas as pd
import numpy as np
from shapely.geometry import Point, MultiPolygon
from datetime import datetime
import matplotlib.pyplot as plt
import gc  # Import garbage collection module
from tqdm import tqdm  # Import tqdm for progress bar

shp_folder = '../../data/input_shps_utm11/'
tif_folder = '../../data/GEE_ANALYSIS_UTM/FULL_GRIDMET11_ee-20240923T025810Z-001/FULL_GRIDMET_ee'

# Provided band names
band_short_names = ['pr', 'rmax', 'rmin', 'sph', 'srad', 'th', 'tmmn', 'tmmx', 'vs', 'erc', 'eto', 'bi', 'fm100', 'fm1000', 'etr', 'vpd']
band_long_names = ['Precipitation', 'MaxRelHumidity', 'MinRelHumidity', 'SpecificHumidity', 'SolarRadiation', 'WindDirection', 'MinTemp', 'MaxTemp', 'WindSpeed', 'EnergyReleaseComponent', 'RefEvapotranspiration', 'BurningIndex', 'FuelMoisture100', 'FuelMoisture1000', 'ActualEvapotranspiration', 'VaporPressureDeficit']

def extract_date_from_filename(filename):
    date_str = filename.split('_')[1].split('.')[0]
    return datetime.strptime(date_str, '%Y-%m-%d').date()

def get_pixel_value_at_centroid(src, geom):
    centroid = geom.centroid
    coords = [(centroid.x, centroid.y)]
    pixel_values = []
    for val in src.sample(coords):
        pixel_values.append(val)
    return pixel_values

def process_shapefiles_and_tifs(shp_folder, tif_folder):
    data = []
    shp_files = [f for f in os.listdir(shp_folder) if f.endswith('.shp')]
    tif_files = [f for f in os.listdir(tif_folder) if f.endswith('.tif')]
    
    for shp_file in tqdm(shp_files, desc="Processing shapefiles"):
        shp_path = os.path.join(shp_folder, shp_file)
        gdf = gpd.read_file(shp_path)
        for tif_file in tqdm(tif_files, desc="Processing TIFF files", leave=False):
            tif_path = os.path.join(tif_folder, tif_file)
            date = extract_date_from_filename(tif_file)
            with rasterio.open(tif_path) as src:
                band_names = src.descriptions
                if not band_names or all(band_name is None for band_name in band_names):
                    band_names = band_long_names
                for geom in gdf.geometry:
                    pixel_values = get_pixel_value_at_centroid(src, geom)
                    if pixel_values:
                        for band_index, band_name in enumerate(band_names):
                            data.append({
                                'shapefile': shp_file,
                                'date': date,
                                'band_name': band_name,
                                'pixel_value': pixel_values[0][band_index]
                            })
            # Free up memory after processing each TIFF file
            gc.collect()
    df = pd.DataFrame(data)
    df.to_csv('extracted_pixel_values_accumulated.csv', index=False)
    return df

def accumulate_and_plot(df):
    # Convert the 'date' column to datetime format
    df['date'] = pd.to_datetime(df['date'])
    # Extract year and day of the year from the 'date' column
    df['year'] = df['date'].dt.year
    df['day_of_year'] = df['date'].dt.dayofyear
    
    # Filter for the months of May, June, July, August, September, and October
    df_filtered = df[df['date'].dt.month.isin([5, 6, 7, 8, 9, 10])]

    # Accumulate pixel values by day of the year for each band
    accumulated_data = df_filtered.groupby(['shapefile', 'band_name', 'year', 'day_of_year']).agg({'pixel_value': 'sum'}).groupby(level=[0, 1, 2]).cumsum().reset_index()
    accumulated_data.to_csv('accumulated_pixel_values_accumulated.csv', index=False)

    # Plot the progressive accumulation for each band
    output_dir = '../../data/GRIDMET_acccumulated_figures1'
    os.makedirs(output_dir, exist_ok=True)
    
    for shp_name in tqdm(accumulated_data['shapefile'].unique(), desc="Plotting shapefiles"):
        for band_name in tqdm(accumulated_data['band_name'].unique(), desc="Plotting bands", leave=False):
            plt.figure(figsize=(10, 6))
            for year in accumulated_data['year'].unique():
                df_year = accumulated_data[(accumulated_data['shapefile'] == shp_name) & (accumulated_data['band_name'] == band_name) & (accumulated_data['year'] == year)]
                plt.plot(df_year['day_of_year'].to_numpy(), df_year['pixel_value'].to_numpy(), label=f'Year {year}')
            plt.title(f'Progressive Accumulation of {band_name} for {shp_name}', fontsize=14)
            plt.xlabel('Julian Date (Day of Year)', fontsize=16)
            plt.ylabel('Accumulated Pixel Value', fontsize=16)
            plt.legend(title='Year', fontsize=16)
            plt.xticks(fontsize=14)
            plt.yticks(fontsize=14)
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f'{shp_name}_{band_name}_accumulation.png'))
            plt.close()
            # Free up memory after saving each plot
            gc.collect()

# Process shapefiles and TIFFs
df = process_shapefiles_and_tifs(shp_folder, tif_folder)

# Accumulate and plot
accumulate_and_plot(df)
