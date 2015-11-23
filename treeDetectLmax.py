#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on Fri Jan 10 09:23:53 2014

Author: Matt Parkan, lasig, EPFL 

Description:

treeDetectLmax.py detects tree tops in a raster canopy height model (CHM) 
using the local maxima method. It exports the resulting point geometries 
(x, y, height) to the .shp and .kml data formats.

Usage:

    treeDetectLmax.py Suffix WinRad MinHeightThres src dst

Args:
    Suffix: each output file name is named according to the input file name with a _suffix added 
    WinRad: radius of the local maxima search window in pixels
    MinHeightThres: minimal height threshold in the units of the canopy height model
    src: the path to a single image file (OGR compatible format, check http://www.gdal.org/formats_list.html) or to folder containing several images
    dst: the path to the destination folder

Example:

    treeDetectLmax.py "tree" 4 2 "E:/data/mnc/test" "E:/" 

"""


import os
import sys
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdalconst
import numpy as np
import scipy.signal
import scipy.ndimage

from os.path import basename

def main(options):
    filename = basename(os.path.splitext(options['src'])[0])
    shapePath = options['dst'] + '//' + filename + '_' + options['suffix'] + '.shp'
    kmlPath = options['dst'] + '//' + filename + '_' + options['suffix'] + '.kml'
    trees = processCHM(options)
    shpsave(shapePath, trees)
    kmlsave(kmlPath, trees)
    print 'done'
    

def processCHM(options):
    ''' Extract tree positions from canopy height model
        @param  options       Input options (dictionnary)
    '''
    print 'process in progress'
    dataset = gdal.Open(options['src'], gdalconst.GA_ReadOnly)
    
    # georeference
    geotransform = dataset.GetGeoTransform()
    prj_wkt = dataset.GetProjectionRef()

    # extract raster values
    band = dataset.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, dataset.RasterXSize, dataset.RasterYSize)

    # create kernel
    radius = options['WinRad']
    kernel = np.zeros((2*radius+1, 2*radius+1))
    y,x = np.ogrid[-radius:radius+1, -radius:radius+1]
    mask = x**2 + y**2 <= radius**2
    kernel[mask] = 1

    # compute local maximum image
    data_max = scipy.ndimage.maximum_filter(data, size=None, footprint=kernel, output=None, mode='reflect', cval=0.0, origin=0)
    maxima = (data == data_max) * (data >= options['MinHeightThres']) # and data.all(data > 2)

    # determine location of local maxima
    labeled, num_objects = scipy.ndimage.label(maxima)
    slices = scipy.ndimage.find_objects(labeled)
    x, y = [], []
    for dy,dx in slices:
        x_center = (dx.start + dx.stop - 1)/2
        x.append(x_center)
        y_center = (dy.start + dy.stop - 1)/2
        y.append(y_center)

    px = np.asarray(x).astype(int) # x coordinate
    py = np.asarray(y).astype(int) # y coordinate
    pz = data[py,px] # height value
    mx, my = ApplyGeoTransform(px,py,geotransform)
    
    return {'xpos':mx, 'ypos':my ,'height':pz, 'prj_wkt':prj_wkt}


def shpsave(shapePath, trees):
    ''' Save data to a shp file
        @param  shpPath       Input path to the shp which will be created (Str)
        @param  trees         Input tree data (dictionnary)
    '''
    
    geoLocations = np.column_stack((trees['xpos'],trees['ypos']))
    height = trees['height']
    
    # Get driver
    driver = ogr.GetDriverByName('ESRI Shapefile')
    
    # Create shapeData
    shapePath = validateShapePath(shapePath)
    if os.path.exists(shapePath):
        os.remove(shapePath)
    shapeData = driver.CreateDataSource(shapePath)
    
    # Create spatialReference
    spatialReference = getSpatialReferenceFromWkt(trees['prj_wkt'])

    # Create layer
    layerName = os.path.splitext(os.path.split(shapePath)[1])[0]
    layer = shapeData.CreateLayer(layerName, spatialReference, ogr.wkbPoint)
    #layer.CreateField(ogr.FieldDefn("H", ogr.OFTReal))
    
    field_height = ogr.FieldDefn("H", ogr.OFTReal)
    field_height.SetWidth(4)
    field_height.SetPrecision(2)
    
    layer.CreateField(field_height)
    
    for pointIndex, geoLocation in enumerate(geoLocations):
        # Create point
        geometry = ogr.Geometry(ogr.wkbPoint)
        geometry.SetPoint(0, geoLocation[0], geoLocation[1])
        # Create feature
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(geometry)
        feature.SetFID(pointIndex)
        feature.SetField("H",float(height[pointIndex]))
        #feature.SetField("H",int(height[pointIndex]*100))
        
        # Save feature
        layer.CreateFeature(feature)
        # Cleanup
        geometry.Destroy()
        feature.Destroy()
    # Cleanup
    shapeData.Destroy()
    # Return
    return shapePath


def kmlsave(kmlPath, trees):
    ''' Save data to a kml file
        @param  kmlPath       Input path to the kml which will be created (Str)
        @param  trees         Input tree data (dictionnary)
    '''
    geoLocations = np.column_stack((trees['xpos'],trees['ypos']))
    height = trees['height']
    
    driver = ogr.GetDriverByName('KML')

    # Create shapeData
    kmlPath = validateKmlPath(kmlPath)
    if os.path.exists(kmlPath):
        os.remove(kmlPath)
        
    kmlData = driver.CreateDataSource(kmlPath)
    # Create spatialReference
    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(4326) # output SpatialReference
    
    spatialReference = getSpatialReferenceFromWkt(trees['prj_wkt'])
    transform = osr.CoordinateTransformation(spatialReference, outSpatialRef)

    # Create layer
    layerName = os.path.splitext(os.path.split(kmlPath)[1])[0]
    layer = kmlData.CreateLayer(layerName, outSpatialRef, ogr.wkbPoint)
    
    field_height = ogr.FieldDefn("H", ogr.OFTReal)
    field_height.SetWidth(4)
    field_height.SetPrecision(2)
    
    layer.CreateField(field_height)
    
    for pointIndex, geoLocation in enumerate(geoLocations):
        # Create point
        geometry = ogr.Geometry(ogr.wkbPoint)
        geometry.SetPoint(0, geoLocation[0], geoLocation[1])
        geometry.Transform(transform)
        
        # Create feature
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(geometry)
        feature.SetFID(pointIndex)
        feature.SetField("H",float(height[pointIndex]))
        
        # Save feature
        layer.CreateFeature(feature)
        # Cleanup
        geometry.Destroy()
        feature.Destroy()
    # Cleanup
    kmlData.Destroy()
    # Return
    return kmlPath
    

def getSpatialReferenceFromWkt(Wkt):
    '''Return GDAL spatial reference object from proj4 string'''
    spatialReference = osr.SpatialReference()
    spatialReference.ImportFromWkt(Wkt)
    return spatialReference
    
def validateShapePath(shapePath):
    '''Validate shapefile extension'''
    return os.path.splitext(str(shapePath))[0] + '.shp'
    
def validateKmlPath(kmlPath):
    '''Validate kml extension'''
    return os.path.splitext(str(kmlPath))[0] + '.kml'    
    
# convert pixel coordinates to geospatial coordinates
def ApplyGeoTransform(inx,iny,gt):
    ''' Apply a geotransform
        @param  inx       Input x coordinate (double)
        @param  iny       Input y coordinate (double)
        @param  gt        Input geotransform (six doubles)
        @return outx,outy Output coordinates (two doubles)
    '''
    outx = gt[0] + inx*gt[1] + iny*gt[2]
    outy = gt[3] + inx*gt[4] + iny*gt[5]
    return (outx,outy)    


# if __name__ == "__main__":
    
    # options = {
    # 'WinRad': float(sys.argv[2]), 
    # 'MinHeightThres': float(sys.argv[3]),
    # 'suffix': str(sys.argv[1]),
    # 'src': str(sys.argv[4]),
    # 'dst': str(sys.argv[5])
    # }
    # print options
    # print "--main a été activée"
    # if not options['src'].endswith('/'):
        # options['src'] = options['src'] + '/' 
        
    # if not options['dst'].endswith('/'):
        # options['dst'] = options['dst'] + '/'         
        
    # if os.path.isdir(options['src']) == False:
        # main(options)
    # if os.path.isdir(options['src']) == True:
        # file_list = os.listdir(options['src'])
        # inputDir = options['src']
        # shpdst = options['dst'] + 'shp'
        # kmldst = options['dst'] + 'kml'
        # if not os.path.exists(shpdst):
            # os.makedirs(shpdst)
            # print 'output folder ' + shpdst + ' was created'
        # if not os.path.exists(kmldst):
            # os.makedirs(kmldst)
            # print 'output folder ' + kmldst + ' was created'
        # for k, file_list in enumerate(file_list):
            # print('processing ' + file_list)
            # options['src'] = inputDir + file_list
            # main(options)

__author__ = "Matthew Parkan, LASIG, EPFL"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Matthew Parkan"
__email__ = "matthew.parkan@gmail.com"
__status__ = "Production"