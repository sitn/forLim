# -*- coding: utf-8 -*-

"""
Created on Fri Nov 27 09:23:53 2015

Author: SFFN/APM

Description:

delaunayMethod.py process a Canopy Height Model Raster Tile into forest and 
wooden pasture elements using a coverage ratio calculated on a Delaunay's
triangulation of the treetops.The result is exported as a segmented shp file.

Usage:

Args:

Example:
    
"""

# Import custom methods
import forestDetectShape
import treeDetectTops
import treeDetectCrowns
import treeSelector
import convexHullComputer


def main(options):
    '''
    Runs a set of tasks to determine the forest delimitation using
    Delaunay's Method
    '''

    print 'You have chosen the Delaunay Method'

    processing(options)

    print 'Delaunay method terminated'


def processing(options):
    '''
    Processes the canopy height model to determine the forest delimitation
    '''

    ###################################
    #  0. Forest shape extraction     #
    ###################################
    # Run the general forest prior shape, contour and isolated trees extraction 
    forestDetectShape.main(options)

    ###################################
    #  1. Treetops extraction         #
    ###################################    

    # run Matthew Parkan's treeDetectLmax modified version    
    treeDetectTops.main(options)

    ###################################
    #  2. Tree crowns extraction      #
    ###################################
    # run the treecrown detection from the previously calculated treetops
    treeDetectCrowns.main(options)

    ###################################
    #  3. Trees selection             #
    ###################################
    # Select the trees from forest contour and isolated trees
    treeSelector.main(options)

    ###################################
    #  4. Convex hulls computation    #
    ###################################
    # Compute for each triangle the convex hull and the coverage ratio
    convexHullComputer.main(options)
    

    print 'Computing convex hulls operation complete'

        # self.dlg.progressBar.reset()
    # self.messageBar.pushMessage("Delaunay!", "Fini!", QgsMessageBar.INFO, 7)
    # Clear data sources

if __name__ == "__main__":

    main(options)

__author__ = "SFFN/APM"
__license__ = "GPL"
__version__ = "0.1.0"
__status__ = "Development"
