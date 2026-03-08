
import logging
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from qq.ntool.smooth import smooth_golay
import numpy as np
from pathlib import Path
from pprint import pprint
import copy
from collections import namedtuple


from qq.ntool.detect_peaks import detect_peaks
from qq.ntool.baseline import baseline_correction
from qq.spectrum.spectrumio import SpectrumIO
from qq.spectrum.square_root_scale import SquareRootScale
import matplotlib.scale as mscale
mscale.register_scale(SquareRootScale)



class Spectrum:
    def __init__(self, path=None, data=None, header=None):
        if not header and path:
            header, data = SpectrumIO(path).read()

        if not header:
            raise ValueError("Header must be provided if path is not given")

        # Now, based on the header, instantiate the correct Spectrum subclass
        if header['DATATYPE'] == 'INFRARED SPECTRUM':
            self.__class__ = IrSpectrum
        elif header['DATATYPE'] == 'RAMAN SPECTRUM':
            self.__class__ = RamanSpectrum
        elif header['DATATYPE'] == 'EDS_SEM' or header['SIGNALTYPE'] == 'EDS_SEM':
            self.__class__ = EdsSpectrum
        else:
            self.__class__ = BaseSpectrum
        
        # Initialize the instance with the provided data and header
        self.__init__(path=path, data=data, header=header)

    @staticmethod
    def create(path=None, data=None, header=None):
        return Spectrum(path=path, data=data, header=header)


