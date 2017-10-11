# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIntValidator, QDoubleValidator, QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QApplication, QMessageBox

from qgis.core import QgsVectorLayer, QgsRasterLayer
from qgis.core import QgsCoordinateReferenceSystem
from qgis.gui import QgsMessageBar

# QgsMapLayerRegistry => Adapt for this change
# Initialize Qt resources from file resources.py
from . import resources
from .forLim_dialog import forLimDialog
from datetime import datetime
from osgeo import ogr
from .delaunay import delaunayMethod
from processing import *
import os
from uuid import uuid4 as uuid4
from .delaunay.postProcessing import merge, clip


class forLim:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'forLim_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = forLimDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&forLim')
        self.toolbar = self.iface.addToolBar(u'forLim')
        self.toolbar.setObjectName(u'forLim')

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('forLim', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
            parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        self.messageBar = self.iface.messageBar()

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        # Input
        global last_path_input
        last_path_input = self.dlg.LE_input.text()

        self.dlg.PB_input.clicked.connect(self.select_input_files)
        self.dlg.LE_input.editingFinished.connect(self.check_input_path)

        # Output
        global last_path_output, output_message
        last_path_output = self.dlg.LE_output.text()
        output_message = True

        self.dlg.PB_output.clicked.connect(self.select_output_directory)
        self.dlg.LE_output.editingFinished.connect(self.check_output_path)
        self.dlg.PB_quit.clicked.connect(self.quit_plugin)
        self.dlg.PB_ok.clicked.connect(self.run)

        # Remove menu
        self.dlg.widget_hedges.hide()
        self.dlg.CB_removeHedges.clicked.connect(self.show_widget_hedges)
        self.dlg.PB_hedges.clicked.connect(self.hedges_path)
        self.dlg.LE_hedges.editingFinished.connect(self.check_hedges_path)
        self.dlg.widget_polygons.hide()
        self.dlg.CB_removePolygons.clicked.connect(self.show_widget_polygons)
        self.dlg.PB_polygons.clicked.connect(self.polygons_path)
        self.dlg.LE_polygons.editingFinished.connect(self.check_polygons_path)
        self.dlg.widget_polylines.hide()
        self.dlg.CB_removePolylines.clicked.connect(self.show_widget_polylines)
        self.dlg.PB_polylines.clicked.connect(self.polylines_path)
        self.dlg.LE_polylines.editingFinished \
            .connect(self.check_polylines_path)
        # Set current window and widget when opening the plugin
        self.dlg.tabWidget.setCurrentIndex(0)

        # Set current line edit
        self.dlg.LE_input.setFocus()

        # Check validation
        self.dlg.LE_minHeightThres.setValidator(QIntValidator())
        self.dlg.LE_maxHeightThres.setValidator(QIntValidator())
        self.dlg.LE_DRFD.setValidator(QDoubleValidator())
        self.dlg.LE_DRPB.setValidator(QDoubleValidator())
        self.dlg.txt_triangle_peri.setValidator(QDoubleValidator())
        self.dlg.LE_minWidthThres.setValidator(QIntValidator())
        self.dlg.LE_minForSurfThres.setValidator(QIntValidator())
        self.dlg.LE_minClearingSurfThres.setValidator(QIntValidator())
        self.dlg.LE_gradConvDiameter.setValidator(QIntValidator())

        # Set add result to canevas as default
        self.dlg.CB_addLayer.setCheckState(2)

        # set progress bar settings
        self.dlg.progressBar.setMinimum(0)
        self.dlg.progressBar.setValue(0)

        icon_path = ':/plugins/forLim/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'forLim'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def select_input_files(self):
        filenames = QFileDialog.getOpenFileNames(filter="Images (*.tif)")
        files_to_process = ''
        print(filenames)
        print(filenames[0])
        print(filenames[0][0])
        if filenames:
            for f in filenames[0]:
                files_to_process += f + ';'
            files_to_process = files_to_process[:-1]
            self.dlg.LE_input.setText(files_to_process)

    def check_input_path(self):
        global last_path_input
        path_input = self.dlg.LE_input.text()
        if path_input and not path_input == last_path_input:
            last_path_input = path_input
            files = path_input.split(";")
            f_exist = True
            for f in files:
                if not os.path.exists(f):
                    self.messageBar.pushMessage("Input"
                                                "Le champ '" + f +
                                                "' n'existe pas.",
                                                QgsMessageBar.CRITICAL, 7)
                    f_exist = False

    def select_output_directory(self):
        self.dlg.LE_output.setFocus()
        folder = QFileDialog.getExistingDirectory()
        if folder:
            if not os.path.exists(folder):
                self.messageBar.pushMessage("Output",
                                            "Le champ 'Dossier Destination '" +
                                            "est invalide.",
                                            QgsMessageBar.CRITICAL, 7)
            else:
                self.dlg.LE_output.setText(folder)

    def check_output_path(self):
        path_output = self.dlg.LE_output.text()
        global last_path_output
        if not path_output == last_path_output:
            if os.path.exists(path_output):
                last_path_output = path_output
            elif path_output:
                self.messageBar.pushMessage("Attention",
                                            "Le champ 'Dossier Destination' " +
                                            "est invalide.",
                                            QgsMessageBar.CRITICAL, 7)

    def show_widget_hedges(self):
        if self.dlg.CB_removeHedges.isChecked():
            self.dlg.widget_hedges.show()
            self.dlg.LE_hedges.setFocus()
        if not self.dlg.CB_removeHedges.isChecked():
            self.dlg.widget_hedges.hide()

    def hedges_path(self):
        geom = QFileDialog.getOpenFileName(filter="*.shp")
        if geom:
            ds = ogr.Open(geom)
            layer = ds.GetLayer()
            if layer.GetGeomType() != 2:
                self.messageBar.pushMessage("Fichier haies",
                                            "Le fichier specifie ne " +
                                            "contient pas de polyligne.",
                                            QgsMessageBar.CRITICAL, 7)
            else:
                self.dlg.LE_hedges.setText(geom)
                self.check_hedges_path()

    def check_hedges_path(self):
        path_hedges = self.dlg.LE_hedges.text()
        if path_hedges:
            if os.path.exists(path_hedges) and \
               path_hedges.split(".")[-1] == "shp":
                source = ogr.Open(path_hedges, 0)
                layer = source.GetLayer()
                layer_defn = layer.GetLayerDefn()

                f_names = []
                type_names = ["Real", "Integer"]
                for i in range(layer_defn.GetFieldCount()):
                    if layer_defn.GetFieldDefn(i).GetTypeName() in type_names:
                        f_names.append(layer_defn.GetFieldDefn(i).GetName())

                # define Combo Box for attribute choice
                self.dlg.CBox_hedgesBuffer.clear()
                self.dlg.CBox_hedgesBuffer.addItems(field_names)
            else:
                self.dlg.CBox_hedgesBuffer.clear()
                self.messageBar.pushMessage("Fichier haies",
                                            "Le fichier specifie n'existe pas",
                                            QgsMessageBar.CRITICAL, 7)
        else:
            self.dlg.CBox_hedgesBuffer.clear()

    def show_widget_polygons(self):
        if self.dlg.CB_removePolygons.isChecked():
            self.dlg.widget_polygons.show()
            self.dlg.LE_polygons.setFocus()
        else:
            self.dlg.widget_polygons.hide()

    def polygons_path(self):
        geom = QFileDialog.getOpenFileName(filter="*.shp")
        if geom:
            ds = ogr.Open(geom)
            layer = ds.GetLayer()
            if layer.GetGeomType() != 3:
                self.messageBar.pushMessage("Fichier polygones",
                                            "Le fichier specifie ne contient" +
                                            " pas de polygone.",
                                            QgsMessageBar.CRITICAL, 7)
            else:
                self.dlg.LE_polygons.setText(geom)

    def check_polygons_path(self):
        path = self.dlg.LE_polygons.text()
        if path:
            if not os.path.exists(path):
                self.messageBar.pushMessage("Fichier polygones",
                                            "Le fichier specifie" +
                                            "n'existe pas.",
                                            QgsMessageBar.CRITICAL, 7)

    def show_widget_polylines(self):
        if self.dlg.CB_removePolylines.isChecked():
            self.dlg.widget_polylines.show()
            self.dlg.LE_polylines.setFocus()
        else:
            self.dlg.widget_polylines.hide()

    def polylines_path(self):
        geom = QFileDialog.getOpenFileName(filter="*.shp")
        if geom:
            ds = ogr.Open(geom)
            layer = ds.GetLayer()
            if layer.GetGeomType() != 2:
                self.messageBar.pushMessage("Fichier polylignes",
                                            "Le fichier specifie ne contient" +
                                            " pas de polyligne.",
                                            QgsMessageBar.CRITICAL, 7)
            else:
                self.dlg.LE_polylines.setText(geom)
                self.check_polylines_path()

    def check_polylines_path(self):
        path_polylines = self.dlg.LE_polylines.text()
        if path_polylines:
            if os.path.exists(path_polylines) and \
               path_polylines.split(".")[-1] == "shp":
                source = ogr.Open(path_polylines, 0)
                layer = source.GetLayer()
                layer_defn = layer.GetLayerDefn()

                f_names = []
                type_names = ["Real", "Integer"]
                for i in range(layer_defn.GetFieldCount()):
                    if layer_defn.GetFieldDefn(i).GetTypeName() in type_names:
                        f_names.append(layer_defn.GetFieldDefn(i).GetName())

                self.dlg.CBox_polylinesBuffer.clear()
                self.dlg.CBox_polylinesBuffer.addItems(field_names)
            else:
                self.dlg.CBox_polylinesBuffer.clear()
                self.messageBar.pushMessage("Fichier polylignes",
                                            "Le fichier specifie " +
                                            " n'existe pas.",
                                            QgsMessageBar.CRITICAL, 7)
        else:
            self.dlg.CBox_polylinesBuffer.clear()

    def quit_plugin(self):
        self.dlg.close()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&forLim'),
                action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        ok_result = self.dlg.exec_()
        # See if OK was pressed
        if ok_result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            c = False
            error_msg = str()

            if not self.dlg.LE_input.text():
                error_msg = error_msg + "Ajouter un chemin d'acces " + \
                            "au(x) fichier(s) source.\n\n"
                c = True
            if not self.dlg.LE_output.text():
                error_msg = error_msg + "Ajouter un chemin d'acces pour " + \
                            "le dossier de destination ou seront déposes " + \
                            "les fichiers produits.\n\n"
                c = True
            if self.dlg.CB_removeHedges.isChecked() and not \
               self.dlg.LE_hedges.text():
                error_msg = error_msg + "Completer ou fermer " + \
                            "la rubrique des haies.\n\n"
                c = True
            if self.dlg.CB_removePolylines.isChecked() and not \
               self.dlg.LE_polylines.text():
                error_msg = error_msg + "Completer ou fermer la " + \
                            "rubrique des polylignes.\n\n"
                c = True
            if self.dlg.CB_removePolygons.isChecked() and not \
               self.dlg.LE_polygons.text():
                error_msg = error_msg + "Completer ou fermer la " + \
                            "rubrique des polygones.\n\n"
                c = True

            if c:
                QMessageBox.warning(None, "Erreur(s)", error_msg)
            else:

                options = {
                    # Chemin d'accès au Modèle Numérique de Canopée (entrée)
                    "Path_input":
                    str(self.dlg.LE_input.text()),
                    # Chemin d'accès au dossier de sortie
                    "Path_output":
                    str(self.dlg.LE_output.text()),
                    # Hauteur de la fenêtre de lissage
                    "WinRad":
                    int(self.dlg.LE_gradConvDiameter.text()),
                    # Hauteur minimale des arbres
                    "MinHeightThres":
                    int(self.dlg.LE_minHeightThres.text()),
                    # Hauteur maximale des arbres
                    "MaxHeightThres":
                    int(self.dlg.LE_maxHeightThres.text()),
                    # Degré de recouvrement pour la foret dense
                    "forestRatio":
                    float(self.dlg.LE_DRFD.text()),
                    # Degré de recouvrement pour le paturage boise
                    "woodenPastureRatio":
                    float(self.dlg.LE_DRPB.text()),
                    # largeur minimale forêt
                    "WidthThres":
                    int(self.dlg.LE_minWidthThres.text()),
                    # surface minimum forêt
                    "MinAreaThres":
                    int(self.dlg.LE_minForSurfThres.text()),
                    # surface minimum clairière
                    "MaxAreaThres":
                    int(self.dlg.LE_minClearingSurfThres.text()),
                    # Périmètre max des triangles de Delaunay
                    "MaxTrianglePerimeter":
                    float(self.dlg.txt_triangle_peri.text()),
                    # Ajouter le shapefile forêt
                    "AddLayer":
                    bool(self.dlg.CB_addLayer.isChecked()),
                    "Remove_polygons":
                    bool(self.dlg.CB_removePolygons.isChecked()),
                    # Supprimer les zones urbanisées
                    "Path_polygons":
                    str(self.dlg.LE_polygons.text()),
                    "Remove_polylines":
                    bool(self.dlg.CB_removePolylines.isChecked()),
                    # Supprimer les lignes à haute tension
                    "Path_polylines":
                    str(self.dlg.LE_polylines.text()),
                    # Supprimer les haies
                    "Remove_hedges":
                    bool(self.dlg.CB_removeHedges.isChecked()),
                    "Path_hedges":
                    str(self.dlg.LE_hedges.text()),
                    "plugin":
                    True
                }

                # Set default values of process bar
                self.dlg.progressBar.reset()
                self.dlg.progressBar.setMinimum(0)
                self.dlg.progressBar.setMaximum(1000)

                # Print progress on user window
                self.dlg.label_printActualProcess.setText("ForLim...")
                self.dlg.progressBar.setValue(0)
                QApplication.processEvents()

                now_time = datetime.now()

                name = "forLim_" + str(uuid4())
                options["Path_output"] = \
                    os.path.join(options["Path_output"], name)
                os.mkdir(options["Path_output"])

                # Get file list
                path_input = options["Path_input"]
                files = options["Path_input"].split(";")
                nfiles = len(files)

                ###################################
                #  Delaunay's triangulation    #
                ###################################

                options['src'] = str(options['Path_input'])
                options['dst'] = str(options['Path_output'])
                f = open(options['Path_output'] + '/forlim_medatata.txt', 'w')
                f.write(str(options))
                f.close()

                i = 0
                for f in enumerate(files):
                    i += 1
                    self.dlg.label_printActualProcess \
                        .setText("Processing tile " + str(i) + "/" +
                                 str(len((files))))
                    options['Path_input'] = f[1]
                    options['src'] = str(options['Path_input'])
                    delaunayMethod.main(self, options, i)
                # # Merge tiles
                # if i > 1:
                #     merge(options, '_forest_zones.shp')
                #     merge(options, '_ch_wpastures_dissolved.shp')
                #     merge(options, '_ch_forest_dissolved.shp')
                #
                # # remove wooden pastures from forest zones
                # clip(options)

                # Merge convexhull calculation results
                self.dlg.label_printActualProcess.setText(u'Calcul terminé')
                self.iface.mapCanvas().zoomToFullExtent()
