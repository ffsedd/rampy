#!/usr/bin/env python3
'''
'''

import pandas as pd
import logging
import numpy as np
from pathlib import Path
import re
from pprint import pprint
import jcamp
import dateutil
import xmltodict



def main():
    
    
    f = Path("/home/m/Dropbox/appy/qq/qq/spectrum/test_spectra/Crocoite__R050044-3__Raman__514__0__depolarized__Raman_Data_Processed__4672.jdx")
    f = Path("/home/m/Y/JETSTREAM/2024/J2425_Schwarzenberg/j490_J2425_bottom-left__100-850-20/MULTIPOINT/11.spx")
    s = SpectrumIO(f).read()
    print(s)
    
    
    print(f"{Path(__file__).resolve()} finished")

def format_float(number, significant_digits=7):
    """
    Format a float number with a specified number of significant digits.
    
    Args:
        number (float): The float number to be formatted.
        significant_digits (int): The number of significant digits. Default is 8.
    
    Returns:
        str: The formatted string representing the float number.
    """
    # Convert the float number to a string with scientific notation and desired precision
    formatted_number = '{:.{}g}'.format(number, significant_digits)

    # Check if the formatted number contains a decimal point
    if '.' in formatted_number:
        integer_part, decimal_part = formatted_number.split('.')
        # Remove trailing zeros from the decimal part
        decimal_part = decimal_part.rstrip('0')
        # Remove the decimal point if the decimal part is empty
        formatted_number = integer_part + '.' + decimal_part if decimal_part else integer_part
    return formatted_number


def add_line_breaks(strings, max_length=80, break_str="\n      "):

    broken_list = []
    
    for item in strings:
        if len(item) > max_length:
            modified_item = ''
            for i in range(0, len(item), max_length):
                modified_item += item[i:i+max_length]
                if i <= len(item)-max_length:
                    modified_item +=  break_str
            broken_list.append(modified_item)
        else:
            broken_list.append(item)
    
    return broken_list


