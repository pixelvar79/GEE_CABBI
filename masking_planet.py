import os
import rasterio
from rasterio.enums import Resampling
from shutil import copyfile
from collections import defaultdict
from rasterio.warp import reproject

import os
import rasterio
from rasterio.mask import mask
import fiona
from collections import defaultdict
from shutil import copyfile

# Function to group folders based on common prefix
def group_folders_by_prefix(planet_folder):
    folder_groups = defaultdict(list)

    # List all immediate subdirectories of the "planet" folder
    subdirs = [d for d in os.listdir(planet_folder) if os.path.isdir(os.path.join(planet_folder, d))]

    # Iterate through immediate subdirectories
    for subdir in subdirs:
        # Exclude zip files
        if not subdir.endswith('.zip'):
            # Extract the common prefix (assuming folders are separated by underscores)
            common_prefix = subdir.split('_')[0]

            # Append the folder path to the corresponding group
            folder_path = os.path.join(planet_folder, subdir)
            folder_groups[common_prefix].append(folder_path)

    return folder_groups

# Function to list all tifs ending with harmonized_clip.tif in each group
def list_tifs_in_group(group):
    tif_files = []

    for folder in group:
        # Walk through the folder and find tif files
        for dirpath, _, filenames in os.walk(folder):
            for filename in filenames:
                if filename.endswith('_harmonized_clip.tif'):
                    tif_files.append(os.path.join(dirpath, filename))

    return tif_files

# Function to find common patterns in file names
def find_common_pattern(folder_path):
    common_patterns = set()

    # Walk through the folder and find common patterns
    for _, _, filenames in os.walk(folder_path):
        for filename in filenames:
            # Extract common pattern (assuming shapefiles end with '.shp')
            if filename.endswith('.shp'):
                common_pattern = os.path.splitext(filename)[0]
                common_patterns.add(common_pattern)

    return common_patterns


def attach_tifs_to_groups(groups, common_patterns, shp_folder):
    attached_groups = {pattern: [] for pattern in common_patterns}

    # Walk through the shp_folder
    for _, _, filenames in os.walk(shp_folder):
        for filename in filenames:
            # Extract common pattern from shapefile (assuming shapefiles end with '.shp')
            common_pattern = os.path.splitext(filename)[0]

            # Attach tif files to the corresponding group
            for group_pattern, group_folders in groups.items():
                if group_pattern in common_pattern:
                    attached_groups[group_pattern].extend(group_folders)

    return attached_groups

# Function to generate masks for the images using the provided shapefile
def generate_mask(tif_paths, shapefile_path):
    with fiona.open(shapefile_path, "r") as shapefile:
        # Read all features
        features = [feature for feature in shapefile]

    # Extract the geometries from all features
    geometries = [feature['geometry'] for feature in features]

    for tif_path in tif_paths:
        with rasterio.open(tif_path) as src:
            # Read the image data
            img_data = src.read()

            # Copy the metadata from the source image
            out_meta = src.meta.copy()

            # Extract the folder path of the rescaled tif
            folder_path = os.path.dirname(tif_path)

            # Generate the mask using rasterio.mask
            masked_image, out_transform = mask(src, geometries, crop=True)

            # Update metadata with the new transform and shape
            out_meta.update({
                "height": masked_image.shape[1],
                "width": masked_image.shape[2],
                "transform": out_transform
            })

            # Construct the output path for the masked image in the same folder
            #output_path = os.path.join(folder_path, f'{tif_base_name}_masked.tif')
            
            # Construct the output path for the rescaled tif file
            output_tif = tif_path.replace('harmonized_clip.tif', f'_harmonized_clip_only_masked.tif')

            # Save the masked image to the specified output path
            with rasterio.open(output_tif, "w", **out_meta) as dest:
                dest.write(masked_image)

            print(f" - Masked and saved: {output_tif}")


# Specify the root directory
root_directory = '../data'

# Construct paths to relevant folders
planet_folder = os.path.join(root_directory, 'input_images', 'planet')
topo_folder = os.path.join(root_directory, '3DEP10m_ee_utm1')
shp_folder = os.path.join(root_directory, 'input_shps_sub_utm')

# Group folders based on common prefix at the immediate sublevel of the "planet" folder
folder_groups = group_folders_by_prefix(planet_folder)
print('f folder groups are: ', folder_groups)

# Find common patterns in file names in the topo folder
common_patterns = find_common_pattern(shp_folder)
print('f common patterns are: ', common_patterns)

# Attach tifs to corresponding groups
attached_groups = attach_tifs_to_groups(folder_groups, common_patterns, shp_folder)

print('f attached groups are: ', attached_groups)

for pattern, groups in attached_groups.items():
    print(f"Processing files for shapefile pattern '{pattern}':")

    # Iterate through each group
    for group in groups:
        # List tif files in the group
        tif_files = list_tifs_in_group([group])

        # Generate masks for the rescaled.tif files using the shapefile
        generate_mask(tif_files, os.path.join(shp_folder, f'{pattern}.shp'))

print("Processing complete.")