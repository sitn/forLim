# -*- coding: utf-8 -*-

"""
Created on Fri Nov 27 09:23:53 2015

Author: Arnaud Poncet-Montanges, SFFN, Couvet (CH)

Description:

delaunayMethod.py process a Canopy Height Model Raster Tile into forest and 
wooden pasture elements using a coverage ratio calculated on a Delaunay's
triangulation of the treetops.The result is exported as a segmented shp file.

Usage:

    delaunayMethod.main(Args)

Args:

    Suffix: each output file name is named according to the input file name 
        with a _suffix added 
    WinRad: radius of the local maxima search window in pixels
    MinHeightThres: minimal height threshold in the units of the canopy 
        height model
    src: the path to a single image file (OGR compatible format, check 
        http://www.gdal.org/formats_list.html) or to folder containing 
        several images
    dst: the path to the destination folder

Example:

    delaunayMethod.main(Args)
    
"""

import treeDetectTops
import treeDetectCrowns

def main(options):
    '''
    Runs a set of tasks to determine the forest delimitation using
    Delaunay's Method
    '''
    
    print 'You have chosen the Delaunay Method'
    
    processing(options)
    
    print 'Done'


def processing(options):
    '''
    Processes the canopy height model to determine the forest delimitation
    '''

    print 'Computing treetops'
    
    ###################################
    #  0. Treetops Extraction         #
    ###################################    

    # run Matthew Parkan's treeDetectLmax modified version    

    treeDetectTops.main(options)

    ###################################
    #  1. Tree Crowns Extraction      #
    ###################################
    
    # run the treecrown detection from the previously calculated treetops
#    treeDetectCrowns.main(options)
    
    ###################################
    #  2. Mathematical Morph          #
    ###################################

    
if __name__ == "__main__":
    
    main(options)
    

__author__ = "Arnaud Poncet-Montanges, SFFN, Couvet (CH)"
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Arnaud Poncet-Montanges"
__email__ = "arnaudponcetmontanges@gmail.com"
__status__ = "Development"