class SpectrumIO:
    
    def __init__(self, path):
        # logging.debug("SpectrumIO", path)
        self.path = Path(path)
        
    @property
    def suffix(self):
        return self.path.suffix.lower()
    
    def read(self):
        header = {
                'TITLE':'',
                'XUNITS':'',
                'YUNITS':'',
                'SIGNALTYPE':'',
                'DATATYPE':'',
                'SAMPLE DESCRIPTION':'',
                'NAMES':'',
                'CAS NAME':'',
                'CAS REGISTRY NO':'',
                'SPECTROMETER/DATA SYSTEM':'',
                'SAMPLING PROCEDURE':'',
                'MOLFORM':'',
                'COLOR':'',
                'LASER':'',
                'COMMENTS':'',
                          }
        data = None
        if self.suffix.lower() == '.csv':
            h, data = CSVSpectrumParser(self.path).parse()
        elif self.suffix.lower() == '.msa':
            h, data = MSASpectrumParser(self.path).parse()
        elif self.suffix.lower() == '.spx':
            h, data = SPXSpectrumParser(self.path).parse()
        elif self.suffix.lower() == '.jdx':
            h, data = JDXSpectrumParser(self.path).parse()

        if data is None:
            raise ValueError(f"Spectrum data missing: {self.path}")
        

    
        
        header.update(h)
        
        return header, data
    
    def write(self, spectrum):
        if self.suffix.lower() == '.csv':
            logging.error("write to csv NOT IMPLEMENTED")
        elif self.suffix.lower() == '.msa':
            self.write_to_msa(spectrum)
        elif self.suffix.lower() == '.jdx':
            self.write_to_jdx(spectrum)
            
    def write_to_jdx(self, spectrum):

        path = self.path

        if path.is_file():
            path.rename(path.with_suffix(".bak"))
            
        yfactor = 1
        #  data to string
        data = ""
        for x, y in zip(spectrum.x,spectrum.y):
            data += f"{format_float(x)} {format_float(y/yfactor)}\n"  # 7 significant digits
        data = data.replace("nan","?")
        dt = spectrum.header.get('DATE','')
        if dt:
            if type(dt) == str:
                dt = dateutil.parser.parse(dt)
            # ~ print(d)
            date = f"{dt:%y/%m/%d}"
            longdate = f"{dt:%Y/%m/%d}"
            time = f"{dt:%H:%M:%S}"
        else:
            date = ""
            longdate = ""
            time = ""

        comment_lines = spectrum.header.get('COMMENTS',"").replace("',","',\n ").split("\n")
        header_lines = [
            # 6.1
            f"##TITLE={spectrum.title}",
            "##JCAMP-DX=5.01",
            f"##DATA TYPE={spectrum.datatype.upper()}",
            # 6.2    
            f"##XUNITS={spectrum.xunits.upper()}",
            f"##YUNITS={spectrum.yunits.upper()}",
            f"##MAXY={spectrum.ymax}",
            f"##MINY={spectrum.ymin}",
            f"##MAXX={spectrum.xmax}",
            f"##MINX={spectrum.xmin}",
            "##XFACTOR=1",
            f"##YFACTOR={yfactor}",
            f"##FIRSTX={spectrum.x[0]}",
            f"##LASTX={spectrum.x[-1]}",
            f"##FIRSTY={spectrum.y.iloc[0]}",
            f"##NPOINTS={len(spectrum.x)}",
            # 6.3
            f"##DELTAX={spectrum.deltax}",
            # 7.1
            f"##ORIGIN={spectrum.header.get('ORIGIN','')}",
            f"##OWNER={spectrum.header.get('OWNER','')}",
            f"##DATE={date}",
            f"##TIME={time}",
            f"##LONGDATE={longdate}",
            # 7.2        
            f"##SAMPLE DESCRIPTION={spectrum.header.get('SAMPLE DESCRIPTION','')}",
            f"##CAS NAME={spectrum.header.get('CAS NAME','')}",
            f"##NAMES={spectrum.header.get('NAMES','')}",
            f"##MOLFORM={spectrum.header.get('MOLFORM','')}",
            f"##CAS REGISTRY NO={spectrum.header.get('CAS REGISTRY NO','')}",
            # 7.3
            f"##SPECTROMETER/DATA SYSTEM={spectrum.header.get('SPECTROMETER/DATA SYSTEM','')}",
            # 7.4
            f"##SAMPLING PROCEDURE={spectrum.header.get('SAMPLING PROCEDURE','')}",    
            f"##DATA PROCESSING={spectrum.header.get('DATA PROCESSING','')}",
            # 7.5
            "##COMMENTS="
            ] + comment_lines + [ # multiline comment section
            f"##COLOR={spectrum.header.get('COLOR','')}",
            f"##LASER={spectrum.header.get('LASER','')}",
            # 6.4
            "##XYDATA=(XY..XY) \n", # works in Omnic
            ]
        footer = "##END= \n"
        header_lines = add_line_breaks(header_lines, max_length=160)
        header = "\n".join(header_lines)
        path.write_text(header + data + footer)
        logging.debug(f"spectrum saved: {path}")


class MSASpectrumParser:
    
    def __init__(self, path):
        # logging.debug("MSASpectrumParser", path)
        self.path = Path(path)        

    def parse(self):
        with open(self.path, 'r') as f:
            content = f.read().splitlines()
