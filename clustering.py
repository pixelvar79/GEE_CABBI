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

# def process_folder(root_folder_path):
#     """Process all masked TIFs in the given folder."""
#     accumulated_ndre = None

#     for root, dirs, files in os.walk(root_folder_path):
#         tif_files = [f for f in files if f.endswith('masked.tif')]

#         for tif_file in tif_files:
#             tif_path = os.path.join(root, tif_file)

#             with rasterio.open(tif_path) as src:
#                 image = src.read()

#             # Calculate NDRE for the image
#             ndre = calculate_ndre(image)

#             # Accumulate NDRE for each pixel
#             if accumulated_ndre is None:
#                 accumulated_ndre = np.zeros_like(ndre)
#             accumulated_ndre += ndre
            
#     #print(accumulated_ndre)
#     return accumulated_ndre, tif_path

# def process_folder(root_folder_path):
#     accumulated_ndre = None
#     tif_path = None  # Initialize tif_path here

#     # Look for _masked.tif files in the subfolder
#     masked_tif_files = [f for f in os.listdir(root_folder_path) if f.endswith('_masked.tif')]

#     if not masked_tif_files:
#         print(f"No '_masked.tif' files found in subfolder: {root_folder_path}")
#         return None, None  # Return None values when no files are found

#     for masked_tif_file in masked_tif_files:
#         tif_path = os.path.join(root_folder_path, masked_tif_file)

#         with rasterio.open(tif_path) as src:
#             image = src.read()

#         # Mask out nodata values before calculating NDRE
#         ndre = calculate_ndre(image)
#         ndre_masked = np.ma.masked_invalid(ndre)

#         # Accumulate NDRE for each pixel
#         if accumulated_ndre is None:
#             accumulated_ndre = np.zeros_like(ndre_masked)
#         accumulated_ndre += ndre_masked

#     return accumulated_ndre, tif_path

def process_folder(root_folder_path, output_tif_path):
    accumulated_ndre = None
    tif_path = None  # Initialize tif_path here

    # Look for _masked.tif files in the subfolder
    masked_tif_files = [f for f in os.listdir(root_folder_path) if f.endswith('_only_masked.tif')]

    if not masked_tif_files:
        print(f"No '_masked.tif' files found in subfolder: {root_folder_path}")
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
    save_accumulated_ndre_as_tif(accumulated_ndre, tif_path, output_tif_path)

    return accumulated_ndre, tif_path, output_tif_path

def save_accumulated_ndre_as_tif(accumulated_ndre, input_tif_path, output_tif_path):
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

# def cluster_and_plot(accumulated_ndre, n_clusters=None, random_state=None):
#     """Perform k-means classification on the accumulated NDRE."""
#     reshaped_ndre = accumulated_ndre.reshape(-1, 1)
#     #print(reshaped_ndre.unique())

#     #kmeans = KMeans(n_clusters=n_clusters, random_state=random_state)
    
#     reshaped_ndre = np.nan_to_num(reshaped_ndre)
    
#     non_zero_mask = np.all(reshaped_ndre != 0, axis=1)

#     # Apply k-means classification only to the masked pixels
#     kmeans = KMeans(n_clusters=n_clusters, random_state=random_state)
#     try:
#         kmeans.fit(reshaped_ndre[non_zero_mask])
        
#     # try:
#     #     # Replace NaN with 0 before fitting k-means
#     #     #kmeans.fit(np.nan_to_num(reshaped_ndre))
#     #     kmeans.fit(reshaped_ndre)
#     except ValueError as e:
#         print(f"Error: {e}")
#         print("Please check your data for NaN values.")
#         sys.exit(1)

#     cluster_labels_image = kmeans.labels_.reshape(accumulated_ndre.shape)
#     cmap = cm.get_cmap('rainbow', n_clusters)

#     return cluster_labels_image, cmap

from scipy.stats import mode

