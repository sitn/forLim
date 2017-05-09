# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:50:13 2015

@author: Nono
"""

import spatialIO as spio
from osgeo import gdal

input_filename_01 = 'C:\\Users\\Nono\\Desktop\\APoncet\\MNC Demo\\1143224.tif'

output_filename_01 = 'C:\\Users\\Nono\\Desktop\\APoncet\\raster_output\\temp\\1143224_forest_isolated.tif'

#data2, geotransform2, prj_wkt2 = spio.rasterReader(input_filename_01)

# gdal.GDT_Float32
#spio.rasterWriter(data2, output_filename_01, geotransform2, prj_wkt2, gdal.GDT_Float32)

spio.rasterWriter(forest_isolated, output_filename_01, geotransform2, prj_wkt2, gdal.GDT_Byte)


