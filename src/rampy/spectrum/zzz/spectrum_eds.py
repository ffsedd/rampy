#!/usr/bin/env python3



import os
import sys

import matplotlib.pyplot as plt
from pathlib import Path
 

import pandas as pd
import numpy as np

from qq.spectrum.spectrum import Spectrum



PEAK_LINES = pd.read_csv(Path(__file__).parent / "data/peak_lines.tsv", sep='\t', header=0, skip_blank_lines=True)
PEAK_COLORS = pd.read_csv(Path(__file__).parent / "data/peak_colors.tsv", sep='\t', header=0, skip_blank_lines=True)
PEAK_FIND_HWIDTH = .02


def main():
    f = sys.argv[1] if len(sys.argv) > 1 else "test/1.msa"
    
    s = EdsSpectrum(fpath=f)
    s.plot()
    s.plot_peaks(s.y)
    plt.show()



class EdsSpectrum(Spectrum):

    def __init__(self, fpath=None):
        super().__init__(fpath)
        self.datatype = "EDS SPECTRUM"
        self.xunits = "keV"
        self.yunits = "counts"




##=====================================================================================================


if __name__ == "__main__":

    main()




