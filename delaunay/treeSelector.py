# -*- coding: utf-8 -*-


import os
from os.path import basename
from osgeo import ogr

# Import custom modules

import spatialIO as spio

# Check whether we're on QGIS or not
import qgis.utils

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from processing import runalg
from folderManager import initialize


def main(options):

    # Prepare the folders for outputs:
    initialize(options)

    # For direct file input
    if not os.path.isdir(options['src']):
        options['filePath'] = options['src']
        filename = basename(os.path.splitext(options['filePath'])[0])
        processing(options, filename)

    # For folder input
    if os.path.isdir(options['src']):
        if not options['src'].endswith('/'):
            options['src'] = options['src'] + '/'

        file_list = os.listdir(options['src'])
        inputDir = options['src']

        # Iterate each file for processing and exports
        for k, file_list in enumerate(file_list):
            options['filePath'] = inputDir + file_list
            filename = basename(os.path.splitext(options['filePath'])[0])

            # Process each file


def processing(options, f):
    '''
    Select trees which are on the contour of the forest and isolated trees.
    '''
    # Export Grid contour and isolated to crowns values
    forestSelectedPath = options['dst'] + 'tif/' + f + \
        '_forest_selected.tif'
    crownsPath = options['dst'] + 'shp/' + f + '_crowns.shp'
    crownsStatsPath = options['dst'] + 'shp/' + f + '_crowns_stats.shp'

    # get the MAX value
    runalg('saga:gridstatisticsforpolygons', forestSelectedPath,
           crownsPath, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, crownsStatsPath)

    # Loads new crowns layer in edit mode
    driver = ogr.GetDriverByName('ESRI Shapefile')

    ds_crownsStats = driver.Open(crownsStatsPath, 1)
    crowns = ds_crownsStats.GetLayer()

    layerDefinition = crowns.GetLayerDefn()

    #  Filter out tree at the forest limit
    # Find FID of each unselected crown and remove it
    selected_array = []
    unselected_array = []

    for feature in crowns:
        if feature.GetField(1) == 1:  # TODO: USE NAMED FIELD
            selected_array.append(feature.GetField("N"))
        else:
            unselected_array.append(feature.GetField("N"))
            crowns.DeleteFeature(feature.GetFID())

    ds_crownsStats.Destroy()
    treetopsPath = options['dst'] + 'shp/' + f + '_treetops.shp'

    ds_treetops = driver.Open(treetopsPath, 1)
    treetops = ds_treetops.GetLayer()

    # remove the unselected FIDs
    for feature in treetops:
        if (feature.GetFID() + 1) in unselected_array:
            treetops.DeleteFeature(feature.GetFID())

    # Clear dataSources
    ds_treetops.Destroy()

    treetopsSelectedPath = options['dst'] + 'shp/' + f + \
        '_treetops_selected.shp'
    crownsSelectedPath = options['dst'] + 'shp/' + f + '_crowns_selected.shp'
    treetopsTrianglesPath = options['dst'] + 'shp/' + f + \
        '_treetops_triangles.shp'

    runalg('qgis:advancedpythonfieldcalculator', treetopsPath,
           'N', 0, 10, 0, '', 'value = $id', treetopsSelectedPath)

    runalg('qgis:joinattributesbylocation', crownsStatsPath,
           treetopsSelectedPath, u'contains', 0.0,  0, '', 0,
           crownsSelectedPath)
    runalg('qgis:delaunaytriangulation',
           treetopsSelectedPath, treetopsTrianglesPath)


if __name__ == "__main__":

    main(options)
