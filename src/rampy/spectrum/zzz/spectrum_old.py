#!/usr/bin/env python3



import os
import sys

import matplotlib.pyplot as plt
from pathlib import Path
 

import pandas as pd
import numpy as np

from qq.spectrum.spectrum_parser import SpectrumParser

from qq.ntool.detect_peaks import detect_peaks
from qq.ntool.baseline import baseline_correction



PEAK_LINES = pd.read_csv(Path(__file__).parent / "data/peak_lines.tsv", sep='\t', header=0, skip_blank_lines=True)
PEAK_COLORS = pd.read_csv(Path(__file__).parent / "data/peak_colors.tsv", sep='\t', header=0, skip_blank_lines=True)
PEAK_FIND_HWIDTH = .02


def main():
    f = sys.argv[1] if len(sys.argv) > 1 else "test/1.msa"
    
    s = Spectrum(fpath=f)
    print(s.df, s.df.max())
    # print(s.x)
    # print(s.y)
    s.plot()
    s.plot_peaks(s.y)
    plt.show()


def test_show_spectra():
    indir = "."
    fps = sorted(list(Path(indir).glob("*.msa")))
    print("infiles: ", fps)

    # create objects
    spectra = [ Spectrum(fpath=fp) for fp in fps ]
    plt.figure(figsize=(20,8))
    # plot all
    for s in spectra:
        s.datatype = "EDS SPECTRUM"
        s.xunits = "keV"
        s.yunits = "counts"
#        s.info()

        s.plot(ysquared=True, dy=True, ylog=False, xlim=(0,15), peaks=True)
        s.plot_peak_lines()

    plt.show()





class Spectrum:
    """

    Attributes:
    
    title
    fpath
    
    df - pandas dataframe  
    x = df index, 
    y = df column 0
    
    """

    def __init__(self, fpath=None, title='', smooth=0):
        """    """
        self.fpath = fpath
        self.title = title
        self.df = pd.DataFrame(index={"x":None}, columns=["y"])
        
        self.parser = SpectrumParser(self)  # parse file > df
        
        self.dataprocessing = ''
        self.datatype = ''
        self.date = ''
        self.end = ''
        self.jcampdx = ''
        self.longdate = ''
        self.origin = ''
        self.owner = ''
        self.time = ''
        self.samplingprocedure = ''
        self.spectrometerdatasystem = ''
        
        self.xfactor = 1.0
        self.xunits = None
        self.yfactor = 1.0
        self.yunits = None

        self.at_perc = None
        self.mass_perc = None
        
        self.smooth = smooth
        
        if fpath and os.path.isfile(fpath):
            self.load(fpath)
        else:
            print("no valid fpath", fpath)

    @property
    def x(self):
        return self.df.index.to_numpy()
    
    @x.setter
    def x(self, x):
        self.df.index = x
        
    @property
    def y(self):
        return self.df.iloc[:,0]

    @y.setter
    def y(self, y):
        self.df.iloc[:,0] = y

    def load(self, fpath):
        # ~ print("...load file")
        fp = Path(fpath)
        self.fpath = fp
        self.title = fp.stem

        if self.fpath.suffix.lower() == ".spx":
            self.parser.loadspx(fp)        
        elif self.fpath.suffix.lower() == ".jdx":
            self.parser.loadjdx(fp)
        elif self.fpath.suffix.lower() == ".msa":
            self.parser.loadmsa(fp)
        elif self.fpath.suffix.lower() == ".xls":
            self.parser.loadxls(fp)
        else:
            self.parser.loadtxt(fp)

        self.df.columns = ["y"]
        # ~ self.process()

    def process(self):
        ''' Baseline correction, smoothing, calculate derivatives'''

        # ~ print("...start processing")
        self.baseline_correction()
        
        # smooth
        if self.smooth:
            self.df['yraw'] = self.df['y'].copy()
            self.df['y'] = self.df.y.rolling(self.smooth, center=True).mean()
 
        
        self.df['dy'] = np.gradient(self.df.y)
        self.df.dy = self.df.dy.rolling(self.smooth, center=True).mean()
        
        self.df['d2y'] = np.gradient(-self.df.dy)
        self.df.d2y = self.df.d2y.rolling(self.smooth, center=True).mean()
        
        self.df.d2y[self.df.d2y<0] = 0  # drop negative values
        self.df.d2y *= self.df.y.max() / self.df.d2y.max() / 2   # normalize d2y
        # ~ print(self.df.y.max())
        # ~ print(self.df.d2y.max())
        # ~ print("...done")

    def baseline_correction(self, niter=10, lam=1e8, p=0.05):
