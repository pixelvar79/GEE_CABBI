# import os
# import numpy as np
# import rasterio
# from sklearn.cluster import KMeans
# from matplotlib import cm
# import matplotlib.pyplot as plt
# from datetime import datetime
# import pandas as pd



# def extract_info_from_filename(tif_filename):
#     """Extract information from the filename (date string)."""
#     # Assuming your filename format is like 'YYYYMMDD_hhmmss_...._masked.tif'
#     parts = tif_filename.split('_')
    
#     # Extracting the date string
#     date_string = parts[0]

#     return date_string

# def calculate_ndre(band_7_value, band_8_value):
#     """Calculate simplified NDRE for given band values."""
#     # Perform NDRE calculation using the provided band values
#     red_edge = band_7_value
#     nir = band_8_value
    
#     ndre = (nir - red_edge) / (nir + red_edge)  # Replace NaN with 0
#     return ndre


# def generate_random_points_in_class(class_mask, num_points, seed_value=30):
#     """Generate random x, y points within the given class mask."""
#     y_indices, x_indices = np.where(class_mask)

#     # Set a fixed seed for reproducibility
#     np.random.seed(seed_value)

#     random_indices = np.random.choice(len(y_indices), num_points, replace=False)

#     random_points = list(zip(x_indices[random_indices], y_indices[random_indices]))
#     return random_points

# def extract_ndre_at_points(tif_path, random_points, cluster_class):
#     """Extract NDRE values at the specified points for the given TIF file."""
#     with rasterio.open(tif_path) as src:
#         date_string = extract_info_from_filename(os.path.basename(tif_path))
#         julian_date = datetime.strptime(date_string, '%Y%m%d').timetuple().tm_yday  # Convert to Julian date

#         ndre_values = []

#         for point_num, point in enumerate(random_points, start=1):
#             # Read bands 7 and 8 at the specified point
#             band_7_value = src.read(7, window=((point[1], point[1] + 1), (point[0], point[0] + 1)))
#             band_8_value = src.read(8, window=((point[1], point[1] + 1), (point[0], point[0] + 1)))

#             # Calculate NDRE using the band values
#             ndre_value = calculate_ndre(band_7_value, band_8_value)

#             # Append information about cluster class, random point number, and NDRE value
#             ndre_values.append({
#                 'cluster_class': cluster_class,
#                 'random_point_number': point_num,
#                 'julian_date': julian_date,
#                 'ndre_value': ndre_value
#             })

#     return ndre_values


# def extract_topo_values(tif_path, random_points, cluster_class):
#     """Extract values from 3DEP10m_btrust_topo.tif for each band at specified points."""
#     topo_values_list = []

#     topo_folder = '../data/input_images/3DEP10m_ee_utm1'
#     topo_file = os.path.join(topo_folder, '3DEP10m_btrust_topo.tif')
#     print(topo_file)

#     for point_num, point in enumerate(random_points, start=1):
#         topo_values = {}

#         for i in range(1, 5):
#             with rasterio.open(topo_file) as topo_src:
#                 topo_value = topo_src.read(i, window=((point[1], point[1] + 1), (point[0], point[0] + 1)))
#                 topo_values[f'band_{i}'] = topo_value[0][0]

#         topo_values_list.append({
#             'cluster_class': cluster_class,
#             'random_point_number': point_num,
#             **topo_values  # Flatten the dictionary
#         })

#     return topo_values_list

# def generate_topo_boxplot(df):
#     """Generate boxplot for each cluster class and topo band."""
#     # Specify the new topo band names
#     topo_band_names = ['altitude', 'hillshade', 'slope', 'curvature']

#     # Rename columns in the DataFrame to match the new band names
#     df.rename(columns={'band_1': 'altitude', 'band_2': 'hillshade', 'band_3': 'slope', 'band_4': 'curvature'}, inplace=True)

#     # Create a figure and axis for boxplot
#     fig, axes = plt.subplots(nrows=len(topo_band_names), ncols=1, figsize=(10, 8), sharex=True)
    
