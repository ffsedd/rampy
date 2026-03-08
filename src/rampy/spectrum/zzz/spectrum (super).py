
import logging
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
import numpy as np
from pathlib import Path
import copy
from qq.ntool.detect_peaks import detect_peaks
from qq.ntool.baseline import baseline_correction
from qq.spectrum.spectrumio import SpectrumIO


class Spectrum:
    
    
    def __new__(cls, path=None, data=None, header=None):
        assert path or header

        if not header:
            logging.debug(f"read spectrum {path}")
            header, data = SpectrumIO(path).read()

        # CHANGE SPECTRUM CLASS BY HEADER
        if header['DATATYPE'] == 'INFRARED SPECTRUM':
            instance = super(Spectrum, cls).__new__(IrSpectrum)
        elif header['DATATYPE'] == 'RAMAN SPECTRUM':
            instance = super(Spectrum, cls).__new__(RamanSpectrum)
        elif header['SIGNALTYPE'] == 'EDS_SEM':
            instance = super(Spectrum, cls).__new__(EdsSpectrum)
        else:
            instance = super(Spectrum, cls).__new__(cls)

        instance.path = path
        instance.data = data
        instance.header = header
        return instance

  
    
    
    def __init__(self, path=None, data=None, header=None):
        pass
        # logging.debug("Spectrum __init__", type(path), type(data), type(header))
        


    def __str__(self):
        return f'''Spectrum | TITLE: {self.title} | DATATYPE: {self.datatype} | len: {len(self.data)} | 
                xmin: {self.xmin} xmax: {self.xmax} | ymin: {self.ymin} ymax: {self.ymax}'''

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, header):
        self._validate_header(header)
        
    @property
    def x(self):
        return self._data.index
        
    @property
    def y(self):
        return self._data.y
        
    @y.setter
    def y(self, y):
        self._data.y = y
            
    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._validate_data(data)
            
    @property
    def title(self):
        return self.header["TITLE"] 
    
    @property
    def xunits(self):
        return self.header["XUNITS"] 
    
    @property
    def yunits(self):
        return self.header["YUNITS"] 
    
    @property
    def xlabel(self):
        return self.header["XUNITS"] 
    
    @property
    def ylabel(self):
        return self.header["YUNITS"] 
    
    @property
    def ymin(self):
        return self.data.y.min() 
    
    @property
    def ymax(self):
        return self.data.y.max() 
    
    @property
    def xmin(self):
        return self.data.index.min() 
    
    @property
    def xmax(self):
        return self.data.index.max() 
    
    @property
    def deltax(self):
        x = self.x
        deltax = abs(x[0] - x[-1]) / (len(x) - 1)
        return round(deltax, 3)
        
    @property
    def datatype(self):
        return self.header["DATATYPE"] 
        
    @property
    def peaks(self):
        if not hasattr(self, "_peaks"):
            self._peaks = self.find_peaks()
        return self._peaks     

    def info(self):
        print("\n*** SPECTRUM INFO: {} ***".format(self.title))
        attribs = [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self,a))]
        for a in attribs:
            print(a + "\t\t" + str(getattr(self, a, "#NA")))




# ================== VALIDATE =====================================


       
    def _validate_data(self, data):

        d = pd.DataFrame(index={"x":None}, columns=["y"])
        
        if data is not None:
            if not len(data):
                raise ValueError("Spectrum empty")
            d = pd.DataFrame(index=data.index, data={"y":data.iloc[:,0].astype(float)})
            d.index = data.index.astype(float)
            d.index.names = ['x']
            

        self._data = d
        
    def _validate_header(self, header):
        
        h = {
                "TITLE":"",
                "XUNITS":"",
                "YUNITS":"",
                "SIGNALTYPE":"",
                "DATATYPE":"",
                          }
        if not header is None:
                
            try:
                h.update({k.upper() : v for k, v in header.items()})
            except Exception as e:
                logging.error(f"header validation failed, {e}")
        self._header = h


# ================== IO =====================================

        
    def write(self, path):
        SpectrumIO.write(self, path)
        return self
        
    def save(self, path):
        logging.info(f"spectrum saved {path}")
        SpectrumIO(path).write(self)
        return self

# ================== PROCESSING =====================================

    def copy(self):
        return Spectrum(data=self.data.copy(), header=self.header.copy())
    
    def smooth(self, window=9, poly=3):
        self.data['y'] = savgol_filter(self.data['y'], window, poly)
        return self
    
    def nan_negative(self):
        self.data.loc[self.data.y < 0, "y"] = np.nan
        
        
