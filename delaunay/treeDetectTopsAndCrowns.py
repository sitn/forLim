#!/usr/bin/python
# -*- coding: utf-8 -*-

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

    # Prepare the folders for outputs:
    initialize(options)

    # For direct file input
    if not os.path.isdir(options['src']):
        options['filePath'] = options['src']
        filename = basename(os.path.splitext(options['filePath'])[0])
        trees, crowns, geotransform = processCHM(options)
        treetopsPath = options['dst'] + 'shp/' + filename + '_treetops.shp'
        spio.pointShpWriter(treetopsPath, trees['prj_wkt'], trees['xpos'],
                            trees['ypos'], trees['height'], 'H')

        crownsPath = options['dst'] + 'tif/' + filename + '_crowns.tif'
        spio.rasterWriter(crowns, crownsPath,
                          geotransform, trees['prj_wkt'], gdal.GDT_Int16)
        polyPath = options['dst'] + 'shp/' + filename + '_crowns.shp'
        forest_maskPath = options['dst'] + \
            'tif/' + filename + '_forest_mask.tif'

        spio.polygonizer(crownsPath, forest_maskPath, polyPath)

    # For folder input
    if os.path.isdir(options['src']):
        if not options['src'].endswith('/'):
            options['src'] = options['src'] + '/'

        file_list = os.listdir(options['src'])
        inputDir = options['src']

        for k, file_list in enumerate(file_list):
            options['filePath'] = inputDir + file_list
            filename = basename(os.path.splitext(options['filePath'])[0])
            trees = processCHM(options)
            treetopsPath = options['dst'] + 'shp/' + filename + '_treetops.shp'
            spio.pointShpWriter(treetopsPath, trees['prj_wkt'], trees['xpos'],
                                trees['ypos'], trees['height'], 'H')


def initialize(options):
    '''
    Prepare the folders for outputs:
    '''

    if not os.path.isdir(options['dst']):
        os.mkdir(options['dst'])
    if not options['dst'].endswith('/'):
        options['dst'] = options['dst'] + '/'
    tifdst = options['dst'] + 'tif'
    if not os.path.exists(tifdst):
        os.makedirs(tifdst)
    shpdst = options['dst'] + 'shp'
    if not os.path.exists(shpdst):
        os.makedirs(shpdst)


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
    y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
    mask = x**2 + y**2 <= radius**2
    kernel[mask] = 1

    # compute local maximum image
    data_max = scipy.ndimage.maximum_filter(data, size=None, footprint=kernel,
                                            output=None, mode='reflect',
                                            cval=0.0, origin=0)

    maxima = (data == data_max) * (data >= options['MinHeightThres'])

    # determine location of local maxima
    labeled, num_objects = scipy.ndimage.label(maxima)
    slices = scipy.ndimage.find_objects(labeled)
    x, y = [], []
    for dy, dx in slices:
        x_center = (dx.start + dx.stop - 1)/2
        x.append(x_center)
        y_center = (dy.start + dy.stop - 1)/2
        y.append(y_center)

    px = np.asarray(x).astype(int)  # x coordinate
    py = np.asarray(y).astype(int)  # y coordinate
    pz = data[py, px]  # height value
    mx, my = ApplyGeoTransform(px, py, geotransform)

    crowns = scipy.ndimage.watershed_ift(data.astype(np.uint16),
                                         labeled.astype(np.int32))

    crowns = (crowns == -1) + crowns

    # return crowns, geotransform, prj_wkt

    return {'xpos': mx, 'ypos': my, 'height': pz, 'prj_wkt': prj_wkt}, \
        crowns, geotransform


# convert pixel coordinates to geospatial coordinates
def ApplyGeoTransform(inx, iny, gt):
    ''' Apply a geotransform
        @param  inx       Input x coordinate (double)
        @param  iny       Input y coordinate (double)
        @param  gt        Input geotransform (six doubles)
        @return outx,outy Output coordinates (two doubles)
    '''
    outx = gt[0] + inx*gt[1] + iny*gt[2]
    outy = gt[3] + inx*gt[4] + iny*gt[5]
    return (outx, outy)


if __name__ == "__main__":

    options = {
        'WinRad': float(sys.argv[1]),
        'MinHeightThres': float(sys.argv[2]),
        'src': str(sys.argv[3]),
        'dst': str(sys.argv[4])
    }

    main(options)
