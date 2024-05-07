import os
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
import geopandas as gpd
from fiona.crs import from_epsg
import shutil

def create_or_recreate_folder(folder):
    if os.path.exists(folder):
        print(f"Removing existing folder: {folder}")
        shutil.rmtree(folder)
    print(f"Creating folder: {folder}")
    os.makedirs(folder)
    return folder

def reproject_tiff(input_path, output_folder_reprojected, target_crs="epsg:32615"):
    # Create the output directory if it doesn't exist
    #os.makedirs(output_folder_reprojected, exist_ok=True)

    # Extract the base name of the TIFF file
    tif_base_name = os.path.splitext(os.path.basename(input_path))[0]

    # Construct the output path for the reprojected TIFF using the original name
    output_path = os.path.join(output_folder_reprojected, f'{tif_base_name}.tif')

    # Open the input TIFF file
    with rasterio.open(input_path) as src:
        # Check if the TIFF is already in the target CRS
        if src.crs.to_string() == target_crs:
            print(f"TIFF file '{input_path}' is already in the target CRS '{target_crs}'. No reprojection needed.")
            return

        # Read the metadata
        meta = src.meta.copy()

        # Reproject the TIFF
        # transform, width, height = calculate_default_transform(
        #     src.crs, target_crs, src.width, src.height, *src.bounds
        # )
        
        transform, width, height = calculate_default_transform(
        src.crs, target_crs, src.width, src.height, *src.bounds,
        resolution = 1  # Set target resolution
    )

        meta.update({
            'crs': target_crs,
            'transform': transform,
            'width': width,
            'height': height
        })
        
        
        print(f"TIFF file '{input_path}' is being reprojected to '{target_crs}'.")
        # Create the output raster file
        with rasterio.open(output_path, 'w', **meta) as dest:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dest, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=target_crs,
                    resampling=Resampling.bilinear
                )

def reproject_shp(input_path, output_folder, target_crs="EPSG:32615"):
    # Extract the base name of the shapefile
    shp_base_name = os.path.splitext(os.path.basename(input_path))[0]

    # Construct the output path for the reprojected shapefile using the original name
    output_path = os.path.join(output_folder, f'{shp_base_name}.shp')

    # Read the input shapefile
    gdf = gpd.read_file(input_path)

    # Check if the shapefile is already in the target CRS
    if gdf.crs == target_crs:
        print(f"Shapefile '{input_path}' is already in the target CRS '{target_crs}'. No reprojection needed.")
        return

    # Reproject the shapefile
    gdf = gdf.to_crs(target_crs)
    
    print(f"Shapefile '{input_path}' is being reprojected to '{target_crs}'.")
    # Save the reprojected shapefile to the output path
    gdf.to_file(output_path)

def reproject_all_shps(input_folder, output_folder):
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Iterate through each file in the input folder and its subfolders
    for root, dirs, files in os.walk(input_folder):
        for filename in files:
            if filename.endswith(".shp"):
                input_path = os.path.join(root, filename)
                reproject_shp(input_path, output_folder)

if __name__ == "__main__":
    # # Replace 'input_folder' and 'output_folder' with your actual folder paths
    # input_download = '../data/sentinel'
    # #output_folder_reprojected = '../temp_files'
    # output_folder_utm = '../data/sentinel_utm'
    
    #input_download = '../data/input_images/input_3dep1m/3DEP1m_ee-20231230T004620Z-001/3DEP1m_ee'
    
    input_download = '../data/input_images/3DEP1m_ee_utm'
    #output_folder_reprojected = '../temp_files'
    output_folder_utm = '../data/input_images/3DEP1m_ee_utm1'
    
    

    # Create or recreate the output folder for reprojected files
    #output_folder_reprojected = create_or_recreate_folder(output_folder_reprojected)
    output_folder_utm = create_or_recreate_folder(output_folder_utm)

    # Iterate through each file in the input folder and reproject
    for filename in os.listdir(input_download):
        if filename.endswith(".tif"):
            input_path = os.path.join(input_download, filename)
            reproject_tiff(input_path, output_folder_utm)



    # inp_shps = '../data/input_shps'
    # output_folder_shps = '../data/input_shps_utm'

    # # Reproject all shapefiles in inp_shps and its subfolders
    # reproject_all_shps(inp_shps, output_folder_shps)

    # # Move the reprojected files to the new destination
    # #shutil.move(output_folder_reprojected, output_folder_downloaded)
    # download_choice = input("Do delete the original download folder?")

    # if download_choice.lower() == 'y':
    
    #     print(f"Deleting original ee downloaded folder: {input_download}")
    #     shutil.rmtree(input_download)

            
