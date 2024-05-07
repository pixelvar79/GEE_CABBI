
import gdown
import os
import shutil

url = 'https://drive.google.com/drive/folders/1DUyvk3u09GLNPOu6HY1x3DpwvWv-lbK2?usp=sharing'

# Remove any query parameters from the URL
if url.split('/')[-1] == '?usp=sharing':
    url = url.replace('?usp=sharing', '')

def create_or_recreate_folder(folder):
    if os.path.exists(folder):
        print(f"Removing existing folder: {folder}")
        shutil.rmtree(folder)
    print(f"Creating folder: {folder}")
    os.makedirs(folder)
    return folder


# Specify the local output path where the folder structure will be created
output_path = '../data/sentinel_ee'

output_path = create_or_recreate_folder(output_path)

# Create the output folder if it doesn't exist
#os.makedirs(output_path, exist_ok=True)

# Download the folder
gdown.download_folder(url, output=output_path)

