from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import shutil

def create_or_recreate_folder(folder):
    if os.path.exists(folder):
        print(f"Removing existing folder: {folder}")
        shutil.rmtree(folder)
    print(f"Creating folder: {folder}")
    os.makedirs(folder)
    return folder

def download_files_from_folder(folder_name, output_folder):
    # Authenticate with Google Drive
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Authenticates using a local web server
    drive = GoogleDrive(gauth)

    # Use the Google Drive API to dynamically identify the folder by name
    folder_id = get_folder_id_by_name(drive, folder_name)

    if folder_id:
        # List all files in the folder
        file_list = drive.ListFile({'q': f"'{folder_id}' in parents"}).GetList()

        # Download each file to the output folder
        for file in file_list:
            try:
                file.GetContentFile(os.path.join(output_folder, file['title']))
                print(f"Downloaded file: {file['title']}")
            except Exception as e:
                print(f"Error downloading file {file['title']}: {e}")

        # Delete all files in the Google Drive folder
        delete_files_in_folder(drive, folder_id)
    else:
        print(f"Folder with name '{folder_name}' not found.")

def get_folder_id_by_name(drive, folder_name):
    # Use the Google Drive API to search for the folder by name
    query = f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    folders = drive.ListFile({'q': query}).GetList()

    if folders:
        return folders[0]['id']
    else:
        return None

def delete_files_in_folder(drive, folder_id):
    # List all files in the folder
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents"}).GetList()

    # Delete each file in the folder
    for file in file_list:
        try:
            print(f"Deleting file: {file['title']}")
            file.Delete()
        except Exception as e:
            print(f"Error deleting file {file['title']}: {e}")

if __name__ == "__main__":
    # Specify the Google Drive folder name
    folder_name = 'sentinel_ee'

    # Specify the local output path where the folder structure will be created
    output_path = '../data/sentinel_ee'

    # Create or recreate the local output folder
    output_path = create_or_recreate_folder(output_path)

    # Download files from the dynamically identified Google Drive folder
    download_files_from_folder(folder_name, output_path)