#        self.df.y = baseline_correction(self.df.y, niter=10, lam=2e7, p=0.05)
        self.df.y = baseline_correction(self.df.y, niter=niter, lam=lam, p=p)

    def smooth(self, window=3):
        self.df.y = self.df.y.rolling(window, center=True).mean()

    def get_peaks(self, series):
        ''' Find peaks in series (x as index)
        Return series (x as index)
        '''
        peak_idx = detect_peaks(series, mph=series.max()/40, edge='both', mpd=10, kpsh=True,  threshold=series.max()/10000)
        peaks = series.iloc[peak_idx]
        # ~ print(peaks)
        return peaks


    def plot_peaks(self, series, ax = None, **kw):
        if ax is None:
            ax = plt.gca()
        p = self.get_peaks(series)
        ax.scatter(p.index, p, s=1, **kw)
        for px, py in zip(p.index.tolist(),p.tolist()):
            ax.annotate(round(px,2), xy=(px, py), xytext=(px, py), fontsize=6)



    def plot_peak_lines(self, elements=None, fontsize=8, peak_colors_df=PEAK_COLORS):

        df = self.df
        elements = elements or pd.unique(PEAK_LINES.Element)
        
        for element in elements:
            peaks_df = PEAK_LINES.loc[PEAK_LINES["Element"] == element].reset_index()
            peak_x, peak_y = peaks_df["Energy"].to_list(), peaks_df["Intensity"].to_list()
            peak_name = peaks_df["Line"].to_list()
            try:
                color = peak_colors_df[peak_colors_df.Element == element].iloc[0,1]
            except IndexError:
                color = "grey"
            
            max_peak = peaks_df["Energy"].iloc[peaks_df["Intensity"].idxmax()]
            # ~ print(element)
            
            # print(max_peak)

            roi = max_peak - PEAK_FIND_HWIDTH, max_peak + PEAK_FIND_HWIDTH
            # ~ print(df)
            hei = df.loc[(df.index > roi[0]) & (df.index < roi[1]), "y"].max()
            # ~ print(hei)
            # ~ print(f'{element}, {peak_x}, {peak_y}, {color}, max peak: {max_peak} hei: {hei}')
            y = np.array(peak_y) # predefined peak heights
            y /= y.max() # normalize
            y *= hei # fit max intensity
            # print(peak_y)
            # print(y)
            ax = plt.gca()
            ax.bar(peak_x, y,  width=1e-6, bottom=0,  linewidth=1, edgecolor=color)

            for i, (px, py) in enumerate(zip(peak_x, y)):
                # ~ print(i, peak_x, peak_y)
                ax.annotate(f'{element} {peak_name[i]}', xy=(px, py), xytext=(px + 0, py), fontsize=fontsize, color=color, rotation=90)


    def new_plot(self, figsize=(10,5), ax=None, fig=None, xlim='', ylim='', fontsize=None,):
        
        if ax:
            self.ax = ax
            self.fig = plt.gcf()
            return    
   
        if plt.fignum_exists(1):
            # reuse figure
            self.ax = plt.gca()
        else:
            # new figure
            self.fig, self.ax = plt.subplots(figsize=figsize)
       
        if fontsize:
            # ~ print("set font size",fontsize)
            plt.rc('font', size=fontsize)
            plt.rc('legend', fontsize=fontsize+2)    # legend fontsize
            plt.rc('figure', titlesize=fontsize)
            plt.tick_params(axis='both', which='major', labelsize=fontsize)
            plt.tick_params(axis='both', which='minor', labelsize=fontsize)
            plt.rc('axes', titlesize=fontsize, labelsize=fontsize)
        
        # show datatype as chart title
            plt.title(self.datatype)
            plt.legend(fontsize=fontsize)
        # axis range
        if xlim:
            self.ax.set_xlim(xlim)
        if ylim:
            self.ax.set_ylim(ylim)

        # scientific notation
        self.ax.ticklabel_format(axis='y', style='sci', scilimits=(-2,2))


        # axis labels
        if self.xunits:
            if self.xunits.lower() == "1/cm":
                xlabel = "Wavenumber (cm$^{-1}$)"
            else:
                xlabel = self.xunits
            # plt.xlabel(xlab, fontsize = fontsize)
            self.ax.set_xlabel(xlabel.upper())

        if self.yunits:
            self.ax.set_ylabel(self.yunits.upper())


        if self.datatype.lower()=="infrared spectrum":
            if not self.ax.xaxis_inverted():
                self.ax.invert_xaxis()

    def plot(self, title=None, linewidth=1, ax=None, **kwargs):

        self.new_plot()

        # plot, show title or filename in legend
        label = title or self.title or self.filestem or ""
        self.ax.plot(self.x, self.y, label=label, linewidth=linewidth, **kwargs)





    def __add__(self, other):
        new = Spectrum()
        new.__dict__.update(self.__dict__)
        new.y = self.y + other.y
        print("added", self.title, other.title)
        return new

    def __sub__(self, other):
        new = Spectrum()
        new.__dict__.update(self.__dict__)
        new.y = self.y - other.y
        print("subtracted", self.title, other.title)
        return new


    def __mul__(self, num):
        new = Spectrum()
        new.__dict__.update(self.__dict__)
        new.y = num * self.y
        print("multiplied", self.title, num)
        return new

    __rmul__ = __mul__

    def __truediv__(self, num):
        new = Spectrum()
        new.__dict__.update(self.__dict__)
        new.y = self.y / num
        print("divided", self.title, num)
        return new

    def subtract(self, bg):
        if len(self.y) != len(bg.y):
            raise BaseException("Cannot subtract, sizes not match: ",  len(self.y),  len(bg.y))
        if self.yunits == 'ABSORBANCE' and bg.yunits == 'ABSORBANCE':
            self.y -= bg.y
        elif self.yunits == bg.yunits:
            self.y /= bg.y
            self.yunits = "TRANSMITTANCE"
        self.tidy()
        return self

    # ------------------------------------------------------------------

    def info(self):
        # print(self.__dict__)
        # pprint.pprint(vars(self))
        print("\n*** SPECTRUM INFO: {} ***".format(self.title))
        attribs = [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self,a))]
        for a in attribs:
            print(a + "\t\t" + str(getattr(self, a, "#NA")))






    def _sort_xy(self):
        xy = np.array( list(zip(self.x,self.y)), dtype=[('x',float),('y',float)])
        xy.sort(order=['x'])
        self.x = xy['x']
        self.y = xy['y']

    def save_as_jdx(self, out_fp=None):
        if not out_fp:
            if self.fpath:
                out_fp = self.fpath+".jdx"
            else:
                raise BaseException("Spectrum save fpath undefined")


        if out_fp.is_file():
            out_fp.rename(str(out_fp) + ".bak")

        # sort data
