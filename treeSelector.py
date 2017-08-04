# -*- coding: utf-8 -*-


import os
from os.path import basename
from osgeo import ogr

# Import custom modules

import spatialIO as spio

# Check whether we're on QGIS or not
import qgis.utils
inqgis = qgis.utils.iface is not None

if inqgis:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
    from qgis.core import *
    from qgis.gui import *
    from processing import runalg
else:

    import os
    import sys
    import glob
    # Prepare the environment
    from qgis.core import *
    from PyQt4.QtGui import *

    from os.path import expanduser
    home = expanduser("~")

    # Prepare processing framework
    sys.path.append(home + '\.qgis2\python\plugins')
    from processing.core.Processing import Processing
    Processing.initialize()
    from processing.tools import *


def main(options):
    print 'Selecting trees of interest'

    # Prepare the folders for outputs:
    initialize(options)

    # For direct file input
    if not os.path.isdir(options['src']):
        print("SINGLE FILE INPUT")
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
            print('Processing file ' + file_list)
            options['filePath'] = inputDir + file_list
            filename = basename(os.path.splitext(options['filePath'])[0])

            # Process each file
            processing(options, filename)


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


def processing(options, filename):
    '''
    Select trees which are on the contour of the forest and isolated trees.
    '''
    # Export Grid contour and isolated to crowns values
    forestSelectedPath = options['dst'] + 'tif/' + filename + \
        '_forest_selected.tif'
    crownsPath = options['dst'] + 'shp/' + filename + '_crowns.shp'
    crownsStatsPath = options['dst'] + 'shp/' + filename + '_crowns_stats.shp'
    print(crownsStatsPath)
    # TODO: WHICH STAT HAS TO BE CALCULATED ???
    if options['plugin']:
        runalg('saga:gridstatisticsforpolygons', forestSelectedPath,
               crownsPath, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, crownsStatsPath)
    else:
        general.runalg('saga:gridstatisticsforpolygons', forestSelectedPath,
                       crownsPath, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0,
                       crownsStatsPath)

    # Select Crown features with contour or isolated values

    # Loads new crowns layer in edit mode
    driver = ogr.GetDriverByName('ESRI Shapefile')

    ds_crownsStats = driver.Open(crownsStatsPath, 1)
    crowns = ds_crownsStats.GetLayer()

    layerDefinition = crowns.GetLayerDefn()

    # Find FID of each unselected crown and remove it from the new crown layer
    selected_array = []
    unselected_array = []

    for feature in crowns:
        if feature.GetField(1) != 1:  # TODO: CHECK THAT THIS IS CORECT!!!
            selected_array.append(feature.GetField("N"))
        else:
            unselected_array.append(feature.GetField("N"))
            crowns.DeleteFeature(feature.GetFID())

    ds_crownsStats.Destroy()
    treetopsPath = options['dst'] + 'shp/' + filename + '_treetops.shp'

    ds_treetops = driver.Open(treetopsPath, 1)
    treetops = ds_treetops.GetLayer()

    # remove the unselected FIDs
    for feature in treetops:
        if (feature.GetFID() + 1) in unselected_array:
            treetops.DeleteFeature(feature.GetFID())

    # Clear dataSources
    ds_treetops.Destroy()


    treetopsSelectedPath = options['dst'] + 'shp/' + filename + '_treetops_selected.shp'
    crownsSelectedPath = options['dst']+ 'shp/' + filename + '_crowns_selected.shp'
    treetopsTrianglesPath = options['dst'] + 'shp/' + filename + '_treetops_triangles.shp'

    if options['plugin']:
        runalg('qgis:advancedpythonfieldcalculator', treetopsPath,
               'N', 0, 10, 0, '', 'value = $id +1', treetopsSelectedPath)
        runalg('qgis:advancedpythonfieldcalculator', crownsStatsPath,
               'ROW', 0, 10, 0, '', 'value = $id', crownsSelectedPath)
        runalg('qgis:delaunaytriangulation',
               treetopsSelectedPath, treetopsTrianglesPath)

    else:
        general.runalg('qgis:advancedpythonfieldcalculator', treetopsPath,
                       'N', 0, 10, 0, '', 'value = $id +1',
                       treetopsSelectedPath)
        general.runalg('qgis:advancedpythonfieldcalculator', crownsStatsPath,
                       'ROW', 0, 10, 0, '', 'value = $id', crownsSelectedPath)
        general.runalg('qgis:delaunaytriangulation', treetopsSelectedPath,
                       treetopsTrianglesPath)


if __name__ == "__main__":

    main(options)