#    def smooth(self, window=3):
#        self._data['y'] = self.data.y.rolling(window, center=True).mean()

    def baseline_correction(self, niter=10, lam=1e8, p=0.05):

        try:
            self._data['y'] = baseline_correction(self._data.y, niter=niter, lam=lam, p=p)
        except ValueError as e:
            logging.error(f"baseline correction failed {e}")    
        return self    

    def diff1(self, multiply=1, plot=True):
        if not 'dy' in self._data.columns:
            self._data["dy"] = self.data.y.diff() * multiply
        if plot:
            plt.gca().plot(self._data["dy"])
        return self._data["dy"]

    def diff2(self, multiply=-10, plot=True):
        if not 'd2y' in self._data.columns:
            self._data["d2y"] = self.diff1(plot=False).diff(-10)
            self._data["d2y"][self._data["d2y"] < 0] = 0
        if plot:
            plt.gca().plot(self._data.index, self._data.d2y)     
        return self._data["d2y"]


# ================== PLOT =====================================

    
    def plot(self, ax=None, *a, **kw):
        ax = ax or plt.gca()
#        self.new_plot()
        ax.plot(self.data.index, self.data.y, label=self.title, *a, **kw)
        plt.xlabel(self.xunits)
        plt.ylabel(self.yunits)
        plt.legend()
        return self
    
    def find_peaks(self, rmph=.01, mpd=0.01, rthr=1e-5):
        """
        mph minimum peak height
        mpd 	default = 1. Detect peaks that are at least separated by minimum peak distance (in number of data)
        threshold 	default = 0. Detect peaks (valleys) that are greater (smaller) than threshold in relation to their immediate neighbors
        """
        peak_idx = detect_peaks(self.data.y, mph=self.data.y.max() * rmph, 
                                edge='both', mpd=mpd, kpsh=True,  
                                threshold=self.data.y.max() * rthr)
        self._peaks = self.data.y.iloc[peak_idx]                        
        return self._peaks
    
    def plot_peaks(self, rng=None, ax=None, peaks=None, decimals=2, s=5, fontsize=6, *a, **kw):

        ax = ax or plt.gca()
        peaks = peaks or self.find_peaks()
        ax.scatter(peaks.index, peaks, s=s, *a, **kw)
        
        for px, py in zip(peaks.index.tolist(),peaks.tolist()):
            if rng and not (rng[0] < px < rng[1]): # ignore out of range peaks
                continue
            else:    
                # ~ ax.annotate(round(px, decimals), xy=(px, py), xytext=(px, py), fontsize=fontsize)
                ax.annotate(f"{px:.0f}", xy=(px, py), xytext=(px, py), fontsize=fontsize)
        return self    


        
    def new_plot(self, figsize=(17,10), ax=None, xlim='', ylim='', fontsize=None,):
        
        if ax:
            self.ax = ax
            self.fig = plt.gcf()
            return    
   
        elif plt.fignum_exists(1):
            # reuse figure
            self.ax = plt.gca()
            self.fig = plt.gcf()
        else:
            # new figure
            self.fig, self.ax = plt.subplots(figsize=figsize)
       
        if fontsize:
            # ~ logging.error("set font size",fontsize)
            plt.rc('font', size=fontsize)
            plt.rc('legend', fontsize=fontsize+2)    # legend fontsize
            plt.rc('figure', titlesize=fontsize)
            plt.tick_params(axis='both', which='major', labelsize=fontsize)
            plt.tick_params(axis='both', which='minor', labelsize=fontsize)
            plt.rc('axes', titlesize=fontsize, labelsize=fontsize)
        
        # show datatype as chart title
            plt.title(f'{self.signaltype} spectrum')
            plt.legend(fontsize=fontsize)
        # axis range
        if xlim:
            self.ax.set_xlim(xlim)
        if ylim:
            self.ax.set_ylim(ylim)

        # scientific notation
        self.ax.ticklabel_format(axis='y', style='sci', scilimits=(-2,2))


        self.ax.set_xlabel(self.xlabel)
        self.ax.set_ylabel(self.xlabel)


        if self.datatype.lower()=="infrared spectrum":
            if not self.ax.xaxis_inverted():
                self.ax.invert_xaxis()
        return self        





# ================== MATH OPERATIONS =====================================


    def __add__(self, other):
        if (self.data.index == other.data.index).all():
            result = copy.deepcopy(self)
            result.data['y'] = self.data['y'] + other.data['y']
            logging.debug(f"added {self.title} {other.title}")
            return result
        else:
            raise ValueError("x axis of the spectra mismatch")

    def __sub__(self, other):
        logging.debug(f"subtract {self.title} {other.title}")
        return self + (other * -1)
        
    def __mul__(self, number):
        result = copy.deepcopy(self)
        result.data['y'] = self.data['y'] * number
        logging.debug(f"mutiply {self.title} {number}")
        return result
    
    def __truediv__(self, number):    
        logging.debug(f"divide {self.title} {number}")
        return self * (1 / number)

    __rmul__ = __mul__
        

class RamanSpectrum(Spectrum):
    
    def __new__(cls, *a, **kw):
        return super(RamanSpectrum, cls).__new__(cls, *a, **kw)

    def __init__(self, path=None, data=None, header=None):
        logging.info(f"RamanSpectrum init, type: {type(self)}")
        super().__init__(path=path, data=data, header=header) 



    



