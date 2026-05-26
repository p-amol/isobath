import sys
import os
from PyQt6.QtWidgets import (
    QDialog,
    QApplication,
    QPushButton,
    QMainWindow,
    QFileDialog,
    QDockWidget,
    QWidget,
    QLabel,
    QComboBox,
    QMessageBox,
    QRadioButton,
    QFormLayout,
    QVBoxLayout,
    QSpinBox,
    QDoubleSpinBox,
)
from PyQt6.QtCore import pyqtSignal, Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.path import Path

import numpy as np
import netCDF4 as nc
from scipy import stats
from .area_selector import WindowSelector
from .lasso_selector import SelectFromCollection

PACKAGE_DIR = os.path.dirname(__file__)


class NavigateWidget(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle("Navigation Settings")

        fbox = QFormLayout()

        text1 = QLabel("Contour Depth")
        fbox.addRow(text1)

        self.sbd = QDoubleSpinBox()
        self.sbd.setMinimum(-5000)
        self.sbd.setMaximum(5000)
        fbox.addRow(self.sbd)

        text2 = QLabel("Contour Number")
        fbox.addRow(text2)
        self.sb = QSpinBox()
        self.sb.setMinimum(0)
        self.sb.setMaximum(10)
        fbox.addRow(self.sb)

        text3 = QLabel("Coordinate Axis")
        fbox.addRow(text3)
        self.rb1 = QRadioButton("Latitude")
        self.rb1.setChecked(True)
        self.rb2 = QRadioButton("Longitude")
        fbox.addRow(self.rb1)
        fbox.addRow(self.rb2)

        text4 = QLabel("Start Point")
        fbox.addRow(text4)
        self.start_point = QDoubleSpinBox()
        self.start_point.setMinimum(-180)
        self.start_point.setMaximum(180)
        fbox.addRow(self.start_point)

        text5 = QLabel("End Point")
        fbox.addRow(text5)
        self.end_point = QDoubleSpinBox()
        self.end_point.setMinimum(-180)
        self.end_point.setMaximum(180)
        fbox.addRow(self.end_point)

        text6 = QLabel("Average Interval")
        fbox.addRow(text6)
        self.avg_interval = QDoubleSpinBox()
        self.avg_interval.setMinimum(0)
        self.avg_interval.setMaximum(30)
        fbox.addRow(self.avg_interval)

        text7 = QLabel("Coordinate Interval")
        fbox.addRow(text7)
        self.coord_interval = QDoubleSpinBox()
        self.coord_interval.setMinimum(0)
        self.coord_interval.setMaximum(30)
        fbox.addRow(self.coord_interval)

        self.anglebutton = QPushButton("Compute Angle")
        fbox.addRow(self.anglebutton)

        self.setLayout(fbox)


class MainWindow(QMainWindow):
    def __init__(self):
        """MainWindow constructor."""
        super().__init__()

        self.setWindowTitle("Slope Calculator")
        self.resize(1280, 640)

        self.index = 0
        self.error = False

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.mpltool = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout()
        layout.addWidget(self.mpltool)
        layout.addWidget(self.canvas)

        widget = QWidget()
        widget.setLayout(layout)

        self.setCentralWidget(widget)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        self.open_menu = file_menu.addAction("Open", self.open_file_button)
        self.open_menu.setShortcut("Ctrl+O")
        file_menu.addSeparator()

        self.save_menu = file_menu.addAction("Save", self.save_button)
        self.save_menu.setShortcut("Ctrl+S")
        self.save_menu.setEnabled(False)
        self.saveas_menu = file_menu.addAction("Save As", self.saveas_button)
        self.saveas_menu.setShortcut("Ctrl+Shift+S")
        self.saveas_menu.setEnabled(False)
        self.quit_menu = file_menu.addAction("Quit", self.close)
        self.quit_menu.setShortcut("Ctrl+Q")

        dockwidget = QDockWidget("Settings")
        self.nav = NavigateWidget()
        dockwidget.setWidget(self.nav)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dockwidget)

        view_menu = menubar.addMenu("View")
        self.dock_menu = view_menu.addAction("Settings", dockwidget.show)

        self.contour_index = -1
        self.nav.sb.valueChanged.connect(self.contindexchange)
        self.contour = 0
        self.nav.sbd.valueChanged.connect(self.contchange)
        self.nav.anglebutton.clicked.connect(self.compute_button)
        self.nav.rb1.clicked.connect(self.radio_button)
        self.nav.rb2.clicked.connect(self.radio_button)

        toolbar = self.addToolBar("File Operations")
        self.open = toolbar.addAction("Open", self.open_file_button)
        toolbar.addAction("Sample File", self.sample_file_button)
        self.save = toolbar.addAction("Save", self.save_button)
        self.saveas = toolbar.addAction("Save As", self.saveas_button)

        toolbar2 = self.addToolBar("Compute Navigation")
        self.prev = toolbar2.addAction("Previous", self.prev_button)
        self.next = toolbar2.addAction("Next", self.next_button)

        toolbar3 = self.addToolBar("Selection Tools")
        self.lasso = toolbar3.addAction("Lasso", self.lasso_activate)
        self.undo = toolbar3.addAction("Undo", self.undo_button)
        self.delete = toolbar3.addAction("Delete", self.delete_button)

        self.disable_buttons()

    def lasso_activate(self):
        if self.mpltool.mode == "zoom rect":
            self.mpltool.zoom()
        elif self.mpltool.mode == "pan/zoom":
            self.mpltool.pan()

        if hasattr(self, "selector") and self.selector:
            if hasattr(self, "pts") and self.pts:
                self.selector = SelectFromCollection(self.ax2, self.pts)
                self.canvas.draw_idle()

    def contchange(self):
        self.contour = self.nav.sbd.value()
        self.plot_data()

    def set_contnumber(self):
        self.nav.sb.setMinimum(0)
        self.nav.sb.setMaximum(self.cslen)

    def contindexchange(self):
        self.contour_index = self.nav.sb.value() - 1
        self.plot_data()

    def radio_button(self):
        if self.nav.rb1.isChecked():
            self.nav.start_point.setValue(min(self.yin))
            self.nav.end_point.setValue(max(self.yin))
        elif self.nav.rb2.isChecked():
            self.nav.start_point.setValue(min(self.xin))
            self.nav.end_point.setValue(max(self.xin))

    def compute_button(self):
        self.zstart = self.nav.start_point.value()
        self.zend = self.nav.end_point.value()
        self.avginterval = self.nav.avg_interval.value()
        self.zinterval = self.nav.coord_interval.value()

        self.index = 1
        self.lastindex = int(np.ceil((self.zend - self.zstart) / self.zinterval))

        self.pick_interval()

        if self.error:
            self.error = False
            return

        self.plot_slope()

        self.next.setEnabled(True)
        self.lasso.setEnabled(True)
        self.delete.setEnabled(True)
        self.undo.setEnabled(True)
        self.save.setEnabled(True)
        self.saveas.setEnabled(True)
        self.save_menu.setEnabled(True)
        self.saveas_menu.setEnabled(True)

    def plot_data(self):
        if self.index == 0:
            self.figure.clear()
            self.ax1 = self.figure.add_subplot(121)
            self.ax2 = self.figure.add_subplot(122)
            self.ax1.axis("off")

        self.ax1.cla()
        self.ax1.contourf(self.xin, self.yin, self.datain)
        cs = self.ax1.contour(self.xin, self.yin, self.datain, [self.contour])

        paths = []
        for path in cs.get_paths():
            vertices = path.vertices
            codes = path.codes

            current_path_vertices = []
            current_path_codes = []

            for i, (vert, code) in enumerate(zip(vertices, codes)):
                if code == Path.MOVETO and current_path_vertices:
                    paths.append(
                        Path(
                            np.array(current_path_vertices),
                            np.array(current_path_codes),
                        )
                    )
                    current_path_vertices = [vert]
                    current_path_codes = [code]
                else:
                    current_path_vertices.append(vert)
                    current_path_codes.append(code)

            if current_path_vertices:
                paths.append(
                    Path(np.array(current_path_vertices), np.array(current_path_codes))
                )

        self.cslen = len(paths)
        self.set_contnumber()

        if self.cslen == 0:
            QMessageBox.warning(
                self, "No Contour Found", f"No contour found for depth {self.contour}."
            )
            self.xcoord = np.array([])
            self.ycoord = np.array([])
            self.canvas.draw_idle()
            return

        if self.contour_index == -1:
            if paths:
                p = max(paths, key=len)
                v = p.vertices
            else:
                QMessageBox.warning(
                    self,
                    "No Contour Data",
                    "No contour paths were generated. Please check your data or contour settings.",
                )
                self.xcoord = np.array([])
                self.ycoord = np.array([])
                self.canvas.draw_idle()
                return
        else:
            try:
                p = paths[self.contour_index]
                v = p.vertices
            except IndexError:
                QMessageBox.warning(
                    self,
                    "Invalid Contour Index",
                    f"Contour index {self.contour_index + 1} is out of bounds. Please choose a valid number between 1 and {self.cslen}.",
                )
                self.xcoord = np.array([])
                self.ycoord = np.array([])
                self.canvas.draw_idle()
                return

        self.xcoord = v[:, 0]
        self.ycoord = v[:, 1]

        if self.index == 0:
            self.ax1.plot(
                self.xcoord, self.ycoord, color="red", label=f"Contour {self.contour}"
            )
        else:
            self.ax1.plot(
                self.xcoord, self.ycoord, color="red", label=f"Contour {self.contour}"
            )
            if hasattr(self, "xx") and hasattr(self, "yy") and self.xx.size > 0:
                self.ax1.plot(
                    self.xx,
                    self.yy,
                    "o",
                    color="blue",
                    markersize=3,
                    label="Selected Points",
                )

        self.ax1.legend()
        self.canvas.draw_idle()

    def pick_interval(self):
        z = self.zstart
        dz = self.avginterval

        z1 = z + dz / 2.0
        z2 = z - dz / 2.0

        self.x1 = np.array([])
        self.y1 = np.array([])

        if self.nav.rb1.isChecked():
            coord_to_check = self.ycoord
        elif self.nav.rb2.isChecked():
            coord_to_check = self.xcoord
        else:
            self.error = True
            return

        mask = (coord_to_check > z2) & (coord_to_check < z1)
        self.x1 = self.xcoord[mask]
        self.y1 = self.ycoord[mask]

        if self.x1.size < 2 or self.y1.size < 2:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setText("Error")
            msg.setInformativeText(
                f"No enough points found in the interval {z2:.2f} to {z1:.2f} degrees for {z:.2f} degree."
            )
            msg.setWindowTitle("Error")
            msg.exec()
            self.error = True

    def plot_slope(self):
        if self.x1.size < 2:
            QMessageBox.warning(
                self,
                "Insufficient Data",
                "Cannot compute slope with less than 2 points.",
            )
            return

        slope, intercept, r_value, p_value, std_err = stats.linregress(self.x1, self.y1)
        ymodel = slope * self.x1 + intercept
        angle = np.arctan(slope) * 180 / np.pi
        if angle < 0:
            angle = 180 + angle

        if self.index == 1:
            self.output = np.zeros((int(self.lastindex) + 1, 2))

        i = self.index - 1
        if 0 <= i < self.output.shape[0]:
            self.output[i, :] = self.zstart, angle
        else:
            QMessageBox.warning(
                self,
                "Computation Error",
                "Output array index out of bounds. This indicates a potential issue with interval calculation.",
            )
            return

        self.ax2.cla()
        textstr = "\n".join(
            (
                r"Coordinate: $%.1f^\circ$" % (self.zstart,),
                r"Angle: $%.1f^\circ$" % (angle,),
                r"R-squared: $%.3f$" % (r_value**2,),
            )
        )

        props = dict(boxstyle="round", facecolor="wheat", alpha=0.5)

        self.xx = self.x1
        self.yy = self.y1
        self.plot_data()

        self.pts = self.ax2.scatter(
            self.x1, self.y1, color="k", label="Selected Points"
        )
        self.ax2.plot(self.x1, ymodel, color="C1", label="Linear Regression")
        self.ax2.text(
            0.05,
            0.95,
            textstr,
            transform=self.ax2.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=props,
        )
        self.ax2.set_xlabel(
            self.xin.name if hasattr(self.xin, "name") else "X-coordinate"
        )
        self.ax2.set_ylabel(
            self.yin.name if hasattr(self.yin, "name") else "Y-coordinate"
        )
        self.ax2.set_title(f"Slope for {self.zstart:.1f} degrees")
        self.ax2.legend()
        self.selector = SelectFromCollection(self.ax2, self.pts)
        self.canvas.draw_idle()

    def get_data(self, x_data, y_data, data_values):
        self.xin = x_data
        self.yin = y_data
        self.datain = data_values

        min_y = min(y_data) if y_data.size > 0 else -180
        max_y = max(y_data) if y_data.size > 0 else 180

        self.nav.start_point.setValue(min_y)
        self.nav.end_point.setValue(max_y)
        self.nav.avg_interval.setValue(1)
        self.nav.coord_interval.setValue(1)

        self.nav.rb1.setChecked(True)

        self.activate_buttons()

        self.index = 0
        self.plot_data()

    def disable_buttons(self):
        self.next.setEnabled(False)
        self.prev.setEnabled(False)
        self.lasso.setEnabled(False)
        self.undo.setEnabled(False)
        self.delete.setEnabled(False)
        self.save.setEnabled(False)
        self.saveas.setEnabled(False)
        self.save_menu.setEnabled(False)
        self.saveas_menu.setEnabled(False)

        self.nav.anglebutton.setEnabled(False)
        self.nav.start_point.setEnabled(False)
        self.nav.end_point.setEnabled(False)
        self.nav.avg_interval.setEnabled(False)
        self.nav.coord_interval.setEnabled(False)
        self.nav.sbd.setEnabled(False)
        self.nav.sb.setEnabled(False)
        self.nav.rb1.setEnabled(False)
        self.nav.rb2.setEnabled(False)

    def activate_buttons(self):
        self.nav.anglebutton.setEnabled(True)
        self.nav.start_point.setEnabled(True)
        self.nav.end_point.setEnabled(True)
        self.nav.avg_interval.setEnabled(True)
        self.nav.coord_interval.setEnabled(True)
        self.nav.sbd.setEnabled(True)
        self.nav.sb.setEnabled(True)
        self.nav.rb1.setEnabled(True)
        self.nav.rb2.setEnabled(True)

    def open_file_button(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            caption="Open NetCDF file",
            filter="NetCDF Files (*.nc *.cdf);;All Files (*)",
        )
        if not filename:
            return

        self.filewindow = WindowSelector(filename)
        self.filewindow.submitted.connect(self.get_data)
        self.filewindow.show()

    def sample_file_button(self):
        sample_path = os.path.join(PACKAGE_DIR, "sample.nc")
        try:
            ds = nc.Dataset(sample_path)
            self.xin = ds["X7208_7808151_541"][:]
            self.yin = ds["Y2703_3604211_632"][:]
            self.datain = ds["DEPTH"][:]
            ds.close()
        except FileNotFoundError:
            QMessageBox.critical(
                self,
                "File Error",
                "sample.nc not found. Please ensure it's in the package directory.",
            )
            self.disable_buttons()
            return
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Sample",
                f"An error occurred loading sample.nc: {e}",
            )
            self.disable_buttons()
            return

        self.contour_index = -1
        self.plot_data()

        self.nav.start_point.setValue(8)
        self.nav.end_point.setValue(20)
        self.nav.avg_interval.setValue(1)
        self.nav.coord_interval.setValue(1)

        self.activate_buttons()

    def save_button(self):
        if not hasattr(self, "output") or self.output is None or self.output.size == 0:
            QMessageBox.warning(
                self,
                "No Data to Save",
                "There is no data to save. Please compute angles first.",
            )
            return

        outfile = "file_coord_angle.txt"
        try:
            np.savetxt(outfile, (self.output[0 : self.index]), fmt="%4.4f")
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("Information")
            msg.setInformativeText(f"Saved to {outfile}")
            msg.setWindowTitle("File Saved")
            msg.exec()
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"An error occurred while saving the file: {e}"
            )

    def saveas_button(self):
        if not hasattr(self, "output") or self.output is None or self.output.size == 0:
            QMessageBox.warning(
                self,
                "No Data to Save",
                "There is no data to save. Please compute angles first.",
            )
            return

        outfile, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            filter="Text Files (*.txt);;Data Files (*.dat);;All Files (*)",
        )
        if not outfile:
            return
        try:
            np.savetxt(outfile, (self.output[0 : self.index]), fmt="%4.4f")
            QMessageBox.information(
                self, "File Saved", f"Successfully saved to {outfile}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"An error occurred while saving the file: {e}"
            )

    def prev_button(self):
        if self.zstart - self.zinterval >= self.nav.start_point.minimum():
            self.index -= 1
            self.zstart = self.zstart - self.zinterval
            if self.index >= 1:
                self.pick_interval()
                if not self.error:
                    self.plot_slope()
                else:
                    self.next.setEnabled(True)
                    self.error = False
            else:
                self.prev.setEnabled(False)
                if self.index == 0:
                    self.next.setEnabled(True)
        else:
            self.prev.setEnabled(False)
            QMessageBox.information(self, "Navigation Limit", "Cannot go further back.")

    def next_button(self):
        if self.zstart + self.zinterval <= self.nav.end_point.value():
            self.index += 1
            self.zstart = self.zstart + self.zinterval
            if self.index > 1:
                self.prev.setEnabled(True)

            self.pick_interval()
            if not self.error:
                self.plot_slope()
            else:
                self.prev.setEnabled(True)
                self.error = False
        else:
            self.next.setEnabled(False)
            QMessageBox.information(
                self, "Navigation Limit", "Cannot go further forward."
            )
            return

    def undo_button(self):
        if hasattr(self, "xx") and hasattr(self, "yy") and self.xx.size > 0:
            self.x1 = self.xx
            self.y1 = self.yy
            self.plot_slope()
        else:
            QMessageBox.information(
                self,
                "Undo",
                "No previous points to undo to or no computation has been done yet.",
            )

    def delete_button(self):
        if (
            hasattr(self, "selector")
            and self.selector
            and self.selector.ind is not None
            and len(self.selector.ind) > 0
        ):
            self.x1 = np.delete(self.x1, self.selector.ind)
            self.y1 = np.delete(self.y1, self.selector.ind)
            self.ax2.set_title("")
            self.canvas.draw_idle()
            self.plot_slope()
        else:
            QMessageBox.information(
                self, "Delete", "No points selected by lasso to delete."
            )


def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
