#!/usr/bin/env python3

import numpy as np
import re
import os
from six import string_types
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime

#import sys

import qq

# CONSTANTS

SQZ_digits = {
    '@':'+0', 'A':'+1', 'B':'+2', 'C':'+3', 'D':'+4', 'E':'+5', 'F':'+6', 'G':'+7', 'H':'+8', 'I':'+9',
    'a':'-1', 'b':'-2', 'c':'-3', 'd':'-4', 'e':'-5', 'f':'-6', 'g':'-7', 'h':'-8', 'i':'-9',
    '+':'+', ## For PAC
    '-':'-', ## For PAC
    ',':' ', ## For CSV
}
DIF_digits = {
    '%': 0, 'J':1,  'K':2,  'L':3,  'M':4,  'N':5,  'O':6,  'P':7,  'Q':8,  'R':9,
            'j':-1, 'k':-2, 'l':-3, 'm':-4, 'n':-5, 'o':-6, 'p':-7, 'q':-8, 'r':-9,
}
DUP_digits = {
    'S':1, 'T':2, 'U':3, 'V':4, 'W':5, 'X':6, 'Y':7, 'Z':8, 's':9,
}

class Jdx(object):
    """

    Attributes:
    """

    def __init__(self, filepath='', title=None, txt_sep=";"):
        """    """

        self.dataprocessing = ''
        self.datatype = ''
        self.date = None
        self.end = ''
        self.jcampdx = '5.01'
        self.maxx = 0.0
        self.maxy = 0.0
        self.minx = 0.0
        self.miny = 0.0
        self.origin = ''
        self.owner = ''
        self.time = None
        self.samplingprocedure = ''
        self.spectrometerdatasystem = ''
        self.txt_sep = txt_sep

        self.x = ''
        self.xfactor = 1.0
        self.xunits = ''
        self.xydata = ''
        self.y = ''
        self.yfactor = 1.0
        self.yunits = ''

        self.title = title


        if filepath:
            if not os.path.isfile(filepath):
                raise OSError(f"file not found {filepath}")
#            print(filepath)
            self._jdx_from_file(filepath)
        else:
            # print("no valid filepath", filepath)
            self.filepath = Path("new.jdx")
            self.date = datetime.now()



