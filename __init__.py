# -*- coding: utf-8 -*-
"""
/***************************************************************************
 forLim
                                 A QGIS plugin
 Determine forest limits
                             -------------------
        begin                : 2015-07-30
        copyright            : (C) 2015 by M.Ruferner
        email                : marc.rufener@epfl.ch
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load forLim class from file forLim.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .forLim import forLim
    return forLim(iface)
