# -*- coding: utf-8 -*-
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIntValidator, QDoubleValidator, QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QApplication, QMessageBox

from qgis.core import QgsVectorLayer, QgsRasterLayer
from qgis.core import QgsCoordinateReferenceSystem
from qgis.gui import QgsMessageBar

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
            'forLim_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '5.6.0':
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
        self.dlg.show()
        ok_result = self.dlg.exec_()
        if ok_result:

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
                    # Calcul selon la convolution uniquement
                    "onlyConvolution":
                    self.dlg.chkConvolution.isChecked(),
                    "AddLayer":
                    self.dlg.CB_addLayer.isChecked(),
                    "plugin": True
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

                self.dlg.label_printActualProcess.setText(u'Calcul terminé')
                self.iface.mapCanvas().zoomToFullExtent()