#     for ax, topo_band in zip(axes, topo_band_names):
#         # Clean outliers using the IQR method
#         q1 = df[topo_band].quantile(0.15)
#         q3 = df[topo_band].quantile(0.85)
#         iqr = q3 - q1
#         lower_bound = q1 - 1.5 * iqr
#         upper_bound = q3 + 1.5 * iqr

#         # Filter out values outside the lower and upper bounds
#         df_cleaned = df[(df[topo_band] >= lower_bound) & (df[topo_band] <= upper_bound)]

#         # Create a boxplot for each cluster class with wider whiskers
#         df_cleaned.boxplot(column=topo_band, by='cluster_class', ax=ax, whis=[5, 95])
#         ax.set_title(f'Boxplot for {topo_band.capitalize()}')
#         ax.set_ylabel(f'{topo_band.capitalize()} Value')
#         ax.set_xlabel('Cluster Class')

#     plt.suptitle('Boxplots of Topo Bands for Each Cluster Class')
#     plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust layout to prevent overlap
#     plt.show()


# def process_folder(cluster_tif_path, input_folder_path):
#     """Process all masked TIFs in the given folder."""
#     # Load the pre-clustered image
#     with rasterio.open(cluster_tif_path) as src:
#         cluster_labels_image = src.read(1)
#         n_clusters = len(np.unique(cluster_labels_image))
#         print(np.unique(cluster_labels_image))
#     random_points_per_class = {}

#     all_ndre_values = []  # List to store all NDRE values for different TIF files
#     all_topo_values = []

#     for root, dirs, files in os.walk(input_folder_path):
#         tif_files = [f for f in files if f.endswith('masked.tif')]
#         #print(tif_files)

#         for tif_file in tif_files:
#             tif_path = os.path.join(root, tif_file)
#             print(tif_path)

#             # Iterate through each cluster class
#             for class_label in range(n_clusters):
#                 if class_label == 0:
#                     continue  # Skip generating random points for class_label = 0

#                 class_mask = (cluster_labels_image == class_label)

#                 # Check if the class mask is not empty
#                 if np.any(class_mask):
#                     # Generate random points and store them in the dictionary
#                     random_points = generate_random_points_in_class(class_mask, num_points=10)
#                     random_points_per_class.setdefault(class_label, []).extend(random_points)

#                     # Extract NDRE values at the generated random points for the current TIF file
#                     ndre_values = extract_ndre_at_points(tif_path, random_points, class_label)
                    
#                     # Extract topo values for each band
#                     topo_values = extract_topo_values(tif_path, random_points, class_label)
                    
#                     #topo_values = extract_topo_values_all_pixels(cluster_tif_path, class_mask, class_label)

                    
#                     # # Append the NDRE values to the list
#                     all_ndre_values.extend(ndre_values)
#                     all_topo_values.extend(topo_values)
                    
#                     # Append the NDRE and topo values to the list
#                     # for ndre_value, topo_value in zip(ndre_values, topo_values):
#                     #     ndre_value.update(topo_value)
#                     #     all_ndre_values.append(ndre_value)

#     # Convert the list of dictionaries to a DataFrame
#     df = pd.DataFrame(all_ndre_values)

#     # Flatten the ndre_value column
#     df['ndre_value'] = df['ndre_value'].apply(lambda x: x[0][0] if x else None)
    
#     dftopo = pd.DataFrame(all_topo_values)

#     # Now df is a pandas DataFrame with a flattened ndre_value column
#     # Generate boxplots for each topo band and cluster class
#     generate_topo_boxplot(dftopo)

#     return df
import os
import numpy as np
import rasterio
from sklearn.cluster import KMeans
from matplotlib import cm
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
import seaborn as sns