#        logging.debug(content)
        header = {}
        data_lines = []

        read_spectrum = False
        for line in content:
            if line.startswith('#'):
                if line.startswith('#SPECTRUM'):
                    read_spectrum = True
                elif line.startswith('#ENDOFDATA'):
                    break
                else:
                    line = line[1:].split(':', 1)
                    if len(line) == 2:
                        header[line[0].strip()] = line[1].strip()

            elif read_spectrum:
                values = line.split(',')
                if len(values) == 2:
                    x, y = map(float, values)
                    data_lines.append((x, y))

        data = pd.DataFrame(data_lines, columns=['x', 'y'])
        data.set_index('x', inplace=True)  # Setting 'x' as the index
        logging.debug(f"{header} {data}")
        if "SIGNALTYPE" in header and "eds" in header["SIGNALTYPE"].lower():
            header["datatype"] = "EDS spectrum"
        return header, data

    
    
class CSVSpectrumParser:
    
    def __init__(self, path):
        # logging.debug("CSVSpectrumParser", path)
        self.path = Path(path)        

    def parse(self):
        with open(self.path, 'r') as f:
            content = f.read().splitlines()
#        logging.debug(content)
        header = {"TITLE": self.path.stem}
        data_lines = []

        for line in content:
            if line.startswith('#'):  # skip header
               continue
            else:
                try:
                    line = re.sub("[ \t,;]\s?", ";", line) # separated by whitespace, comma, semicolon, tab
                    values = line.split(";")
                    data_lines.append([float(v) for v in values])
                except Exception as e:
                    logging.debug(f"skip line: {line} {e}")
        # ~ pprint(data_lines)

        data = pd.DataFrame(data_lines, columns=['x', 'y'])
        data.set_index('x', inplace=True)  # Setting 'x' as the index

        logging.debug(f"{header} {data}")

        return header, data


class SPXSpectrumParser:
    """
    Read Bruker Jestream SPX spectrum from a given file path.
    """
    
    def __init__(self, path):
        """
        Initialize the parser with the path to the spectrum file.
        
        Parameters
        ----------
        path : str or Path
            The file path to the spectrum file.
        """
        self.path = Path(path)

    def parse(self):
        """
        Parse the spectrum file and extract header and data.

        Returns
        -------
        header : dict
            Parsed header information.
        data : DataFrame
            Spectrum data with 'x' as index and 'y' as column.
        """
        header = {}

        with open(self.path, "rb") as file:
            xml_dict = xmltodict.parse(file.read())
        
        self._parse_header(xml_dict, header)
        data = self._parse_data(xml_dict, header)
        print("parsed", header, data)
        return header, data

    def _parse_header(self, xml_dict, header):
        """
        Parse the header information from the XML dictionary.

        Parameters
        ----------
        xml_dict : dict
            Dictionary parsed from XML file.
        header : dict
            Dictionary to store the parsed header information.
        """
        header["TITLE"] = xml_dict['TRTSpectrum']['ClassInstance']['@Name']

        xml_tree = xml_dict['TRTSpectrum']['ClassInstance']['TRTHeaderedClass']['ClassInstance']
        hardware_header = self._xmlnode_to_dict(xml_tree, 'TRTSpectrumHardwareHeader')
        header.update({k.upper(): v for k, v in hardware_header.items()})

        spectrum_header_tree = xml_dict['TRTSpectrum']['ClassInstance']['ClassInstance']
        spectrum_header = self._xmlnode_to_dict(spectrum_header_tree, 'TRTSpectrumHeader')
        header.update({k.upper(): v for k, v in spectrum_header.items()})
        
        self._convert_header_values(header)

        result_header = self._xmlnode_to_dict(spectrum_header_tree, 'TRTResult')
        if 'Result' in result_header:
            header['RESULT'] = result_header['Result']
        pprint(header)    

    def _convert_header_values(self, header):
        """
        Convert header values to appropriate data types.

        Parameters
        ----------
        header : dict
            Dictionary containing header information to be converted.
        """
        int_keys = ('SIZE', 'KV', 'MA', 'REALTIME', 'LIFETIME', 'ANODE', 
                    'CHANNELCOUNT', 'DETECTORCOUNT', 'PULSEDENSITY', 
                    'SELECTEDDETECTORS', 'SHAPINGTIME', 'AMPLIFICATION', 
                    'ZEROPEAKFREQUENCY', 'ZEROPEAKPOSITION')

        float_keys = ('CALIBABS', 'CALIBLIN', 'SIGMAABS', 'SIGMALIN')

        for key in int_keys:
            try:
                header[key] = int(header[key])
            except (KeyError, ValueError):
                pass
        
        for key in float_keys:
            try:
                header[key] = float(header[key])
            except (KeyError, ValueError):
                pass

    def _parse_data(self, xml_dict, header):
        """
        Parse the spectrum data from the XML dictionary.

        Parameters
        ----------
        xml_dict : dict
            Dictionary parsed from XML file.
        header : dict
            Dictionary containing header information.
        data : list
            List to store the parsed data.
        """
        xml_tree = xml_dict['TRTSpectrum']['ClassInstance']['Channels']
        
        x0 = header['CALIBABS']
        dx = header['CALIBLIN']
        x = np.arange(x0, dx * int(header['CHANNELCOUNT']) + x0, dx)
        header['XUNITS'] = "Energy [kV]"
        
        y = np.fromstring(xml_tree, dtype=int, sep=',')
        if header["REALTIME"]:
            y = y / header["REALTIME"] * 1000
            header['YUNITS'] = "Intensity [counts/s]"
        else:
            header['YUNITS'] = "Intensity [counts]"
        header['SIGNALTYPE'] = 'EDS_SEM'
        
        df = pd.DataFrame(y, index=pd.Series(x, name="x"), columns=["y"])
        return df

    def _xmlnode_to_dict(self, xml_tree, node_type):
        """
        Find nodes by type and convert them into a dictionary.

        Parameters
        ----------
        xml_tree : list
            List of XML nodes.
        node_type : str
            The type of node to search for.

        Returns
        -------
        dict
            Dictionary of the found node's items.
        """
        for node in xml_tree:
            if node['@Type'] == node_type:
                return dict(node.items())
        return {}

     
