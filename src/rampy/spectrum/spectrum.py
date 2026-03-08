import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from rampy.ntool.smooth import smooth_golay
from pathlib import Path
from pprint import pprint
import copy
from collections import namedtuple
from rampy.ntool.detect_peaks import detect_peaks
from rampy.ntool.baseline import baseline_correction
from rampy.spectrum.spectrumio import SpectrumIO
from rampy.spectrum.square_root_scale import SquareRootScale
import matplotlib.scale as mscale

mscale.register_scale(SquareRootScale)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

class Spectrum:
    def __init__(self, path=None, data=None, header=None):
        logging.debug(f"Initializing Spectrum with path={path}, data={data}, header={header}")
        if not header and path:
            header, data = SpectrumIO(path).read()

        if not header:
            raise ValueError("Header must be provided if path is not given")

        # Dynamically assign the correct subclass based on DATATYPE
        spectrum_classes = {
            'INFRARED SPECTRUM': IrSpectrum,
            'INFRARED': IrSpectrum,
            'RAMAN SPECTRUM': RamanSpectrum,
            'RAMAN': RamanSpectrum,
            'EDS_SEM': EdsSpectrum,
            'EDS': EdsSpectrum,
            'SIGNALTYPE': EdsSpectrum
        }
        self.__class__ = spectrum_classes.get(header['DATATYPE'], BaseSpectrum)

        # Initialize with the provided data and header
        self.__init__(path=path, data=data, header=header)

    @staticmethod
    def create(path=None, data=None, header=None):
        logging.debug(f"Creating Spectrum with path={path}, data={data}, header={header}")
        return Spectrum(path=path, data=data, header=header)

