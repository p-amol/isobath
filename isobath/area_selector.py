import sys

from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6.QtWidgets import QPushButton, QLabel, QComboBox, QMessageBox
from PyQt6.QtWidgets import QFormLayout, QGridLayout
from PyQt6.QtCore import pyqtSignal

import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import numpy as np
import netCDF4 as nc


def find_index(data, value):
    i = data.searchsorted(value)
    if i > (len(data) - 1):
        i = i - 1
    if i != 0:
        x2 = abs(data[i] - value)
        x1 = abs(data[i - 1] - value)
        if x2 > x1:
            i = i - 1
    return i


class WindowSelector(QDialog):
    submitted = pyqtSignal(np.ndarray, np.ndarray, np.ndarray)

    def __init__(self, filename):
        super().__init__()

        self.setWindowTitle("Area Selector")
        self.resize(960, 640)

        self.figure = plt.figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.figure)
        self.savebutton = QPushButton("Save and Continue")

        self.ds = nc.Dataset(filename)
        varlist = list(self.ds.variables.keys())

        vartext = QLabel("Variables")
        lattext = QLabel("Latitude")
        lontext = QLabel("Longitude")

        fbox = QFormLayout()
        gbox = QGridLayout()

        self.cbvar = QComboBox()
        self.cbdim1 = QComboBox()
        self.cbdim2 = QComboBox()
        self.default_text = "--Select--"
        self.cbdim1.addItem(self.default_text)
        self.cbdim2.addItem(self.default_text)
        self.cbvar.addItem(self.default_text)

        gbox.addWidget(vartext, 0, 0)
        gbox.addWidget(lontext, 0, 1)
        gbox.addWidget(lattext, 2, 1)
        for varname in varlist:
            var = self.ds[varname]
            if var.ndim > 1:
                self.cbvar.addItem(var.name)
                gbox.addWidget(self.cbvar, 1, 0)

        gbox.addWidget(self.cbdim1, 1, 1)
        gbox.addWidget(self.cbdim2, 3, 1)
        self.cbdim1.setEnabled(False)
        self.cbdim2.setEnabled(False)

        self.cbvar.currentIndexChanged.connect(self.selectvar)
        self.cbdim1.currentIndexChanged.connect(self.selectcbdim1)
        self.cbdim2.currentIndexChanged.connect(self.selectcbdim2)

        self.submit_button = QPushButton("Submit")
        fbox.addRow(gbox)
        fbox.addRow(self.submit_button)
        self.mpltool = NavigationToolbar(self.canvas, self)
        self.area_button = QPushButton("Rectangle Selector")
        self.mpltool.addWidget(self.area_button)
        fbox.addRow(self.mpltool)
        fbox.addRow(self.canvas)
        fbox.addRow(self.savebutton)

        self.area_button.clicked.connect(self.area_select_activate)
        self.submit_button.clicked.connect(self.on_submit)
        self.savebutton.clicked.connect(self.on_save)
        self.setLayout(fbox)
        self.show()

    def area_select_activate(self):
        if self.mpltool.mode == "zoom rect":
            self.mpltool.zoom()
        elif self.mpltool.mode == "pan/zoom":
            self.mpltool.pan()

    def selectcbdim1(self, i):
        if self.cbdim1.currentText() != self.default_text:
            self.x = self.ds[self.cbdim1.currentText()][:]
            self.xslice = self.x

    def selectcbdim2(self, i):
        if self.cbdim2.currentText() != self.default_text:
            self.y = self.ds[self.cbdim2.currentText()][:]
            self.yslice = self.y

    def selectvar(self, i):
        if self.cbvar.currentText() == self.default_text:
            return

        self.data = self.ds[self.cbvar.currentText()][:]
        self.dataslice = self.data

        var = self.ds[self.cbvar.currentText()]

        if var.ndim == 1 or var.ndim > 2:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Error")
            msg.setInformativeText("No. of dimension should be 2")
            msg.exec()
            return

        self.cbdim1.setEnabled(True)
        self.cbdim2.setEnabled(True)

        for i in range(var.ndim):
            self.cbdim1.addItem(var.dimensions[i])
            self.cbdim2.addItem(var.dimensions[i])

    def on_submit(self):
        if (
            self.cbvar.currentText() == self.default_text
            or self.cbdim1.currentText() == self.default_text
            or self.cbdim2.currentText() == self.default_text
        ):
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Error")
            msg.setInformativeText("Item not selected from drop list")
            msg.setWindowTitle("Error")
            msg.exec()
        else:
            self.ax1 = self.figure.add_subplot(121)
            self.ax2 = self.figure.add_subplot(122)

            self.ax1.contourf(self.x, self.y, self.data)
            self.ax1.set_title("Select the region of interest", fontsize=6)
            self.ax2.clear()
            self.ax2.contourf(self.x, self.y, self.data)
            textstr = "\n".join(
                (
                    r"Latitude: $%.1f^\circ$N, $%.1f^\circ$N" % (self.y[0], self.y[-1]),
                    r"Longitude: $%.1f^\circ$N, $%.1f^\circ$N" % (self.x[0], self.x[-1]),
                )
            )
            props = dict(boxstyle="round", facecolor="wheat", alpha=0.5)
            self.ax2.text(
                0.05,
                0.15,
                textstr,
                transform=self.ax2.transAxes,
                fontsize=6,
                verticalalignment="top",
                bbox=props,
            )

            self.canvas.draw()
            self.span = RectangleSelector(self.ax1, self.onselect, interactive=True)

    def onselect(self, eclick, erelease):
        self.yc = eclick.ydata
        self.yr = erelease.ydata
        self.xc = eclick.xdata
        self.xr = erelease.xdata

        i1 = find_index(self.x, self.xc)
        i2 = find_index(self.x, self.xr)
        j1 = find_index(self.y, self.yc)
        j2 = find_index(self.y, self.yr)

        self.xslice = self.x[i1:i2]
        self.yslice = self.y[j1:j2]
        self.dataslice = self.data[j1:j2, i1:i2]

        textstr = "\n".join(
            (
                r"Latitude: $%.1f^\circ$N, $%.1f^\circ$N" % (self.yc, self.yr),
                r"Longitude: $%.1f^\circ$N, $%.1f^\circ$N" % (self.xc, self.xr),
            )
        )
        self.ax2.clear()
        self.ax2.contourf(self.xslice, self.yslice, self.dataslice)
        props = dict(boxstyle="round", facecolor="wheat", alpha=0.5)
        self.ax2.text(
            0.05,
            0.15,
            textstr,
            transform=self.ax2.transAxes,
            fontsize=6,
            verticalalignment="top",
            bbox=props,
        )

        self.canvas.draw_idle()
        self.canvas.flush_events()

    def on_save(self):
        self.submitted.emit(self.xslice, self.yslice, self.dataslice)
        self.close()
