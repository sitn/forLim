# -*- coding: utf-8 -*-


import os
from os.path import basename
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsExpression
from qgis.core import QgsFeedback, QgsField, QgsFeatureRequest
from qgis.PyQt.QtCore import QVariant
import processing as qgsproc
from qgis.core import QgsProcessingFeatureSourceDefinition
from qgis.core import QgsProcessingOutputLayerDefinition
from .folderManager import initialize
from qgis.analysis import QgsZonalStatistics
from processing.algs.qgis import SpatialJoin
from processing import run

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
    # crownsStatsPath = options['dst'] + 'shp/' + f + '_crowns_stats.shp'
    outputDir = options["dst"]
    fileTxt = open(outputDir + "/log.txt", "a")
    fileTxt.write("gridstatisticsforpolygons started\n")
    fileTxt.close()

    crowns = QgsVectorLayer(crownsPath, "crowns", "ogr")
    inputStatRaster = QgsRasterLayer(forestSelectedPath, "forestSelected")
    z_stat = QgsZonalStatistics(crowns, inputStatRaster, '_', 1,
                                QgsZonalStatistics.Max)

    result_z_stat = z_stat.calculateStatistics(QgsFeedback())

    outputDir = options["dst"]
    fileTxt = open(outputDir + "/log.txt", "a")
    fileTxt.write("gridstatisticsforpolygons passed\n")
    fileTxt.close()
    # crowns = QgsVectorLayer(crownsStatsPath, 'Crowns stats', 'ogr')
    crowns.selectByExpression('"_max"=1.0')
    selected_array = crowns.getValues("N", True)
    crowns.invertSelection()
    unselected_array = crowns.getValues("N", True)
    unselected_crowns_ids = crowns.getValues("$id", True)
    unselected_top_ids = crowns.getValues('"N" - 1', True)
    crowns.dataProvider().deleteFeatures(unselected_crowns_ids[0])

    treetopsPath = options['dst'] + 'shp/' + f + '_treetops.shp'
    treetops = QgsVectorLayer(treetopsPath, 'Tree tops', 'ogr')

    treetops.dataProvider().deleteFeatures(unselected_top_ids[0])

    treetopsSelectedPath = options['dst'] + 'shp/' + f + \
        '_treetops_selected.shp'
    crownsSelectedPath = options['dst'] + 'shp/' + f + '_crowns_selected.shp'
    treetopsTrianglesPath = options['dst'] + 'shp/' + f + \
        '_treetops_triangles.shp'

    outputDir = options["dst"]
    fileTxt = open(outputDir + "/log.txt", "a")
    fileTxt.write("advancedpythonfieldcalculator started\n")
    fileTxt.close()

    treetops.dataProvider().addAttributes([QgsField(
        'N', QVariant.Int)])
    treetops.updateFields()
    treetops.startEditing()
    for treetop in treetops.getFeatures():
        print(treetop.id())
        treetops.changeAttributeValue(treetop.id(),
                                      treetop.fieldNameIndex('N'),
                                      treetop.id())
    treetops.commitChanges()

    outputDir = options["dst"]
    fileTxt = open(outputDir + "/log.txt", "a")
    fileTxt.write("joinattributesbylocation started\n")
    fileTxt.close()

    crowns.dataProvider().addAttributes([QgsField(
        'tid', QVariant.Int)])
    crowns.updateFields()
    crowns.startEditing()
    for crown in crowns.getFeatures():
        request = QgsFeatureRequest()
        request.setFilterRect(crown.geometry().boundingBox())
        dp = treetops.dataProvider()
        for r in dp.getFeatures(request):
            if crown.geometry().intersects(r.geometry()):
                # crown.setAttribute('tid', r.id())
                crowns.changeAttributeValue(crown.id(),
                                            crown.fieldNameIndex('tid'),
                                            r.id())
    crowns.commitChanges()

    fileTxt = open(outputDir + "/log.txt", "a")
    fileTxt.write("delaunaytriangulation started\n")
    fileTxt.close()
    runalg('qgis:delaunaytriangulation',
           treetopsSelectedPath, treetopsTrianglesPath)

    #  Remove triangles with perimeter higher than threshold
    triangles = QgsVectorLayer(treetopsTrianglesPath, 'triangles', 'ogr')
    maxPeri = str(options['MaxTrianglePerimeter'])
    triangles.selectByExpression('$perimeter > ' + maxPeri)
    triangles_to_delete_ids = triangles.getValues("$id", True)
    triangles.dataProvider().deleteFeatures(triangles_to_delete_ids[0])

    outputDir = options["dst"]
    fileTxt = open(outputDir + "/log.txt", "a")
    fileTxt.write("treeSelector passed\n")
    fileTxt.close()


if __name__ == "__main__":

    main(options)
