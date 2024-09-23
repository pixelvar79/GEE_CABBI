import ee

try:
    ee.Initialize()
    print("Authentication successful. Earth Engine is ready to use.")
except ee.EEException as e:
    print(f"Authentication failed. Error: {e}")