#        self.to_transmittance()

    @property
    def filename(self):
        return self.filepath.name

    @property
    def filestem(self):
        return self.filepath.stem

    @property
    def fileext(self):
        return self.filepath.suffix.lower()

    def get_firstx(self):
        return self.x[0]

    def get_firsty(self):
        return self.y[0]

    def get_lastx(self):
        return self.x[-1]

    def get_maxx(self):
        return max(self.x)

    def get_minx(self):
        return min(self.x)

    def get_maxy(self):
        return max(self.y)

    def get_miny(self):
        return min(self.y)

    def get_npoints(self):
        return len(self.x)

    def get_deltax(self):
        x = self.x
        deltax = abs(x[0] - x[-1]) / (len(x) - 1)
        return round(deltax, 3)

    def _jdx_from_file(self,  filepath):
        self.filepath = Path(filepath).resolve()

        if self.fileext == ".jdx":
            self.loadjdx(filepath)
            self.tidy()

        elif self.fileext == ".spa":
            self.from_spa(self.filepath)
            self.tidy()

        elif self.fileext == ".scn":
            self.from_scn(self.filepath)

        else:
            self.loadtxt(filepath)

    def __add__(self, other):
        new = Jdx()
        new.__dict__.update(self.__dict__)
        new.y = self.y + other.y
        print("added", self.title, other.title)
        return new

    def __sub__(self, other):
        new = Jdx()
        new.__dict__.update(self.__dict__)
        new.y = self.y - other.y
        print("subtracted", self.title, other.title)
        return new


    def __mul__(self, num):
        new = Jdx()
        new.__dict__.update(self.__dict__)
        new.y = num * self.y
        print("multiplied", self.title, num)
        return new

    __rmul__ = __mul__

    def __truediv__(self, num):
        new = Jdx()
        new.__dict__.update(self.__dict__)
        new.y = self.y / num
        print("divided", self.title, num)
        return new

    def _is_float(self, s):
        '''
        Test if a string, or list of strings, contains a numeric value(s).
        Parameters
        ----------
        s : str, or list of str
            The string or list of strings to test.
        Returns
        -------
        is_float_bool : bool or list of bool
            A single boolean or list of boolean values indicating whether each input can be converted into a float.
        '''

        if isinstance(s,tuple) or isinstance(s,list):
            if not all(isinstance(i, string_types) for i in s):
                raise TypeError("Input {} is not a list of strings".format(s))
            if (len(s) == 0):
                raise ValueError('Input {} is empty'.format(s))
            else:
                bool = list(True for i in range(0,len(s)))
                for i in range(0,len(s)):
                    try:
                        float(s[i])
                    except ValueError:
                        bool[i] = False
            return(bool)
        else:
            if not isinstance(s, string_types):
                raise TypeError("Input '%s' is not a string" % (s))

            try:
                float(s)
                return(True)
            except ValueError:
                return(False)


    def _get_value(self, num, is_dif, vals):
        n = float(num)
        if is_dif:
            lastval = vals[-1]
            val = n + lastval
        else:
            val = n
        return val



    def _jcamp_parse(self, line):
        line = line.strip()

        datavals = []
        num = ""

        ## Convert whitespace into single space by splitting the string then re-assembling with single spaces.
        line = ' '.join(line.split())

        ## If there are any coded digits, then replace the codes with the appropriate numbers.
        str_DUP_digits = ''.join(DUP_digits.keys())
        if any(i in 'line' for i in str_DUP_digits):
            ## Split the line into individual characters so that you can check for coded characters one-by-one.
            newline = list(line[:])
            offset = 0
            for (i,c) in enumerate(line):
                if (c in DUP_digits):
                    prev_c = line[i-1]
                    mul = DUP_digits[c]
                    newline.pop(i + offset)
                    for j in range(mul - 1):
                        newline.insert(i + offset, prev_c)
                    offset += mul
            line = "".join(newline)

        DIF = False
        for c in line:
            if c.isdigit() or (c == "."):
                num += c
            elif (c == ' '):
                DIF = False
                if num:
                    n = self._get_value(num, DIF, datavals)
                    datavals.append(n)
                num = ''
            elif (c in SQZ_digits):
                DIF = False
                if num:
                    n = self._get_value(num, DIF, datavals)
                    datavals.append(n)
                num = SQZ_digits[c]
            elif (c in DIF_digits):
                if num:
                    n = self._get_value(num, DIF, datavals)
                    datavals.append(n)
                DIF = True
                num = str(DIF_digits[c])
            elif c == '?': #  NA values
                num += 'nan'
                # raise Exception("Data contain ? characters," % c)
            else:
                raise Exception("Unknown character (%s) encountered while parsing data" % c)

        if num:
            n = self._get_value(num, DIF, datavals)
            datavals.append(n)

        return datavals


    def tidy(self):
        '''
        X to wavenumbers
        Y to absorbance
        clip Y axis
        clear CO2
        round
        '''

        ## X to wavenumbers
        if self.xunits.lower() in ('1/cm' ,'cm-1', 'cm^-1', 'cm ^ -1'):
            pass
        elif (self.xunits.lower() in ('micrometers','um','wavelength (um)')):
            self.x = 10000.0 / self.x
        elif (self.xunits.lower() in ('nanometers','nm','wavelength (nm)')):
            self.x = 10000 * 1000.0 / self.x
        else:
            print('Don\'t know how to convert the spectrum\'s x units ("' + self.xunits + '") to wavenumbers.')
        self.xunits='1/CM'

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

        self.clear()

        self.x = signif(self.x, 6)
        self.y = signif(self.y, 8)


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

    def loadjdx(self, filepath):

        '''
        Read a JDX-format file, and return a dictionary containing the header info, a 1D numpy vectors `x` for
        the abscissa information (e.g. wavelength or wavenumber) and `y` for the ordinate information (e.g.
        transmission).
        Parameters
        ----------

        '''

        with open(filepath, 'rb') as f:
            filedata = f.readlines()




        lines = [line.decode('utf-8','ignore').strip() for line in filedata]

 #       pprint.pprint(lines[:30])    # print 30 lines

        xstart = []
        xnum = []
        y = []
        x = []
        datastart = False
        re_num = re.compile(r'\d+')


        for line in lines:
            if not line:
                continue
            if line.startswith('$$'):
                continue
            ## --------------
            ## PARSE HEADER
            ## --------------
            if line.startswith('##'):
                line = line.strip('##')
                (lhs,rhs) = line.split('=', 1)
                lhs = lhs.strip().lower()
                lhs = re.sub(r'\W+', '', lhs)   # remove non alnum. chars (cannot be used as object attribute name)
                rhs = rhs.strip()
                #continuation = rhs.endswith('=')
                #print(lhs,rhs)

                try:
                    if lhs.upper() == "TITLE" and rhs:
                        self.title = rhs
                        continue

                    if lhs.upper() == "DATE" and rhs:
                        self.date = datetime.strptime(rhs, '%y/%m/%d')
                        continue

                    if lhs.upper() == "LONGDATE" and rhs:
                        self.date = datetime.strptime(rhs, '%Y/%m/%d')
                        print("longdate,", rhs, self.date)
                        continue

                    if lhs.upper() == "TIME" and rhs:
                        self.time = datetime.strptime(rhs, '%H:%M:%S').time()
                        continue
                except ValueError as e:
                    print(e)
                    continue

                if rhs.isdigit():
                    setattr(self, lhs, int(rhs))
                elif self._is_float(rhs):
                    setattr(self, lhs, float(rhs))
                else:
                    setattr(self, lhs, str(rhs))

                if lhs in ('xydata','xypoints','peak table'):
                    ## This is a new data entry, reset x and y.
                    x = []
                    y = []
                    datastart = True
                    valtype = rhs
                    xvaltype = rhs
                    continue        ## data starts on next line
                elif lhs == 'end':
                    bounds = [int(i) for i   in re_num.findall(rhs)]
                    datastart = True
                    valtype = bounds
