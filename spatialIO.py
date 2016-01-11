# -*- coding: utf-8 -*-

"""
Created on Fri Nov 27 09:23:53 2015

Author: Arnaud Poncet-Montanges, SFFN, Couvet (CH)

Description:

spatialIO.py is a library of methods for spatial data Input / Output in python using the osgeo / gdal / osr / ogr / scipy / numpy libraries

Usage:

    import spatialIO as spio
    
    # To read raster :
    data, geotransform, prj_wkt = spio.rasterReader(rasterPath)
    
    # To write raster
    spio.rasterWriter(band, rasterPath, geotransform, prj_wkt, gdalformat)
    
    # To write point shapefile
    spio.pointShpWriter(pointPath, spatialRefWKT, x, y, attribute, label)
    

Input Args:

    rasterPath: complete input file path name
    band: numpy array of shape m x n
    geotransform: requested geotransform
    prj_wkt: projection in wkt
    gdalformat: requested gdal format 

Example:

    import spatialIO as spio

    data2, geotransform2, prj_wkt2 = spio.rasterReader(input_filename_01)

    spio.rasterWriter(forest_isolated, output_filename_01, geotransform2, prj_wkt2, gdal.GDT_Byte) 

    
"""

import os
from os.path import basename

from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdalconst

import numpy as np

import scipy.ndimage


def main():
    '''
    Usage: 
    
    import spatialIO as spio
    
    data, geotransform, prj_wkt = spio.rasterReader(rasterPath)

    spio.rasterWriter(band, rasterPath, geotransform, prj_wkt, gdalformat)
    '''


def rasterReader(rasterPath):
    '''
    Reads an a raster and give an array with geotransorm and geoprojection 
    ref as output
    '''
    # gdal import raster
    dataset = gdal.Open(rasterPath, gdalconst.GA_ReadOnly)
    
    # georeference
    geotransform = dataset.GetGeoTransform()
    prj_wkt = dataset.GetProjectionRef()
    
    # extract raster values
    band = dataset.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, dataset.RasterXSize, dataset.RasterYSize)
    
    return data, geotransform, prj_wkt;


def rasterWriter(band, rasterPath, geotransform, prj_wkt, gdalformat):
    '''
    Write an array in a raster with a given path, geotransform and 
    geoprojection ref as input
    '''    
    # Can be improve with variable args inputs as geoformat as optional and default
    # Mutliple bands or band selector
    # Check if file already exists
    if os.path.exists(rasterPath):
        os.remove(rasterPath)
    
    # extract array size
    RasterYSize, RasterXSize = band.shape
    
    #create and write raster file    
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(rasterPath, RasterXSize, RasterYSize, 1, gdalformat )
    ds.SetProjection(prj_wkt)
    ds.SetGeoTransform(geotransform)
    ds.GetRasterBand(1).WriteArray(band)
    
    #close raster file
    ds = None
    

def pointShpWriter(pointPath, spatialRefWKT, x, y, attribute, label):
    # Get driver
    driver = ogr.GetDriverByName('ESRI Shapefile')
    
    # Create shapeData
    pointPath = os.path.splitext(str(pointPath))[0] + '.shp'
    if os.path.exists(pointPath):
        os.remove(pointPath)
    shapeData = driver.CreateDataSource(pointPath)
    
    # Create spatialReference from WKT input
    spatialReference = osr.SpatialReference()
    spatialReference.ImportFromWkt(spatialRefWKT)

    # Create layer
    layerName = os.path.splitext(os.path.split(pointPath)[1])[0]
    layer = shapeData.CreateLayer(layerName, spatialReference, ogr.wkbPoint)

    field_height = ogr.FieldDefn(label, ogr.OFTReal)
    field_height.SetWidth(4)
    field_height.SetPrecision(2)
    
    layer.CreateField(field_height)    
    
    geoLocations = np.column_stack((x,y))
    
    for pointIndex, geoLocation in enumerate(geoLocations):
        # Create point
        geometry = ogr.Geometry(ogr.wkbPoint)
        geometry.SetPoint(0, geoLocation[0], geoLocation[1])
        # Create feature
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(geometry)
        feature.SetFID(pointIndex)
        feature.SetField(label,float(attribute[pointIndex]))
        
        # Save feature
        layer.CreateFeature(feature)
        # Cleanup
        geometry.Destroy()
        feature.Destroy()
    # Cleanup
    shapeData.Destroy()
    # Return
    return pointPath

    
def array2shp(shapePath, array):
    ''' Save data to a shp file
        @param  shpPath       Input path to the shp which will be created (Str)
        @param  trees         Input tree data (dictionnary)
        
    '''
    print('to be implemented')

    
def polygonizer(rasterPath, maskPath, shapePath ):
    '''Uses gdal.polygonize to vectorize a polygon layer
        @param rasterPath       Input Raster Path
        @param shapePath        Output Shape Path
        @param maskPath         Mask Layer Path (binary raster)
    '''
    # gdal import raster
    dataset = gdal.Open(rasterPath, gdalconst.GA_ReadOnly)
    band = dataset.GetRasterBand(1)
    
    # gdal import mask
    if maskPath:
        dsmask = gdal.Open(maskPath, gdalconst.GA_ReadOnly)
        mask = dataset.GetRasterBand(1)    
    else:
        mask = None
        
    # gdal export vector layer settings
    if os.path.exists(shapePath):
        os.remove(shapePath)
    drv = ogr.GetDriverByName("ESRI Shapefile")
    ds_vec = drv.CreateDataSource( shapePath )
    layer = ds_vec.CreateLayer("polygonized", srs = None )
    newField = ogr.FieldDefn('N', ogr.OFTInteger)
    layer.CreateField(newField)
        
    # Polygonize
    gdal.Polygonize(band, mask, layer, 0, [], callback=None )

    # Destroy features and datasources
    dataset = None
    dsmask = None
    ds_vec = None
    
    print('Layer has been polygonized')

if __name__ == "__main__":
    main()


__author__ = "Arnaud Poncet-Montanges, SFFN, Couvet (CH)"
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Arnaud Poncet-Montanges"
__email__ = "arnaudponcetmontanges@gmail.com"
__status__ = "Development"
