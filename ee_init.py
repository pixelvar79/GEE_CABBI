import ee

# # Authenticate with Earth Engine using your Google account (only needed once)
# # ee.Authenticate()
# try:
#     ee.Initialize(project='mygdriveproject-405920')
#     print("Earth Engine API initialized successfully.")
# except ee.EEException as e:
#     print("Failed to initialize the Earth Engine API. Please check your credentials and authentication.")
#     print(str(e))

# Optionally, you can define some common functions or variables here


import ee

class EarthEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EarthEngine, cls).__new__(cls)
            cls._instance.initialize_ee()
        return cls._instance

    def initialize_ee(self):
        try:
            ee.Initialize(project='mygdriveproject-405920')
            print('Successfully initialized the Earth Engine API.')
        except ee.EEException as e:
            print("Earth Engine API not initialized:", e)

# # Usage
# ee_instance = EarthEngine()