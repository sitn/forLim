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

from osgeo import gdal
from osgeo import ogr
from osgeo import gdalconst
import numpy as np
import scipy.ndimage

def main(options):
    '''
    Runs a set of tasks to determine the tree crowns using watershed 
    segmentation
    '''
    processing(options)
    
    print 'Done'

def processing(options):
    '''
    Processes the canopy height model to determine the forest delimitation
    '''
    print 'Tree crowns calculation in progress'
    
    # 1 Import Raster and compute Tree tops for markers use
    # THIS CODE SECTION IS DIRECTLY IMPORTED FROM MATTHEW PARKAN's
    # treeDetectLmax script under GPL license
    # see https://github.com/mparkan/sylva/blob/master/Python/treeDetectLmax.py
    
    # gdal import raster canopy height model in read only
    dataset = gdal.Open(options['src'], gdalconst.GA_ReadOnly)
    
    # get the georeference using gdal item methods
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
    
    # 2 Computes Watershed segmentation
    
    #to omit precision loss during int16 conversion /!\ int16 max value is 65,535 
    data = data * 1000
    
    # labels the non forest zone with -9999 (uint16(55537))
    #labeled = (data == 0) * (55537) + labeled 
    labeled = (data == 0) * (55537) + labeled
    
    crowns = scipy.ndimage.watershed_ift(data.astype(np.uint16), labeled.astype(np.int16))
    
    # 3 Writes down the crowns grid into a raster file
    
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(options['output'], dataset.RasterXSize, dataset.RasterYSize, 1, gdal.GDT_Int16 )
    
    ds.SetProjection(prj_wkt)
    ds.SetGeoTransform(geotransform)
    outband=ds.GetRasterBand(1)
    #outband.SetStatistics(0, np.max(crowns), 1, 1)
    outband.WriteArray(crowns)
    ds = None
    
    # 4 Polygonize the raster grid
    
    
    
if __name__ == "__main__":
    main(options)

__author__ = "Arnaud Poncet-Montanges, SFFN, Couvet (NE)"
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Arnaud Poncet-Montanges"
__email__ = "arnaudponcetmontanges@gmail.com"
__status__ = "Development"