#        self._sort_xy()

        x, y = self.x, self.y
        # ~ print(x)
        # ~ print(y)
        # scale data by xfactor, yfactor(omnic cannot read float values), estimate best yfactor not to lose decimal value
        # exp = int(-np.log10(np.max(y))) + 9
        # print(np.max(y), exp)
        # yfactor = 10**(-exp)
        yfactor = 1
        # yfactor = 10**(-exp)
        # print(yfactor)
        # y = y / yfactor
        # print(y)

        #  data to string
        data = ""
        for xi,yi in zip(x,y):
            data += "{:.2f} {:.8f}\n".format(xi,yi)

        data = data.replace("nan","?")

        deltax = abs ( x[0] - x[-1] ) / ( len(x) - 1 )
        #(##LASTX= minus ##FIRSTX=)/(##NPOINTS= minus 1).

        header = "\n".join([
                 "##TITLE={}".format(self.title) ,
                 "##JCAMP-DX=5.01",
                 "##DATA TYPE={}".format(self.datatype) ,
                 "##SAMPLING PROCEDURE={}".format(self.samplingprocedure) ,
                 "##ORIGIN={}".format(self.origin)  ,
                 "##OWNER={}".format(self.owner)  ,
                 "##DATE={}".format(self.date)  ,
                 "##TIME={}".format(self.time)  ,
                 "##LONG DATE={}".format(self.longdate)  ,
                 "##DATA PROCESSING={}".format(self.dataprocessing)  ,
                 "##SPECTROMETER/DATA SYSTEM={}".format(self.spectrometerdatasystem) ,
                 "##XUNITS={}".format(self.xunits) ,
                 "##YUNITS={}".format(self.yunits) ,
                 "##XFACTOR=1",
                 "##YFACTOR={}".format(yfactor),
                 "##FIRSTX={:.2f}".format(x[0]) ,
                 "##LASTX={:.2f}".format(x[-1]) ,
                 "##FIRSTY={:.0f}".format(y[0]) ,
                 "##NPOINTS={}".format(len(x)),
                 "##DELTAX={:.4f}".format(deltax) ,
                 "##XYDATA=(X++(Y..Y)) ",
                 ""          ]
                 )
        footer = "##END= \n"


        with open(out_fp ,"w") as f:
            f.write(header + data + footer)
        print("saved: ", out_fp)
        #print(Spectrum_txt[:500],"...")



