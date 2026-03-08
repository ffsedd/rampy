#!/usr/bin/env python3

import re
from six import string_types
from pathlib import Path
import logging

import pandas as pd
import numpy as np



# CONSTANTS - digit compression codes

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



def main():
    pass

 




class SpectrumParser:
    
    ''' Load data from file. Parse x, y values and metadata. Manipulate parent spectrum. '''

    def __init__(self, spectrum):
        
        '''Parent spectrum to be changed.'''
        self.spectrum = spectrum



    def loadtxt(self, fpath):
        # try to read data from txt file

        with open(fpath, 'rb') as f:
            lines = f.readlines()

        # ~ self.fpath = fpath
        # ~ self.filename = qq.misc.fname(fpath)
        # ~ self.filestem = qq.misc.fstem(fpath)
        # ~ print("spectrum loaded", fpath)

        y = []
        x = []

        for l in lines:

            if not l:
                continue
            try:
                l = l.decode('utf-8','ignore').strip()
                # print(l)
                # x y can be separated by whitespace, comma, semicolon, tab
                l = re.sub("\s+", ";", l)
                l = re.sub(",", ";", l)
                
                xi,yi = l.split(";")
                # print(l)
                x.append(float(xi))
                y.append(float(yi))
                #xnum += 1

            except Exception as e:
                print("skip... ", l, e)
        
        try:
            # print(x, y)
            self.spectrum.df = pd.DataFrame({'y': y}, index=x)
            # self.spectrum.x = np.array(x)
            # self.spectrum.y = np.array(y)
        except AttributeError:
            logging.error(f"Cannot parse spectrum, is it txt format? {fpath}")


    def loadspx(self, fpath):

        '''
        Read Bruker Jestream SPX spectrum
        Parameters
        ----------
        '''
        from brukerspx import Spx
        spx = Spx(fpath)

        self.spectrum.df = pd.DataFrame(spx.y, index=pd.Series(spx.x, name="x"), columns=["y"])

        #print( self.spectrum.df)

        spx_atts = [a for a in dir(spx) if a[0] != "_"]      
        s_atts = [a for a in dir(self.spectrum) if a[0] != "_"]          
        for a in spx_atts:
            if not a.lower() in s_atts:  # update existing attributes only
                continue
            if a in ("x","y"):  # already set 
               continue    
            print(a)    
            setattr(self.spectrum, a.lower(), getattr(spx, a))


    def loadxls(self, fpath):

        '''
        Read Bruker Jestream XLS spectrum
        Parameters
        ----------
        '''
        df = pd.read_excel(fpath, skiprows=20, index_col=1)

        df.index.names = ["x"]
        df = df[["Counts"]]
        self.spectrum.df = df
        

        

    def loadmsa(self, fpath):

        '''
        Read a MSA-format file, and return a dictionary containing the header info, a 1D numpy vectors `x` for
        the abscissa information (e.g. wavelength or wavenumber) and `y` for the ordinate information (e.g.
        transmission).
        Parameters
        ----------

        '''

        # TODO: parse xunit, yunit.....

        df = pd.read_csv(fpath, sep=",", comment='#', skip_blank_lines=True, index_col=0, names=["y"])

        df.index.names = ["x"]
        # ~ print(df)
#        df.Counts = df.Counts.fillna(0)

        self.spectrum.df = df


    def loadjdx(self, fpath):

        '''
        Read a Spectrum-format file, and return a dictionary containing the header info, a 1D numpy vectors `x` for
        the abscissa information (e.g. wavelength or wavenumber) and `y` for the ordinate information (e.g.
        transmission).
        Parameters
        ----------

        '''

        with open(fpath, 'rb') as f:
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
                # print(lhs,rhs)
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

        self.spectrum.df = pd.DataFrame(y, index=x)


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



##=====================================================================================================


if __name__ == "__main__":

    main()




