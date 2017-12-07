# forLim
* A QGIS Plugin to delimitate forested surfaces from a digital canopy model (raster)*

## Requirements
0. QGIS 3+ with scipy dependency installed.
1. On windows, this may or may not mean that QGIS has to be install with OSGEO4W

## Installation

1. Clone this repository on your machine
2. Link the new directory with the QGIS plugin directory or copy everything in the plugin directory

## Features

forLim is a QGIS plugin to delimitate forested surfaces using the canopy height model (CHM) as reference information.

The parameters for this delimitation are set by default to respect the swiss federal and cantonal legislations for forest delimitations.

At this stage, only the first step, that is the delimitation of the forest zones using the convolution method is fully operational on large datasets.
the other steps of the Delaunay method to filter the forest zones' borders might crash due on memory issue with large datasets

Postprocessing will be required in most cases, depending of the canopy model. For instance, buildings, electric cables, ... need to be removed

## Todos

Remove python loops doing processing algorithms that will soon have a native implementation within QGIS 3. Only steps fro Delaunay methods completion are concerned

