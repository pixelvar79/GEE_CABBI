from bbox_generator import process_shapefile, process_shapefiles_folder
from checker_wrapper import process_s2, process_s1
import os
import ee
import sys
import pandas as pd

# initialize empty list to store the requested scenes metadata
output_list = []

def validate_date_format(date_string):
    try:
        # Try to parse the date
        ee.Date(date_string).format('YYYY-MM-dd').getInfo()
        return True
    except ee.ee_exception.EEException:
        return False
    
if __name__ == "__main__":
    # Specify the input folder
    # Authenticate with Earth Engine using your Google account
    #ee.Authenticate()
    
    if len(sys.argv) != 3:
        print("Usage: python script.py input_folder_path gdrive_output_path")
        sys.exit(1)

    input_folder_path = sys.argv[1]
    gdrive_output_path = sys.argv[2]
    
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
                # Iterate over each bounding box in the shapefile entry
                for bbox in coordinates:
                    bounding_box = ee.Geometry.Rectangle([bbox[0], bbox[1], bbox[2], bbox[3]])

                    # Capture the output_data_list from each function call
                    output_data_list_s2 = process_s2(bounding_box, start_date, end_date, shp_name)
                    #output_data_list_s1 = process_s1(bounding_box, start_date, end_date, shp_name)

                    # Extend the main output_data_list with the sub-lists
                    output_list.extend(output_data_list_s2)
                    #output_list.extend(output_data_list_s1)
        #print(output_list)
        # After all iterations are complete, concatenate the lists into a DataFrame
        output_df = pd.DataFrame(output_list)
        #print(output_df)
        

        # Save the DataFrame as a CSV file
       #output_df.to_csv('../check_sentinel_available_filtering.csv', index=False)
        
        csv_path = '../check_sentinel_available.csv'

        # Check if the CSV file already exists
        if os.path.exists(csv_path):
            # If it exists, read the existing CSV into a DataFrame
            existing_df = pd.read_csv(csv_path)

            # Concatenate the existing DataFrame with the new DataFrame
            updated_df = pd.concat([existing_df, output_df], ignore_index=True)

            # Save the updated DataFrame to the CSV file
            updated_df.to_csv(csv_path, index=False)
            print('Appended new rows to existing monitoring file')
        else:
            # If the CSV file doesn't exist, save the DataFrame to a new CSV file
            output_df.to_csv(csv_path, index=False)
            print('Created a new local file for monitoring the availability of new scenes from these sensors')