class EdsSpectrum(Spectrum):

    def __init__(self, fpath=None):
        super().__init__(fpath)
        self.datatype = "EDS SPECTRUM"
        self.xunits = "keV"
        self.yunits = "counts"



class IrSpectrum(Spectrum):

    def __init__(self, fpath=None):
        super().__init__(fpath)


    @property
    def inverted(self):
        if self.yunits.lower() in ['transmittance', 'transmitance' , 'reflectance' ]:
            return True
        else:
            return False

    def plot(self):

        ax = plt.gca()

        if self.xunits.lower() == "1/cm":
            xlabel = "Wavenumber (cm$^{-1}$)"
        else:
            xlabel = ""

        if self.inverted and not ax.xaxis_inverted():
            ax.invert_xaxis()

        super().plot(xlabel=xlabel)

    def tidy(self):
        '''
        X to wavenumbers
        Y to absorbance
        clip Y axis

        '''

        ## X to wavenumbers
        xunitslow = self.xunits.lower()
        if ('1/cm' in xunitslow) or  ('cm-1' in xunitslow)  or ('cm^-1' in xunitslow):
            pass
        elif (self.xunits.lower() in ('micrometers','um','wavelength (um)')):
            self.x = 10000.0 / self.x
        elif (self.xunits.lower() in ('nanometers','nm','wavelength (nm)')):
            self.x = 10000 * 1000.0 / self.x
        else:
            print('Don\'t know how to convert the spectrum\'s x units ("' + self.xunits + '") to wavenumbers.')
        self.xunits='1/cm'

        ## Y to absorbance.
        if (self.yunits.lower() == 'absorbance'):
            self.yunits = 'ABSORBANCE'
        elif (self.yunits.lower() in ['transmittance', 'transmitance' , 'reflectance' ]):
            ## Correct for any unphysical negative values.
            y = self.y
            y[y < 0.0] = 0.0
            ## If in transmittance, then any y > 1.0 are unphysical.
            # y[y > 1.0] = 1.0
#            y[y > 2.0] = 2.0  # nahrazeno 2, pro jistotu
            ## Convert to absorbance.
            okay = (y > 0.0)
            y[okay] = -np.log10(y[okay])
            y[np.logical_not(okay)] = np.nan
            self.y = y
            self.yunits = 'ABSORBANCE'
        else:
            print(self.yunits, " ...not converted to absorbance")
            # ignore raman intensity




    def clear(self, bounds=(2290,2390), interp=True):
        ''' Replace y data in region with interpolated values if interp, else with np.nan '''
#        print("clear",  bounds,  interp,  self.filename)
        x = self.x
        y = self.y
        # najdi krajní body (sorted - musí být ve správném pořadí)
        i = (np.abs(x-sorted(bounds)[0])).argmin()
        j = (np.abs(x-sorted(bounds)[1])).argmin()

        if interp:
            self.y[i:j] =  np.interp(x[i:j], x[(i,j),], y[(i,j),])
#            print (self.filename,"replaced CO2 with line in", bounds)
        else:
            self.y[i:j] = np.nan
#            print (self.filename,"erased CO2 in", bounds)











##=====================================================================================================


if __name__ == "__main__":

    main()