#                    datalist = []
                    continue
                elif datastart:
                    datastart = False

            if self.time and self.date:
                self.date = datetime.combine(self.date, self.time)

            ## --------------
            ## PARSE DATA
            ## --------------
            if datastart and (xvaltype == '(X++(Y..Y))'):
                ## If the line does not start with '##' or '$$' then it should be a data line.
                ## The pair of lines below involve regex splitting on floating point numbers and integers. We can't just
                ## split on spaces because JCAMP allows minus signs to replace spaces in the case of negative numbers.
                datavals = self._jcamp_parse(line)
                xstart.append(float(datavals[0]))
                xnum.append(len(datavals) - 1)
                for dataval in datavals[1:]:
                    y.append(float(dataval))

            elif datastart and (xvaltype == '(XY..XY)'):
                datavals = [v.strip() for v in re.split(r"[, ]", line) if v]  ## be careful not to allow empty strings
                if not all(self._is_float(datavals)): continue
                datavals = np.array(datavals)
                x.extend(datavals[0::2])        ## every other data point starting at the zeroth
                y.extend(datavals[1::2])        ## every other data point starting at the first

            elif datastart and isinstance(valtype,list):
                ## If the line does not start with '##' or '$$' then it should be a data line.
                ## The pair of lines below involve regex splitting on floating point numbers and integers. We can't just
                ## split on spaces because JCAMP allows minus signs to replace spaces in the case of negative numbers.
                datavals = self._jcamp_parse(line)
                raise BaseException("datavalsname not defined")
#                datalist += datavalsname
                datastart = False
        # print(xvaltype)
        ## --------------
        ## WRITE TO OBJECT
        ## --------------
        if (xvaltype == '(X++(Y..Y))'):
            ## You got all of the Y-values. Next you need to figure out how to generate the missing X's...
            ## First look for the "lastx" dictionary entry. You will need that one to finish the set.
            xstart.append(self.lastx)
            x = np.array([])

            for n in range(len(xnum)-1):
                dx = (xstart[n+1] - xstart[n]) / xnum[n]
                x = np.append(x, xstart[n]+(dx*np.arange(xnum[n])))
                #print(n, xstart[n], xstart[n+1], xnum[n], xstart[n]+(dx*np.arange(xnum[n])))

            ## The last line must be treated separately.
            if (xnum[len(xnum)-1] > 1):
                dx = (self.lastx - xstart[len(xnum)-1]) / (xnum[len(xnum)-1] - 1.0)
                x = np.append(x, xstart[len(xnum)-1]+(dx*np.arange(xnum[len(xnum)-1])))
                #print(n, xstart[len(xnum)-1]+(dx*np.arange(xnum[len(xnum)-1])))
            else:
                x = np.append(x, self.lastx)
            y = np.array([float(yval) for yval in y])
        else:
            x = np.array([float(xval) for xval in x])
            y = np.array([float(yval) for yval in y])

        ## The "xfactor" and "yfactor" variables contain any scaling information that may need to be applied
        ## to the data. Go ahead and apply them.
        x *= self.xfactor
        y *= self.yfactor

        self.x = x
        self.y = y

        print("spectrum loaded",filepath, self.title)
        
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



    def from_spa2(self, fpath):
        """Convert SPA file to JDX"""
        fp = Path(fpath)
        self.y, self.x, self.title = read_spa(fp)

        self.datatype = "INFRARED SPECTRUM"
        self.xunits='1/CM'
        self.yunits = "ABSORBANCE"
        self.fpath = fp.parent / (fp.stem + "_spa.jdx")


    def from_spa(self, fpath):
        """Convert SPA file to JDX"""
        from zumpy.ir.read.spa import Spa


        fp = Path(fpath)
        s = Spa(fp)
        self.__dict__.update(s.__dict__)

    def from_scn(self, fpath):
        """Convert SPA file to JDX"""
        from zumpy.ir.read.scn import Scn


        fp = Path(fpath)
        s = Scn(fp)
        self.__dict__.update(s.__dict__)


    def loadtxt(self, filepath):
        # try to read data from txt file

        with open(filepath, 'rb') as f:
            lines = f.readlines()

        self.filepath = Path(filepath)
