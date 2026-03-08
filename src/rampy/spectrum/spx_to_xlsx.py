#!/usr/bin/env python3

# import matplotlib.pyplot as plt
import re

from qq.spectrum import brukerspx, periodictable
from pathlib import Path
import pandas as pd
import numpy as np

# SETTINGS

# INDIR = "/home/m/temp/"
INDIR = Path(".").resolve()

# LOGSCALE = True
#XRNG = (0,15)   # zumi
#YRNG = (5e-2,1e2)    # zumi
# XRNG = (0,25)   # jetstream
# YRNG = (1e-0,1e4) # jetstream
#YRNG = (0,500) # jetstream
OVERWRITE = True
# SAVE_FORMATS = [".png"]

RATIOS = [
    ("P","Ca"),
    ("Sr","Ca"),
    ("Ti","Ca"),
    ("Fe","Ca"),
    ("Zn","Ca"),
    ("Ba","Ca"),
    ("Mg","Ca"),
    
    ("Sr","P"),
    ("Ti","P"),
    ("Fe","P"),
    ("Zn","P"),
    ("Ba","P"),
    ("Mg","P"),
    
    ("Sr","Fe"),
    ("Ti","Fe"),
    ("Zn","Fe"),
    ("Ba","Fe"),
    

    ("Ni","Co"),
    ("As","Co"),
    ("Bi","Co"),
    ("K","Co"),
    ("Al","Co"),
    ("Si","Co"),   
    
    ("Sn","Au"),
    ("Ag","Au"),
    ("Cu","Au"),
    ("Zn","Au"),
    
    ("Ba","S"),
    ("Ca","S"),
    ("Hg","S"),
    ("Cd","S"),
    ("As","S"),
    
    ("Ba","Pb"),
    ("As","Pb"),
    ("Cr","Pb"),
    ("Zn","Pb"),
    ("Sn","Pb"),
    ("Cu","Pb"),
    ("Sb","Pb"),
    
    ("Sb","Sn"),
    ]
    


def spxtoxlsx(indir):
    
    indir = Path(indir).resolve()
    meas_id = get_meas_id(indir)
    print(f"spx2xlsx started in {indir}")
    dfa = spx_to_df(indir, 'at_perc')
    dfm = spx_to_df(indir, 'mass_perc')
    # print(dfm)
    dfc = df_correlate(dfm)
    # print(dfc)
    dfr = calc_ratio(dfm)
    # print(dfr)
    
    dataframes = dict(zip(
    ("mass_perc", "at_perc_norm", "mass_perc_corr", "mass_perc_ratio"),
    (dfm, dfa, dfc, dfr)
    )
        )
    # print(dataframes)    
        
        
    
    df_to_formatted_xlsx(indir / f"{meas_id}_concentrations.xlsx", dataframes, widths=[4,4,2,5])
    
    return dataframes



def df_correlate(df, min_conc=0.1, min_r2=0.5):
    df = df.drop(columns=["Sum"])
    # df = df.drop(["Mean", "Std","Min","Max"])
    # df = df.drop(["Mean"])
    # print(df)
    
    
    df = df[(df > min_conc)]
    df = df.corr(method='pearson', min_periods=1)
    df[(df<=min_r2)] = np.nan
    np.fill_diagonal(df.values, np.nan)
    

    return df

def spx_to_df(indir, attrib):

    df = pd.DataFrame()

    fps = sorted(list(indir.glob("*.spx")))
    # print(fps)
    for f in fps:
        # print(f)
        try:
            s = brukerspx.Spx(f)
        except Exception as e:
            print(" --------> ERROR", f.resolve(), "\n\n", e)
            continue    
        dfi = getattr(s, attrib).sort_values(by=['el_no']).T
        dfi.columns = dfi.iloc[0].astype('int') # header from 1st row
        dfi = dfi[1:]
        dfi = dfi.set_index([pd.Index([s.filename])])
        df = pd.concat([df, dfi], axis=0)

    df.columns = pd.Series(df.columns.values).apply(periodictable.number_to_symbol)
    
    
    df['Sum'] = df.sum(axis=1)
    
    # df.loc["Mean"] = df.mean()
    # df.loc["Std"] = df.std()
    # df.loc["Min"] = df.min()
    # df.loc["Max"] = df.max()

    
    
    return df


def calc_ratio(df):
    

    # data = df.drop(["Mean", "Std","Min","Max"])
    # data = df.drop(["Mean"])
    df0 = df
    
    df = pd.DataFrame()
    for a,b in RATIOS:
        # print(a,b)
        
        if a in df0.columns and b in df0.columns:
            df[f'{a}/{b}'] = df0[a] / df0[b]
    
    
    
    # df.loc["Mean"] = df.mean()
    # df.loc["Std"] = df.std()
    # df.loc["Min"] = df.min()
    # df.loc["Max"] = df.max()
    
    
    
    return df  
    



def df_to_formatted_xlsx(fpath, dataframes, widths=None):
    ''' '''
    print(f"save to file: {fpath} ")

    # Create a Pandas Excel writer using XlsxWriter as the engine.
    with pd.ExcelWriter(fpath, engine='xlsxwriter') as writer:

        for i, (sheet_name, df) in enumerate(dataframes.items()):
            # Convert the dataframe to an XlsxWriter Excel object.
            df.to_excel(writer, sheet_name=sheet_name, index=True, freeze_panes=(1,1) ,float_format="%.6f")

            # Get the xlsxwriter objects from the dataframe writer object.
            worksheet = writer.sheets[sheet_name]

            # Set Column width
            if widths:
                wid = widths[i]
            else:
                wid = 10
            
            worksheet.set_column(0, 0, 20)  # first column width
            worksheet.set_column(1, 100, wid)  # next col widths

            # Set Conditioanal formatting
            worksheet.conditional_format('A1:AZ100', {'type': '3_color_scale',
                                                 'min_color': "#ffffff",
                                                'mid_type':'percentile', 'mid_value':80, 'mid_color': "#ffff99",
                                                 'max_color': "#ff9999"})
            # ~ writer.save()


def get_meas_id(root):
    '''Get measurement id from parent folder name'''
    regex = re.compile(r"(j\d{3,4})_([a-zA-Z0-9-]+)_.*")
    dirs = Path(root).parts
    mid = [regex.match(dname) for dname in dirs if regex.match(dname)]
    if mid:
        mid = f"{mid[0].group(1)}_{mid[0].group(2)}_{dirs[-1]   }"
    else:
        mid = dirs[-1]    
    return mid
    

        
    
# ==========================================================================================

if __name__ == "__main__":
    spxtoxlsx(INDIR)


