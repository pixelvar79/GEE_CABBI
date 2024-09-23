from bbox_generator import process_shapefile, process_shapefiles_folder
#from ee_gdrive_wrapper import export_3dem_to_drive, export_s2,export_chirp_to_drive,export_polaris_to_drive #, export_s1
#from ee_gdrive_wrapper_S2_L1C_Py6S import export_3dem_to_drive, export_s2,export_chirp_to_drive,export_polaris_to_drive #, export_s1
from ee_gdrive_wrapper_S2_L1C_simplified_cal import export_s2#, export_s1
from ee_gdrive_wrapper import export_gridmet_to_drive
import gdown
import os
import ee
import sys
import shutil

def download_google_drive_folder(url, output_path, delete_after_download=False):
    # Remove any query parameters from the URL
    if url.split('/')[-1] == '?usp=sharing':
        url = url.replace('?usp=sharing', '')

    # Create the output folder if it doesn't exist
    #os.makedirs(output_path, exist_ok=True)
    
    #def create_or_recreate_folder(folder):
    if os.path.exists(output_path):
        print(f"Removing existing folder: {output_path}")
        shutil.rmtree(output_path)
    print(f"Creating folder: {output_path}")
    os.makedirs(output_path)
    #return output_path

    # Download the folder
    gdown.download_folder(url, output=output_path)
    
def validate_date_format(date_string):
    try:
        # Try to parse the date
        ee.Date(date_string).format('YYYY-MM-dd').getInfo()
        return True
    except ee.ee_exception.EEException:
        return False
    
if __name__ == "__main__":
    # Specify the input folder
    
    if len(sys.argv) != 3:
        print("Usage: python script.py input_folder_path gdrive_output_path")
        sys.exit(1)

    input_folder_path = sys.argv[1]
    #gdrive_output_path = sys.argv[2]
    
    # Check if the provided path is a file or a folder
    if os.path.isfile(input_folder_path):
        result = [process_shapefile(input_folder_path)]
    elif os.path.isdir(input_folder_path):
        result = process_shapefiles_folder(input_folder_path)
    else:
        print("Invalid path provided. Please provide a valid shapefile or folder path.")
        sys.exit(1)

    # Define date_ranges interactively
    date_ranges = []
    
    print("Enter date pairs in the format YYYY-MM-DD. Press Enter without entering a date to finish.")
    
    while True:
        start_date = input("Enter start date: ")

        # Check if the user pressed Enter without entering a start date
        if not start_date:
            # If no start date is provided, break out of the loopn
            break

        # Validate the date format
        if not validate_date_format(start_date):
            print("Invalid date format. Please enter dates in the format YYYY-MM-DD.")
            continue

        end_date = input("Enter end date: ")

        # Validate the date format
        if not validate_date_format(end_date):
            print("Invalid date format. Please enter dates in the format YYYY-MM-DD.")
            continue

        # Check if both start and end dates are provided and end date is later than start date
        if start_date and end_date and start_date < end_date:
            date_ranges.append((start_date, end_date))
        else:
            # If either start or end date is missing, or end date is not later than start date, skip the current pair
            print("Skipping the current pair. Both start and end dates are required, and end date should be later than start date.")

        # Prompt the user if they want to continue
        continue_input = input("Do you want to add another date range? (y/n): ")
        if continue_input.lower() != 'y':
            # If the user chooses not to continue, break out of the loop
            restart_input = input("Do you want to restart with new date pairs? (y/n): ")
            if restart_input.lower() == 'y':
                date_ranges = []  # Clear the existing date ranges
                continue
            else:
                break

    # Check if at least one complete date pair is provided
    if not date_ranges:
        print("No complete date pairs provided. Exiting.")
    else:
        # Iterate over each date range
        for start_date, end_date in date_ranges:
            # Iterate over each shapefile entry
            for entry in result:
                shp_name = entry["name"]
                coordinates = entry["coordinates"]
                
                print(f'Solving case for: {shp_name}')

                # Iterate over each bounding box in the shapefile entry
                for bbox in coordinates:
                    bounding_box = ee.Geometry.Rectangle([bbox[0], bbox[1], bbox[2], bbox[3]])
                    
                    export_s2(bounding_box, start_date, end_date, shp_name)
                    #export_s1(bounding_box, start_date, end_date, shp_name)
                    #export_3dem_to_drive(bounding_box, shp_name)
                    #export_chirp_to_drive(bounding_box, start_date, end_date, shp_name)
                    #export_polaris_to_drive(bounding_box, start_date, end_date, shp_name)
                    
                    #export_gridmet_to_drive(bounding_box, start_date, end_date, shp_name)

        #     # Prompt the user for input on whether to download the Google Drive folder
        # download_choice = input("Do you want to download the Google Drive folder? (y/n): ")

        # if download_choice.lower() == 'y':
        #     gdrive_url = 'https://drive.google.com/drive/folders/1DUyvk3u09GLNPOu6HY1x3DpwvWv-lbK2?usp=sharing'
        #     # Prompt the user for input on whether to delete files after download
        #     #delete_after_download_choice = input("Do you want to delete files in the Google Drive folder after download? (y/n): ")

        #     download_google_drive_folder(gdrive_url, gdrive_output_path)
        #     print("Google Drive folder download completed.")
        # else:
        #     print("Skipped Google Drive folder download.")