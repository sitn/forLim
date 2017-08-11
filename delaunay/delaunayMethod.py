# -*- coding: utf-8 -*-

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

    processing(options)


def processing(options):
    '''
    Processes the canopy height model to determine the forest delimitation
    '''
    outputDir = options["dst"]
    f = open(outputDir + "/log.txt", "w")
    ###################################
    #  0. Forest shape extraction     #
    ###################################
    # Run the general forest prior shape, contour and isolated trees extraction
    forestDetectShape.main(options)
    f.write("forestDetectShape passed\n")
    ###################################
    #  1. Treetops extraction         #
    ###################################

    # run Matthew Parkan's treeDetectLmax modified version
    treeDetectTops.main(options)
    f.write("treeDetectTops passed\n")

    ###################################
    #  2. Tree crowns extraction      #
    ###################################
    # run the treecrown detection from the previously calculated treetops
    treeDetectCrowns.main(options)
    f.write("treeDetectCrowns passed\n")

    ###################################
    #  3. Trees selection             #
    ###################################
    # Select the trees from forest contour and isolated trees
    treeSelector.main(options)
    f.write("treeSelector passed\n")

    ###################################
    #  4. Convex hulls computation    #
    ###################################
    # Compute for each triangle the convex hull and the coverage ratio
    convexHullComputer.main(options)
    f.write("convexHullComputer passed\n")
    f.close()

if __name__ == "__main__":

    main(options)
