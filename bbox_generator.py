import os
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Proj, Transformer

def reproject_to_wgs84(geometry, source_crs):
    
    transformer = Transformer.from_crs(source_crs, "epsg:4326", always_xy=True)
    return Point(transformer.transform(geometry.bounds[0], geometry.bounds[1]))

def get_extent_corners(gdf, source_crs,shapefile_path):
    print(f'Reprojecting {shapefile_path} to epsg:4326..')
    min_x, min_y, max_x, max_y = gdf.total_bounds
    buffer_distance = 200
    min_x -= buffer_distance
    min_y -= buffer_distance
    max_x += buffer_distance
    max_y += buffer_distance

    if source_crs != "epsg:4326":
        min_x, min_y = reproject_to_wgs84(Point(min_x, min_y), source_crs).coords[0]
        max_x, max_y = reproject_to_wgs84(Point(max_x, max_y), source_crs).coords[0]

    coordinates = [(min_x, min_y, max_x, max_y)]
    #print(coordinates)

    return coordinates

def process_shapefile(shapefile_path):
    print(f'Processing shapefile from file: {shapefile_path}')
    gdf = gpd.read_file(shapefile_path)
    source_crs = gdf.crs
    #print(source_crs)
    coordinates = get_extent_corners(gdf, source_crs, shapefile_path)
    shp_name = os.path.splitext(os.path.basename(shapefile_path))[0]
    return {"name": shp_name, "coordinates": coordinates}



def process_shapefiles_folder(folder_path):
    coordinates_list = []

    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if filename.endswith(".shp"):
                shapefile_path = os.path.join(root, filename)
                #print(f'Processing shapefile from folder: {shapefile_path}')
                bounding_box_info = process_shapefile(shapefile_path)
                coordinates_list.append(bounding_box_info)

    return coordinates_list


# def process_shapefiles_folder(folder_path):
#     coordinates_list = []

#     for filename in os.listdir(folder_path):
#         if filename.endswith(".shp"):
#             shapefile_path = os.path.join(folder_path, filename)
#             bounding_box_info = process_shapefile(shapefile_path)
#             coordinates_list.append(bounding_box_info)

#     return coordinates_list
