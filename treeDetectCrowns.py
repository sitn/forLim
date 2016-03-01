# -*- coding: utf-8 -*-
"""
Created on Mon Dec 07 08:54:39 2015

Author: Arnaud Poncet-Montanges, SFFN, Couvet (NE)

Description:

treeDetectCrowns.py detects tree crowns in a raster canopy height model (CHM) 
using the watershed algorithm from numpy and the tree tops as markers.

Usage:

Args:

Example:

"""
import os
from os.path import basename
from osgeo import gdal
from osgeo import ogr
from osgeo import gdalconst
import numpy as np
import scipy.ndimage

# Custom modules
import spatialIO as spio

def main(options):
    print 'Computing treecrowns'
    
    # Prepare the folders for outputs:
    initialize(options)
    
    # For direct file input
    if os.path.isdir(options['src']) == False:
        options['filePath'] = options['src']
        filename = basename(os.path.splitext(options['filePath'])[0])
        crowns, geotransform, prj_wkt = processing(options)
        crownsPath = options['dst'] + 'tif//' + filename + '_crowns.tif'
        spio.rasterWriter(crowns, crownsPath, geotransform, prj_wkt, gdal.GDT_Int16)
        polyPath = options['dst'] + 'shp//' + filename + '_crowns.shp'
        forest_maskPath = options['dst'] + 'tif//' + filename + '_forest_mask.tif'
        spio.polygonizer(crownsPath, forest_maskPath, polyPath )

    # For folder input
    if os.path.isdir(options['src']) == True:
        if not options['src'].endswith('/'):
            options['src'] = options['src'] + '//' 
            
        file_list = os.listdir(options['src'])
        inputDir = options['src']

        for k, file_list in enumerate(file_list):
            print('processing ' + file_list)
            options['filePath'] = inputDir + file_list
            filename = basename(os.path.splitext(options['filePath'])[0])            
            crowns, geotransform, prj_wkt = processing(options)
            crownsPath = options['dst'] + 'tif//' + filename + '_crowns.tif'
            spio.rasterWriter(crowns, crownsPath, geotransform, prj_wkt, gdal.GDT_Int16)
            polyPath = options['dst'] + 'shp//' + filename + '_crowns.shp'
            forest_maskPath = options['dst'] + 'tif//' + filename + '_forest_mask.tif'
            spio.polygonizer(crownsPath, forest_maskPath, polyPath )
            
    print 'Treecrowns have been correctly computed'


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
    Processes the canopy height model to determine the forest delimitation
    '''
    print 'Tree crowns calculation in progress'
    
    # 1 Import Raster and compute Tree tops for markers use
    data, geotransform, prj_wkt = spio.rasterReader(options['filePath'])
    
    # Filter non realstic data
    data = (data < 60) * (data > 1) * data
    
    # create kernel
    radius = options['WinRad']
    kernel = np.zeros((2*radius+1, 2*radius+1))
    y,x = np.ogrid[-radius:radius+1, -radius:radius+1]
    mask = x**2 + y**2 <= radius**2
    kernel[mask] = 1

    # compute local maximum image
    data_max = scipy.ndimage.maximum_filter(data, size=None, footprint=kernel, output=None, mode='reflect', cval=0.0, origin=0)
    maxima = (data == data_max) * (data >= options['MinHeightThres'])
    
    # determine location of local maxima
    labeled, num_objects = scipy.ndimage.label(maxima)
    
    ## 2 Computes Watershed segmentation
    #to omit precision loss during int16 conversion /!\ int16 max value is 65,535 
    data = data * 1000
    
    # labels the non forest zone with -99999
    labeled = (data == 0) * (-1) + labeled
    
    crowns = scipy.ndimage.watershed_ift(data.astype(np.uint16), labeled.astype(np.int16))
    
    crowns = (crowns == -1) + crowns 
    
    return crowns, geotransform, prj_wkt    
    
    
if __name__ == "__main__":
    main(options)

__author__ = "Arnaud Poncet-Montanges, SFFN, Couvet (NE)"
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Arnaud Poncet-Montanges"
__email__ = "arnaudponcetmontanges@gmail.com"
__status__ = "Development"
