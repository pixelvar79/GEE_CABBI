import os
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.enums import Resampling
from sklearn.cluster import KMeans
from matplotlib import cm
import matplotlib.pyplot as plt
import sys  # Add this line to import the sys module
import seaborn as sns

from matplotlib import cm, colors

def calculate_julian_date(calendar_date):
    """Calculate Julian date from calendar date."""
    # Assuming the calendar_date format is YYYYMMDD
    year, month, day = int(calendar_date[:4]), int(calendar_date[4:6]), int(calendar_date[6:])
    start_of_year = np.datetime64(f'{year}-01-01')
    julian_date = (np.datetime64(f'{year}-{month:02d}-{day:02d}') - start_of_year) / np.timedelta64(1, 'D') + 1
    return int(julian_date)

def group_julian_date(julian_date):
    """Group Julian date into specified ranges."""
    if julian_date < 175:
        return "<175"
    elif 175 <= julian_date <= 265:
        return "175-265"
    else:
        return ">265"
def process_folder_by_julian_date_range(root_folder_path, output_folder_path):
    grouped_ndre_by_julian_date = {}  # Dictionary to store accumulated NDRE arrays for each Julian date range

    # Look for _masked.tif files in the subfolder
    masked_tif_files = [f for f in os.listdir(root_folder_path) if f.endswith('_masked.tif')]

    if not masked_tif_files:
        return None, None  # Return None values when no files are found

    for masked_tif_file in masked_tif_files:
        tif_path = os.path.join(root_folder_path, masked_tif_file)

        with rasterio.open(tif_path) as src:
            image = src.read()

        # Mask out nodata values before calculating NDRE
        ndre = calculate_ndre(image)
        ndre_masked = np.ma.masked_invalid(ndre)

        # Extract calendar date from filename
        calendar_date = masked_tif_file.split('_')[0]

        # Calculate Julian date
        julian_date = calculate_julian_date(calendar_date)

        # Group Julian date
        date_group = group_julian_date(julian_date)

        if date_group not in grouped_ndre_by_julian_date:
            grouped_ndre_by_julian_date[date_group] = np.zeros_like(ndre_masked)

        # Accumulate NDRE for each pixel
        grouped_ndre_by_julian_date[date_group] += ndre_masked

    # Save accumulated NDRE for each Julian date range as GeoTIFF and PNG
    for date_group, accumulated_ndre in grouped_ndre_by_julian_date.items():
        ndre_tif_path = os.path.join(output_folder_path, f'{date_group}_cum_ndre.tif')
        ndre_png_path = os.path.join(output_folder_path, f'{date_group}_cum_ndre.png')
        save_ndre_as_tif(accumulated_ndre, tif_path, ndre_tif_path)
        plot_ndre(accumulated_ndre, title=f'Accumulated NDRE - {date_group}', save_path=ndre_png_path)

        
def process_folder_by_julian_date_range_with_sd(root_folder_path, output_folder_path):
    grouped_ndre_by_julian_date = {}  # Dictionary to store accumulated NDRE arrays for each Julian date range

    # Look for _masked.tif files in the subfolder
    masked_tif_files = [f for f in os.listdir(root_folder_path) if f.endswith('_masked.tif')]

    if not masked_tif_files:
        return None, None  # Return None values when no files are found

    for masked_tif_file in masked_tif_files:
        tif_path = os.path.join(root_folder_path, masked_tif_file)

        with rasterio.open(tif_path) as src:
            image = src.read()

        # Mask out nodata values before calculating NDRE
        ndre = calculate_ndre(image)
        ndre_masked = np.ma.masked_invalid(ndre)

        # Extract calendar date from filename
        calendar_date = masked_tif_file.split('_')[0]

        # Calculate Julian date
        julian_date = calculate_julian_date(calendar_date)

        # Group Julian date
        date_group = group_julian_date(julian_date)

        if date_group not in grouped_ndre_by_julian_date:
            grouped_ndre_by_julian_date[date_group] = []

        # Accumulate NDRE for each pixel
        grouped_ndre_by_julian_date[date_group].append(ndre_masked)

    # Calculate SD for each Julian date range
    for date_group, ndre_arrays in grouped_ndre_by_julian_date.items():
        ndre_stack = np.stack(ndre_arrays)
        sd_values = np.std(ndre_stack, axis=0)
        sd_tif_path = os.path.join(output_folder_path, f'{date_group}_sd_ndre.tif')
        sd_png_path = os.path.join(output_folder_path, f'{date_group}_sd_ndre.png')
        save_sd_as_tif(sd_values, sd_tif_path)
        plot_ndre(sd_values, title=f'Standard Deviation NDRE - {date_group}', save_path=sd_png_path)


    

def extract_info_from_filename(tif_filename):
    """Extract information from the filename (shapefile name and year)."""
    # Assuming your filename format is like 'shapefile_name_20210101_....'
    parts = tif_filename.split('_')
    shapefile_name = parts[0]
    
    # Extracting the first four characters from the year string
    year = parts[1][:4]

    return shapefile_name, year

