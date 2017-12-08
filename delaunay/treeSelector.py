# -*- coding: utf-8 -*-


import os
from os.path import basename
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsExpression
from qgis.core import QgsFeedback, QgsField, QgsFeatureRequest
from qgis.core import QgsVectorFileWriter, QgsCoordinateReferenceSystem
from qgis.core import QgsFields, QgsWkbTypes, QgsGeometry
from qgis.core import QgsProcessingException, QgsFeature, QgsPoint
from qgis.core import QgsLineString, QgsPolygon
from qgis.PyQt.QtCore import QVariant
import processing as qgsproc
from qgis.core import QgsProcessingFeatureSourceDefinition
from qgis.core import QgsProcessingOutputLayerDefinition
from .folderManager import initialize
from qgis.analysis import QgsZonalStatistics
# TODO: replace by native QGIS c++ algo when available...
from . import voronoi


def main(options, progressBar, progressMessage):

    # Prepare the folders for outputs:
    initialize(options)

    # For direct file input
    if not os.path.isdir(options['src']):
        options['filePath'] = options['src']
        filename = basename(os.path.splitext(options['filePath'])[0])
        processing(options, filename, progressBar, progressMessage)

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


def processing(options, f, progressBar, progressMessage):
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
        treetops.changeAttributeValue(treetop.id(),
                                      treetop.fieldNameIndex('N'),
                                      treetop.id())
    treetops.commitChanges()

    outputDir = options["dst"]
    fileTxt = open(outputDir + "/log.txt", "a")
    fileTxt.write("joinattributesbylocation started\n")
    fileTxt.close()

    # Adapted from https://github.com/qgis/QGIS-Processing
    # TODO: replace by native QGIS c++ algo when available...

    crowns.dataProvider().addAttributes([QgsField(
        'tid', QVariant.Int)])
    crowns.updateFields()
    crowns.startEditing()
    fcount = crowns.featureCount()
    counter = 0
    for crown in crowns.getFeatures():
        counter += 1
        progressBar.setValue(100 + int(counter * (600 / fcount)))
        progressMessage.setText('Joining crown ' + str(counter)
                                + '/' + str(fcount))
        request = QgsFeatureRequest()
        request.setFilterRect(crown.geometry().boundingBox())
        dp = treetops.dataProvider()
        for r in dp.getFeatures(request):
            if crown.geometry().intersects(r.geometry()):
                crowns.changeAttributeValue(crown.id(),
                                            crown.fieldNameIndex('tid'),
                                            r.id())
    crowns.commitChanges()

    fileTxt = open(outputDir + "/log.txt", "a")
    fileTxt.write("delaunaytriangulation started\n")
    fileTxt.close()

    # delaunay triangulation Adapted from official Python plugin
    # TODO: replace by native QGIS c++ algo when available...

    fields = QgsFields()
    fields.append(QgsField('POINTA', QVariant.Double, '', 24, 15))
    fields.append(QgsField('POINTB', QVariant.Double, '', 24, 15))
    fields.append(QgsField('POINTC', QVariant.Double, '', 24, 15))
    crs = QgsCoordinateReferenceSystem('EPSG:2056')
    triangleFile = QgsVectorFileWriter(treetopsTrianglesPath,
                                       'utf-8',
                                       fields,
                                       QgsWkbTypes.Polygon,
                                       crs,
                                       'ESRI Shapefile')

    pts = []
    ptDict = {}
    ptNdx = -1
    c = voronoi.Context()
    features = treetops.getFeatures()
    total = 100.0 / treetops.featureCount() if treetops.featureCount() else 0
    progressMessage.setText('Starting triangulation...')
    for current, inFeat in enumerate(features):
        geom = QgsGeometry(inFeat.geometry())
        if geom.isNull():
            continue
        if geom.isMultipart():
            points = geom.asMultiPoint()
        else:
            points = [geom.asPoint()]
        for n, point in enumerate(points):
            x = point.x()
            y = point.y()
            pts.append((x, y))
            ptNdx += 1
            ptDict[ptNdx] = (inFeat.id(), n)
    progressMessage.setText('Triangulation step 1 ok')

    if len(pts) < 3:
        raise QgsProcessingException(
            'Input file should contain at least 3 points. Choose '
            'another file and try again.')

    uniqueSet = set(item for item in pts)
    ids = [pts.index(item) for item in uniqueSet]
    sl = voronoi.SiteList([voronoi.Site(*i) for i in uniqueSet])
    c.triangulate = True
    voronoi.voronoi(sl, c)
    triangles = c.triangles
    feat = QgsFeature()

    total = 100.0 / len(triangles) if triangles else 1
    for current, triangle in enumerate(triangles):

        indices = list(triangle)
        indices.append(indices[0])
        polygon = []

        attrs = []
        step = 0
        for index in indices:
            fid, n = ptDict[ids[index]]
            request = QgsFeatureRequest().setFilterFid(fid)
            inFeat = next(treetops.getFeatures(request))
            geom = QgsGeometry(inFeat.geometry())
            point = QgsPoint(geom.asPoint())

            polygon.append(point)
            if step <= 3:
                attrs.append(ids[index])
            step += 1

        linestring = QgsLineString(polygon)
        poly = QgsPolygon()
        poly.setExteriorRing(linestring)
        feat.setAttributes(attrs)
        geometry = QgsGeometry().fromWkt(poly.asWkt())
        feat.setGeometry(geometry)
        triangleFile.addFeature(feat)
    progressMessage.setText('Triangulation terminated')

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
    progressMessage.setText('Starting convexhull computing...')


if __name__ == "__main__":

    main(options)
