import os
import rasterio
import geopandas as gpd
from rasterio.mask import mask
import matplotlib.pyplot as plt
import numpy as np
from skimage import exposure

def plot_ndre_and_bands(ndre, rescaled_bands, topo_bands, shp_name, output_folder, date):
    
    #rgb_rescaled = rescaled_bands[[5, 3, 1], :, :].transpose(1, 2, 0) #/ 4000  # Normalize to [0, 1]
    
    # Save Rescaled TIF as RGB Composite
    #rgb_rescaled = rescaled_bands[[5, 3, 1], :, :].transpose(1, 2, 0)   # Normalize to [0, 1]

    rgb_rescaled = rescaled_bands[[7, 5, 5], :, :].transpose(1, 2, 0) #/ 65535.0  # Normalize to [0, 1]
     # Convert masked array to a regular numeric array
    rgb_rescaled_numeric = np.ma.masked_invalid(rgb_rescaled).filled(0)


    # Apply histogram equalization to each channel separately
    equalized_r = exposure.equalize_hist(rgb_rescaled_numeric[..., 0])
    equalized_g = exposure.equalize_hist(rgb_rescaled_numeric[..., 1])
    equalized_b = exposure.equalize_hist(rgb_rescaled_numeric[..., 2])

    equalized_rgb_rescaled = np.stack([equalized_r, equalized_g, equalized_b], axis=-1)

    data_shape = equalized_rgb_rescaled.shape
    figsize = (data_shape[1]/5, data_shape[0]/6)  # Adjust the divisor based on your preference
    #plt.figure(figsize=(16, 10))
    plt.figure(figsize=figsize)
    #plt.figure(figsize=(16, 10))

    plt.title('Rescaled TIF (RGB Composite)')
    plt.imshow(equalized_rgb_rescaled)

    #plt.colorbar(label='Pixel Value')
    plt.axis('off')  # Remove axis labels
    output_path = os.path.join(output_folder, f'{shp_name}_rescaled_rgb_{date}.png')
    plt.savefig(output_path)
    plt.close()

    # Save NDRE plot with fixed color scale (0-1)
    #plt.figure(figsize=(10, 10))
    plt.figure(figsize=figsize)
    #plt.figure(figsize=(16, 16))
    plt.title(f'NDRE: {shp_name} {date}')
    plt.imshow(ndre, cmap='rainbow', aspect='auto', vmin=0, vmax=1)
    plt.colorbar(label='NDRE Value',shrink=0.4)
    
    plt.axis('off')  # Remove axis labels
    output_path = os.path.join(output_folder, f'{shp_name}_ndre_{date}.png')
    plt.savefig(output_path)
    plt.close()
    #plt.figure(figsize=(16, 10))
    # Save individual plots for each band of the corresponding topo.tif
    for i, band in enumerate(topo_bands, start=1):
        #plt.figure(figsize=(10, 10))
        #plt.figure(figsize=figsize)
        
        band_title = ""
        if i == 1: 
            band_title = "Altitude"
        if i == 2:
            band_title = "Hillshade"
        elif i == 3:
            band_title = "Slope"
        elif i == 4:
            band_title = "Profile Curvature"
        elif i == 5:
            band_title = "Plan Curvature"

        # Rescale Topo Band 4 to a narrow color range
        plt.title(f'{shp_name} {band_title}')
        plt.figure(figsize=figsize)
        if i == 4:
            #pass
            #plt.imshow(band, cmap='rainbow', vmin=np.percentile(band, 0), vmax=np.percentile(band, 10))
            # band_min, band_max = np.percentile(band, 10), np.percentile(band, 90)
            # band_to_show = np.clip(band, band_min, band_max)
            plt.imshow(band, cmap='rainbow',vmin=-2,vmax=2)
           
        else:
        #     # plt.figure(figsize=figsize)
        #     # #plt.figure(figsize=(16, 16))
        #     # plt.title(f'{shp_name} {band_title}')
            plt.imshow(band, cmap='rainbow', aspect='auto')
            
        plt.colorbar(label='Pixel Value',shrink=0.4)
        plt.axis('off')  # Remove axis labels
        output_path = os.path.join(output_folder, f'{shp_name}_{band_title}.png')
        plt.savefig(output_path)
        plt.close()

