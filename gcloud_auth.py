import ee
from google.cloud import storage
from googleapiclient.discovery import build
from google.oauth2 import service_account

def authenticate_earth_engine(private_key_path, service_account_email):
    credentials = ee.ServiceAccountCredentials(service_account_email, private_key_path)
    ee.Initialize(credentials)
    print("Earth Engine authentication successful.")

def authenticate_cloud_storage(private_key_path, service_account_email):
    credentials = service_account.Credentials.from_service_account_file(
        private_key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    storage_client = storage.Client(credentials=credentials)
    print("Cloud Storage authentication successful.")

def authenticate_google_drive(private_key_path, service_account_email):
    credentials = service_account.Credentials.from_service_account_file(
        private_key_path,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    drive_service = build("drive", "v3", credentials=credentials)
    print("Google Drive authentication successful.")

if __name__ == "__main__":
    private_key_path = 'editor_key.json'
    service_account_email = '1032697420965-compute@developer.gserviceaccount.com'

    try:
        authenticate_earth_engine(private_key_path, service_account_email)
        authenticate_cloud_storage(private_key_path, service_account_email)
        authenticate_google_drive(private_key_path, service_account_email)
    except Exception as e:
        print(f"Authentication failed. Error: {str(e)}")
