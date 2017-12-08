# -*- coding: utf-8 -*-

import os
from os.path import basename
from osgeo import ogr
from osgeo import osr
from qgis.core import QgsVectorLayer, QgsProject
from qgis.core import QgsCoordinateReferenceSystem
from . import folderManager
import processing

# Import custom modules
from .spatialIO import pathChecker


def main(options):

    # Prepare the folders for outputs:
    folderManager.initialize(options)

    # For direct file input
    if not os.path.isdir(options['src']):
        options['filePath'] = options['src']
        filename = basename(os.path.splitext(options['filePath'])[0])
        dissolve(options, filename)

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
            dissolve(options, filename)


def dissolve(options, f):
    #  Create the new layers to store forest and wooden pasture convex hulls
    CHsForestPath = options['dst'] + 'shp/' + f + '_convexHulls_forest.shp'
    CHsWoodenPasturePath = options['dst'] + 'shp/' + f + \
        '_convexHulls_wooden_pasture.shp'

    dissolvedF = options['dst'] + 'shp/' + f + '_ch_forest_dissolved.shp'
    pathChecker(dissolvedF)
    dissolvedW = options['dst'] + 'shp/' + f + '_ch_wpastures_dissolved.shp'
    pathChecker(dissolvedW)

    # TODO: fix processing use
    result = processing.run('qgis:union',
                            {'INPUT': CHsForestPath,
                             'OVERLAY': CHsForestPath,
                             'OUTPUT': dissolvedF})

    # TODO: fix processing use
    result = processing.run('qgis:union',
                            {'INPUT': CHsWoodenPasturePath,
                             'OVERLAY': CHsWoodenPasturePath,
                             'OUTPUT': dissolvedW})

    return


def merge(options, layer_suffix):

    merge_candidates = ''

    for f in os.listdir(options['dst'] + '/shp'):
        if layer_suffix in f:
            merge_candidates += options['dst'] + 'shp/' + f + ';'

    merge_candidates = merge_candidates[:-1]

    dst = options['dst'] + 'shp/merged' + layer_suffix
    # TODO: fix processing use
    processing.run('qgis:mergevectorlayers', merge_candidates, dst)

    if options["AddLayer"]:
        merged = QgsVectorLayer(dst, 'Merged ' + layer_suffix[:-4], 'ogr')
        QgsProject.instance().addMapLayer(merged)


def clip(options):

    forest_zones = ''
    wooden_pastures = ''
    dst = options['dst']
    multiF = False
    for f in os.listdir(options['dst'] + '/shp'):
        if 'merged_forest_zones.shp' in f:
            multi = True
    forest_zones = options['dst'] + 'shp/merged_forest_zones.shp'

    if not multiF:
        for f in os.listdir(options['dst'] + '/shp'):
            if 'forest_zones.shp' in f:
                forest_zones = options['dst'] + 'shp/' + f

    multiW = False
    for f in os.listdir(options['dst'] + '/shp'):
        if 'merged_ch_wpastures_dissolved.shp' in f:
            multi = True

    wooden_pastures = options['dst'] + 'shp/' + \
        'merged_ch_wpastures_dissolved.shp'

    if not multiW:
        for f in os.listdir(options['dst'] + '/shp'):
            if '_ch_wpastures_dissolved.shp' in f:
                wooden_pastures = options['dst'] + 'shp/' + f

    result_diff = dst + 'shp/' + 'difference_forest_zones.shp'
    result_deag = dst + 'shp/' + 'deagragated_forest_zones.shp'

    # TODO: fix processing use
    processing.run('qgis:difference',
                   {'INPUT': forest_zones,
                    'OVERLAY': wooden_pastures,
                    'IGNORE_INVALID': False,
                    'OUTPUT': result_diff})

    # TODO: fix processing use
    processing.run('qgis:multiparttosingleparts', result_diff, result_deag)

    forest_raw = QgsVectorLayer(result_deag, 'ToFilter ', 'ogr')
    dp = forest_raw.dataProvider()
    forest_raw.selectByExpression('$area < ' + str(options['MinAreaThres']))
    forest_to_delete_ids = forest_raw.getValues("$id", True)
    dp.deleteFeatures(forest_to_delete_ids[0])

    outputDir = options["dst"]
    f = open(outputDir + "/log.txt", "a")
    f.write("postProcessing passed\n")
    f.close()

    if options["AddLayer"]:
        forest = QgsVectorLayer(result_deag, 'Final forLim forest ', 'ogr')
        QgsProject.instance().addMapLayer(forest)

    return result_deag


if __name__ == "__main__":
    main(options)
