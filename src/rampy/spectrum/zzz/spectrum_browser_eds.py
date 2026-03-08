#!/usr/bin/env python3

from pathlib import Path
from collections import deque
import logging
import numpy as np
import pandas as pd
from natsort import natsorted
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator, AutoMinorLocator

from qq.spectrum.spectrum import Spectrum, PEAK_LINES, PEAK_COLORS, PEAK_FIND_HWIDTH
SPECTRUM_EXTS = (".msa", ".jdx", ".spx", ".csv")

ICO = Path(__file__).with_suffix(".png")




import sys
import matplotlib
matplotlib.use('Qt5Agg')


from PyQt5 import QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar




XLIM = (0,11)
# ~ PEAK_LINES = pd.read_csv(Path(__file__).parent / "peak_lines.tsv", sep='\t', header=0, skip_blank_lines=True)
# ~ PEAK_COLORS = pd.read_csv(Path(__file__).parent / "peak_colors.tsv", sep='\t', header=0, skip_blank_lines=True)
# ~ PEAK_FIND_HWIDTH = .02

ANOT_FONTSIZE=6
# ~ print(PEAK_COLORS)
# ~ print(PEAK_LINES)

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, browser, *args, **kwargs):

        super(MainWindow, self).__init__(*args, **kwargs)

        self.canvas = MplCanvas(self, width=30, height=15, dpi=100)
        self.setCentralWidget(self.canvas)

        self.browser = browser
        self.spectrum = browser.spectrum

        # hotkeys
        QtWidgets.QShortcut(QtGui.QKeySequence("left"), self , self.prev)
        QtWidgets.QShortcut(QtGui.QKeySequence("right"), self , self.next)
        QtWidgets.QShortcut(QtGui.QKeySequence("up"), self , self.first)
        QtWidgets.QShortcut(QtGui.QKeySequence("down"), self , self.last)
        
        # icon
        self.setWindowIcon(QtGui.QIcon(str(ICO)))

        self.update_plot()

        self.show()

        # Create toolbar, passing canvas as first parament, parent (self, the MainWindow) as second.
        toolbar = NavigationToolbar(self.canvas, self)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)

        # Create a placeholder widget to hold our toolbar and canvas.
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        self.show()


    def update_title(self):
        self.setWindowTitle(str(self.browser.path))


    def plot_peaks(self, elements=None):

        df = self.browser.spectrum.df
        elements = elements or pd.unique(PEAK_LINES.Element)
        for element in elements:
            p = PEAK_LINES.loc[PEAK_LINES["Element"] == element].reset_index()
            x, y = p["Energy"].to_list(), p["Intensity"].to_list()
            name = p["Line"].to_list()
            try:
                color = PEAK_COLORS[PEAK_COLORS.Element == element].iloc[0,1]
            except IndexError:
                color = "grey"
            # ~ print(    p["Energy"], p["Intensity"])
            max_peak = p["Energy"].iloc[p["Intensity"].idxmax()]


            roi = max_peak - PEAK_FIND_HWIDTH, max_peak + PEAK_FIND_HWIDTH
            # ~ print(df)
            hei = df.loc[(df.index > roi[0]) & (df.index < roi[1]), "y"].max()
            # ~ print(f'{element}, {x}, {y}, {color}, max peak: {max_peak} hei: {hei}')
            y = np.array(y) # predefined peak heights
            y /= y.max() # normalize
            y *= hei # fit max intensity

            ax = self.canvas.axes
            ax.bar(x, y,  width=1e-6, bottom=0,  linewidth=1, edgecolor=color)

            for i, (px, py) in enumerate(zip(x, y)):
                # ~ print(i, x,y)
                ax.annotate(f'{element} {name[i]}', xy=(px, py), xytext=(px + 0, py + 200), fontsize=ANOT_FONTSIZE, color=color, rotation=90)


    def plot_lines(self, x, y, max_peak=0, color="grey"):

        df = self.browser.spectrum.df
        roi = x[max_peak] - .04, x[max_peak] + .04
        hei = df.loc[(df.index > roi[0]) & (df.index < roi[1]), "Intensity"].max()
        y = np.array(y) * hei

        ax = self.canvas.axes
        ax.bar(x, y,  width=1e-6, bottom=0,  linewidth=1, edgecolor=color)


    def update_plot(self):

        spectrum = self.browser.spectrum

        ax = self.canvas.axes
        x = spectrum.df.index
        y = spectrum.df.y
        d2y = spectrum.df.d2y
        l = str(spectrum.fpath.resolve())

        ax.cla()  # Clear the canvas.

        self.plot_peaks()

        ax.plot(x, y, label=l)  # spectrum
        ax.plot(x, d2y, alpha=.3) # 2nd derivative
        ax.text(.5,1.02,l, transform = ax.transAxes)  # title

        p = spectrum.get_peaks(y)
        ax.scatter(p.index, p, s=1)
        for px, py in zip(p.index.tolist(),p.tolist()):  # peak y labels
            ax.annotate(px, xy=(px, py), xytext=(px + 0, py * 1), fontsize=6)

        p = spectrum.get_peaks(d2y)
        ax.scatter(p.index, p, s=1)
        for px, py in zip(p.index.tolist(),p.tolist()):  # peak d2y labels
            ax.annotate(px, xy=(px, py), xytext=(px + 0, py * 1), fontsize=6)

        # ~ ax.set_xlim(*XLIM)
        # ~ ax.xaxis.set_major_locator(MultipleLocator(1))
        # ~ ax.xaxis.set_minor_locator(MultipleLocator(.1))
        # ~ ax.yaxis.set_major_locator(MultipleLocator(5000))
        ax.xaxis.set_minor_locator(AutoMinorLocator())
        ax.yaxis.set_minor_locator(AutoMinorLocator())
        self.canvas.draw()

        self.update_title()

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

    def __init__(self, indir="."):

        self.dir = Path(indir).resolve()
        logging.debug(self.dir)
        self.reset()
        self.load(0)

    def reset(self):
        self.fs = natsorted([f for f in self.dir.glob("*.*") if f.suffix.lower() in SPECTRUM_EXTS], key=str)
        print(self.dir, self.fs)
        self.fpaths = deque(self.fs)
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
        self.spectrum = Spectrum(self.path)

if __name__ == "__main__":

    logging.basicConfig(format='!%(levelno)s [%(module)10s%(lineno)4d]	%(message)s',  
                        level=10 )

    indir = sys.argv[1] if len(sys.argv) > 1 else "test"
    print("spectrum browser started in:", indir)
    browser = Browser(indir)
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow(browser)
    app.exec_()

