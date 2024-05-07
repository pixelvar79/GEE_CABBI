import os

def delete_rescaled_tifs(root_folder):
    # Walk through the planet folder
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            # Check if the file is a rescaled TIFF
            if 'only_masked' in filename and filename.endswith('.tif'):
                file_path = os.path.join(dirpath, filename)
                
                # Delete the file
                os.remove(file_path)
                print(f"Deleted: {file_path}")

# Specify the root directory
root_directory = '../data/input_images/planet'

# Call the function to delete rescaled TIFF files
delete_rescaled_tifs(root_directory)