def generate_temporal_profile_plot(df, output_folder_path, figure_name):
    """Generate temporal profile plot for NDRE values."""
    # Create a figure and axis
    
    palette = sns.color_palette("husl", 4)
    
    fig, ax = plt.subplots()

    # Set fixed x-axis and y-axis ranges
    ax.set_xlim(100, 360)
    ax.set_ylim(0, 1)

    # Iterate through each cluster class
    for i, (cluster_class, cluster_data) in enumerate(df.groupby('cluster_class')):

    #for cluster_class, cluster_data in df.groupby('cluster_class'):
        # List to store NDRE values for each random point within the cluster class
        ndre_values_per_class = []

        # Iterate through each random point within the cluster class
        for point_num, point_data in cluster_data.groupby('random_point_number'):
            ndre_values_per_class.append(point_data['ndre_value'].values)

        # Calculate mean and standard deviation for each Julian Day
        mean_values = np.mean(ndre_values_per_class, axis=0)
        std_values = np.std(ndre_values_per_class, axis=0)

        # Plot the mean trajectory with shaded standard deviation using the cluster color
        #ax.plot(point_data['julian_date'], mean_values, label=f'Cluster {cluster_class}', linewidth=2)
        #ax.fill_between(point_data['julian_date'], mean_values - std_values, mean_values + std_values, alpha=0.3)
        ax.plot(point_data['julian_date'], mean_values, label=f'Cluster {cluster_class}', linewidth=2, color=palette[i])
        ax.fill_between(point_data['julian_date'], mean_values - std_values, mean_values + std_values, alpha=0.3, color=palette[i])

    # Set labels and title
    ax.set_xlabel('Julian Day')
    ax.set_ylabel('NDRE Value')
    ax.set_title(f'Temp. Profile: {figure_name}')

    # Show legend
    ax.legend()

    # Save the figure to the specified folder with input folder name in the filename
    figure_path = os.path.join(output_folder_path, f'{figure_name}_temporal_profile.png')
    plt.savefig(figure_path)

    # Show the plot
    plt.show()




# if __name__ == "__main__":
#     # Specify the path to the pre-clustered TIF file in the processing folder
#     cluster_tif_path = '../data/processing/btrust_kmeans.tif'

#     # Specify the root directory
#     root_directory = '../data/input_images'

#     # Construct paths to relevant folders
#     planet_folder = os.path.join(root_directory, 'planet')
#     input_folder_path = os.path.join(planet_folder, 'btrust_mask_2021_psscene_analytic_8b_sr_udm2')

#     # Process the folder and calculate accumulated NDRE
#     df = process_folder(cluster_tif_path, input_folder_path)
#     generate_temporal_profile_plot(df)

def extract_info_from_filename(tif_filename):
    """Extract information from the filename (date string)."""
    # Assuming your filename format is like 'YYYYMMDD_hhmmss_...._masked.tif'
    parts = tif_filename.split('_')
    # Extracting the date string
    date_string = parts[0]
    return date_string

def calculate_ndre(band_7_value, band_8_value):
    """Calculate simplified NDRE for given band values."""
    # Perform NDRE calculation using the provided band values
    red_edge = band_7_value
    nir = band_8_value
    ndre = (nir - red_edge) / (nir + red_edge)  # Replace NaN with 0
    return ndre

def generate_random_points_in_class(class_mask, num_points, seed_value=30):
    """Generate random x, y points within the given class mask."""
    y_indices, x_indices = np.where(class_mask)
    # Set a fixed seed for reproducibility
    np.random.seed(seed_value)
    random_indices = np.random.choice(len(y_indices), num_points, replace=False)
    random_points = list(zip(x_indices[random_indices], y_indices[random_indices]))
    return random_points