#        self.filename = self.filepath.name
#        self.filestem = self.filepath.stem
        print("spectrum loaded", filepath, self.title)

        y = []
        x = []

        for l in lines:

            if not l:
                continue
            try:
                l = l.decode('utf-8','ignore').strip()
                # ~ print(l)
                # x y can be separated by whitespace, comma, semicolon, tab
                xi,yi = re.split(' ?, ?| ?; ?|\t|\s+',l)[:2]
#                l = re.sub("\s+", ";", l)
#                l = re.sub(",", ";", l)
#                l = re.sub(",", ";", l)
#                xi,yi = l.split(";")
                # ~ print(yi, len(yi))
                x.append(float(xi.strip()))
                y.append(float(yi.strip()))
                #xnum += 1

            except Exception as e:
                print("skip... ", l, e)

        self.x = np.array(x)
        self.y = np.array(y)


    def _sort_xy(self):
        xy = np.array( list(zip(self.x,self.y)), dtype=[('x',float),('y',float)])
        xy.sort(order=['x'])
        self.x = xy['x']
        self.y = xy['y']


    def to_transmittance(self):
        if self.yunits.lower() == "absorbance":
            self.y = 10**(-self.y)
            self.yunits = "TRANSMITTANCE"

    def to_absorbance(self):
        if self.yunits.lower() == "transmittance":
                ## If in transmittance, then any y > 1.0 are unphysical.
            self.y[self.y > 1.0] = 1.0
                ## Convert to absorbance.
            okay = (self.y > 0.0)
            self.y[okay] = -np.log10(self.y[okay])
            self.y[~okay] = np.nan
            self.yunits = "ABSORBANCE"

    def save(self, out_fp=None):


        if not out_fp:
            if self.filepath:
                out_fp = self.filepath.with_suffix(".jdx")
            else:
                raise BaseException("jdx save filepath undefined")

        out_fp = Path(out_fp)

        if out_fp.is_file():
            out_fp.rename(out_fp.with_suffix(".bak"))
        # sort data
        self._sort_xy()

        yfactor = 1

        #  data to string
        data = ""
        for x, y in zip(self.x,self.y):
            # data += "{:.2f} {:.8f}\n".format(x[i],y[i])
            data += f"{round(x,3)} {round(y/yfactor,8)}\n"

        data = data.replace("nan","?")

        #(##LASTX= minus ##FIRSTX=)/(##NPOINTS= minus 1).

        if self.date:
            date = "{:%y/%m/%d}".format(self.date)
            longdate = "{:%Y/%m/%d}".format(self.date)
            time = "{:%H:%M:%S}".format(self.date)
        else:
            date = ""
            longdate = ""
            time = ""

        header = "\n".join([
            f"##TITLE={self.title}",
            "##JCAMP-DX=5.01",
            f"##DATA TYPE={self.datatype.upper()}",
            f"##SAMPLING PROCEDURE={self.samplingprocedure}",
            f"##ORIGIN={self.origin}",
            f"##OWNER={self.owner}",
            f"##DATE={date}",
            f"##TIME={time}",
            f"##LONGDATE={longdate}",
            f"##DATA PROCESSING={self.dataprocessing}",
            f"##SPECTROMETER/DATA SYSTEM={self.spectrometerdatasystem}",
            f"##XUNITS={self.xunits.upper()}",
            f"##YUNITS={self.yunits.upper()}",
            f"##MAXY={self.get_maxy()}",
            f"##MINY={self.get_miny()}",
            f"##MAXX={self.get_maxx()}",
            f"##MINX={self.get_minx()}",
            f"##XFACTOR=1",
            f"##YFACTOR={yfactor}",
            f"##FIRSTX={self.get_firstx()}",
            f"##LASTX={self.get_lastx()}",
            f"##FIRSTY={self.get_firsty()}",
            f"##NPOINTS={self.get_npoints()}",
            f"##DELTAX={self.get_deltax()}",
            # "##XYDATA=(X++(Y..Y)) ",
            f"##XYDATA=(XY..XY) \n", # works in Omnic
            ]
            )
        footer = "##END= \n"

        with open(out_fp ,"w") as f:
            f.write(header + data + footer)

        print("saved: ", out_fp)


    def clear(self, bounds=(2250,2450), interp=True):
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


    def smooth(self, window_size=31, **kw):
        from qq.ntool.smooth import smooth_golay
        self.y = smooth_golay(self.y, window_size=window_size, **kw)

    def plot_peaks(self, rng=(0,3000), xoffset=0, fontsize=8, **kw):

        peaks_xy = self.find_peaks(**kw)

        ax = plt.gca()
        for px, py in peaks_xy:

            if rng[0] < px < rng[1]: # ignore out of range peaks
                #print(px,py)
                ax.annotate(int(px), xy=(px, py), xytext=(px + xoffset, py), fontsize=fontsize)


    def find_peaks2(self, mph=-.5, mpd=20, threshold=.000001, **kw):
        from qq.ntool.detect_peaks import detect_peaks
        
        valley = (self.yunits.lower() in ('transmittance', 'reflectance')) # upside down 

        peaks_i = detect_peaks(self.y,
                               mph=mph,
                               mpd=mpd,
                               threshold=threshold,
                               edge='rising',
                               kpsh=False,
                               valley=valley,
                               show=False,
                               ax=None)
        peaks_y = self.y[peaks_i]
        peaks_x = self.x[peaks_i]

        return list(zip(peaks_x, peaks_y))

    def find_peaks(self):
        """
        height      number or ndarray or sequence, optional

            Required height of peaks. Either a number, None, an array matching x or a 2-element sequence of the former.
            The first element is always interpreted as the minimal and the second, if supplied, as the maximal required height.

        threshold       number or ndarray or sequence, optional

            Required threshold of peaks, the vertical distance to its neighboring samples.
            Either a number, None, an array matching x or a 2-element sequence of the former.
            The first element is always interpreted as the minimal and the second, if supplied, as the maximal required threshold.

        distance    number, optional

            Required minimal horizontal distance (>= 1) in samples between neighbouring peaks.
            Smaller peaks are removed first until the condition is fulfilled for all remaining peaks.

        prominence      number or ndarray or sequence, optional

            Required prominence of peaks. Either a number, None, an array matching x or a 2-element sequence of the former.
            The first element is always interpreted as the minimal and the second, if supplied, as the maximal required prominence.

        width   number or ndarray or sequence, optional

            Required width of peaks in samples. Either a number, None, an array matching x or a 2-element sequence of the former.
            The first element is always interpreted as the minimal and the second, if supplied, as the maximal required width.

        wlen    int, optional

            Used for calculation of the peaks prominences, thus it is only used if one of the arguments prominence or width is given.
            See argument wlen in peak_prominences for a full description of its effects.

        rel_height  float, optional

            Used for calculation of the peaks width, thus it is only used if width is given.
            See argument rel_height in peak_widths for a full description of its effects.

        plateau_size    number or ndarray or sequence, optional

            Required size of the flat top of peaks in samples. Either a number, None, an array matching x or a 2-element sequence of the former.
            The first element is always interpreted as the minimal and the second, if supplied as the maximal required plateau size.

        """
        try:
            from scipy.signal import find_peaks
        except ImportError:
            return self.find_peaks2()

        if self.yunits.lower() in ('transmittance', 'reflectance'): # upside down
            y = -self.y
        else:
            y = self.y
            
        peaks, _ = find_peaks(y,
                   height=None,
                   threshold=None,
                   distance=40,
                   prominence=.005,
                   width=5,
                   wlen=None,
                   rel_height=0.5,
                   plateau_size=None)
        peaks_y = self.y[peaks]
        peaks_x = self.x[peaks]
        return list(zip(peaks_x, peaks_y))



    def baseline_correction(self, plot=False):
        from scipy import sparse
        from scipy.sparse.linalg import spsolve
        # ~ from scipy.optimize import curve_fit


        niter = 10
        lam = 2e7
        p = 0.005

        y = self.y

        L = len(y)
        D = sparse.diags([1,-2,1],[0,-1,-2], shape=(L,L-2))
        w = np.ones(L)
        for i in range(niter):
            W = sparse.spdiags(w, 0, L, L)
            Z = W + lam * D.dot(D.transpose())
            z = spsolve(Z, w*y)
            w = p * (y > z) + (1-p) * (y < z)

        corr = y - z
        if np.isnan(corr).all():
            print("baseline correction failed")
            return

        #%% Plot spectrum, baseline and corrected spectrum
        if plot:
            plt.clf()
            plt.plot(y)
            plt.plot(z)
            plt.plot(corr)
            plt.gca().invert_xaxis()
            plt.show()

        self.y = corr

    def calibrate_x(self, x_values_old=(906.7, 2850.7), x_values_new=(906.7, 2850.7)):
        '''Two point calibration of x axis. 
        x_values_old : tuple of float, eg (907.7, 2861.9)
        x_values_new : tuple of float, eg (906.7, 2850.7)
        '''
        
        if x_values_new == x_values_old:
            return
        
        from scipy.interpolate import interp1d

        # rescale x axis
        o1, o2 = x_values_old
        n1, n2 = x_values_new
        x_corr = n1 + (self.x - o1) / (o2 - o1) * (n2 - n1)
        
        # interpolate y to old x axis
        f = interp1d(x_corr, self.y, fill_value="extrapolate")
        y_new = f(self.x)
        self.y = y_new





