import ee

# Authenticate with Earth Engine
#ee.Authenticate()
ee.Initialize()
print('EE has been initialized')
# Create an ImageCollection for Sentinel-2 data
sentinel2_collection = ee.ImageCollection('COPERNICUS/S2')
print('sentinel collection has been specified')

# Get the earliest date in the collection
earliest_date = sentinel2_collection.aggregate_min('system:time_start')

print('earliest date for sentinel collection has been found :', ee.Date(earliest_date).format().getInfo())


#print("Earliest date for Sentinel-2 data in GEE:", ee.Date(earliest_date).format().getInfo())