def extract_ndre_at_points(tif_path, random_points, cluster_class):
    """Extract NDRE values at the specified points for the given TIF file."""
    with rasterio.open(tif_path) as src:
        date_string = extract_info_from_filename(os.path.basename(tif_path))
        julian_date = datetime.strptime(date_string, '%Y%m%d').timetuple().tm_yday  # Convert to Julian date
        ndre_values = []
        for point_num, point in enumerate(random_points, start=1):
            # Read bands 7 and 8 at the specified point
            band_7_value = src.read(7, window=((point[1], point[1] + 1), (point[0], point[0] + 1)))
            band_8_value = src.read(8, window=((point[1], point[1] + 1), (point[0], point[0] + 1)))
            # Calculate NDRE using the band values
            ndre_value = calculate_ndre(band_7_value, band_8_value)
            # Append information about cluster class, random point number, and NDRE value
            ndre_values.append({
                'cluster_class': cluster_class,
                'random_point_number': point_num,
                'julian_date': julian_date,
                'ndre_value': ndre_value
            })
    return ndre_values

# def extract_topo_values(tif_path, random_points, cluster_class):
#     """Extract values from 3DEP10m_btrust_topo.tif for each band at specified points."""
#     topo_values_list = []
#     topo_folder = '../data/input_images/3DEP10m_ee_utm1'
#     topo_file = os.path.join(topo_folder, '3DEP10m_btrust_topo.tif')
#     print(topo_file)
#     for point_num, point in enumerate(random_points, start=1):
#         topo_values = {}
#         for i in range(1, 5):
#             with rasterio.open(topo_file) as topo_src:
#                 topo_value = topo_src.read(i, window=((point[1], point[1] + 1), (point[0], point[0] + 1)))
#                 topo_values[f'band_{i}'] = topo_value[0][0]
#         topo_values_list.append({
#             'cluster_class': cluster_class,
#             'random_point_number': point_num,
#             **topo_values  # Flatten the dictionary
#         })
#     return topo_values_list
import re
import os
import re
import rasterio

def extract_topo_values(input_folder_path, planet_folder, keyword, random_points, cluster_class):
    """Extract values from corresponding topo.tif for each band at specified points."""
    topo_values_list = []

    # Extract the first string from the input_folder_path (e.g., 'btrust' from 'btrust_mask_2021_psscene_analytic_8b_sr_udm2')
    input_folder_name = os.path.basename(os.path.normpath(input_folder_path))
    input_folder_match = re.match(r'(\w+)_mask_\d+_\w+', input_folder_name)

    if input_folder_match:
        first_string_input_folder = input_folder_match.group(1)

        # Iterate through files in the planet directory
        for planet_folder_name in os.listdir(planet_folder):
            # Check if the first strings match
            if planet_folder_name.startswith(first_string_input_folder):
                # Iterate through files in the topo folder
                topo_folder = os.path.join('../data/input_images/3DEP10m_ee_utm1', f'3DEP10M_{first_string_input_folder}_topo.tif')
                #print(topo_folder)
                for point_num, point in enumerate(random_points, start=1):
                    topo_values = {}
                    for i in range(1, 5):
                
                    #for i, point in enumerate(random_points, start=1):
                        with rasterio.open(topo_folder) as topo_src:
                            topo_value = topo_src.read(i, window=((point[1], point[1] + 1),
                                                                (point[0], point[0] + 1)))
                            topo_values[f'band_{i}'] = topo_value[0][0]

                    topo_values_list.append({
                    'cluster_class': cluster_class,
                    'random_point_number': point_num,
                    **topo_values  # Flatten the dictionary
                })

    return topo_values_list

# def extract_topo_values(input_folder_path, planet_folder, keyword, random_points, cluster_class):
#     """Extract values from corresponding topo.tif for each band at specified points."""
#     topo_values_list = []
    
#     # Extract the second string from the topo_folder name (e.g., 'btrust' from '3DEP10M_btrust_topo.tif')
#     input_folder_name = os.path.basename(os.path.normpath(input_folder_path))
#     input_folder_match = re.match(r'\d{4}_(\w+)_\w+', input_folder_name)
    
#     if input_folder_match:
#         first_string_input_folder = input_folder_match.group(1)

#         # Iterate through folders in the planet directory
#         for planet_folder_name in os.listdir(planet_folder):
#             planet_folder_match = re.match(r'(\w+)_mask_\d+_\w+', planet_folder_name)
            
#             if planet_folder_match:
#                 first_string_planet_folder = planet_folder_match.group(1)