def scatterplot_ndre_vs_topo(ndre, topo_bands, shp_name, output_folder, date):
    # Create a scatterplot for NDRE vs each topo.tif band
    fig, axs = plt.subplots(1, len(topo_bands), figsize=(5 * len(topo_bands), 5))
    fig.suptitle(f'Scatterplots for NDRE vs Topo Bands - {shp_name} - Date: {date}')

    # Scatterplot for each topo.tif band
    for i, band in enumerate(topo_bands, start=0):
        axs[i].scatter(ndre.flatten(), band.flatten(), alpha=0.5, marker='.')
        axs[i].set_title(f'Band {i+1}')

    # Set common labels
    fig.text(0.5, 0.04, 'NDRE', ha='center')
    fig.text(0.04, 0.5, 'Topo Bands', va='center', rotation='vertical')

    # Save the figure
    output_path = os.path.join(output_folder, f'{shp_name}_scatterplots_{date}.png')
    plt.savefig(output_path)
    plt.close()

# def save_individual_figures(data, output_folder, shp_name, date):
#     for i, band in enumerate(data[:-1], start=1):
#         fig, ax = plt.subplots(figsize=(10, 5))
#         ax.imshow(band, cmap='viridis', aspect='auto')
#         ax.set_title(f'{shp_name} - {date} - Topo Band {i}')
#         output_path = os.path.join(output_folder, f'{shp_name}_band_{i}_{date}.png')
#         plt.savefig(output_path)
#         plt.close()

#     # Save figure for rescaled.tif
#     fig, ax = plt.subplots(figsize=(10, 5))
#     ax.imshow(data[-1], cmap='viridis', aspect='auto')
#     ax.set_title(f'{shp_name} - {date} - Rescaled TIF')
#     output_path = os.path.join(output_folder, f'{shp_name}_rescaled_{date}.png')
#     plt.savefig(output_path)
#     plt.close()

# Function to calculate NDRE index
def calculate_ndre(red_edge_band, nir_band):
    ndre = (nir_band - red_edge_band) / (nir_band + red_edge_band)
    return ndre

# Function to mask raster data using a shapefile
def mask_raster_with_shapefile(raster_path, shapefile_path):
    with rasterio.open(raster_path) as src:
        # Read the shapefile
        metadata = src.meta
        shapefile = gpd.read_file(shapefile_path)

        # Mask the raster using the shapefile
        masked_data, _ = mask(src, shapefile.geometry, crop=True, filled=False)

    return masked_data, metadata

# Function to dynamically find topo.tif files matching the shp_name
def find_topo_tif(topo_folder, shp_name):
    topo_files = [f for f in os.listdir(topo_folder) if shp_name.lower() in f.lower() and f.endswith('_topo.tif')]
    #print(topo_files)

    if len(topo_files) > 0:
        return os.path.join(topo_folder, topo_files[0])
    else:
        raise FileNotFoundError(f"No matching topo.tif file found for {shp_name}")

# Function to mask raster data using a shapefile
def mask_shapefiles(raster_path, shapefile_folder):
    with rasterio.open(raster_path) as src:
        metadata = src.meta

        # Iterate through each shapefile in the folder
        for shapefile_name in os.listdir(shapefile_folder):
            shapefile_path = os.path.join(shapefile_folder, shapefile_name)

            if shapefile_name.endswith('.shp'):
                shapefile = gpd.read_file(shapefile_path)

                # Mask the raster using the shapefile
                masked_data, _ = mask(src, shapefile.geometry, crop=True, filled=False)

                # Save the masked data as a new raster
                output_path = os.path.join(shapefile_folder, f'masked_{shapefile_name[:-4]}.tif')
                with rasterio.open(output_path, 'w', **metadata) as dst:
                    dst.write(masked_data)