class BaseSpectrum:
    
   
    def __init__(self, path=None, data=None, header=None):

        logging.debug(f"BaseSpectrum __init__ {type(path)}")
        # ~ logging.debug(f"BaseSpectrum __init__ {type(path)}, {type(data)}, {type(header)}")
        
        assert path or header

        

        if not header:
            logging.debug(f"read spectrum {path}")
            header, data = SpectrumIO(path).read()

        self.path = path
        self.data = data
        self.header = header
        # ~ print("spectrum init done, path", self.path)

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
    def path(self):
        return self._path if hasattr(self,"_path") else None 

    @path.setter
    def path(self, path):
        self._path = Path(path) if path else None
             
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
        
    @title.setter
    def title(self, value):
        self.header["TITLE"] = str(value)
    
    @property
    def xunits(self):
        return self.header["XUNITS"] 
        
    @xunits.setter
    def xunits(self, value):
        self.header["XUNITS"] = str(value).upper()    
    
    @property
    def yunits(self):
        return self.header["YUNITS"] 
        
    @yunits.setter
    def yunits(self, value):
        self.header["YUNITS"] = str(value).upper()  
        
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

    @datatype.setter
    def datatype(self, value):
        self.header["DATATYPE"] = str(value).upper()
                
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
            #print(data)
            if not len(data):
                raise ValueError("Spectrum empty")
            if isinstance(data, pd.Series):
                d = pd.DataFrame(index=data.index, data=data)
            elif isinstance(data, (tuple, list)):
                d = pd.DataFrame(index=data[0], data=data[1])    
            elif isinstance(data, pd.DataFrame):        
                d = pd.DataFrame(index=data.index, data=data.iloc[:,0])
            d.index = d.index.astype(float)
            d.index.names = ['x']
            d = d.astype(float)
            d = d.rename(columns={d.columns[0]: "y"})
            # ~ print(type(d))
            

        self._data = d
        
    def _validate_header(self, header):
        ''' Ensure essential items are in header. '''
        h = {
                "TITLE":"",
                "XUNITS":"",
                "YUNITS":"",
                "SIGNALTYPE":"",
                "DATATYPE":"",
                "DATE":"",
                "SAMPLING PROCEDURE":"",
                "ORIGIN":"",
                "OWNER":"",
                "DATA PROCESSING":"",
                "SPECTROMETER/DATA SYSTEM":"",
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
        
    def save(self, path=None):
        path = path if path is not None else self.path
        logging.info(f"spectrum saved {path}")
        SpectrumIO(path).write(self)
        return self

# ================== PROCESSING =====================================

    def copy(self):
        return Spectrum(path=self.path, data=self.data.copy(), header=self.header.copy())
    
    def smooth(self, window=9, poly=3, method="savgol"):
        if method=="savgol":
            self.data['y'] = savgol_filter(self.data['y'], window, poly)
        elif method=="running":  
            self.data['y'] = np.convolve(self.data['y'], np.ones(window)/window, mode='same')
        else:
            raise ValueError(f"smoothing method missing: {method}")    
        return self
    
    def nan_negative(self):
        self.data.loc[self.data.y < 0, "y"] = np.nan
        
    def baseline_correction(self, niter=10, lam=1e8, p=0.05):

        try:
            self._data['y'] = baseline_correction(self._data.y, niter=niter, lam=lam, p=p)
        except ValueError as e:
            logging.error(f"baseline correction failed {e}")    
        return self  
        
    def baseline_removal(self, method="ZhangFit", polynomial_degree=3):
        from qq.spectrum.tools.BaselineRemoval import BaselineRemoval
        y = self._data['y'].values
        #print(type(y))
        
        baseObj=BaselineRemoval(y)
        
        if method == "ModPoly":
            y = baseObj.ModPoly(polynomial_degree)
        elif method == "IModPoly":            
            y = baseObj.IModPoly(polynomial_degree)
        elif method == "ZhangFit":            
            y = baseObj.ZhangFit()
        elif method == "Scipy":
            y = baseline_correction(self._data.y, niter=10, lam=1e8, p=0.05) 
        else:
            raise ValueError(f"baseline_removal method not implemented: {method}")       
        self.y = y
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
        
        
    def resample(self, step, xlimits=(None, None), spline_order=1):

        from scipy.interpolate import interp1d

        logging.debug(f"resample {self.title} to step {step}, range {xlimits}")
        
        if xlimits == (None, None):
            xlimits = (self.y.index.min(), self.y.index.max()) 
        xlimits = [round(x//step*step,0) for x in xlimits]

        # Create a new index with desired range and number of points
        x_new = pd.Index(np.arange(xlimits[0], xlimits[1], step))
        # Interpolate the data 
        f = interp1d(self.x, self.y, bounds_error=False, fill_value="extrapolate")
        y2 = f(x_new)
        self.data = x_new.tolist(), y2
        
    def rescale_intensity(self):
        from skimage.exposure import rescale_intensity
        self.y = rescale_intensity(self.data.values, out_range=(0,1))

# ================== PLOT =====================================

    
    def plot(self, ax=None, *a, **kw):
        ax = ax or plt.gca()
#        self.new_plot()
        ax.plot(self.data.index, self.data.y, label=self.title, *a, **kw)
        plt.xlabel(self.xunits)
        plt.ylabel(self.yunits)
        plt.legend()
        return self
    
    def find_peaks(self, rmph=.01, mpd=0.01, rthr=1e-5, smooth=11):
        """
        rmph   realtive minimum peak height = mph/max
        mpd    default=1. Detect peaks that are at least separated by minimum peak distance (in number of data)
        rthr   relative threshold (default=0). Detect peaks (valleys) that are greater (smaller) than threshold in relation to their immediate neighbors = thr/max
        smooth = smooth spectrum before finding peaks
        """
        # ~ y = savgol_filter(self.data['y'], smooth, 3)
        y = self.data['y'].rolling(smooth, center=True).mean()
        peak_idx = detect_peaks(y, mph=y.max() * rmph, 
                                edge='both', mpd=mpd, kpsh=True,  
                                threshold=y.max() * rthr)
        self._peaks = self.data.y.iloc[peak_idx]                        
        return self._peaks
    
    def plot_peaks(self, rng=None, ax=None, peaks=None, decimals=2, s=2, fontsize=6, color="#cccccc", *a, **kw):

        ax = ax or plt.gca()
        peaks = peaks if peaks is not None else self.find_peaks()
        ax.scatter(peaks.index, peaks, s=s, *a, **kw)
        
        for px, py in zip(peaks.index.tolist(),peaks.tolist()):
            if rng and not (rng[0] < px < rng[1]): # ignore out of range peaks
                continue
            else:    
                ax.annotate(round(px, decimals), xy=(px, py), xytext=(px, py), fontsize=fontsize, color=color)
                # ~ ax.annotate(f"{px:.0f}", xy=(px, py), xytext=(px, py), fontsize=fontsize)
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
        

class RamanSpectrum(BaseSpectrum):
    
    def __init__(self, path=None, data=None, header=None):
        logging.debug(f"RamanSpectrum init, type: {type(self)}")
        super().__init__(path=path, data=data, header=header) 



    



class IrSpectrum(BaseSpectrum):

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

        
               
class EdsSpectrum(BaseSpectrum):
    
    PEAK_LINES = pd.read_csv(Path(__file__).parent / "data/peak_lines.tsv", sep='\t', header=0, skip_blank_lines=True)
    PEAK_COLORS = pd.read_csv(Path(__file__).parent / "data/peak_colors.tsv", sep='\t', header=0, skip_blank_lines=True)
    PEAK_FIND_HWIDTH = .02
    PEAK_ELEMENTS = pd.unique(PEAK_LINES.element) 
    
    def __init__(self, path=None, data=None, header=None):
        logging.debug(f"EdsSpectrum init, type: {type(self)}")
        #print(path, data, header)
        super().__init__(path=path, data=data, header=header) 
    
    
    @property
    def peak_lines(self):
        if not hasattr(self, "_peak_lines"):
            pl = {}
            df = EdsSpectrum.PEAK_LINES
            for e in df['element'].unique():
                peaks_df = EdsSpectrum.PEAK_LINES.loc[df["element"] == e].reset_index()
                peak_x, peak_y = peaks_df["kV"].to_list(), peaks_df["intensity"].to_list()
                peak_name = peaks_df["line"].to_list()
                try:
                    color = EdsSpectrum.PEAK_COLORS[EdsSpectrum.PEAK_COLORS.element == e].iloc[0,1]
                except IndexError:
                    color = "grey"
                max_peak = peaks_df["kV"].iloc[peaks_df["intensity"].idxmax()]    
                roi = max_peak - EdsSpectrum.PEAK_FIND_HWIDTH, max_peak + EdsSpectrum.PEAK_FIND_HWIDTH
                pl[e] = (peak_x, peak_y, peak_name, color, max_peak, roi)
            self._peak_lines = pl
            
        return self._peak_lines 
        
    def plot_peak_lines(self, elements=None, limit=.001, fontsize=8, ax=None, xlimits=(None,None)):
        '''
        limit - minimum relative height to ymax 
        peak_halfwidth - tolerance in which element peak is searched
        '''
        
        ax = ax or plt.gca()
        df = self.data
        elements = elements or EdsSpectrum.PEAK_ELEMENTS

        for element in elements:
            peak_x, peak_y, peak_name, color, max_peak, roi = self.peak_lines[element]
            
            hei = df.loc[(df.index > roi[0]) & (df.index < roi[1]), "y"].max()
            if hei < limit * self.ymax:
                # skip if peak smaller than limit
                continue
            y = np.array(peak_y) # predefined peak heights
            y *= hei / y.max() # normalize # fit max intensity
            
            ax.bar(peak_x, y,  width=1e-6, bottom=0,  linewidth=1, edgecolor=color)
            for i, (px, py) in enumerate(zip(peak_x, y)):
                # ~ ax.annotate(f'{element} {peak_name[i]}', xy=(px, py), xytext=(px, py), fontsize=fontsize, color=color, rotation=90)
                if np.isnan(py) or np.isnan(px):
                    continue
                if xlimits[0] is not None and xlimits[0] > px:
                    continue
                if xlimits[1] is not None and xlimits[1] < px:
                    continue                    
                ax.text(px, py, f'{element} {peak_name[i]}',
            ha="center", va="center", rotation=90, size=fontsize, color=color,
            # ~ bbox=dict(boxstyle="ellipse,pad=0.1", fc="white", ec="grey", lw=1)
                      )
        return self
        



def resample(x,y,x_new,**kwargs):
    
    """Resample a y signal associated with x, along the x_new values.

    Parameters
    ----------
    x : ndarray
        The x values
    y : ndarray
        The y values
    x_new : ndarray
        The new X values
    kind : str or int, optional
        Specifies the kind of interpolation as a string (‘linear’, ‘nearest’, ‘zero’, ‘slinear’, ‘quadratic’, ‘cubic’, ‘previous’, ‘next’, where ‘zero’, ‘slinear’, ‘quadratic’ and ‘cubic’ refer to a spline interpolation of zeroth, first, second or third order; ‘previous’ and ‘next’ simply return the previous or next value of the point) or as an integer specifying the order of the spline interpolator to use. Default is ‘linear’.
    axis : int, optional
        Specifies the axis of y along which to interpolate. Interpolation defaults to the last axis of y.
    copy : bool, optional
        If True, the class makes internal copies of x and y. If False, references to x and y are used. The default is to copy.
    bounds_error : bool, optional
        If True, a ValueError is raised any time interpolation is attempted on a value outside of the range of x (where extrapolation is necessary). If False, out of bounds values are assigned fill_value. By default, an error is raised unless fill_value=”extrapolate”.
    fill_value : array-like or (array-like, array_like) or “extrapolate”, optional
        if a ndarray (or float), this value will be used to fill in for requested points outside of the data range. If not provided, then the default is NaN. The array-like must broadcast properly to the dimensions of the non-interpolation axes.
        If a two-element tuple, then the first element is used as a fill value for x_new < x[0] and the second element is used for x_new > x[-1]. Anything that is not a 2-element tuple (e.g., list or ndarray, regardless of shape) is taken to be a single array-like argument meant to be used for both bounds as below, above = fill_value, fill_value.

        New in scipy version 0.17.0.

        If “extrapolate”, then points outside the data range will be extrapolated.

        New in scipy version 0.17.0.

    assume_sorted : bool, optional
        If False, values of x can be in any order and they are sorted first. If True, x has to be an array of monotonically increasing values.

    Returns
    -------
    y_new : ndarray
        y values interpolated at x_new.

    Remarks
    -------
    Uses scipy.interpolate.interp1d. Optional arguments are passed to scipy.interpolate.interp1d, see https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.interp1d.html

    """
    from scipy.interpolate import interp1d
    
    f = interp1d(x,y,**kwargs)
    return f(x_new)

    

        
if __name__ == "__main__":

    import logging
    logging.basicConfig(format='!%(levelno)s [%(module)10s%(lineno)4d]	%(message)s',  
                        # ~ filename=Path(__file__).with_suffix(".log"), filemode='w'
                        level=10 )
    logging.getLogger('matplotlib.font_manager').disabled = True

    plt.rcParams['figure.figsize'] = [10, 7]
    
            
    fp = '/home/m/Dropbox/appy/qq/qq/spectrum/test/10.spx'
    # ~ fp = '/home/m/Dropbox/appy/qq/qq/spectrum/test/Az-Che_017.spx'
    # ~ fp = '/home/m/Dropbox/appy/qq/qq/spectrum/test/180427-7_manila_kopal.jdx'
    fp = "/home/m/Y/JETSTREAM/2024/J2425_Schwarzenberg/j490_J2425_bottom-left__100-850-20/sum.jdx"   
     
    s = Spectrum(fp)
    print(s.header)

    s.smooth(51)
    s.baseline_removal()

    s.plot()
    s.plot_peaks()
    s.plot_peak_lines()
    s.diff2()
    # ~ plt.gca().set_yscale('squareroot')
    plt.show()
    s.info()
            

