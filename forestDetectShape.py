# -*- coding: utf-8 -*-

"""
Created on Mon Jan 04 13:24:57 2016

Author: Arnaud Poncet-Montanges, SFFN, Couvet (CH)

Description:

forestDetectShape.py detects general forest polygons, forest contour and 
isolated trees using mathematical morphology operations from the scipy ndimage
library. Result are stored as binary tif files, ideal for mask use or binary 
selection purposes.

Usage:

    forestDetectShape.py Suffix WinRad MinHeightThres src dst

Args:

    Suffix: each output file name is named according to the input file name with a _suffix added 
    WinRad: radius of the local maxima search window in pixels
    MinHeightThres: minimal height threshold in the units of the canopy height model
    src: the path to a single image file (OGR compatible format, check http://www.gdal.org/formats_list.html) or to folder containing several images
    dst: the path to the destination folder

Example:

    forestDetectShape.py "bin" 4 2 "E:/data/mnc/test" "E:/" 

"""

import os
from os.path import basename
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdalconst
import numpy as np
import scipy.ndimage

# Import custom modules

import spatialIO as spio


def main(options):
    print 'Computing forest shapes'
    
    # Prepare the folders for outputs:
    initialize(options)
    
    # For direct file input
    if os.path.isdir(options['src']) == False:
        options['filePath'] = options['src']
        filename = basename(os.path.splitext(options['filePath'])[0])
        forest_mask, forest_zones, forest_outline, forest_isolated = processing(options)
        
        # export raster results
        forest_maskPath = options['dst'] + 'tif//' + filename + '_forest_mask.tif'
        spio.rasterWriter(forest_mask, forest_maskPath, options['geotransform'], options['prj_wkt'], gdal.GDT_Byte)
            
        forest_zonesPath = options['dst'] + 'tif//' + filename + '_forest_zones.tif'
        spio.rasterWriter(forest_zones, forest_zonesPath, options['geotransform'], options['prj_wkt'], gdal.GDT_Byte)
            
        forest_outlinePath = options['dst'] + 'tif//' + filename + '_forest_outline.tif'
        spio.rasterWriter(forest_outline, forest_outlinePath, options['geotransform'], options['prj_wkt'], gdal.GDT_Byte)

        forest_isolatedPath = options['dst'] + 'tif//' + filename + '_forest_isolated.tif'
        spio.rasterWriter(forest_isolated, forest_isolatedPath, options['geotransform'], options['prj_wkt'], gdal.GDT_Byte)
            
        # vectorize the forest zones
        polyPath = options['dst'] + 'shp//' + filename + '_forest_zones.shp'
        spio.polygonizer(forest_zonesPath, forest_zonesPath, polyPath )

    # For folder input
    if os.path.isdir(options['src']):
        if not options['src'].endswith('/'):
            options['src'] = options['src'] + '//' 
            
        file_list = os.listdir(options['src'])
        inputDir = options['src']

        for k, file_list in enumerate(file_list):
            print('processing ' + file_list)
            options['filePath'] = inputDir + file_list
            filename = basename(os.path.splitext(options['filePath'])[0])            
            forest_mask, forest_zones, forest_outline, forest_isolated = processing(options)
            
            # export raster results
            forest_maskPath = options['dst'] + 'tif//' + filename + '_forest_mask.tif'
            spio.rasterWriter(forest_mask, forest_maskPath, options['geotransform'], options['prj_wkt'], gdal.GDT_Byte)
            
            forest_zonesPath = options['dst'] + 'tif//' + filename + '_forest_zones.tif'
            spio.rasterWriter(forest_zones, forest_zonesPath, options['geotransform'], options['prj_wkt'], gdal.GDT_Byte)
            
            forest_outlinePath = options['dst'] + 'tif//' + filename + '_forest_outline.tif'
            spio.rasterWriter(forest_outline, forest_outlinePath, options['geotransform'], options['prj_wkt'], gdal.GDT_Byte)

            forest_isolatedPath = options['dst'] + 'tif//' + filename + '_forest_isolated.tif'
            spio.rasterWriter(forest_isolated, forest_isolatedPath, options['geotransform'], options['prj_wkt'], gdal.GDT_Byte)
            
            # vectorize the forest zones
            polyPath = options['dst'] + 'shp//' + filename + '_forest_zones.shp'
            spio.polygonizer(forest_zonesPath, forest_zonesPath, polyPath )

    print 'Computing forest shapes completed'
    

def initialize(options):
    '''
    Prepare the folders for outputs:
    '''
    
    if not os.path.isdir(options['dst']):
        os.mkdir(options['dst'])
        print 'output folder was created'
    if not options['dst'].endswith('/'):
        options['dst'] = options['dst'] + '//'
    tifdst = options['dst'] + 'tif'
    if not os.path.exists(tifdst):
        os.makedirs(tifdst)
        print 'output folder ' + tifdst + ' was created'
    shpdst = options['dst'] + 'shp'
    if not os.path.exists(shpdst):
        os.makedirs(shpdst)
        print 'output folder ' + shpdst + ' was created'
        

def processing(options):
    '''
    Extract Forest zones from canopy height model with respect to minimal 
    legal shape size. Output are forest zones, forest contour, isolated trees
    '''
    
    # Import CHM raster data
    data, geotransform, prj_wkt = spio.rasterReader(options['filePath'])
    options['geotransform'] = geotransform
    options['prj_wkt'] = prj_wkt
    RasterYSize, RasterXSize = data.shape
    
    # Filter non realstic data
    data = (data < 60) * (data > 1) * data
    
    # Computes no-tree/forest binary data
    forest_mask = (data > 0)
    
    # Fill the small holes
    forest_filled = scipy.ndimage.binary_fill_holes(forest_mask).astype(bool)
    
    # Label the different zones
    labeled_array, num_features = scipy.ndimage.label(forest_filled, structure = None, output = np.int)
    
    # Initiate the forest zones array
    forest_zones = np.zeros((RasterYSize, RasterXSize), dtype=np.bool)
    
    # filter the elements by size
    matches = np.bincount(labeled_array.ravel())> options['MinAreaThres']
    
    # Get the IDs corresponding to matches
    match_feat_ID = np.nonzero(matches)[0]
    valid_match_feat_ID = np.setdiff1d(match_feat_ID,[0,num_features])

    # ORing operation
    forest_zones = np.in1d(labeled_array,valid_match_feat_ID).reshape(labeled_array.shape)

#    # Previous lines are an optimization of this loop
#    
#    for i in range(1, num_features):
#        zone_array = labeled_array == i
#        zone = np.sum(zone_array)
#        if zone > 800:
#            forest_zones += zone_array
    
    # create kernel
    radius = options['WinRad']
    kernel = np.zeros((2*radius+1, 2*radius+1))
    y,x = np.ogrid[-radius:radius+1, -radius:radius+1]
    mask = x**2 + y**2 <= radius**2
    kernel[mask] = 1
    
    # Computing outline     
    forest_eroded = scipy.ndimage.binary_erosion(forest_zones, kernel)
    forest_outline = forest_zones - forest_eroded
    
    # Computing inner elements
    forest_inside = forest_zones - forest_outline
    
    # Computing small elements
    forest_isolated = forest_filled - forest_zones
    
    return forest_mask, forest_zones, forest_outline, forest_isolated
    
    
if __name__ == "__main__":
    main(options)

__author__ = "Arnaud Poncet-Montanges, SFFN, Couvet (CH)"
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Arnaud Poncet-Montanges"
__email__ = "arnaudponcetmontanges@gmail.com"
__status__ = "Development"