def calculate_ndre(image):
    """Calculate simplified NDRE for a given image."""
    red_edge = image[6]  # Red Edge band is at index 6 (0-based index)
    nir = image[7]  # NIR band is at index 7
    
    ndre = (nir - red_edge) / (nir + red_edge)  # Replace NaN with 0
    return ndre

def process_folder(root_folder_path, output_tif_path):
    accumulated_ndre = None
    tif_path = None  # Initialize tif_path here

    # Look for _masked.tif files in the subfolder
    masked_tif_files = [f for f in os.listdir(root_folder_path) if f.endswith('_masked.tif')]

    if not masked_tif_files:
        #print(f"No '_masked.tif' files found in subfolder: {root_folder_path}")
        return None, None  # Return None values when no files are found

    for masked_tif_file in masked_tif_files:
        tif_path = os.path.join(root_folder_path, masked_tif_file)

        with rasterio.open(tif_path) as src:
            image = src.read()

        # Mask out nodata values before calculating NDRE
        ndre = calculate_ndre(image)
        ndre_masked = np.ma.masked_invalid(ndre)

        # Accumulate NDRE for each pixel
        if accumulated_ndre is None:
            accumulated_ndre = np.zeros_like(ndre_masked)
        accumulated_ndre += ndre_masked

    # Save accumulated NDRE as GeoTIFF
    #output_tif_path = os.path.join(output_folder_path, f'{folder_name}_accumulated_ndre.tif')
    save_ndre_as_tif(accumulated_ndre, tif_path, output_tif_path)

    return accumulated_ndre, tif_path, output_tif_path

def save_ndre_as_tif(accumulated_ndre, input_tif_path, output_tif_path):
    with rasterio.open(input_tif_path) as src:
        profile = src.profile
        profile.update(
            dtype='float32',  # Adjust the datatype as needed
            count=1,
            compress='lzw'  # You can adjust compression options if needed
        )

        # Write the accumulated NDRE as a new GeoTIFF file
        with rasterio.open(output_tif_path, 'w', **profile) as dst:
            dst.write(accumulated_ndre.filled(0), 1)  # Fill mask
            
        
def save_sd_as_tif(data_array, output_tif_path, input_tif_path=None):
    if input_tif_path:
        # Use the profile of the provided input TIF file
        with rasterio.open(input_tif_path) as src:
            profile = src.profile
    else:
        # Create a default profile if no input TIF file is provided
        profile = {
            'driver': 'GTiff',
            'count': 1,
            'dtype': 'float32',
            'compress': 'lzw'  # Adjust compression options as needed
        }

    # Create a masked array to handle fill values
    masked_data_array = np.ma.masked_invalid(data_array)

    # Write the data array as a new GeoTIFF file
    with rasterio.open(output_tif_path, 'w', **profile) as dst:
        dst.write(masked_data_array, 1)
            
def load_accumulated_ndre(folder_path):
    # Assuming the accumulated NDRE TIFF follows the naming pattern {folder_name}_accumulated_ndre.tif
    accumulated_ndre_path = os.path.join(folder_path, f'{os.path.basename(folder_path)}_cum_ndre.tif')
    
    with rasterio.open(accumulated_ndre_path) as src:
        return np.ma.masked_invalid(src.read(1))
    
def plot_ndre(image, title="NDRE Image", save_path=None):
    """Plot NDRE image and save as PNG."""
    #plt.figure(figsize=(8, 8))
    plt.imshow(image)#, cmap='viridis')
    plt.title(title)
    plt.colorbar(label='NDRE Values', shrink=0.4)
    
    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()

def plot_cv(cv_values, title="Coefficient of Variation", save_path=None):
    """Plot coefficient of variation as an image and save as PNG."""
    num_groups, num_columns = cv_values.shape
    cv_values_2d = cv_values.reshape(num_groups, num_columns)
    
    plt.figure(figsize=(8, 5))
    plt.imshow(cv_values_2d, cmap='viridis')
    plt.colorbar(label='Coefficient of Variation (%) values', shrink=0.4)
    
    plt.title(title)

    if save_path:
        plt.savefig(save_path)
    else:
        plt.show()

# Specify the path to the input folder
# Specify the root directory
root_directory = '../data/input_images'

# Construct paths to relevant folders
planet_folder = os.path.join(root_directory, 'planet')
output_folder_path = '../data/processing/multiyear'

# Create output folder if it does not exist
if not os.path.exists(output_folder_path):
    os.makedirs(output_folder_path)
# Set a fixed seed for reproducibility
random_state_seed = 123