# Function to process each planet subfolder
def process_folder(root_directory):
    planet_folder = os.path.join(root_directory, 'planet')
    output_base_folder = '../data/processing/figures1'

    # Iterate through each planet subfolder
    for planet_subfolder in os.listdir(planet_folder):
        # Skip processing if it's a zip folder
        if planet_subfolder.endswith('.zip'):
            print(f"Skipping processing for {planet_subfolder} as it is a zip file.")
            continue
        output_folder = os.path.join(output_base_folder, planet_subfolder)

        # Create output folder if it does not exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Construct paths to relevant folders
        current_planet_folder = os.path.join(planet_folder, planet_subfolder)

        # Find all rescaled tif files in the folder using os.walk()
        #rescaled_tif_files = [os.path.join(dirpath, filename) for dirpath, _, filenames in os.walk(current_planet_folder) for filename in filenames if filename.endswith('_rescaled.tif')]
        rescaled_tif_files = [os.path.join(dirpath, filename) for dirpath, _, filenames in os.walk(current_planet_folder) for filename in filenames if filename.endswith('_only_masked.tif')]
        
        # Define the shapefile path and extract the shp_name
        shp_path = '../data/input_shps_sub_utm/' + planet_subfolder.split('_mask')[0] + '.shp'
        shp_name = os.path.splitext(os.path.basename(shp_path))[0]
        #print(shp_path)
        #print(shp_name)

        # Iterate through each rescaled tif file
        for tif_path in rescaled_tif_files:
            tif_file = os.path.basename(tif_path)

            # Extract the date from the rescaled tif filename
            date = tif_file[:8]
            month = tif_file[4:6]

            # Check if the month is June (06)
            #if month == '06':
                # Mask the tif file using the shapefile
            #print(tif_path)
            masked_image, metadata = mask_raster_with_shapefile(tif_path, shp_path)

            # Calculate NDRE for the masked data
            red_edge_band = masked_image[6]  # assuming red_edge_band is band 7
            nir_band = masked_image[7]  # assuming nir_band is band 8
            ndre = calculate_ndre(red_edge_band, nir_band)

            # Identify the corresponding topo.tif file dynamically based on the naming pattern
            topo_folder = os.path.join(root_directory, '3DEP10m_ee_utm1')
            topo_tif_path = find_topo_tif(topo_folder, shp_name)

            # Mask the topo.tif file using the shapefile
            masked_topo, _ = mask_raster_with_shapefile(topo_tif_path, shp_path)

            # Create subplots figure and save
            plot_ndre_and_bands(ndre, masked_image, masked_topo, shp_name, output_folder, date)
            
            # Save individual figures for NDRE, topo bands, and rescaled.tif
            #save_individual_figures([masked_topo[6], masked_topo[7], masked_topo[8], masked_topo[9], ndre], output_folder, shp_name, date)

            # Create scatterplots of NDRE vs Topo Bands
            #scatterplot_ndre_vs_topo(ndre, [masked_topo[6], masked_topo[7], masked_topo[8], masked_topo[9]], shp_name, output_folder, date)
            #scatterplot_ndre_vs_topo(ndre, masked_topo, shp_name, output_folder, date)

        print(f"Processing complete for each map in {planet_subfolder}.")

        # Initialize an array to accumulate NDRE values
        accumulated_ndre = None

        # Iterate through each rescaled tif file
        for tif_path in rescaled_tif_files:
            tif_file = os.path.basename(tif_path)

            # Extract the date from the rescaled tif filename
            date = tif_file[:8]

            # Mask the tif file using the shapefile
            print(tif_file)
            masked_image, metadata = mask_raster_with_shapefile(tif_path, shp_path)

            # Calculate NDRE for the masked data
            red_edge_band = masked_image[6]  # assuming red_edge_band is band 7
            nir_band = masked_image[7]  # assuming nir_band is band 8
            ndre = calculate_ndre(red_edge_band, nir_band)

            # Accumulate NDRE values
            if accumulated_ndre is None:
                accumulated_ndre = ndre
            else:
                accumulated_ndre += ndre
        # Normalize accumulated NDRE to 0-1 scale
        normalized_accumulated_ndre = (accumulated_ndre - np.min(accumulated_ndre)) / (np.max(accumulated_ndre) - np.min(accumulated_ndre))
        data_shape = normalized_accumulated_ndre.shape
        figsize = (data_shape[1] / 5, data_shape[0] / 6)  # Adjust the divisor based on your preference

        plt.figure(figsize=figsize)
        # Plot and save the accumulated NDRE figure
        #plt.figure(figsize=(10, 10))
        #plt.figure(figsize=(16, 16))
        plt.title(f'Accumulated NDRE: {shp_name}')
        plt.imshow(normalized_accumulated_ndre, cmap='rainbow', aspect='auto')
        
        plt.colorbar(label='Sum of NDRE Values', shrink=0.4)
        plt.axis('off')  # Remove axis labels

        # Save the figure inside the current planet subfolder
        output_path = os.path.join(output_folder, f'{shp_name}_accumulated_ndre.png')
        print(output_path)
        plt.savefig(output_path)
        plt.close()

        print(f"Processing complete for cum NDRE in {planet_subfolder}.")

# Example usage:
root_directory = '../data/input_images'
process_folder(root_directory)
