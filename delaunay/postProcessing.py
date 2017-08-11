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


def clip(clipper, clippee, destination):
    dst = option['dst']
    runalg(dst + clippee, dst + clipper, dst, dst + destination)


if __name__ == "__main__":
    main(options)