# # Dynamically iterate through folders and subfolders in the planet directory
for root, dirs, files in os.walk(planet_folder):
    for folder_name in dirs:
        # Exclude certain subfolders (e.g., 'PSScene')
        if folder_name != 'PSScene':
            folder_path = os.path.join(root, folder_name)

            # Check if it's not a zip file
            if not folder_name.endswith('.zip'):
                # Look for the subfolder containing '_masked.tif' files
                subfolder_path = None
                for subfolder in os.listdir(folder_path):
                    subfolder_path = os.path.join(folder_path, subfolder)
                    if os.path.isdir(subfolder_path) and any(f.endswith('_masked.tif') for f in os.listdir(subfolder_path)):
                        break

                if subfolder_path:
                    # Create an output folder for each input folder
                    folder_output_path = os.path.join(output_folder_path, folder_name)
                    os.makedirs(folder_output_path, exist_ok=True)

                    # Process the subfolder and calculate accumulated NDRE by Julian date range
                    process_folder_by_julian_date_range(subfolder_path, folder_output_path)

                    # Process the subfolder and calculate accumulated NDRE and SD by Julian date range among years
                    #process_folder_by_julian_date_range_with_sd(subfolder_path, folder_output_path)

# # # Dynamically iterate through folders and subfolders in the planet directory
# for root, dirs, files in os.walk(planet_folder):
#     for folder_name in dirs:
#         # Exclude certain subfolders (e.g., 'PSScene')
#         if folder_name != 'PSScene':
#             folder_path = os.path.join(root, folder_name)

#             # Check if it's not a zip file
#             if not folder_name.endswith('.zip'):
#                 # Look for the subfolder containing '_masked.tif' files
#                 subfolder_path = None
#                 for subfolder in os.listdir(folder_path):
#                     subfolder_path = os.path.join(folder_path, subfolder)
#                     if os.path.isdir(subfolder_path) and any(f.endswith('_masked.tif') for f in os.listdir(subfolder_path)):
#                         break

#                 if subfolder_path:
#                     #print(f"Processing folder: {folder_name}")
#                     # Create an output folder for each input folder
#                     folder_output_path = os.path.join(output_folder_path, folder_name)
#                     os.makedirs(folder_output_path, exist_ok=True)

#                     # Process the subfolder and calculate accumulated NDRE
#                     output_tif_path = os.path.join(folder_output_path, f'{folder_name}_cum_ndre.tif')
#                     accumulated_ndre, tif_path, output_tif_path = process_folder(subfolder_path, output_tif_path)
                    
#                     # Plot and save NDRE image as PNG
#                     png_ndre_path = os.path.join(folder_output_path, f'{folder_name}_cum_ndre.png')
#                     plot_ndre(accumulated_ndre, title=f'Accumulated NDRE - {folder_name}', save_path=png_ndre_path)

# def calculate_cv(image):
#     """Calculate the coefficient of variation for a given image."""
#     mean_value = np.mean(image)
#     std_deviation = np.std(image)
    
#     # Avoid division by zero
#     if mean_value == 0:
#         return 0
#     else:
#         return (std_deviation / mean_value) * 100

# grouped_ndre_arrays = {}  # Dictionary to store accumulated NDRE arrays for each group

        
# # Calculate coefficient of variation for each group
# for folder_name in os.listdir(output_folder_path):
#     if os.path.isdir(os.path.join(output_folder_path, folder_name)):
#         common_prefix = folder_name.split('_')[0]  # Extract the first string of the folder name
#         #print(common_prefix)
#         folder_path = os.path.join(output_folder_path, folder_name)

#         if common_prefix not in grouped_ndre_arrays:
#             grouped_ndre_arrays[common_prefix] = []

#         # Calculate and load accumulated NDRE
#         accumulated_ndre = load_accumulated_ndre(folder_path)
#         grouped_ndre_arrays[common_prefix].append(accumulated_ndre)

#         # Calculate coefficient of variation for each group
#         cv_values = np.apply_along_axis(calculate_cv, axis=0, arr=grouped_ndre_arrays[common_prefix])
#         #print(f'Coefficient of Variation for Group {common_prefix}: {cv_values}')
        
#         #original_cv_values = np.vstack(grouped_ndre_arrays[common_prefix])
#         # Plot and save coefficient of variation as PNG
#         png_cv_path = os.path.join(output_folder_path, f'{common_prefix}_cv.png')
#         plot_cv(cv_values, title=f'Coefficient of Variation - Group {common_prefix}', save_path=png_cv_path)

#         # Save coefficient of variation as GeoTIFF using the profile of cum_ndre.tif
#         cum_ndre_tif_path = os.path.join(output_folder_path, folder_name, f'{folder_name}_cum_ndre.tif')
#         cv_tif_path = os.path.join(output_folder_path, f'{common_prefix}_cv.tif')

#         save_sd_as_tif(cv_values, cv_tif_path, cum_ndre_tif_path)

#         # Print or save the coefficient of variation for each group
#         #print(f"Coefficient of Variation for Group {common_prefix}: {cv_values}")