#                 # Check if the first and second strings match
#                 if first_string_planet_folder == first_string_input_folder:
#                     # Iterate through files in the topo folder
#                     for topo_file in os.listdir(input_folder_folder):
#                         if keyword in topo_file and topo_file.endswith("_topo.tif"):
#                             # Construct the corresponding planet filename based on the common pattern
#                             planet_file_prefix = f"{first_string_planet_folder}_{keyword}"
#                             planet_file = next((f for f in os.listdir(os.path.join(planet_folder, planet_folder_name))
#                                                if f.startswith(planet_file_prefix)), None)

#                             if planet_file:
#                                 # Process the files, extract values, and append to topo_values_list
#                                 topo_path = os.path.join(topo_folder, topo_file)
#                                 planet_path = os.path.join(planet_folder, planet_folder_name, planet_file)

#                                 topo_values = {}
#                                 for i, point in enumerate(random_points, start=1):
#                                     with rasterio.open(topo_path) as topo_src:
#                                         topo_value = topo_src.read(i, window=((point[1], point[1] + 1),
#                                                                            (point[0], point[0] + 1)))
#                                         topo_values[f'band_{i}'] = topo_value[0][0]

#                                 topo_values_list.append({
#                                     'cluster_class': cluster_class,
#                                     'random_point_number': random_points[i-1][2],  # Assuming random_points[i-1][2] is the point number
#                                     **topo_values
#                                 })

#                             else:
#                                 print(f"Planet file not found for {topo_file} in {planet_folder_name}")
#     return topo_values_list

# def generate_boxplot(df, output_folder_path, figure_name):
#     """Generate boxplot for each cluster class and topo band."""
#     # Specify the new topo band names
#     topo_band_names = ['altitude', 'hillshade', 'slope', 'curvature']
#     # Rename columns in the DataFrame to match the new band names
#     df.rename(columns={'band_1': 'altitude', 'band_2': 'hillshade', 'band_3': 'slope', 'band_4': 'curvature'}, inplace=True)
#     # Create a figure and axis for boxplot
#     fig, axes = plt.subplots(nrows=len(topo_band_names), ncols=1, figsize=(12, 6), sharex=True)
#     plt.tight_layout()  # Add tight layout

#     # Define colors for each boxplot
#     colors = ['red', 'green', 'blue', 'orange']

#     for ax, topo_band, color in zip(axes, topo_band_names, colors):
#         # Clean outliers using the IQR method
#         q1 = df[topo_band].quantile(0.15)
#         q3 = df[topo_band].quantile(0.85)
#         iqr = q3 - q1
#         lower_bound = q1 - 1.5 * iqr
#         upper_bound = q3 + 1.5 * iqr
#         # Filter out values outside the lower and upper bounds
#         df_cleaned = df[(df[topo_band] >= lower_bound) & (df[topo_band] <= upper_bound)]
#         # Create a boxplot for each cluster class with wider whiskers
#         df_cleaned.boxplot(column=topo_band, by='cluster_class', ax=ax, whis=[5, 95], color=color)
#         ax.set_ylabel(f'{topo_band.capitalize()} Value')
#         ax.set_xlabel('Cluster Class')

#     plt.suptitle(f'Topographic Descriptors: {figure_name}')

#     # Save the figure to the specified folder with input folder name in the filename
#     figure_path = os.path.join(output_folder_path, f'{figure_name}_boxplot.png')
#     plt.savefig(figure_path)

#     # Show the plot
#     #plt.show()

