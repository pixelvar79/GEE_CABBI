import os
import rasterio
from rasterio.enums import Resampling
from shutil import copyfile
from collections import defaultdict
from rasterio.warp import reproject
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
                if filename.endswith('harmonized_clip.tif'):
                    tif_files.append(os.path.join(dirpath, filename))

    return tif_files

# Function to find common patterns in file names
def find_common_pattern(folder_path):
    common_patterns = set()

    # Walk through the folder and find common patterns
    for _, _, filenames in os.walk(folder_path):
        for filename in filenames:
            # Extract common pattern (assuming files are separated by underscores)
            if filename.endswith('topo.tif'):
                common_pattern = filename.split('_')[1]
                common_patterns.add(common_pattern)

    return common_patterns

# Function to attach tifs to corresponding groups
def attach_tifs_to_groups(groups, common_patterns, topo_folder):
    attached_groups = {pattern: [] for pattern in common_patterns}

    # Walk through the topo folder
    for _, _, filenames in os.walk(topo_folder):
        for filename in filenames:
            # Extract common pattern (assuming files are separated by underscores)
            common_pattern = filename.split('_')[1]

            # Attach tif file to the corresponding group
            for group_pattern, group_folders in groups.items():
                if group_pattern in common_pattern:
                    attached_groups[group_pattern].extend(group_folders)

    return attached_groups

# Function to rescale harmonized_clip.tif files and save as _rescaled.tif using rasterio
# Function to rescale harmonized_clip.tif files and save as _rescaled.tif using rasterio
def rescale_and_save_rasterio(input_tif, output_tif, topo_tif):
    with rasterio.open(input_tif) as src:
        # Open the topo.tif file to get spatial information
        with rasterio.open(topo_tif) as topo_src:
            # Rescale the harmonized_clip.tif to the spatial resolution of topo.tif
            resampled_data = src.read(
                out_shape=(src.count, topo_src.height, topo_src.width),
                resampling=Resampling.bilinear
            )
            
            kwargs = src.meta.copy()
            kwargs.update({
                'transform': topo_src.transform,
                'width': topo_src.width,
                'height': topo_src.height
            })

            with rasterio.open(output_tif, 'w', **kwargs) as dst:
                dst.write(resampled_data)

# Specify the root directory
root_directory = '../data/input_images'

# Construct paths to relevant folders
planet_folder = os.path.join(root_directory, 'planet')
topo_folder = os.path.join(root_directory, '3DEP10m_ee_utm1')

# Group folders based on common prefix at the immediate sublevel of the "planet" folder
folder_groups = group_folders_by_prefix(planet_folder)
print('f folder groups are: ', folder_groups)

# Find common patterns in file names in the topo folder
common_patterns = find_common_pattern(topo_folder)
print('f common patterns are: ', common_patterns)

# Attach tifs to corresponding groups
attached_groups = attach_tifs_to_groups(folder_groups, common_patterns, topo_folder)

print('f attached groups are: ', attached_groups)

# Iterate through each common pattern and corresponding groups
for pattern, groups in attached_groups.items():
    print(f"Processing files for pattern '{pattern}':")

    # Iterate through each group
    for group in groups:
        # List tif files in the group
        tif_files = list_tifs_in_group([group])

        # Iterate through each tif file in the group
        for tif_file in tif_files:
            # Construct the path to the corresponding topo.tif file
            topo_tif = os.path.join(topo_folder, f'3DEP10M_{pattern}_topo.tif')

            # Construct the output path for the rescaled tif file
            output_tif = tif_file.replace('_clip.tif', f'_rescaled.tif')

            # Rescale and save the harmonized_clip.tif file using rasterio
            rescale_and_save_rasterio(tif_file, output_tif, topo_tif)

            print(f" - Rescaled and saved: {output_tif}")

print("Processing complete.")