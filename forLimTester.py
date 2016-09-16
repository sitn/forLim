# -*- coding: utf-8 -*-
"""
Created on Fri Dec 04 11:05:43 2015

Description:

forLimTester.py enables to run the forest delimitation algorithm directly from 
a python call without running QGIS. (a proper osgeo/qgis/python environment 
is required to run this) Both convolution and triangulation methods can be 
chosen.

This is dedicaced to a development/debugging purpose.

Usage:

    forLimTester.py

Example:

    Import forLimTester
    
    forLimTester

"""
# Import both methods scripts
#import convolutionMethod
import delaunayMethod

def main():
    print 'Hi, welcome to forLim in console mode'
    
    options = {}
    options['src'] = 'C:\\workspace\\input2\\'
    options['dst'] = 'C:\\workspace\\output2\\'
    options['MinHeightThres'] = 2
    options['WinRad'] = 4
    options['method'] = 2
    options['suffix'] = "cimes"
    options['MinAreaThres'] = 800
    options['MaxAreaThres'] = 2500
    options['forestRatio'] = 0.8
    options['woodenPastureRatio'] = 0.3
    options['plugin'] = False
    options['srs'] = 'PROJCS["CH1903 / LV03",GEOGCS["CH1903",DATUM["CH1903",SPHEROID["Bessel 1841",6377397.155,299.1528128,AUTHORITY["EPSG","7004"]],TOWGS84[674.374,15.056,405.346,0,0,0,0],AUTHORITY["EPSG","6149"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.01745329251994328,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4149"]],UNIT["metre",1,AUTHORITY["EPSG","9001"]],PROJECTION["Hotine_Oblique_Mercator"],PARAMETER["latitude_of_center",46.95240555555556],PARAMETER["longitude_of_center",7.439583333333333],PARAMETER["azimuth",90],PARAMETER["rectified_grid_angle",90],PARAMETER["scale_factor",1],PARAMETER["false_easting",600000],PARAMETER["false_northing",200000],AUTHORITY["EPSG","21781"],AXIS["Y",EAST],AXIS["X",NORTH]]'
    
    if options['method'] == True:
        #convolutionMethod.main(options)
        print 'You have chosen the convolution method'
        print 'It is not yet implemented for testing'
    else:
        delaunayMethod.main(options)

if __name__ == "__main__":
    main()

__author__ = "Arnaud Poncet-Montanges, SFFN, Couvet (CH)"
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Arnaud Poncet-Montanges"
__email__ = "arnaudponcetmontanges@gmail.com"
__status__ = "Development"