def generate_boxplot(df, output_folder_path, figure_name):
    """Generate boxplot for each topo band with one boxplot per cluster class."""
    # Specify the new topo band names
    topo_band_names = ['altitude', 'hillshade', 'slope', 'curvature']
    # Rename columns in the DataFrame to match the new band names
    df.rename(columns={'band_1': 'altitude', 'band_2': 'hillshade', 'band_3': 'slope', 'band_4': 'curvature'}, inplace=True)
    # Create a figure and axis for boxplot
    fig, axes = plt.subplots(nrows=len(topo_band_names), ncols=1, figsize=(6, 10), sharex=True)

    #colors = ['red', 'green', 'blue', 'orange']
    palette = sns.color_palette("husl", 4)

    #for ax, topo_band, color in zip(axes, topo_band_names, colors):
    for ax, topo_band in zip(axes, topo_band_names):
        # Clean outliers using the IQR method
        q1 = df[topo_band].quantile(0.15)
        q3 = df[topo_band].quantile(0.85)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        # Filter out values outside the lower and upper bounds
        df_cleaned = df[(df[topo_band] >= lower_bound) & (df[topo_band] <= upper_bound)]

        # Create a boxplot for all cluster classes
        #df_cleaned.boxplot(column=topo_band, by='cluster_class', ax=ax, whis=[5, 95], color=color)
        sns.boxplot(x='cluster_class', y=topo_band, data=df_cleaned, ax=ax, palette=palette)
        ax.set_title(topo_band.capitalize())  # Add title for each subplot
        ax.set_ylabel(f'{topo_band.capitalize()} Value')
        ax.set_xlabel('')  # Remove x-axis label for all subplots except the last one

    plt.suptitle(f'Topographic: {figure_name}')
    plt.tight_layout()  # Add tight layout after all subplots have been created

    # Save the figure to the specified folder with input folder name in the filename
    figure_path = os.path.join(output_folder_path, f'{figure_name}_boxplot.png')
    plt.savefig(figure_path)

    
def process_folder(root_directory, output_folder='../data/processing/temporal_profile1'):
    """Process all masked TIFs in the given folder."""
    # for processing_folder, dirs, files in os.walk(os.path.join(root_directory, 'processing')):
    #     #print(f'this are the processing folders: {processing_folder}')
    #     for planet_folder, planet_dirs, planet_files in os.walk(os.path.join(root_directory, 'input_images/planet')):
    #         #print(planet_dirs)
    #         #print(f'this are the processing planet folders: {planet_dirs}')
    #         # Check if there is a common folder between processing and planet
    #         common_folders = set(dirs).intersection(planet_dirs)
    """Process all masked TIFs in the given folder."""
    # Remove os.walk for processing_folder and use the fixed path directly
    processing_folder = os.path.join(root_directory, 'processing', 'clustering1')
    
    for planet_folder, planet_dirs, planet_files in os.walk(os.path.join(root_directory, 'input_images/planet')):
        # Get the common folders directly
        common_folders = set(planet_dirs).intersection(os.listdir(processing_folder))

        
        #print(common_folders)
        print(processing_folder)
        # print(dirs)
        # print(files)
        print(common_folders)
        #print(f'these are the common folders: {common_folders}')
        for common_folder in common_folders:
            # print(processing_folder)
            #print(common_folder)
            
            tif_path = os.path.join(processing_folder, common_folder, f'{common_folder}_kmeans.tif')
            print(tif_path)
            input_folder_path = os.path.join(planet_folder, common_folder)
            #print(input_folder_path)

            if not os.path.exists(tif_path):
                continue  # Skip if kmeans file does not exist for this common folder

            # print(f'Processing folder: {common_folder}')
            # print(f'TIF path: {tif_path}')
            # print(f'Input folder path: {input_folder_path}')

            # Load the pre-clustered image
            with rasterio.open(tif_path) as src:
                cluster_labels_image = src.read(1)
                n_clusters = len(np.unique(cluster_labels_image))
                print(np.unique(cluster_labels_image))

            random_points_per_class = {}

            all_ndre_values = []  # List to store all NDRE values for different TIF files
            all_topo_values = []

            for root, dirs, files in os.walk(input_folder_path):
                tif_files = [f for f in files if f.endswith('_only_masked.tif')]
                

                for tif_file in tif_files:
                    tif_path = os.path.join(root, tif_file)
                    print(tif_path)

                    # Iterate through each cluster class
                    for class_label in range(n_clusters):
                        if class_label == 0:
                            continue  # Skip generating random points for class_label = 0

                        class_mask = (cluster_labels_image == class_label)

                        # Check if the class mask is not empty
                        if np.any(class_mask):
                            # Generate random points and store them in the dictionary
                            random_points = generate_random_points_in_class(class_mask, num_points=20)
                            random_points_per_class.setdefault(class_label, []).extend(random_points)

                            # Extract NDRE values at the generated random points for the current TIF file
