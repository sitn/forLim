# -*- coding: utf-8 -*-
# TODO: selective imports
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
# Initialize Qt resources from file resources.py
import resources_rc
from forLim_dialog import forLimDialog
from datetime import datetime
from osgeo import ogr
import delaunayMethod
import Overlap_fct
import merge_fct
from processing import runalg
import os
from uuid import uuid4 as uuid4


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
        global last_path_input, input_message
        last_path_input = self.dlg.LE_input.text()
        input_message = True
        QObject.connect(self.dlg.PB_input, SIGNAL("clicked()"),
                        self.select_input_files)
        QObject.connect(self.dlg.LE_input, SIGNAL("editingFinished()"),
                        self.check_input_path)

        # Output
        global last_path_output, output_message
        last_path_output = self.dlg.LE_output.text()
        output_message = True
        QObject.connect(self.dlg.PB_output, SIGNAL("clicked()"),
                        self.select_output_directory)
        QObject.connect(self.dlg.LE_output, SIGNAL("editingFinished()"),
                        self.check_output_path)

        QObject.connect(self.dlg.PB_quit, SIGNAL("clicked()"),
                        self.quit_plugin)
        QObject.connect(self.dlg.PB_ok, SIGNAL("clicked()"),
                        self.run)

        # Remove menu
        self.dlg.widget_hedges.hide()
        QObject.connect(self.dlg.CB_removeHedges, SIGNAL("clicked()"),
                        self.show_widget_hedges)
        QObject.connect(self.dlg.PB_hedges, SIGNAL("clicked()"),
                        self.hedges_path)
        QObject.connect(self.dlg.LE_hedges, SIGNAL("editingFinished()"),
                        self.check_hedges_path)

        self.dlg.widget_polygons.hide()
        QObject.connect(self.dlg.CB_removePolygons, SIGNAL("clicked()"),
                        self.show_widget_polygons)
        QObject.connect(self.dlg.PB_polygons, SIGNAL("clicked()"),
                        self.polygons_path)
        QObject.connect(self.dlg.LE_polygons, SIGNAL("editingFinished()"),
                        self.check_polygons_path)

        self.dlg.widget_polylines.hide()
        QObject.connect(self.dlg.CB_removePolylines, SIGNAL("clicked()"),
                        self.show_widget_polylines)
        QObject.connect(self.dlg.PB_polylines, SIGNAL("clicked()"),
                        self.polylines_path)
        QObject.connect(self.dlg.LE_polylines, SIGNAL("editingFinished()"),
                        self.check_polylines_path)

        # Select Method Menu
        self.dlg.radio_TR.setChecked(True)

        # Select method
        QObject.connect(self.dlg.radio_TR, SIGNAL("clicked()"),
                        self.select_tr_method)
        QObject.connect(self.dlg.radio_FC, SIGNAL("clicked()"),
                        self.select_fc_method)

        # Set current window and widget when opening the plugin
        self.dlg.tabWidget.setCurrentIndex(0)

        # Set current line edit
        self.dlg.LE_input.setFocus()

        # Check validation
        self.dlg.LE_minHeightThres.setValidator(QIntValidator())
        self.dlg.LE_maxHeightThres.setValidator(QIntValidator())
        self.dlg.LE_cwDiam.setValidator(QIntValidator())
        self.dlg.LE_DRFD.setValidator(QDoubleValidator())
        self.dlg.LE_DRPB.setValidator(QDoubleValidator())
        self.dlg.LE_minWidthThres.setValidator(QIntValidator())
        self.dlg.LE_minForSurfThres.setValidator(QIntValidator())
        self.dlg.LE_minClearingSurfThres.setValidator(QIntValidator())
        self.dlg.LE_simplifyFactor.setValidator(QDoubleValidator())
        self.dlg.LE_borderWidth.setValidator(QIntValidator())
        self.dlg.LE_gradConvDiameter.setValidator(QIntValidator())
        self.dlg.LE_minSurfBigElem.setValidator(QIntValidator())

        # set default value of minSurfBigElem
        self.dlg.LE_minSurfBigElem.setText(self.dlg.LE_minForSurfThres.text())

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
        if filenames:
            filenames2 = filenames[0]
            for f in filenames[1:]:
                filenames2 = filenames2+";"+f
            self.dlg.LE_input.setText(filenames2)
            if len(filenames) > 1:
                self.input_message()

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
            if len(files) > 1 and f_exist and input_message:
                self.input_message()

    def input_message(self):
        global input_message
        input_message = False
        QMessageBox.warning(None,
                            "Recouvrement entre les tuiles",
                            "Attention: un recouvrement d'environ 500 m " +
                            " entre les tuiles est necessaire." +
                            "\n\nSans ce recouvrement, les effets de bords " +
                            "sont importants.")

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

    def select_tr_method(self):
        if self.dlg.radio_TR.isChecked():
            print "TR method is selected"
            self.dlg.label_5.hide()
            self.dlg.LE_cwDiam.hide()
            self.dlg.label_12.hide()
            self.dlg.label_29.hide()
            self.dlg.LE_gradConvDiameter.hide()
            self.dlg.label_28.hide()

    def select_fc_method(self):
        if self.dlg.radio_FC.isChecked():
            print "FC method is selected"
            self.dlg.LE_cwDiam.show()
            self.dlg.label_5.show()
            self.dlg.label_12.show()
            self.dlg.label_29.show()
            self.dlg.LE_gradConvDiameter.show()
            self.dlg.label_28.show()

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
            if int(self.dlg.LE_minSurfBigElem.text()) < \
               int(self.dlg.LE_minForSurfThres.text()):
                error_msg += "La valeur de 'Surface min. grands elements'" + \
                             " doit etre superieure ou egale a la valeur " + \
                             "de 'Surface minimale de la foret'.\n\n"
                c = True

            if c:
                QMessageBox.warning(None, "Erreur(s)", error_msg)
            else:

                args = {
                    # Chemin d'accès au Modèle Numérique de Canopée (entrée)
                    "Path_input":
                    str(self.dlg.LE_input.text()),
                    # Chemin d'accès au dossier de sortie
                    "Path_output":
                    str(self.dlg.LE_output.text()),
                    # Hauteur de la fenêtre de lissage
                    "GradConvDiameter":
                    int(self.dlg.LE_gradConvDiameter.text()),
                    # Surface minimale des grands éléments
                    "MinAreaBigElem":
                    int(self.dlg.LE_minSurfBigElem.text()),
                    # Marge peuplement dense
                    "BorderWidth":
                    int(self.dlg.LE_borderWidth.text()),
                    # Hauteur minimale des arbres
                    "MinHeightThres":
                    int(self.dlg.LE_minHeightThres.text()),
                    # Hauteur maximale des arbres
                    "MaxHeightThres":
                    int(self.dlg.LE_maxHeightThres.text()),
                    # Diamètre de la fenêtre de convolution
                    "CW_diameter":
                    int(self.dlg.LE_cwDiam.text()),
                    # Degré de recouvrement pour la foret dense
                    "Deg_Recouv_FD":
                    float(self.dlg.LE_DRFD.text()),
                    # Degré de recouvrement pour le paturage boise
                    "Deg_Recouv_PB":
                    float(self.dlg.LE_DRPB.text()),
                    # largeur minimale forêt
                    "WidthThres":
                    int(self.dlg.LE_minWidthThres.text()),
                    # surface minimum forêt
                    "MinAreaThres":
                    int(self.dlg.LE_minForSurfThres.text()),
                    # surface minimum clairière
                    "HoleSizeThres":
                    int(self.dlg.LE_minClearingSurfThres.text()),
                    # Facteur de simplification du shapefile
                    "Simplify_factor":
                    float(self.dlg.LE_simplifyFactor.text()),
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
                }

                global driver
                driver = ogr.GetDriverByName("ESRI Shapefile")

                now_time = datetime.now()
                # USE UUID instead...
                # name = "forLim_" + str(uuid4())
                name = "forLim_" + str(now_time.date()) + "_" + \
                       str(now_time.hour) + "H" + str(now_time.minute)
                args["Path_output"] = os.path.join(args["Path_output"], name)
                os.mkdir(args["Path_output"])

                # Get file list
                path_input = args["Path_input"]
                files = args["Path_input"].split(";")
                nfiles = len(files)

                # Set default values of process bar
                self.dlg.progressBar.reset()
                self.dlg.progressBar.setMinimum(1)
                self.dlg.progressBar.setMaximum(nfiles+9)

                # Print progress on user window
                self.dlg.label_printActualProcess.setText("Processing tiles..")
                self.dlg.progressBar.setValue(1)
                QApplication.processEvents()

                ###################################
                #  A. Delaunay's triangulation    #
                ###################################
                self.iface.actionShowPythonDialog().trigger()

                if self.dlg.radio_TR.isChecked():

                    options = {
                        'WinRad': int(args['GradConvDiameter']),
                        'MinHeightThres': float(args['MinHeightThres']),
                        'src': str(args['Path_input']),
                        'dst': str(args['Path_output']),
                        'MinAreaThres': int(args['MinAreaThres']),
                        'MaxAreaThres': int(args['HoleSizeThres']),
                        'forestRatio': int(args['Deg_Recouv_FD']),
                        'woodenPastureRatio': int(args['Deg_Recouv_PB']),
                        'plugin': True,
                        'args': args
                    }

                    for f in enumerate(files):
                        self.dlg.progressBar.setValue(f[0]+2)
                        args['Path_input'] = f[1]
                        options['src'] = str(args['Path_input'])
                        delaunayMethod.main(options)

                ###################################
                #  B. Convolution Method          #
                ###################################
                else:
                    # Convolution method is chosen
                    print "you chose the moving window method"

                    # Create tiles directory
                    args["Path_output_tiles"] = \
                        os.path.join(args["Path_output"], "tiles")
                    os.mkdir(args["Path_output_tiles"])

                    # Process on each tile
                    for f in enumerate(files):
                        self.dlg.progressBar.setValue(f[0]+2)
                        QApplication.processEvents()
                        args["Path_input"] = f[1]
                        Overlap_fct.main(args)

                    # Re-set path_input for metadata
                    args["Path_input"] = path_input

                    # Set last path
                    if nfiles == 1:
                        lastPath = \
                            os.path.join(args["Path_output_tiles"],
                                         os.path.basename(args["Path_input"])
                                         .split('.tif')[0] + ".shp")

                    ####################################################
                    #  1. assembler les tuiles dans un seul shapefile  #
                    ####################################################

                    # Create merge directory
                    args["Path_output_merge"] = \
                        os.path.join(args["Path_output"], "merge")
                    os.mkdir(args["Path_output_merge"])

                    if nfiles >= 1:

                        # Print progress on user window
                        self.dlg.label_printActualProcess \
                            .setText("Merging shapefiles to one ...")
                        QApplication.processEvents()

                        # Create new files
                        merge_path = os.path.join(args["Path_output_merge"],
                                                  "merge.shp")

                        # Merge shapefiles
                        merge_fct.main(files, merge_path, args)

                    # Print progress on user window
                    self.dlg.progressBar.setValue(self.dlg
                                                  .progressBar.value() + 1)
                    QApplication.processEvents()

                    ###############################
                    #  2. dissoudre les éléments  #
                    ###############################

                    if nfiles >= 1:
                        # Print progress on user window
                        self.dlg.label_printActualProcess \
                            .setText("Dissolving merged shapefile ...")
                        QApplication.processEvents()

                        # Dissolve on FD and PB
                        file_type = ["FD", "PBandFD"]
                        for i in file_type:

                            # Create new files
                            merge_path = os.path \
                                        .join(args["Path_output_merge"],
                                              "merge_" + i + ".shp")

                            dissolve_path = os.path \
                                .join(args["Path_output_merge"],
                                      "dissolve_" + i + ".shp")

                            # Dissolve merge files
                            runalg("gdalogr:dissolvepolygons",
                                   merge_path, "geometry", "TYPE", True, False,
                                   False, False, False, "diss", [],
                                   dissolve_path)

                            if not os.path.exists(dissolve_path):
                                runalg("qgis:dissolve", merge_path, False,
                                       "TYPE", dissolve_path)

                    # Print progress on user window
                    self.dlg.progressBar \
                        .setValue(self.dlg.progressBar.value() + 1)
                    QApplication.processEvents()

                    ################################
                    #  3. simplifier la géométrie  #
                    ################################

                    # Print progress on user window
                    self.dlg.label_printActualProcess \
                        .setText("Simplifying geometry ...")
                    QApplication.processEvents()

                    f = list()
                    files = ["FD", "PBandFD"]
                    for i in files:

                        # Create new files
                        lastPath = os.path.join(args["Path_output_merge"],
                                                "dissolve_" + i + ".shp")
                        tmp_path = os.path.join(args["Path_output_merge"],
                                                "simplify_" + i + "_m2s.shp")
                        simplify_path = os.path.join(args["Path_output_merge"],
                                                     "simplify_" + i + ".shp")
                        f.append(simplify_path)

                        # Processing tools
                        runalg("qgis:simplifygeometries", lastPath,
                               args["Simplify_factor"], tmp_path)
                        runalg("qgis:multiparttosingleparts", tmp_path,
                               simplify_path)

                        # Add area field
                        ds = ogr.Open(simplify_path, 1)
                        lyr = ds.GetLayer()
                        lyr.ResetReading()

                        field_dfn = ogr.FieldDefn("AREA", ogr.OFTInteger)
                        field_dfn.SetWidth(15)
                        lyr.CreateField(field_dfn)

                        if not args["Remove_hedges"]:
                            # Remove each area < specified surface
                            for i in enumerate(lyr):
                                geom = i[1].GetGeometryRef()
                                area = geom.GetArea()
                                if area < args["MinAreaThres"]:
                                    lyr.DeleteFeature(i[0])
                                else:
                                    lyr.SetFeature(i[1])
                                    i[1].SetField("AREA", int(area))
                                    lyr.SetFeature(i[1])
                            lyr = None
                            ds.Destroy()

                    # Set last path
                    lastPath = list()
                    lastPath = f

                    # Print progress on user window
                    self.dlg.progressBar \
                        .setValue(self.dlg.progressBar.value() + 1)
                    QApplication.processEvents()

                    ###################################
                    #  4. créer le masque des tuiles  #
                    ###################################

                    # Create intermediate directory
                    args["Path_output_intermediate"] = os.path \
                        .join(args["Path_output"], "simplify")
                    os.mkdir(args["Path_output_intermediate"])

                    # If user wants to remove something from product file
                    if args["Remove_hedges"] or \
                            args["Remove_polylines"] or \
                            args["Remove_polygons"]:

                        # Print progress on user window
                        self.dlg.label_printActualProcess\
                            .setText("Create mask ...")
                        QApplication.processEvents()

                        tmp_path = os.path \
                            .join(args["Path_output_intermediate"],
                                  "mask_tiled.shp")

                        # Get projection reference
                        ds = ogr.Open(lastPath[0])
                        lyr = ds.GetLayer()
                        proj = lyr.GetSpatialRef()
                        ds.Destroy()

                        # Create temporary file containing polygons of extents
                        driver = ogr.GetDriverByName("ESRI Shapefile")

                        tmp_ds = driver.CreateDataSource(tmp_path)
                        tmp_lyr = tmp_ds.CreateLayer('mask',
                                                     geom_type=ogr.wkbPolygon,
                                                     srs=proj)

                        files = os.listdir(args["Path_output_tiles"])
                        for f in files:
                            if f.endswith(".shp"):

                                # Get extent
                                ds = driver \
                                    .Open(os.path
                                          .join(args["Path_output_tiles"], f))
                                lyr = ds.GetLayer()
                                xmin, xmax, ymin, ymax = lyr.GetExtent()
                                # Write new polygon
                                # Create ring
                                ring = ogr.Geometry(ogr.wkbLinearRing)
                                ring.AddPoint(xmin, ymin)
                                ring.AddPoint(xmin, ymax)
                                ring.AddPoint(xmax, ymax)
                                ring.AddPoint(xmax, ymin)
                                ring.AddPoint(xmin, ymin)

                                # Create polygon
                                poly = ogr.Geometry(ogr.wkbPolygon)
                                poly.AddGeometry(ring)

                                feature = ogr.Feature(tmp_lyr.GetLayerDefn())
                                feature.SetGeometry(poly)
                                tmp_lyr.CreateFeature(feature)

                        # Close tmp data source
                        tmp_ds.Destroy()

                        # Create new files
                        mask_path = os.path \
                            .join(args["Path_output_intermediate"],
                                  "mask.shp")

                        # Processing tools
                        runalg("qgis:dissolve", tmp_path, True, None,
                               mask_path)

                    # Print progress on user window
                    self.dlg.progressBar \
                        .setValue(self.dlg.progressBar.value() + 1)
                    QApplication.processEvents()

                    ############################
                    #  5. supprimer les haies  #
                    ############################

                    file_type = ["FD", "PB"]
                    if args["Remove_hedges"]:

                        # Print progress on user window
                        self.dlg.label_printActualProcess \
                            .setText("Removing hedges layer ...")
                        QApplication.processEvents()

                        # Print progress on user window
                        args["HedgesBuffer"] = str(self.dlg.CBox_hedgesBuffer
                                                   .currentText())

                        # Create new files
                        maskHedges_path = os.path.join(args["Path_output_intermediate"], "mask_hedges.shp")
                        bufferHedges_path = os.path.join(args["Path_output_intermediate"], "buffer_hedges.shp")

                        # Processing tools
                        runalg("qgis:clip", args["Path_hedges"],
                               mask_path, maskHedges_path)
                        runalg("qgis:variabledistancebuffer", maskHedges_path,
                               args["HedgesBuffer"], 5, True,
                               bufferHedges_path)

                        new_file = list()
                        for f in enumerate(lastPath):

                            # Create new files
                            tmp_path = os.path.join(args["Path_output_intermediate"], "simplify_hedges_" + file_type[f[0]] + "_tmp.shp")
                            simplifyHedges_path = os.path.join(args["Path_output_intermediate"], "simplify_hedges_" + file_type[f[0]] + ".shp")
                            new_file.append(simplifyHedges_path)

                            # Processing tools
                            runalg("qgis:difference", f[1], bufferHedges_path,
                                   tmp_path)
                            runalg("qgis:multiparttosingleparts", tmp_path,
                                   simplifyHedges_path)

                            # Add area field
                            ds = ogr.Open(simplifyHedges_path, 1)
                            lyr = ds.GetLayer()
                            lyr.ResetReading()

                            # Remove each area < specified surface
                            for i in enumerate(lyr):
                                geom = i[1].GetGeometryRef()
                                area = geom.GetArea()
                                if area < args["MinAreaThres"]:
                                    lyr.DeleteFeature(i[0])
                                else:
                                    lyr.SetFeature(i[1])
                                    i[1].SetField("AREA", int(area))
                                    lyr.SetFeature(i[1])
                            lyr = None
                            ds.Destroy()

                        # Set last path
                        lastPath = list()
                        lastPath = new_file

                    # Print progress on user window
                    self.dlg.progressBar.setValue(self.dlg.progressBar.value()+1)
                    QApplication.processEvents()

                    ################################
                    #  6. supprimer des polygones  #
                    ################################

                    if args["Remove_polygons"]:

                        # Print progress on user window
                        self.dlg.label_printActualProcess.setText("Removing polygons layer ...")
                        QApplication.processEvents()

                        # Create new files
                        maskPolygons_path = (os.path.join(args["Path_output_intermediate"], "mask_polygons.shp"))

                        # Processing tools
                        runalg("qgis:clip", args["Path_polygons"], mask_path, maskPolygons_path)

                        new_files = list()
                        for i in enumerate(lastPath):
                            # Create new files
                            simplifyPolygons_path = os.path.join(args["Path_output_intermediate"], "simplify_polygons_" + file_type[i[0]] + ".shp")
                            new_files.append(simplifyPolygons_path)

                            # Processing tools
                            runalg("qgis:difference", i[1], maskPolygons_path, simplifyPolygons_path)

                        #Set last path
                        lastPath = new_files

                    # Print progress on user window
                    self.dlg.progressBar.setValue(self.dlg.progressBar.value() + 1)
                    QApplication.processEvents()

                    #################################
                    #  7. supprimer des polylignes  #
                    #################################

                    if args["Remove_polylines"]:

                        # Print progress on user window
                        self.dlg.label_printActualProcess \
                            .setText("Removing polylines layer ...")
                        QApplication.processEvents()

                        # Get attribut column name
                        args["PolylinesBuffer"] = str(self.dlg
                                                      .CBox_polylinesBuffer
                                                      .currentText())

                        # Create new files
                        maskPolylines_path = os.path.join(args["Path_output_intermediate"], "mask_polylines.shp")
                        bufferPolylines_path = os.path.join(args["Path_output_intermediate"], "buffer_polylines.shp")

                        # Processing tools
                        runalg("qgis:clip", args["Path_polylines"], mask_path,
                               maskPolylines_path)
                        runalg("qgis:variabledistancebuffer",
                               maskPolylines_path, args["PolylinesBuffer"],
                               5, True, bufferPolylines_path)

                        new_files = list()
                        for i in enumerate(lastPath):

                            # Create new files
                            simplifyPolylines_path = os.path.join(args["Path_output_intermediate"], "simplify_polylines_" + file_type[i[0]] + ".shp")
                            new_files.append(simplifyPolylines_path)

                            # Processing tools
                            runalg("qgis:difference", i[1],
                                   bufferPolylines_path,
                                   simplifyPolylines_path)

                        # set last path
                        lastPath = new_files

                    # Print progress on user window
                    self.dlg.progressBar.setValue(self.dlg.progressBar
                                                  .value() + 1)
                    QApplication.processEvents()

                    ####################################################
                    #  8. séparer le paturage boisé et la forêt dense  #
                    ####################################################

                    # Create new files
                    simplify_hedges_PB_path = os.path.join(args["Path_output_intermediate"], "simplify_PB_withoutFD.shp")
                    singleParts_PB_path = os.path.join(args["Path_output_intermediate"], "simplify_PB_m2s.shp")
                    simplifyHedges_path = os.path.join(args["Path_output_intermediate"], "simplify.shp")

                    # Processing tools
                    runalg("qgis:difference", lastPath[1], lastPath[0],
                           simplify_hedges_PB_path)
                    runalg("qgis:multiparttosingleparts",
                           simplify_hedges_PB_path, singleParts_PB_path)
                    runalg("qgis:mergevectorlayers", lastPath[0],
                           singleParts_PB_path, simplifyHedges_path)

                    # Set last path
                    lastPath = simplifyHedges_path

                    ###################################
                    #  9. enregistrer fichier forest  #
                    ###################################

                    # Create forest shp
                    forest_path = os.path.join(args["Path_output"],
                                               "forest")

                    # Copy last path and delete FID and AREA columns
                    runalg("qgis:deletecolumn", lastPath, "AREA",
                           forest_path + ".shp")

                    # Add area field
                    ds = driver.Open(forest_path + ".shp", 1)
                    layer = ds.GetLayer()
                    for i in enumerate(layer):
                        geom = i[1].GetGeometryRef()
                        area = geom.GetArea()
                        i[1].SetField("AREA", int(area))
                        layer.SetFeature(i[1])
                    ds.Destroy()

                    # Add vector layer to map canevas
                    self.dlg.label_printActualProcess \
                        .setText("Add vector layer to map canevas ...")
                    QApplication.processEvents()

                    forest_path = os.path.join(args["Path_output"],
                                               "forest.shp")
                    if args["AddLayer"]:
                        vlayer = QgsVectorLayer(forest_path, "forest", "ogr")
                        QgsMapLayerRegistry.instance().addMapLayer(vlayer)

                        forest = {
                            'Foret dense':      (QColor(0, 100, 0),
                                                 'Foret dense'),
                            'Paturage boise':   (QColor(0, 160, 0),
                                                 'Paturage boise')
                        }

                        # create a category for each item in animals
                        categories = []
                        for forest_name, (color, label) in forest.items():
                            symbol = QgsSymbolV2.defaultSymbol(vlayer
                                                               .geometryType())
                            symbol.setColor(QColor(color))
                            category = QgsRendererCategoryV2(forest_name,
                                                             symbol, label)
                            categories.append(category)

                        # create the renderer and assign it to a layer
                        expression = "TYPE"
                        renderer = QgsCategorizedSymbolRendererV2(expression,
                                                                  categories)
                        vlayer.setRendererV2(renderer)

                    # Print progress on user window
                    self.dlg.progressBar.setValue(self.dlg.progressBar
                                                  .maximum())
                    self.dlg.label_printActualProcess.setText("Done.")
                    QApplication.processEvents()

                    # Write metadata
                    infos_path = os.path.join(args["Path_output"],
                                              "metadata.txt")
                    file = open(infos_path, "w")
                    file.write("Processed: " + str(now_time.date()) +
                               "\n\n###############\n\n")
                    for arg_i in args:
                        file.write(arg_i + " : " + str(args[arg_i]) + "\n")
                    file.close()