def read_spa(filepath):
    '''
    Input
    Read a file (string) *.spa
    ----------
    Output
    Return spectra, Wavenumbers (cm-1), titles
    '''
    with open(filepath, 'rb') as f:
        f.seek(564)
        Spectrum_Pts = np.fromfile(f, np.int32,1)[0]
        print(Spectrum_Pts)

        f.seek(30)
        SpectraTitles = np.fromfile(f, np.uint8,255)
        SpectraTitles = ''.join([chr(x) for x in SpectraTitles if x!=0])
        print(SpectraTitles)

        f.seek(576)
        Max_Wavenum=np.fromfile(f, np.single, 1)[0]
        Min_Wavenum=np.fromfile(f, np.single, 1)[0]
        print(Max_Wavenum, Min_Wavenum)


        Wavenumbers = np.linspace(Min_Wavenum, Max_Wavenum, num=Spectrum_Pts, endpoint=True, dtype=float)
        Wavenumbers = np.flip(Wavenumbers)

        f.seek(288);

        Flag=0
        while Flag != 3:
            Flag = np.fromfile(f, np.uint16, 1)

        DataPosition=np.fromfile(f,np.uint16, 1)
        f.seek(DataPosition[0])

        Spectra = np.fromfile(f, np.single, Spectrum_Pts)
    return Spectra, Wavenumbers, SpectraTitles

def signif(x, p):
    x = np.asarray(x)
    x_positive = np.where(np.isfinite(x) & (x != 0), np.abs(x), 10**(p-1))
    mags = 10 ** (p - 1 - np.floor(np.log10(x_positive)))
    return np.round(x * mags) / mags

##=====================================================================================================


def main():

    indir = Path("/home/m/Dropbox/appy/zumpy/zumpy/ir/test/")

    fps = sorted(list(indir.glob("*.jdx")))


    # create objects
    spectra = [ Jdx(fp) for fp in fps ]

    # plot all
    first = True
    for s in spectra:
#        s.datatype = "RAMAN SPECTRUM"
        s.info()
        s.clear()
        s.smooth()
        s.to_absorbance()
        s.plot()

        if first:
            s.plot_peaks()
            first = False
        # s.save(indir)

#    y = s + s
#    y.plot()
#    z = s * 4
#    z.clear()
#    z.plot()
#    a = y / 3
#    a.plot()

#    c = 10 * s + 30 * s
#    c.plot()

    # print(zip(s.x,s.y))

    plt.tight_layout()
    plt.show()



if __name__ == "__main__":
    main()


