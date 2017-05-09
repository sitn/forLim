# forLim
QGIS Plugin to delimitate forested surfaces

forLim is a QGIS plugin to delimitate forested surfaces using the canopy height model (CHM) as reference information.

The parameters for this delimitation are set by default to respect the swiss federal and cantonal legislations for forest delimitations.

Note on The Code structure

forLim.py -> main qgis method, calls different methods/algorithms to process the data and deals with the graphical aspects and primary data validations

convolutionMethod.py -> main method for the convolution method, calls specific spatial scripts and give back to forLim.py the requested information

delaunayMethod.py -> main method for the delaunay method, calls specific spatial scripts and give back to forLim.py the requested information

spatialTransformations.py -> register for spatial transformations methods which will be used in conv and tri methods.

specificFunction.py -> any specific function developped for the cause which is not a "standard" spatial transformation

forLimTester.py	-> A python script to run forLim without using the plugin with hardcoded paths, ideal for debug and dev purposes
