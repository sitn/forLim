# -*- coding: utf-8 -*-
"""
Created on Thu Jan 14 16:49:24 2016

Description: conveHullComputer.py create convex hulls of treetops triangles,
    computing for each one the coverage ratio of total crown area and sorting
    these into forest and wooden pasture possible areas.
    
Usage:

Args:

Example:

"""
import os
from os.path import basename
from osgeo import ogr
from osgeo import osr

# Import custom modules

import spatialIO as spio

def main(options):
    print 'Computing forest shapes'
    
    # Prepare the folders for outputs:
    initialize(options)
    
    # For direct file input
    if os.path.isdir(options['src']) == False:
        options['filePath'] = options['src']
        filename = basename(os.path.splitext(options['filePath'])[0])
        processing(options, filename)
        
        # export raster results
#        export(options, filename, data)
        

    # For folder input
    if os.path.isdir(options['src']):
        if not options['src'].endswith('/'):
            options['src'] = options['src'] + '//' 
            
        file_list = os.listdir(options['src'])
        inputDir = options['src']
        
        # Iterate each file for processing and exports
        for k, file_list in enumerate(file_list):
            print('Processing file ' + file_list)
            options['filePath'] = inputDir + file_list
            filename = basename(os.path.splitext(options['filePath'])[0])
            
            # Process each file
            processing(options, filename)
            
            # export raster results
#        export(options, filename, data)
            
    print 'Selecting trees operation complete'
    

