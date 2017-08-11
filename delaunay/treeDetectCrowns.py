# -*- coding: utf-8 -*-

import os
from os.path import basename
from osgeo import gdal
import numpy as np
import scipy.ndimage
from folderManager import initialize


# Custom modules
import spatialIO as spio


def main(options):

    # Prepare the folders for outputs:
    initialize(options)

    # For direct file input
    if not os.path.isdir(options['src']):
        options['filePath'] = options['src']
        filename = basename(os.path.splitext(options['filePath'])[0])
        crowns, geotransform, prj_wkt = processing(options)
        crownsPath = options['dst'] + 'tif/' + filename + '_crowns.tif'
        spio.rasterWriter(crowns, crownsPath,
                          geotransform, prj_wkt, gdal.GDT_Int16)
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
            crowns, geotransform, prj_wkt = processing(options)
            crownsPath = options['dst'] + 'tif/' + filename + '_crowns.tif'
            spio.rasterWriter(crowns, crownsPath, geotransform,
                              prj_wkt, gdal.GDT_Int16)
            polyPath = options['dst'] + 'shp/' + filename + '_crowns.shp'
            forest_maskPath = options['dst'] + 'tif/' + \
                filename + '_forest_mask.tif'

            spio.polygonizer(crownsPath, forest_maskPath, polyPath)


def processing(options):
    '''
    Processes the canopy height model to determine the forest delimitation
    '''

    # 1 Import Raster
    data, geotransform, prj_wkt = spio.rasterReader(options['filePath'])

    # Filter non realstic data
    data = (data < 60) * (data > 1) * data

    # create kernel
    radius = options['WinRad']
    kernel = np.zeros((2*radius+1, 2*radius+1))
    y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
    mask = x**2 + y**2 <= radius**2
    kernel[mask] = 1

    # compute local maximum image
    data_max = scipy.ndimage.maximum_filter(data, size=None,
                                            footprint=kernel,
                                            output=None,
                                            mode='reflect',
                                            cval=0.0,
                                            origin=0)

    maxima = (data == data_max) * (data >= options['MinHeightThres'])

    # determine location of local maxima
    labeled, num_objects = scipy.ndimage.label(maxima)

    # 2 Computes Watershed segmentation

    # prevent precision loss during int16 conversion
    data = data * 1000

    # labels the non forest zone with -99999
    labeled = (data == 0) * (-1) + labeled

    crowns = scipy.ndimage.watershed_ift(data.astype(np.uint16),
                                         labeled.astype(np.int32))

    crowns = (crowns == -1) + crowns

    return crowns, geotransform, prj_wkt


if __name__ == "__main__":
    main(options)