class IrSpectrum(Spectrum):
    
    def __new__(cls, *a, **kw):
        return super(IrSpectrum, cls).__new__(cls, *a, **kw)

    def __init__(self, path=None, data=None, header=None):
        logging.debug(f"IrSpectrum init, type: {type(self)}")
        super().__init__(path=path, data=data, header=header) 
        self.to_absorbance()

    def subtract(self, other):
        if len(self.y) != len(other.y):
            raise BaseException("Cannot subtract, sizes not match: ",  len(self.y),  len(other.y))
        if self.yunits == 'ABSORBANCE' and other.yunits == 'ABSORBANCE':
            self.y -= other.y
        elif self.yunits == other.yunits:
            self.y /= other.y
            self.yunits = "TRANSMITTANCE"
        self.tidy()
        return self
    
    
    def to_absorbance(self):
                    ## Correct for any unphysical negative values.
        if not self._header['YUNITS'] in ('TRANSMITANCE', 'TRANSMITTANCE', 'TRANSMISSION'):
            return
        y = self.y
        y[y < 0.0] = 0.0
        okay = (y > 0.0)
        y[okay] = -np.log10(y[okay])
        y[np.logical_not(okay)] = np.nan
        self._data.y = y
        self._header['YUNITS'] = 'ABSORBANCE'
#        logging.debug("spectrum converted to absorbance")
        
        
    def plot(self, ax=None, *a, **kw):
        super().plot(ax=ax, *a, **kw)  # Call the plot method of the Spectrum class
        plt.gca().invert_xaxis()  # Reverse the x-axis

        
               
class EdsSpectrum(Spectrum):
    
    PEAK_LINES = pd.read_csv(Path(__file__).parent / "data/peak_lines.tsv", sep='\t', header=0, skip_blank_lines=True)
    PEAK_COLORS = pd.read_csv(Path(__file__).parent / "data/peak_colors.tsv", sep='\t', header=0, skip_blank_lines=True)
    PEAK_FIND_HWIDTH = .02
    PEAK_ELEMENTS = pd.unique(PEAK_LINES.Element) 
    
    def __new__(cls, *a, **kw):
        return super(EdsSpectrum, cls).__new__(cls, *a, **kw)

    def __init__(self, path=None, data=None, header=None):
        logging.debug(f"EdsSpectrum init, type: {type(self)}")
        super().__init__(path=path, data=data, header=header) 
        
    def plot_peak_lines(self, elements=None, limit=.001, peak_halfwidth=PEAK_FIND_HWIDTH, fontsize=8, peak_colors_df=PEAK_COLORS, ax=None):
        '''
        limit - minimum relative height to ymax 
        peak_halfwidth - tolerance in which element peak is searched
        '''
        
        ax = ax or plt.gca()
        df = self.data
        elements = elements or EdsSpectrum.PEAK_ELEMENTS

        for element in elements:
            peaks_df = EdsSpectrum.PEAK_LINES.loc[EdsSpectrum.PEAK_LINES["Element"] == element].reset_index()
            peak_x, peak_y = peaks_df["Energy"].to_list(), peaks_df["Intensity"].to_list()
            peak_name = peaks_df["Line"].to_list()
            try:
                color = peak_colors_df[peak_colors_df.Element == element].iloc[0,1]
            except IndexError:
                color = "grey"
            
            max_peak = peaks_df["Energy"].iloc[peaks_df["Intensity"].idxmax()]
            roi = max_peak - peak_halfwidth, max_peak + peak_halfwidth
            hei = df.loc[(df.index > roi[0]) & (df.index < roi[1]), "y"].max()
            if hei < limit * self.ymax:
                continue
            y = np.array(peak_y) # predefined peak heights
            y /= y.max() # normalize
            y *= hei # fit max intensity
            
            ax.bar(peak_x, y,  width=1e-6, bottom=0,  linewidth=1, edgecolor=color)
            for i, (px, py) in enumerate(zip(peak_x, y)):
                ax.annotate(f'{element} {peak_name[i]}', xy=(px, py), xytext=(px + 0, py + .02*self.ymax), fontsize=fontsize, color=color, rotation=90)
        return self
        





    

        
if __name__ == "__main__":


    plt.rcParams['figure.figsize'] = [15, 10]
    
            
    fp = '/home/m/Dropbox/appy/qq/qq/spectrum/test_spectra/15.csv'
    fp = '/home/m/Dropbox/appy/qq/qq/spectrum/test_spectra/Az-Che_017.spx'
    fp = '/home/m/Dropbox/appy/qq/qq/spectrum/test_spectra/180427-7_manila_kopal.jdx'
       
     
    s = Spectrum(fp)
#    print(s)
    print(s.header)
#    s.to_absorbance()
#    s.plot()

    s.smooth(31)
    s.baseline_correction()
#    s.smooth()
    s.plot()
    s.plot_peaks()
#    s.diff2()
    

    plt.show()
#    s.info()
            