def initialize(options):
    '''
    Prepare the folders for outputs:
    '''
    if not os.path.isdir(options['dst']):
        os.mkdir(options['dst'])
        print 'output folder was created'
    if not options['dst'].endswith('/'):
        options['dst'] = options['dst'] + '//'
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
#    forestSelectedPath = options['dst'] + 'tif//' + filename + '_forest_selected.tif'
    
    # Load 
    # Load ogr driver to read vector files
    driver = ogr.GetDriverByName('ESRI Shapefile')
    
    # Loads treetops selection
    treetopsPath = options['dst'] + 'shp//' + filename + '_treetops_selected.shp'
    ds_treetops = driver.Open(treetopsPath, 0) # 0 means read-only. 1 means writeable.
    treetops = ds_treetops.GetLayer()
    
    # Loads crowns selection
    crownsPath = options['dst'] + 'shp//' + filename + '_crowns_selected.shp'
    ds_crowns = driver.Open(crownsPath, 0) # 0 means read-only. 1 means writeable.
    crowns = ds_crowns.GetLayer()
    
    # Loads treetops triangulation
    trianglesPath = options['dst'] + 'shp//' + filename + '_treetops_triangles.shp'
    ds_triangles = driver.Open(trianglesPath, 0) # 0 means read-only. 1 means writeable.
    triangles = ds_triangles.GetLayer()
    
    ## Create the new layers to store forest and wooden pasture convex hulls
    #
    CHsForestPath = options['dst'] + 'shp//' + filename + '_convexHulls_forest.shp'
    spio.pathChecker(CHsForestPath)
    
    CHsWoodenPasturePath = options['dst'] + 'shp//' + filename + '_convexHulls_wooden_pasture.shp'
    spio.pathChecker(CHsWoodenPasturePath)
    
    # Create the convex hulls forest data source
    ds_CHsForest = driver.CreateDataSource(CHsForestPath)
    
    # Create the convex hulls wooden pasture data source
    ds_CHsWoodenPasture = driver.CreateDataSource(CHsWoodenPasturePath)
    
    # Create Spatial Reference System
    srs = osr.SpatialReference()
    
    # Create layers
    CHsForest = ds_CHsForest.CreateLayer("forest", srs, ogr.wkbPolygon)
    CHsWoodenPasture = ds_CHsWoodenPasture.CreateLayer("wooden_pasture", srs, ogr.wkbPolygon)
    
    # Prepare fields for the forest layer
    CHsForest.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))
    #CHsForest.CreateField(ogr.FieldDefn('crownsArea', ogr.OFTInteger))
    #CHsForest.CreateField(ogr.FieldDefn('convArea', ogr.OFTReal))
    #CHsForest.CreateField(ogr.FieldDefn('CovRatio', ogr.OFTReal))
    
    # Prepare fields for the wooden pasture layer
    CHsWoodenPasture.CreateField(ogr.FieldDefn('ID', ogr.OFTInteger))
    #CHsWoodenPasture.CreateField(ogr.FieldDefn('crownsArea', ogr.OFTInteger))
    #CHsWoodenPasture.CreateField(ogr.FieldDefn('convArea', ogr.OFTReal))
    #CHsWoodenPasture.CreateField(ogr.FieldDefn('CovRatio', ogr.OFTReal))
    
    
    ## For each triangle we will compute a convex hull for each crown composing it.
    # Create the matching table for crowns
    crown_N = []
    
    for crown in crowns:
        crown_N.append(crown.GetField('N'))
    
    
    for tri in triangles:
    
        # Get the corresponding treetop
        alpha = treetops.GetFeature(int(tri.GetField('POINTA')))  
        beta = treetops.GetFeature(int(tri.GetField('POINTB')))
        gamma = treetops.GetFeature(int(tri.GetField('POINTC')))
       
        # Get the corresponding crown
        crown_alpha = crowns.GetFeature(crown_N.index(alpha.GetField('N')))
        crown_beta = crowns.GetFeature(crown_N.index(beta.GetField('N')))
        crown_gamma = crowns.GetFeature(crown_N.index(gamma.GetField('N')))
        
        # Create the triplet of crowns
        geom_collection = ogr.Geometry(ogr.wkbGeometryCollection)
        
        geom_collection.AddGeometry(crown_alpha.geometry())
        geom_collection.AddGeometry(crown_beta.geometry())
        geom_collection.AddGeometry(crown_gamma.geometry())
                
        convex_hull = geom_collection.ConvexHull()
        
        # Compute the triplet metrics and the coverage ratio
        conv_area = ogr.Geometry.Area(convex_hull)
        crowns_area = ogr.Geometry.Area(geom_collection)
        
        ratio = crowns_area / conv_area
        
        # Store the Convex Hulls in the corresponding category 
        forestRatio = 0.9
        WoodenPastureRatio = 0.3
        
        if ratio > forestRatio:
            convHull = ogr.Feature(CHsForest.GetLayerDefn())
            convHull.SetField('ID', int(tri.GetFID()))
    #        convHull.SetField('crownsArea', crowns_area)
    #        convHull.SetField('convArea', conv_area)
    #        convHull.SetField('CovRatio', ratio)
            convHull.SetGeometry(convex_hull)
            
            CHsForest.CreateFeature(convHull)
            
            convHull.Destroy()
            
        elif ratio > WoodenPastureRatio:
            convHull = ogr.Feature(CHsWoodenPasture.GetLayerDefn())
            convHull.SetField('ID', int(tri.GetFID()))
    #        convHull.SetField('crownsArea', crowns_area)
    #        convHull.SetField('convArea', conv_area)
    #        convHull.SetField('CovRatio', ratio)
            convHull.SetGeometry(convex_hull)
            
            CHsWoodenPasture.CreateFeature(convHull)
            
            convHull.Destroy()
    
    
    # Clear data sources
    ds_treetops.Destroy()
    ds_crowns.Destroy()
    ds_triangles.Destroy()
    ds_CHsForest.Destroy()
    ds_CHsWoodenPasture.Destroy()


if __name__ == "__main__":
    main(options)

__author__ = "Arnaud Poncet-Montanges, SFFN, Couvet (CH)"
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Arnaud Poncet-Montanges"
__email__ = "arnaudponcetmontanges@gmail.com"
__status__ = "Development"
