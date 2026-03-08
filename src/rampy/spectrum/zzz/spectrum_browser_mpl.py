#!/usr/bin/env python3

import sys
from pathlib import Path
from collections import deque
import logging
import numpy as np
import pandas as pd
from natsort import natsorted

from qq.spectrum.spectrum import Spectrum

import matplotlib
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, AutoMinorLocator
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from PyQt5 import QtWidgets, QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import AutoMinorLocator

matplotlib.use('Qt5Agg')
logging.getLogger('matplotlib.font_manager').disabled = True

from PyQt5 import QtGui, QtWidgets

SPECTRUM_EXTS = (".msa", ".jdx", ".spx")

ICO = Path(__file__).with_suffix(".png")



class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=None, height=None, dpi=None):
        self.fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, browser, *args, **kwargs):

        super(MainWindow, self).__init__(*args, **kwargs)

        self.canvas = MplCanvas(self, width=30, height=15, dpi=100)
        self.setCentralWidget(self.canvas)

        self.browser = browser
        self.spectrum = browser.spectrum
        self.xlim = [None,None]
        self.ylim = [None,None]

        # hotkeys
        QtWidgets.QShortcut(QtGui.QKeySequence("left"), self , self.prev)
        QtWidgets.QShortcut(QtGui.QKeySequence("right"), self , self.next)
        QtWidgets.QShortcut(QtGui.QKeySequence("up"), self , self.first)
        QtWidgets.QShortcut(QtGui.QKeySequence("down"), self , self.last)
        
        # icon
        self.setWindowIcon(QtGui.QIcon(str(ICO)))

        self.update_plot()

        # Create toolbar, passing canvas as first parament, parent (self, the MainWindow) as second.
        toolbar = NavigationToolbar(self.canvas, self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)

        # Create a placeholder widget to hold our toolbar and canvas.
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)



        # Create input boxes for x and y axis limits
        self.xlim1_input = QtWidgets.QLineEdit(self)
        self.xlim2_input = QtWidgets.QLineEdit(self)
        self.ylim1_input = QtWidgets.QLineEdit(self)
        self.ylim2_input = QtWidgets.QLineEdit(self)

        # Create labels for the input boxes
        xlim_label = QtWidgets.QLabel('X Limit:', self)
        ylim_label = QtWidgets.QLabel('Y Limit:', self)

        # Create a button to apply the limits
        apply_button = QtWidgets.QPushButton('Apply Limits', self)
        apply_button.clicked.connect(self.applylims)

        # Layout for input boxes and button
        limit_layout = QtWidgets.QHBoxLayout()
        limit_layout.addWidget(xlim_label)
        limit_layout.addWidget(self.xlim1_input)
        limit_layout.addWidget(self.xlim2_input)
        limit_layout.addWidget(ylim_label)
        limit_layout.addWidget(self.ylim1_input)
        limit_layout.addWidget(self.ylim2_input)
        limit_layout.addWidget(apply_button)

        # Create toolbar, passing canvas as the first parameter and the parent (self, the MainWindow) as the second.
        toolbar = NavigationToolbar(self.canvas, self)

        # Create a vertical layout to hold the toolbar, input boxes, and canvas
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addLayout(limit_layout)
        layout.addWidget(self.canvas)

        # Create a placeholder widget to hold our toolbar, input boxes, and canvas.
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.show()





    def applylims(self):
        # Get the user input for x and y limits from the input boxes
        xlim1 = self.xlim1_input.text()
        xlim2 = self.xlim2_input.text()
        ylim1 = self.ylim1_input.text()
        ylim2 = self.ylim2_input.text()
        ax = self.canvas.axes
        try:
            xlim1 = float(xlim1) if xlim1 else None
            xlim2 = float(xlim2) if xlim2 else None
            self.xlim = [xlim1,xlim2]
            ylim1 = float(ylim1) if ylim1 else None
            ylim2 = float(ylim2) if ylim2 else None
            self.ylim = [ylim1,ylim2]
            self.update_plot()

        except ValueError:
            QtWidgets.QMessageBox.warning(self, 'Invalid Input', 'Please enter valid numeric values for X and Y limits.')



    def update_plot(self):

        spectrum = self.browser.spectrum
        print(spectrum.path)
        ax = self.canvas.axes
        x = spectrum.data.index
        y = spectrum.data.y

        ax.cla()  # Clear the canvas.

        ax.plot(x, y, label=spectrum.path.name)  # spectrum
        ax.legend()
        # ~ p = spectrum.get_peaks(y)
        # ~ ax.scatter(p.index, p, s=1)
        spectrum.plot_peaks(ax=ax)

        ax.set_xlim(self.xlim)
        ax.set_ylim(self.ylim)
        # ~ ax.xaxis.set_major_locator(MultipleLocator(1))
        # ~ ax.xaxis.set_minor_locator(MultipleLocator(.1))
        # ~ ax.yaxis.set_major_locator(MultipleLocator(5000))
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        
        self.canvas.draw()
        
        # update window title
        self.setWindowTitle(str(self.browser.path))

    def prev(self):
        self.browser.prev()
        self.update_plot()

    def next(self):
        self.browser.next()
        self.update_plot()

    def first(self):
        self.browser.first()
        self.update_plot()

    def last(self):
        self.browser.last()
        self.update_plot()



class Browser:
    ''' Cycle through files in directory, load current spectrum. '''

    def __init__(self, src="."):
        self.fpath = None
        if src.is_file():
            self.dir = src.parent
            self.fpath = src
        else:    
            self.dir = Path(src)
        logging.debug(self.dir)
        self.reset()
        self.load(0)

    def reset(self):
        
        self.files = natsorted([f for f in self.dir.glob("*.*") if f.suffix.lower() in (SPECTRUM_EXTS)], key=str)
        print(self.files)
        assert self.files, f"No files in: {self.dir}"
        self.fpaths = deque(self.files)
        print(self.fpath)
        if self.fpath and self.fpath in self.files:
            while not self.fpaths[0] == self.fpath:
                print (self.fpaths[0], self.fpath)
                self.fpaths.rotate(1)
            
        logging.debug(f"fpaths: {self.fpaths}")

    def first(self):
        self.reset()
        self.load(0)

    def last(self):
        self.reset()
        self.load(-1)

    def next(self):
        self.fpaths.rotate(-1)
        self.load(0)

    def prev(self):
        self.fpaths.rotate(1)
        self.load(0)

    def load(self, no):
        self.path = self.fpaths[no]
        self.spectrum = Spectrum.create(self.path)

if __name__ == "__main__":

    logging.basicConfig(format='!%(levelno)s [%(module)10s%(lineno)4d]	%(message)s',  
                        level=10 )

    src = sys.argv[1] if len(sys.argv) > 1 else Path()
    src = Path(src)
    browser = Browser(src)
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow(browser)
    app.exec_()

