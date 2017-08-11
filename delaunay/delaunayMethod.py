# -*- coding: utf-8 -*-

import forestDetectShape
import treeDetectTops
import treeDetectCrowns
import treeSelector
import convexHullComputer
import postProcessing

def main(self, options, current_tile):
    '''
    Runs a set of tasks to determine the forest delimitation using
    Delaunay's Method
    '''

    processing(self, options, current_tile)


def processing(self, options, current_tile):
    '''
    Processes the canopy height model to determine the forest delimitation
    '''
    outputDir = options["dst"]
    f = open(outputDir + "/log.txt", "w")

    ###################################
    #  0. Forest shape extraction     #
    ###################################
    # Run the general forest prior shape, contour and isolated trees extraction
    self.dlg.label_printActualProcess.setText(u'Running shape detection for' +
                                              ' tile: ' + str(current_tile))
    forestDetectShape.main(options)
    f.write("forestDetectShape passed\n")
    ###################################
    #  1. Treetops extraction         #
    ###################################
    # run Matthew Parkan's treeDetectLmax modified version
    self.dlg.label_printActualProcess.setText(u'Running tree detection for' +
                                              ' tile: ' + str(current_tile))
    treeDetectTops.main(options)
    f.write("treeDetectTops passed\n")

    ###################################
    #  2. Tree crowns extraction      #
    ###################################
    # run the treecrown detection from the previously calculated treetops
    self.dlg.label_printActualProcess.setText(u'Running crown detection for' +
                                              ' tile: ' + str(current_tile))
    treeDetectCrowns.main(options)
    f.write("treeDetectCrowns passed\n")

    ###################################
    #  3. Trees selection             #
    ###################################
    # Select the trees from forest contour and isolated trees
    self.dlg.label_printActualProcess.setText(u'Running tree selection for' +
                                              ' tile: ' + str(current_tile))
    treeSelector.main(options)
    f.write("treeSelector passed\n")

    ###################################
    #  4. Convex hulls computation    #
    ###################################
    # Compute for each triangle the convex hull and the coverage ratio
    self.dlg.label_printActualProcess.setText(u'Calculating convex hulls for' +
                                              ' tile: ' + str(current_tile))
    convexHullComputer.main(options)
    f.write("convexHullComputer passed\n")

    ###################################
    #  5. Dissolve and Clip results    #
    ###################################
    self.dlg.label_printActualProcess.setText(u'Postprocessing for' +
                                              ' tile: ' + str(current_tile))
    postProcessing.main(options)
    f.write("Posprocessing passed\n")
    f.close()


if __name__ == "__main__":

    main(options)
