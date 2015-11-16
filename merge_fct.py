# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 14:54:04 2015

@author: rufenerm
"""


import os
from osgeo import ogr
from processing import runalg

def main(fileList,output,args):
    
    final_output = output
    
    #FD and PB input
    for i in ["_FD", "_PB"]:
        
        fileEndsWith = i + '.shp'
        driverName = 'ESRI Shapefile'
        geometryType = ogr.wkbPolygon
        
        a = fileEndsWith
        if fileEndsWith == "_PB.shp":
            fileEndsWith = "_PBandFD.shp"
            
        output = final_output.split(".shp")[0] + fileEndsWith
        fileEndsWith = a
        
        driver = ogr.GetDriverByName(driverName)
        out_ds = driver.CreateDataSource(output)
        
        firstFile_name = os.path.basename(fileList[0]).split('.tif')[0] + fileEndsWith
        ds = driver.Open(os.path.join(args["Path_output_tiles"], firstFile_name),0)
        lyr = ds.GetLayer()
        spatialRef = lyr.GetSpatialRef()
        out_layer = out_ds.CreateLayer(output, geom_type=geometryType, srs=spatialRef)
        
        for file in fileList:
            file = os.path.join(args["Path_output_tiles"], os.path.basename(file).split('.tif')[0] + fileEndsWith)
            ds = ogr.Open(file)
            lyr = ds.GetLayer()
            for feat in lyr:
                out_feat = ogr.Feature(out_layer.GetLayerDefn())
                out_feat.SetGeometry(feat.GetGeometryRef().Clone())
                out_layer.CreateFeature(out_feat)
                out_layer.SyncToDisk()
    
    
    #Finally make the difference between dense forest and wooded pasture and make a unique layer containing both of them
    DF_path = os.path.join(os.path.dirname(output), "merge_FD.shp")
    PB_path = os.path.join(os.path.dirname(output), "merge_PBandFD.shp")
        
    
    #Add colomn with DF or PB&DF
    driver = ogr.GetDriverByName("ESRI Shapefile")
    dic1 = {"path": DF_path, "text": "Foret dense"}
    dic2 = {"path": PB_path, "text": "Paturage boise"}
    file_list = [dic1, dic2]
    for j in file_list:
        ds = driver.Open(j["path"], 1)
        lyr = ds.GetLayer()
        field_dfn = ogr.FieldDefn("TYPE", ogr.OFTString)
        field_dfn.SetWidth(40)
        lyr.CreateField(field_dfn)
        for i in lyr:
            lyr.SetFeature(i)
            i.SetField( "TYPE", j["text"] )
            lyr.SetFeature(i)
        lyr = None
        ds.Destroy()
        
    


__Author__ = "Marc Rufener, SFFN"
__Version__ = "1.0"
__Date__ = "01.07.2015"

