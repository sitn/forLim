# -*- coding: utf-8 -*-

from qgis.core import QgsVectorLayer
from . import forestDetectShape
from . import treeDetectTopsAndCrowns
from . import treeSelector
from . import convexHullComputer
from . import postProcessing


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

    ###################################
    #  0. Forest shape extraction     #
    ###################################
    # Run the general forest prior shape, contour and isolated trees extraction
    self.dlg.label_printActualProcess.setText(u'Shape detection for' +
                                              ' tile: ' + str(current_tile))
    forestDetectShape.main(options)
    self.dlg.progressBar.setValue(50)

    ###################################
    #  1. Treetops extraction         #
    ###################################
    # run Matthew Parkan's treeDetectLmax modified version
    self.dlg.label_printActualProcess.setText(u'Tree detection for' +
                                              ' tile: ' + str(current_tile))
    treeDetectTopsAndCrowns.main(options)
    self.dlg.progressBar.setValue(100)

    ###################################
    #  3. Trees selection             #
    ###################################
    # Select the trees from forest contour and isolated trees
    self.dlg.label_printActualProcess.setText(u'Tree selection for' +
                                              ' tile: ' + str(current_tile))
    treeSelector.main(options, self.dlg.progressBar,
                      self.dlg.label_printActualProcess)
    self.dlg.progressBar.setValue(800)

    ###################################
    #  4. Convex hulls computation    #
    ###################################
    # Compute for each triangle the convex hull and the coverage ratio
    self.dlg.label_printActualProcess.setText(u'Calculating convex hulls for' +
                                              ' tile: ' + str(current_tile))
    convexHullComputer.main(options)
    self.dlg.progressBar.setValue(1000)

    ###################################
    #  5. Dissolve and Clip results    #
    ###################################
    self.dlg.label_printActualProcess.setText(u'Postprocessing for' +
                                              ' tile: ' + str(current_tile))
    # postProcessing.main(options)



if __name__ == "__main__":

    main(options)
