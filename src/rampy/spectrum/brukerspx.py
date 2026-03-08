#!/usr/bin/env python3

import logging
from pprint import pprint

import numpy as np
import pandas as pd


import re
import xmltodict


from pathlib import Path


# SCDIR = Path(__file__).parent


SPEC_HEADER = "filestem title Amplification CalibAbs CalibLin ChannelCount Date DeadTime LifeTime PulseDensity RealTime ShapingTime SigmaAbs SigmaLin Size Time ZeroPeakFrequency ZeroPeakPosition atom_list fileext filename filepath".split()




class Spx():
    """
    Load data from spx file to object
    Attributes:
    """


    def __init__(self, filepath='', title=''):

        # init values
        self.x = ''
        self.xfactor = 1.0
        self.xunits = ''

        self.y = ''
        self.yfactor = 1.0
        self.yunits = ''

        self.filepath = ''
        self.title = ''
        self.filename = ''

        # load spx
        if filepath:
            self.load_spx(filepath,  title)


    def __str__(self):
        return f"Object: bruker Spx spectrum,\t path: {self.filepath}"



    def load_spx(self, filepath, title=''):
        """
        load spx file to object
        """
        logging.debug("load_spx {filepath}")

        Fp = Path(filepath)

        with open(Fp, "rb") as f:
            xmldict = xmltodict.parse(f.read())


        self.filename = Fp.name
        self.filestem = Fp.stem
        self.filepath = str(Fp)
        self.fileext = Fp.suffix

        # PARSE HEADER --------------------------------------------------
        self.title = xmldict['TRTSpectrum']['ClassInstance']['@Name']

        xml_tree = xmldict['TRTSpectrum']['ClassInstance']['TRTHeaderedClass']['ClassInstance']
        self._parse_xml_nodes(xml_tree, 'TRTSpectrumHardwareHeader')

        xml_tree = xmldict['TRTSpectrum']['ClassInstance']['ClassInstance']
        self._parse_xml_nodes(xml_tree, 'TRTSpectrumHeader')

        # get RESULTS dict
        self._parse_xml_nodes(xml_tree, 'TRTResult')

        for i,dic in enumerate(self.Result):
            for k, v in dic.items():
                self.Result[i][k] = v.replace(",", ".") # ensure comma decimal separator
        #print(self.Result)
        try:
            self.atom_list = [int(res_dict['Atom']) for res_dict in self.Result]

        except Exception as e:
            print(self.title,"...results not found", e)

        # convert to int
        for att in ['kV','mA','RealTime','LifeTime','Anode','ChannelCount']:
            # print("convert",att)
            try:
                v = getattr(self, att,"")
                setattr(self, att, int(v))
            except Exception as e:
                logging.info(att,f"not found: {e}")

        # convert to float
        for att in ['CalibAbs','CalibLin','SigmaAbs','SigmaLin']:
            try:
                v = getattr(self, att,"")
                setattr(self, att, float(v))
            except Exception as e:
                logging.info(att,f"not found: {e}")

        # remove unneeded keys
        for att in ['ExtResults', 'TRTKnownHeader','Name', 'Type']:
            delattr(self, att)

        # PARSE DATA --------------------------------------------------
        self.Channels = xmldict['TRTSpectrum']['ClassInstance']['Channels']
        # get Y values
        self.counts = np.fromstring(self.Channels, dtype=int, sep=',')    # counts
        if self.RealTime:
            self.cps = self.counts / self.RealTime * 1000   # realtime in ms
            self.y = self.cps       # y output CPS !
            self.yunits = "Intensity [counts/s]"
        else:
            self.y = self.counts
            self.yunits = "Intensity [counts]"

        # generate X values
        x0 =  self.CalibAbs
        dx =  self.CalibLin
        self.x = np.arange(x0, dx*int(self.ChannelCount)+x0, dx)
        self.xunits = "Energy [kV]"

        logging.debug("load_spx done {self.filename}")

    def _parse_xml_nodes(self, xml_tree, nodetype):
        """
        find nodes by type and convert it into object attributes, can overwrite other values!!!
        """
        for node in xml_tree:
            if node['@Type'] == nodetype:
                # print(node)
                for key, value in node.items():
                    try:
                        att =  key.strip()
                        att = re.sub(r'\W+', '', att)   # remove non alnum. chars (cannot be used as object attribute name)
                        setattr(self, att, value)
                        #print(att,value)

                    except Exception as e:
                        print("error ", key, value, e)





    @property
    def at_perc(self):

        rows = []
        for dic in self.Result:
            elno = int(dic['Atom'])

            atperc = 100 * float(dic['AtomPercent']) \
                if "AtomPercent" in dic else np.nan

            rows.append({"el_no":elno, "at_%":atperc})

        df = pd.DataFrame(rows)
        return df

    @property
    def mass_perc(self):

        rows = []
        for dic in self.Result:
            elno = int(dic['Atom'])

            massperc = 100 * float(dic['MassPercent']) \
                if "MassPercent" in dic else np.nan

            rows.append({"el_no":elno, "mass_%":massperc})

        df = pd.DataFrame(rows)
        return df





def rtx_zip_to_spx(filepath):
    """
    extract spx files from rtx
    """
    import base64, zlib

    fp = Path(filepath)

    with open(fp) as f:
        xmldict = xmltodict.parse(f.read())

    print("load",fp)

#    filepath = qq.fpath(filepath)

    xml_tree = xmldict['TRTProject']['RTData']

    unzipped = zlib.decompress(base64.b64decode(xml_tree)).decode('cp1252')

    from xml.dom import minidom
    dom = minidom.parseString(unzipped)


    node_list = dom.getElementsByTagName("ClassInstance")
    for node in node_list:
    #print(node,  node.attributes.keys())
        if "Type" in node.attributes.keys():
            if node.getAttribute('Type') == "TRTSpectrum":
#                print("TRTSpectrum",  node.getAttribute("Name"))
#                print(node.toxml())



                dom_new = minidom.parseString('<TRTSpectrum><RTHeader/></TRTSpectrum>')
                dom_new.childNodes[0].appendChild(node)

                out_fp = fp.parent /  node.getAttribute('Name') + '.spx'
                print(f"save... {out_fp}")
                with open(out_fp,  "w") as f:
#                    dom_new.writexml(f)
                    f.write('<?xml version="1.0" encoding="WINDOWS-1252" standalone="yes"?>\n')
                    data = "\n".join(dom_new.toprettyxml().split("\n")[1:]) # omit header
                    f.write(data)


    return



# MAIN ===========================================

if __name__ == "__main__":


    s = Spx("/home/m/Y/JETSTREAM/TESTY/Ba-Ti směs/SPEKTRA/TB6_p007_20kV_100mmAl.spx")
    pprint([o for o in dir(s) if o[0] !="_"])
    print(s.mass_perc)
