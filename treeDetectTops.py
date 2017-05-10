#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Created on Fri Jan 10 09:23:53 2014

Author: Matt Parkan, lasig, EPFL
Modified for QGIS Plugin use by : SFFN/APM

Description:

treeDetectLmax.py detects tree tops in a raster canopy height model (CHM) 
using the local maxima method. It exports the resulting point geometries 
(x, y, height) to the .shp data formats.

Usage:

    treeDetectLmax.py Suffix WinRad MinHeightThres src dst

Args:
    Suffix: each output file name is named according to the input file name with a _suffix added 
    WinRad: radius of the local maxima search window in pixels
    MinHeightThres: minimal height threshold in the units of the canopy height model
    src: the path to a single image file (OGR compatible format, check http:/www.gdal.org/formats_list.html) or to folder containing several images
    dst: the path to the destination folder

Example:

    treeDetectTops.py "tree" 4 2 "E:/data/mnc/test" "E:/" 

"""


import os
from os.path import basename
import sys
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from osgeo import gdalconst
import numpy as np
import scipy.signal
import scipy.ndimage

# Custom modules
import spatialIO as spio

def main(options):
    print 'Computing treetops'

    # Prepare the folders for outputs:
    initialize(options)

    # For direct file input
    if os.path.isdir(options['src']) == False:
        options['filePath'] = options['src']
        filename = basename(os.path.splitext(options['filePath'])[0])
        trees = processCHM(options)
        treetopsPath = options['dst'] + 'shp/' + filename + '_treetops.shp'
        spio.pointShpWriter(treetopsPath, trees['prj_wkt'], trees['xpos'], trees['ypos'], trees['height'], 'H')

    # For folder input
    if os.path.isdir(options['src']) == True:
        if not options['src'].endswith('/'):
            options['src'] = options['src'] + '/' 

        file_list = os.listdir(options['src'])
        inputDir = options['src']

        for k, file_list in enumerate(file_list):
            print('processing ' + file_list)
            options['filePath'] = inputDir + file_list
            filename = basename(os.path.splitext(options['filePath'])[0])            
            trees = processCHM(options)
            treetopsPath = options['dst'] + 'shp/' + filename + '_treetops.shp'
            spio.pointShpWriter(treetopsPath, trees['prj_wkt'], trees['xpos'], trees['ypos'], trees['height'], 'H')

    print 'Computing Treetops completed'


def initialize(options):
    '''
    Prepare the folders for outputs:
    '''

    if not os.path.isdir(options['dst']):
        os.mkdir(options['dst'])
        print 'output folder was created'
    if not options['dst'].endswith('/'):
        options['dst'] = options['dst'] + '/'
    tifdst = options['dst'] + 'tif'
    if not os.path.exists(tifdst):
        os.makedirs(tifdst)
        print 'output folder ' + tifdst + ' was created'
    shpdst = options['dst'] + 'shp'
    if not os.path.exists(shpdst):
        os.makedirs(shpdst)
        print 'output folder ' + shpdst + ' was created'


def processCHM(options):
    ''' Extract tree positions and heights from canopy height model
        @param options Input options (dictionnary)
    '''
    data, geotransform, prj_wkt = spio.rasterReader(options['filePath'])

    # filter non realstic data
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


if __name__ == "__main__":

    options = {
    'WinRad': float(sys.argv[1]), 
    'MinHeightThres': float(sys.argv[2]),
    'src': str(sys.argv[3]),
    'dst': str(sys.argv[4])
    }

    main(options)


__author__ = "Matthew Parkan, LASIG, EPFL"
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Matthew Parkan"
__email__ = "matthew.parkan@gmail.com"
__status__ = "Production"
