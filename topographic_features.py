import os
import numpy as np
import rasterio

from scipy.ndimage import sobel, gaussian_filter
from shapely.geometry import Polygon
from skimage import measure

import rasterio
from rasterio.transform import from_origin
from rasterio.enums import Resampling
import numpy as np

def calculate_hillshade(array, azimuth=315, altitude=45):
    slope_x = sobel(array, axis=0)
    slope_y = sobel(array, axis=1)
    slope = np.arctan(np.sqrt(slope_x**2 + slope_y**2))
    aspect = np.arctan2(-slope_y, slope_x)
    azimuth_rad = np.radians(azimuth)
    altitude_rad = np.radians(altitude)
    hillshade = np.sin(altitude_rad) * np.sin(slope) + np.cos(altitude_rad) * np.cos(slope) * np.cos(azimuth_rad - aspect)
    #hillshade = hillshade * 255  # Scale to 0-255
    return hillshade

# def calculate_slope(array):
    
#     # Create a mask excluding zero values
#     mask = (array != 0)

#     # Apply Sobel operators to the masked array
#     slope_x = sobel(array, axis=0)
#     slope_y = sobel(array, axis=1)

#     # Apply the mask to the gradients
#     slope_x[mask == False] = np.nan
#     slope_y[mask == False] = np.nan

#     slope_x = sobel(array, axis=0)
#     slope_y = sobel(array, axis=1)

#     slope = np.arctan(np.sqrt(slope_x**2 + slope_y**2))
#     #slope = np.arctan(np.sqrt(slope_x + slope_y))
#     #slope_degree = np.degrees(np.arctan2(np.abs(slope_y), np.abs(slope_x)))

#     slope_degree =  np.degrees(slope)
#     return slope

def calculate_slope(array,dem_src):
    # Get the geotransform information
        transform = dem_src.transform
        
        mask = (array != 0)

        # Calculate slope using NumPy's gradient function
        slope_x, slope_y = np.gradient(array, transform[0], transform[4])
        # Apply the mask to the gradients
        slope_x[mask == False] = np.nan
        slope_y[mask == False] = np.nan

        # Calculate slope magnitude
        slope_magnitude = np.sqrt(slope_x**2 + slope_y**2)

        # Convert slope to degrees
        slope_degree = np.degrees(np.arctan(slope_magnitude))
        return slope_degree

def calculate_curvature(array):
    # Sobel operators for gradient calculation
    sobel_x = sobel(array, axis=0)
    sobel_y = sobel(array, axis=1)
    slope = np.sqrt(sobel_x**2 + sobel_y**2)
    
    # Calculate second derivatives
    d2z_dx2 = sobel(sobel_x, axis=0)
    d2z_dy2 = sobel(sobel_y, axis=1)
    
    # Calculate curvature components
    profile_curvature = -(d2z_dx2 + d2z_dy2) / (1 + slope**2)
    
    # Calculate plan curvature
    plan_curvature = -d2z_dx2 * (1 + slope**2) / (slope**2) - d2z_dy2 * (1 + slope**2) / (slope**2)
    
    return profile_curvature, plan_curvature

def process_and_save_dem(input_dem_file, output_directory):
    # Load DEM data
    with rasterio.open(input_dem_file) as dem_src:
        dem_array = dem_src.read(1)

        # Calculate hillshade, slope, and curvatures
        hillshade = calculate_hillshade(dem_array)
        slope_degree = calculate_slope(dem_array, dem_src)
        
        # Handle invalid values (replace with 0)
        profile_curvature, plan_curvature = calculate_curvature(dem_array)

        # Stack the arrays
        stacked_array = np.stack([dem_array, hillshade, slope_degree, profile_curvature, plan_curvature], axis=-1)

        # Handle invalid values (replace with 0)
        # stacked_array[np.isnan(stacked_array)] = 0
        # stacked_array[np.isinf(stacked_array)] = 0

        # Clip data to valid range
        # stacked_array = np.clip(stacked_array, 0, 255).astype(rasterio.uint8)
        # stacked_array = np.clip(stacked_array, 0, 255)

        # Update profile for the output GeoTIFF
        profile = dem_src.profile
        #profile.update(dtype=rasterio.uint8, count=stacked_array.shape[-1])  # Update count parameter
        profile.update(count=stacked_array.shape[-1])  # Update count parameter

        # Generate output file name
        output_basename = os.path.splitext(os.path.basename(input_dem_file))[0]
        output_file = os.path.join(output_directory, f"{output_basename}_topo.tif")

        # Save the result
        with rasterio.open(output_file, 'w', **profile) as dst:
            for i in range(stacked_array.shape[-1]):
                dst.write_band(i + 1, stacked_array[:, :, i])

# Directory containing DEM files
input_directory = "../data/input_images/3DEP10m_ee_utm1"
output_directory = input_directory

# Process and save each DEM
for filename in os.listdir(input_directory):
    if filename.endswith(".tif"):
        input_file = os.path.join(input_directory, filename)
        process_and_save_dem(input_file, output_directory)