class BaseSpectrum:
    def __init__(self, path=None, data=None, header=None):
        logging.debug(f"BaseSpectrum __init__ called with path={path}, data={data}, header={header}")
        
        assert path or header
        if data is None:
            logging.debug(f"Reading spectrum from {path}")
            header, data = SpectrumIO(path).read()
            assert data is not None

        self.path = path
        self.data = data
        self.header = header

    def __str__(self):
        return f'''Spectrum | TITLE: {self.title} | DATATYPE: {self.datatype} | len: {len(self.data)} | 
                xmin: {self.xmin} xmax: {self.xmax} | ymin: {self.ymin} ymax: {self.ymax}'''

    @property
    def header(self):
        return self._header

    @header.setter
    def header(self, header):
        logging.debug(f"Setting header with {header}")
        self._validate_header(header)

    @property
    def path(self):
        return self._path if hasattr(self, "_path") else None

    @path.setter
    def path(self, path):
        logging.debug(f"Setting path to {path}")
        self._path = Path(path) if path else None

    @property
    def x(self):
        return self._data.index

    @property
    def y(self):
        return self._data.y

    @y.setter
    def y(self, y):
        logging.debug(f"Setting y values maxy: {np.nanmax(y)}")
        self._data.y = y

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        logging.debug(f"Setting data with {data}")
        self._validate_data(data)

    @property
    def title(self):
        return self.header["TITLE"]

    @title.setter
    def title(self, value):
        logging.debug(f"Setting title to {value}")
        self.header["TITLE"] = str(value)

    @property
    def xunits(self):
        return self.header["XUNITS"]

    @xunits.setter
    def xunits(self, value):
        logging.debug(f"Setting xunits to {value}")
        self.header["XUNITS"] = str(value).upper()

    @property
    def yunits(self):
        return self.header["YUNITS"]

    @yunits.setter
    def yunits(self, value):
        logging.debug(f"Setting yunits to {value}")
        self.header["YUNITS"] = str(value).upper()

    @property
    def xlabel(self):
        return self.header["XUNITS"]

    @property
    def ylabel(self):
        return self.header["YUNITS"]

    @property
    def ymin(self):
        return np.nanmin(self.data.y)

    @property
    def ymax(self):
        return np.nanmax(self.data.y)

    @property
    def xmin(self):
        return np.nanmin(self.data.index)

    @property
    def xmax(self):
        return np.nanmax(self.data.index)

    @property
    def deltax(self):
        x = self.x
        logging.debug(f"Calculating deltax with x={x[1]}")
        deltax = abs(x[0] - x[-1]) / (len(x) - 1)
        return round(deltax, 3)

    @property
    def datatype(self):
        return self.header["DATATYPE"]

    @datatype.setter
    def datatype(self, value):
        logging.debug(f"Setting datatype to {value}")
        self.header["DATATYPE"] = str(value).upper()

    @property
    def peaks(self):
        if not hasattr(self, "_peaks"):
            logging.debug(f"Finding peaks")
            self._peaks = self.find_peaks()
        return self._peaks

    def info(self):
        logging.debug(f"Displaying spectrum info for {self.title}")
        print(f"\n*** SPECTRUM INFO: {self.title} ***")
        attribs = [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self, a))]
        for a in attribs:
            print(f"{a}\t\t{str(getattr(self, a, '#NA'))}")

    def _validate_data(self, data):
        logging.debug(f"Validating data: {type(data)}")
        d = pd.DataFrame(index={"x": None}, columns=["y"])

        if data is not None:
            
            if not len(data):
                raise ValueError("Spectrum empty")
            if isinstance(data, pd.Series):
                d = pd.DataFrame(index=data.index, data=data)
            elif isinstance(data, (tuple, list)):
                d = pd.DataFrame(index=data[0], data=data[1])
            elif isinstance(data, pd.DataFrame):
                d = pd.DataFrame(index=data.index, data=data.iloc[:, 0])
            d.index = d.index.astype(float)
            d.index.names = ['x']
            d = d.astype(float)
            d = d.rename(columns={d.columns[0]: "y"})
        self._data = d

    def _validate_header(self, header):
        logging.debug(f"Validating header with {header}")
        h = {
            "TITLE": "",
            "XUNITS": "",
            "YUNITS": "",
            "SIGNALTYPE": "",
            "DATATYPE": "",
            "DATE": "",
            "SAMPLING PROCEDURE": "",
            "ORIGIN": "",
            "OWNER": "",
            "DATA PROCESSING": "",
            "SPECTROMETER/DATA SYSTEM": "",
        }
        if header is not None:
            try:
                h.update({k.upper(): v for k, v in header.items()})
            except Exception as e:
                logging.error(f"header validation failed, {e}")
        self._header = h

    def write(self, path):
        logging.debug(f"Writing spectrum to {path}")
        SpectrumIO.write(self, path)
        return self

    def save(self, path=None):
        path = path if path is not None else self.path
        logging.info(f"spectrum saved {path}")
        SpectrumIO(path).write(self)
        return self

    def copy(self):
        logging.debug(f"Copying spectrum")
        return Spectrum(path=self.path, data=self.data.copy(), header=self.header.copy())

    def smooth(self, window=9, poly=3, method="savgol"):
        logging.debug(f"Smoothing spectrum with window={window}, poly={poly}, method={method}")
        if method == "savgol":
            self.data['y'] = savgol_filter(self.data['y'], window, poly)
        elif method == "running":
            self.data['y'] = np.convolve(self.data['y'], np.ones(window) / window, mode='same')
        else:
            raise ValueError(f"smoothing method missing: {method}")
        return self

    def nan_negative(self):
        logging.debug(f"Setting negative values to NaN")
        self.data.loc[self.data.y < 0, "y"] = np.nan

    def baseline_correction(self, niter=10, lam=1e8, p=0.05):
        logging.debug(f"Performing baseline correction with niter={niter}, lam={lam}, p={p}")
        try:
            self._data['y'] = baseline_correction(self._data.y, niter=niter, lam=lam, p=p)
        except ValueError as e:
            logging.error(f"baseline correction failed {e}")
        return self

    def baseline_removal(self, method="ZhangFit", polynomial_degree=3):
        logging.debug(f"Performing baseline removal with method={method}, polynomial_degree={polynomial_degree}")
        from rampy.spectrum.tools.BaselineRemoval import BaselineRemoval
        y = self._data['y'].values
        baseObj = BaselineRemoval(y)

        method_map = {
            "ModPoly": baseObj.ModPoly,
            "IModPoly": baseObj.IModPoly,
            "ZhangFit": baseObj.ZhangFit,
            "Scipy": lambda: baseline_correction(self._data.y, niter=10, lam=1e8, p=0.05),
        }

        if method not in method_map:
            raise ValueError(f"baseline_removal method not implemented: {method}")

        self.y = method_map[method](polynomial_degree) if method != "Scipy" else method_map[method]()
        return self

    def diff1(self, multiply=1, plot=True):
        logging.debug(f"Performing diff1 with multiply={multiply}, plot={plot}")
        if 'dy' not in self._data.columns:
            self._data["dy"] = self.data.y.diff() * multiply
        if plot:
            plt.gca().plot(self._data["dy"])
        return self._data["dy"]

    def diff2(self, multiply=-10, plot=True):
        logging.debug(f"Performing diff2 with multiply={multiply}, plot={plot}")
        if 'd2y' not in self._data.columns:
            self._data["d2y"] = self.diff1(plot=False).diff(-10)
            self._data["d2y"][self._data["d2y"] < 0] = 0
        if plot:
            plt.gca().plot(self._data.index, self._data.d2y)
        return self._data["d2y"]

    def resample(self, step, xlimits=(None, None), spline_order=1):
        logging.debug(f"Resampling with step={step}, xlimits={xlimits}, spline_order={spline_order}")
        from scipy.interpolate import interp1d

        xmin = xlimits[0] if xlimits[0] else self.xmin
        xmax = xlimits[1] if xlimits[1] else self.xmax
        xi = np.arange(xmin, xmax, step)

        f = interp1d(self.x, self.y, kind=spline_order, fill_value="extrapolate")
        self._data = pd.DataFrame(data=f(xi), index=xi, columns=["y"])
        return self

        
    def rescale_intensity(self):
        from skimage.exposure import rescale_intensity
        self.y = rescale_intensity(self.data.values, out_range=(0,1))
        
    def plot(self, ax=None, xlabel=None, ylabel=None, label=None, title=None, *a, **kw):
                
        if ax is None:
            ax = plt.gca()  # Get the current axis if none is provided
            
        logging.debug(f"Plotting with xlabel={xlabel}, ylabel={ylabel}, label={label}")
        xlabel = xlabel if xlabel else self.xlabel
        ylabel = ylabel if ylabel else self.ylabel
        label = label or self.title 

        ax.plot(self.x, self.y, label=label, *a, **kw)
        if not ax.get_title() and title:  
            ax.set_title(title)

        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        plt.legend()

            
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



    def display(self, x=None, y=None, plot=True):
        logging.debug(f"Displaying with x={x}, y={y}, plot={plot}")
        plt.plot(self.data.index, self.data.y)
        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        if plot:
            plt.show()




