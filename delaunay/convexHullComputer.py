# -*- coding: utf-8 -*-

import os
from os.path import basename
from osgeo import ogr
from osgeo import osr
from qgis.core import QgsVectorLayer, QgsProject

# Import custom modules
from .spatialIO import pathChecker
from .folderManager import initialize


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
            processing(options, filename)


def processing(options, f):
    '''
    Select trees which are on the contour of the forest and isolated trees.
    '''
    # Export Grid contour and isolated to crowns values
    driver = ogr.GetDriverByName('ESRI Shapefile')

    # Loads treetops selection
    treetopsPath = options['dst'] + 'shp/' + f + '_treetops.shp'
    ds_treetops = driver.Open(treetopsPath, 0)
    treetops = ds_treetops.GetLayer()

    # Loads crowns selection
    crownsPath = options['dst'] + 'shp/' + f + '_crowns.shp'
    crowns = QgsVectorLayer(crownsPath, "Crows", "ogr")

    # Loads treetops triangulation
    trianglesPath = options['dst'] + 'shp/' + f + '_treetops_triangles.shp'
    triangles = QgsVectorLayer(trianglesPath, "triangles", "ogr")

    #  Create the new layers to store forest and wooden pasture convex hulls
    CHsForestPath = options['dst'] + 'shp/' + f + '_convexHulls_forest.shp'
    pathChecker(CHsForestPath)

    CHsWoodenPasturePath = options['dst'] + 'shp/' + f + \
        '_convexHulls_wooden_pasture.shp'
    pathChecker(CHsWoodenPasturePath)

    # Create the convex hulls forest data source
    ds_CHsForest = driver.CreateDataSource(CHsForestPath)

    # Create the convex hulls wooden pasture data source
    ds_CHsWoodenPasture = driver.CreateDataSource(CHsWoodenPasturePath)

    # Create Spatial Reference System
    srs = osr.SpatialReference()

    # Create layers
    CHsForest = ds_CHsForest.CreateLayer("forest", srs, ogr.wkbPolygon)
    CHsWoodenPasture = ds_CHsWoodenPasture.CreateLayer("wooden_pasture",
                                                       srs, ogr.wkbPolygon)

    # Prepare fields for the forest layer
    CHsForest.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))
    CHsForest.CreateField(ogr.FieldDefn('ratio', ogr.OFTReal))

    # Prepare fields for the wooden pasture layer
    CHsWoodenPasture.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))
    CHsWoodenPasture.CreateField(ogr.FieldDefn('ratio', ogr.OFTReal))

    # Compute the convex hull for each crown that composes a triangle

    crown_N = crowns.getValues("N", False)[0]
    del crowns
    forestRatio = options['forestRatio']
    WoodenPastureRatio = options['woodenPastureRatio']
    ds_crowns = driver.Open(crownsPath, 0)
    crowns = ds_crowns.GetLayer()
    # TODO: get rid of of python loop
    for tri in triangles.getFeatures():

        # Get the corresponding treetop
        alpha = treetops.GetFeature(int(tri['POINTA']))
        beta = treetops.GetFeature(int(tri['POINTB']))
        gamma = treetops.GetFeature(int(tri['POINTC']))
        # Get the corresponding crown
        geom_collection = ogr.Geometry(ogr.wkbGeometryCollection)
        crown_count = 0

        if alpha.GetField("N") in crown_N:
            crown_alpha = crowns.GetFeature(crown_N.index(alpha.GetField('N')))
            geom_collection.AddGeometry(crown_alpha.geometry())
            crown_count += 1

        if beta.GetField("N") in crown_N:
            crown_beta = crowns.GetFeature(crown_N.index(beta.GetField('N')))
            geom_collection.AddGeometry(crown_beta.geometry())
            crown_count += 1
        if gamma.GetField("N") in crown_N:
            crown_gamma = crowns.GetFeature(crown_N.index(gamma.GetField('N')))
            geom_collection.AddGeometry(crown_gamma.geometry())
            crown_count += 1

        if crown_count == 3:
            # Create the triplet of crowns
            convex_hull = geom_collection.ConvexHull()

            # Compute the triplet metrics and the coverage ratio
            conv_area = ogr.Geometry.Area(convex_hull)
            crowns_area = ogr.Geometry.Area(geom_collection)

            ratio = crowns_area / conv_area
            # Store the Convex Hulls in the corresponding category
            if ratio > forestRatio:
                convHull = ogr.Feature(CHsForest.GetLayerDefn())
                convHull.SetField('ID', int(tri.id()))
                convHull.SetField('ratio', ratio)
                convHull.SetGeometry(convex_hull)
                CHsForest.CreateFeature(convHull)
                convHull.Destroy()

            elif ratio > WoodenPastureRatio:
                convHull = ogr.Feature(CHsWoodenPasture.GetLayerDefn())
                convHull.SetField('ID', int(tri.id()))
                convHull.SetField('ratio', ratio)
                convHull.SetGeometry(convex_hull)
                CHsWoodenPasture.CreateFeature(convHull)
                convHull.Destroy()

    outputDir = options["dst"]
    fileTxt = open(outputDir + "/log.txt", "a")
    fileTxt.write("convexHull passed\n")
    fileTxt.close()

    forest = QgsVectorLayer(CHsForestPath, "Pastures CH", "ogr")
    crowns = QgsVectorLayer(crownsPath, "Crowns", "ogr")
    treetops = QgsVectorLayer(treetopsPath, "Forest CH", "ogr")
    triangles = QgsVectorLayer(trianglesPath, "Forest CH", "ogr")
    wooden_p = QgsVectorLayer(CHsWoodenPasturePath, "Forest CH", "ogr")
    QgsProject.instance().addMapLayer(crowns)
    QgsProject.instance().addMapLayer(treetops)
    QgsProject.instance().addMapLayer(triangles)
    QgsProject.instance().addMapLayer(forest)
    QgsProject.instance().addMapLayer(wooden_p)


if __name__ == "__main__":
    main(options)