# def process_folder(root_directory, output_folder='../data/processing/temporal_profile'):
#     """Process all masked TIFs in the given folder."""
#     for processing_folder, dirs, files in os.walk(os.path.join(root_directory, 'processing')):
#         for planet_folder, planet_dirs, planet_files in os.walk(os.path.join(root_directory, 'input_images/planet')):
#             common_folders = set(dirs).intersection(planet_dirs)
#             for common_folder in common_folders:
#                 tif_path = os.path.join(processing_folder, common_folder, f'{common_folder}_kmeans.tif')
#                 input_folder_path = os.path.join(planet_folder, common_folder)

#                 if not os.path.exists(tif_path):
#                     continue  # Skip if kmeans file does not exist for this common folder

#                 # Load the pre-clustered image
#                 with rasterio.open(tif_path) as src:
#                     cluster_labels_image = src.read(1)
#                     unique_labels = np.unique(cluster_labels_image)

#                 # Check for classes with 0 pixels and renumber the classes
#                 valid_classes = [label for label in unique_labels if np.sum(cluster_labels_image == label) > 0]
#                 print(valid_classes)

#                 if not valid_classes:
#                     continue  # Skip if there are no valid classes with pixels

#                 renumbered_labels = np.zeros_like(cluster_labels_image)
#                 for new_label, old_label in enumerate(valid_classes, start=1):
#                     renumbered_labels[cluster_labels_image == old_label] = new_label

#                 n_clusters = len(valid_classes)

#                 random_points_per_class = {}

#                 all_ndre_values = []  # List to store all NDRE values for different TIF files
#                 all_topo_values = []

#                 for root, dirs, files in os.walk(input_folder_path):
#                     tif_files = [f for f in files if f.endswith('masked.tif')]
                
#                     for tif_file in tif_files:
#                         tif_path = os.path.join(root, tif_file)

#                         for class_label in range(1, n_clusters + 1):
#                             class_mask = (renumbered_labels == class_label)

#                             # Check if the class mask is not empty
#                             if np.any(class_mask):
#                                 random_points = generate_random_points_in_class(class_mask, num_points=20)
#                                 random_points_per_class.setdefault(class_label, []).extend(random_points)                          


                            ndre_values = extract_ndre_at_points(tif_path, random_points, class_label)
                            #print(ndre_values)

                            # # Extract topo values for each band
                            
                            #topo_values = extract_topo_values(input_folder_path, planet_folder, common_folder, random_points, class_label)


                            # # Append the NDRE values to the list
                            all_ndre_values.extend(ndre_values)
                            #all_topo_values.extend(topo_values)

            # # Convert the list of dictionaries to a DataFrame
            df = pd.DataFrame(all_ndre_values)
            # # Flatten the ndre_value column
            df['ndre_value'] = df['ndre_value'].apply(lambda x: x[0][0] if x else None)

            #dftopo = pd.DataFrame(all_topo_values)

            # # Now df is a pandas DataFrame with a flattened ndre_value column
            # # Generate boxplots for each topo band and cluster class
        
            # Create output folder for each input folder
            output_folder_path = os.path.join(output_folder, common_folder)
            os.makedirs(output_folder_path, exist_ok=True)
            
            #generate_boxplot(dftopo, output_folder_path, common_folder)

            # Generate temporal profile plot for NDRE values
            generate_temporal_profile_plot(df, output_folder_path, common_folder)

if __name__ == "__main__":
    # Specify the root directory
    root_directory = '../data'

    # Process the folders and calculate accumulated NDRE
    process_folder(root_directory)
