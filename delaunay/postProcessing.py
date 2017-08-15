# -*- coding: utf-8 -*-

import os
from os.path import basename
from osgeo import ogr
from osgeo import osr
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry
from folderManager import initialize
from qgis.analysis import QgsGeometryAnalyzer
from qgis.core import QgsCoordinateReferenceSystem
from processing import runalg

# Import custom modules
import spatialIO as spio


def main(options):

    # Prepare the folders for outputs:
    initialize(options)

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

    if options["AddLayer"]:

        vlayer = QgsVectorLayer(options['dst'] + 'shp/' + filename +
                                '_forest_zones.shp', "forest", "ogr")
        QgsMapLayerRegistry.instance().addMapLayer(vlayer)


def dissolve(options, f):

    #  Create the new layers to store forest and wooden pasture convex hulls
    CHsForestPath = options['dst'] + 'shp/' + f + '_convexHulls_forest.shp'
    CHsWoodenPasturePath = options['dst'] + 'shp/' + f + \
        '_convexHulls_wooden_pasture.shp'

    dissolvedF = options['dst'] + 'shp/' + f + '_ch_forest_dissolved.shp'
    spio.pathChecker(dissolvedF)
    dissolvedW = options['dst'] + 'shp/' + f + '_ch_wpastures_dissolved.shp'
    spio.pathChecker(dissolvedW)

    fLayer = QgsVectorLayer(CHsForestPath, 'Dense forests', 'ogr')
    wLayer = QgsVectorLayer(CHsWoodenPasturePath, 'Wooden pastures', 'ogr')

    analyzer = QgsGeometryAnalyzer()
    analyzer.dissolve(wLayer, dissolvedW)
    analyzer.dissolve(wLayer, dissolvedF)
    if options["AddLayer"]:
        dissolvedWLayer = QgsVectorLayer(dissolvedW,
                                         'Dissolved wooden pastures',
                                         'ogr')
        dissolvedFLayer = QgsVectorLayer(dissolvedF,
                                         'Dissolved dense forest',
                                         'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(dissolvedWLayer)
        QgsMapLayerRegistry.instance().addMapLayer(dissolvedFLayer)
    return


def merge(options, layer_suffix):

    merge_candidates = ''

    for f in os.listdir(options['dst'] + '/shp'):
        if layer_suffix in f:
            merge_candidates += options['dst'] + 'shp/' + f + ';'

    merge_candidates = merge_candidates[:-1]

    dst = options['dst'] + 'shp/merged_' + layer_suffix

    runalg('qgis:mergevectorlayers', merge_candidates, dst)

    if options["AddLayer"]:
        merged = QgsVectorLayer(dst, 'Merged ' + layer_suffix[:-4], 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(merged)


def clip(options):

    forest_zones = ''
    wooden_pastures = ''
    dst = options['dst']
    multiF = False
    for f in os.listdir(options['dst'] + '/shp'):
        if 'merged_forest_zones.shp' in f:  # TODO: CHECK THIS!!!
            forest_zones += options['dst'] + 'shp/' + f
            multi = True

    if not multiF:
        for f in os.listdir(options['dst'] + '/shp'):
            if 'forest_zones.shp' in f:
                forest_zones += options['dst'] + 'shp/' + f

    multiW = False
    for f in os.listdir(options['dst'] + '/shp'):
        if 'merged_ch_wpastures_dissolved.shp' in f:
            wooden_pastures += options['dst'] + 'shp/' + f
            multi = True

    if not multiW:
        for f in os.listdir(options['dst'] + '/shp'):
            if '_ch_wpastures_dissolved.shp' in f:
                wooden_pastures += options['dst'] + 'shp/' + f

    result_diff = dst + 'shp/' + 'difference_forest_zones.shp'
    result_deag = dst + 'shp/' + 'deagragated_forest_zones.shp'

    runalg('qgis:difference', forest_zones, wooden_pastures, False,
           result_diff)
    runalg('qgis:multiparttosingleparts', result_diff, result_deag)

    forest_raw = QgsVectorLayer(result_deag, 'ToFilter ', 'ogr')
    dp = forest_raw.dataProvider()
    features_to_remove = []

    for f in forest_raw.getFeatures():

        if f.geometry().area() < options['MinAreaThres']:
            features_to_remove.append(f.id())
        else:
            geom = f.geometry().simplify(10)
            geom = geom.smooth(4, 0.25)
            dp.changeGeometryValues({f.id(): geom})

    dp.deleteFeatures(features_to_remove)

    if options["AddLayer"]:
        forest = QgsVectorLayer(result_deag, 'Legal forest ', 'ogr')
        QgsMapLayerRegistry.instance().addMapLayer(forest)


if __name__ == "__main__":
    main(options)