class JDXSpectrumParser:

    def __init__(self, path):
        # logging.debug("JDXSpectrumParser", path)
        self.path = Path(path)

    def parse(self):
        # ~ print(f"JDX {self.path}")
        with open(self.path, 'r') as f:
            j = jcamp.jcamp_read(f)
        # ~ pprint(j)
        data = self.xy_to_data(j["x"], j["y"])
        # ~ print(data)
        header = {k.replace(" ","").upper():v for k, v in j.items() if k not in ("x","y")}

        return header, data

    def parse2(self):
        with open(self.path, 'r') as f:
            content = f.read().splitlines()

        header = {}
        data_lines = []
        xx = []
        yy = []
        read_data = False

        for line in content:
            if line.startswith('##END='):
                break
            elif read_data:
                values = line.split()
                if len(values) == 2:
                    try:
                        x, y = map(float, values)
                        data_lines.append((x, y))
                        xx.append(x)
                        yy.append(y)
                    except ValueError:
                        logging.debug(f"Skipping invalid data line: {line}")    
            elif line.startswith('##XYDATA='):
                read_data = True
            elif line.startswith('##'):
                key, value = map(str.strip, line[2:].split('=', 1))
                header[key.upper()] = self._convert_numeric(value)
            else:
                header[key.upper()] += line # add line to multiline row   
        
        if 'DATA TYPE' in header:
            header['DATATYPE'] = header['DATA TYPE']
        else:
            header['DATATYPE'] = ''
        
        data = xy_to_data(xx, yy)
            
        return header, data
            
    def xy_to_data(self, xx, yy):

        df = pd.DataFrame(data={"x":xx,"y": yy})
        df.set_index('x', inplace=True)  # Setting 'x' as the index
        df.sort_index(inplace=True)
        # ~ logging.debug(df)
        return df

            
        

    def _convert_numeric(self, value):
        try:
            if '.' in value or 'e' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return value





    
    
    
    
    
    
    
        
if __name__ == "__main__":
    main()