class RamanSpectrum(BaseSpectrum):
    
    def __init__(self, path=None, data=None, header=None):
        logging.debug(f"RamanSpectrum init, type: {type(self)}")
        super().__init__(path=path, data=data, header=header) 


                
    def plot_with_peaks(self, ax=None, title=None, *a, **kw):
        """
        rmph   realtive minimum peak height = mph/max
        mpd    default=1. Detect peaks that are at least separated by minimum peak distance (in number of data)
        rthr   relative threshold (default=0). Detect peaks (valleys) that are greater (smaller) than threshold in relation to their immediate neighbors = thr/max
        """
        
        
        if ax is None:
            ax = plt.gca()  # Get the current axis if none is provided
        
        super().plot(ax=ax, title=title, *a, **kw)  # Call the plot method of the Spectrum class
        
        peaks = self.find_peaks(rmph=.001, mpd=10, rthr=.000005, smooth=11)
        self.plot_peaks(rng=(100,3000), peaks=peaks, fontsize=8, decimals=0, color="#999999")    

        
        
      
    



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
        plt.gca().invert_xaxis()  # Reverse the x-axis
        super().plot(*a, **kw)  # Call the plot method of the Spectrum class


        
               
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
        





# Example of usage:
if __name__ == "__main__":
    
        # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        
    # Sample usage of the Spectrum class
    path = '/home/m/Dropbox/appy/qq/qq/spectrum/test/180427-7_manila_kopal.jdx'
    header = {'TITLE': 'Sample Spectrum', 'XUNITS': 'cm^-1', 'YUNITS': 'Intensity', 'DATATYPE': 'INFRARED SPECTRUM'}
    spectrum = Spectrum(path=path, header=header)
    # ~ print(spectrum.x, type(spectrum.x))
    # Display basic info
    # ~ spectrum.info()
    
    # Plot spectrum
    spectrum.plot()

