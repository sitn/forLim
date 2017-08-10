# -*- coding: utf-8 -*-

"""
Created on Fri Nov 27 09:23:53 2015

Author: SFFN/APM

Description:

spatialIO.py is a library of methods for spatial data Input /
Output in python using the osgeo / gdal / osr / ogr / scipy / numpy libraries

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

    spio.rasterWriter(forest_isolated, output_filename_01, geotransform2,
    prj_wkt2, gdal.GDT_Byte)


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


def pathChecker(path):
    '''
    Checks if a file path exists, if yes it removes it
    '''
    if os.path.exists(path):
        os.remove(path)


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

    return data, geotransform, prj_wkt


def rasterWriter(band, rasterPath, geotransform, prj_wkt, gdalformat):
    '''
    Write an array in a raster with a given path, geotransform and
    geoprojection ref as input
    '''
    # Can be improve with variable args inputs as geoformat as optional
    # and default
    # Mutliple bands or band selector
    # Check if file already exists
    pathChecker(rasterPath)

    # extract array size
    RasterYSize, RasterXSize = band.shape

    # create and write raster file
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(rasterPath, RasterXSize, RasterYSize, 1, gdalformat)
    ds.SetProjection(prj_wkt)
    ds.SetGeoTransform(geotransform)
    ds.GetRasterBand(1).WriteArray(band)

    # close raster file
    ds = None


def pointShpWriter(pointPath, spatialRefWKT, x, y, attribute, label):
    # Get driver
    driver = ogr.GetDriverByName('ESRI Shapefile')

    # Create shapeData
    pointPath = os.path.splitext(str(pointPath))[0] + '.shp'
    pathChecker(pointPath)
    shapeData = driver.CreateDataSource(pointPath)

    # Create spatialReference from WKT input
    srs = osr.SpatialReference()
    srs.ImportFromWkt(spatialRefWKT)

    # Create layer
    layerName = os.path.splitext(os.path.split(pointPath)[1])[0]
    layer = shapeData.CreateLayer(layerName, srs, ogr.wkbPoint)

    field_height = ogr.FieldDefn(label, ogr.OFTReal)
    field_height.SetWidth(4)
    field_height.SetPrecision(2)

    layer.CreateField(field_height)

    geoLocations = np.column_stack((x, y))

    for pointIndex, geoLocation in enumerate(geoLocations):
        # Create point
        geometry = ogr.Geometry(ogr.wkbPoint)
        geometry.SetPoint(0, geoLocation[0], geoLocation[1])
        # Create feature
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(geometry)
        feature.SetFID(pointIndex)
        feature.SetField(label, float(attribute[pointIndex]))

        # Save feature
        layer.CreateFeature(feature)
        # Cleanup
        geometry.Destroy()
        feature.Destroy()
    # Cleanup
    shapeData.Destroy()
    # Return
    return pointPath


def polygonizer(rasterPath, maskPath, shapePath):
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
    pathChecker(shapePath)
    drv = ogr.GetDriverByName("ESRI Shapefile")
    ds_vec = drv.CreateDataSource(shapePath)

    srs = osr.SpatialReference()
    srs.ImportFromWkt(dataset.GetProjectionRef())

    layer = ds_vec.CreateLayer("polygonized", srs)
    newField = ogr.FieldDefn('N', ogr.OFTInteger)
    layer.CreateField(newField)

    # Polygonize
    gdal.Polygonize(band, mask, layer, 0, [], callback=None)

    # Destroy features and datasources
    dataset = None
    dsmask = None
    ds_vec = None

    print('Layer has been polygonized')


def rasterizer(shapePath, rasterPath, attribute, gridModelPath):
    '''Rasterize a shapefile using its attribute value
        @param shapePath    Input shapefile
        @param rasterPath   Output rasterfile
        @param attribute    Attribute fieldname (string)
        @gridModelPath      grid used to as reference'''
    # Import data, geotransform and projection from the model grid
    data, geotransform, prj_wkt = rasterReader(gridModelPath)
    RasterYSize, RasterXSize = data.shape

    # Import data from the vector layer
    driver = ogr.GetDriverByName('ESRI Shapefile')
    vector_source = driver.Open(shapePath, 0)
    source_layer = vector_source.GetLayer(0)

    target_ds = gdal.GetDriverByName('MEM').Create("", RasterXSize,
                                                   RasterYSize, 1,
                                                   gdal.GDT_Int32)
    target_ds.SetGeoTransform(geotransform)
    target_ds.SetProjection(prj_wkt)

    err = gdal.RasterizeLayer(target_ds, [1], source_layer,
                              options=["ATTRIBUTE=%s" % attribute])
    if err != 0:
        raise Exception("error rasterizing layer: %s" % err)
    data = target_ds.ReadAsArray()
    print data.shape
    rasterWriter(data, rasterPath, geotransform, prj_wkt, gdal.GDT_Int32)


if __name__ == "__main__":
    main()


__author__ = "SFFN/APM"
__license__ = "GPL"
__version__ = "0.1.0"
__status__ = "Development"