def cluster_and_plot(accumulated_ndre, n_clusters=None, random_state=None):
    """Perform k-means classification on the accumulated NDRE."""
    reshaped_ndre = accumulated_ndre.reshape(-1, 1)

    # Identify the most frequent value as a potential nodata value
    most_frequent_value, _ = mode(reshaped_ndre, axis=None)
    most_frequent_value = most_frequent_value.item()

    # Create a mask for potential nodata values
    nodata_mask = reshaped_ndre == most_frequent_value

    # Apply k-means classification only to non-nodata pixels
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state)
    
    try:
        kmeans.fit(reshaped_ndre[~nodata_mask].reshape(-1, 1))
    except ValueError as e:
        print(f"Error: {e}")
        print("Please check your data for NaN values.")
        sys.exit(1)

    # Initialize cluster_labels_image with nodata values
    cluster_labels_image = np.full_like(reshaped_ndre, most_frequent_value)
    cluster_labels_image[~nodata_mask] = kmeans.labels_ +1
    
    # Get unique non-nodata cluster labels
    unique_labels = np.unique(cluster_labels_image[~nodata_mask])

    # Remove empty clusters
    non_empty_clusters = [label for label in unique_labels if np.sum(cluster_labels_image == label) > 0]

    # Assign continuous cluster numbers to remaining clusters
    for i, label in enumerate(non_empty_clusters, start=1):
        cluster_labels_image[cluster_labels_image == label] = i

    cluster_labels_image = cluster_labels_image.reshape(accumulated_ndre.shape)
    #cmap = cm.get_cmap('rainbow', n_clusters)
    cmap = cm.get_cmap('rainbow', len(non_empty_clusters))
    
    # Use seaborn color palette for cmap
    palette = sns.color_palette("husl", len(non_empty_clusters))
    cmap = colors.ListedColormap(palette)

    return cluster_labels_image, cmap

def save_clustered_image(cluster_labels_image, output_path, input_tif_path):
    """Save the clustered image as a GeoTIFF file with the same metadata as the input masked TIF."""
    with rasterio.open(input_tif_path) as src:
        profile = src.profile
        profile.update(
            dtype='uint8',  # Adjust the datatype as needed
            count=1,
            compress='lzw'  # You can adjust compression options if needed
        )

        # Write the clustered image
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(cluster_labels_image.astype('uint8'), 1)

def save_figure(output_folder_path, file_name='clustered_image.png'):
    """Save the current matplotlib figure."""
    plt.axis('off')  # Remove axis labels
    figure_path = os.path.join(output_folder_path, file_name)
    plt.savefig(figure_path)

# Specify the path to the input folder
# Specify the root directory
root_directory = '../data/input_images'

# Construct paths to relevant folders
planet_folder = os.path.join(root_directory, 'planet')
output_folder_path = '../data/processing/clustering1'

# Create output folder if it does not exist
if not os.path.exists(output_folder_path):
    os.makedirs(output_folder_path)
# Set a fixed seed for reproducibility
random_state_seed = 123

# Dynamically iterate through folders and subfolders in the planet directory
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
                    if os.path.isdir(subfolder_path) and any(f.endswith('_only_masked.tif') for f in os.listdir(subfolder_path)):
                        break

                if subfolder_path:
                    print(f"Processing folder: {folder_name}")
                    # Create an output folder for each input folder
                    folder_output_path = os.path.join(output_folder_path, folder_name)
                    os.makedirs(folder_output_path, exist_ok=True)

                    # Process the subfolder and calculate accumulated NDRE
                    output_tif_path = os.path.join(folder_output_path, f'{folder_name}_cum_ndre.tif')
                    accumulated_ndre, tif_path, output_tif_path = process_folder(subfolder_path, output_tif_path)

                    if accumulated_ndre is not None:  # Check if processing was successful
                        # Perform k-means clustering on the accumulated NDRE with fixed seed
                        n_clusters = 5  # Set the number of clusters as needed
                        cluster_labels_image, cmap = cluster_and_plot(accumulated_ndre, n_clusters=n_clusters, random_state=random_state_seed)

                        

                        # Save clustered image with input folder name
                        output_tif_path = os.path.join(folder_output_path, f'{folder_name}_kmeans.tif')
                        save_clustered_image(cluster_labels_image, output_tif_path, tif_path)
                        plt.figure(figsize=(16, 10))
                        # Display the clustered image
                        plt.title(f'Clustering: {folder_name}')
                        plt.imshow(cluster_labels_image, cmap=cmap)
                        plt.colorbar(shrink=0.4)
                        plt.axis('off')  # Remove axis labels

                        # Save the figure with input folder name
                        save_figure(folder_output_path, file_name=f'{folder_name}_clustered_image.png')

                        plt.show()