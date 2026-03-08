import xraydb as x
from pprint import pprint
import pandas as pd
from qq.chemistry.periodictable import ELEMENT_SYMBOLS
print(ELEMENT_SYMBOLS)
syms = ELEMENT_SYMBOLS[:100]

print(x.atomic_number('Ag'))


for name, line in x.xray_lines('Zn', 'K').items():
    print(name, ' = ', line)


print(x.xray_edge('As', 'K'))

elsym = 'Cu'

dfs = []
for s in syms:
    lines = x.xray_lines(s).keys()
    data = (x.xray_lines(s).values())
    # print(data)
    df = pd.DataFrame(index=lines, data=data)
    # dfi = pd.DataFrame(x.xray_lines(s))
    df = df.reset_index()
    df.insert(0, 'element', s)
    # df_melted = pd.melt(dfi, id_vars=['element'])

    # print(df)
    dfs.append(df)
    
df = pd.concat(dfs, axis=0, ignore_index=True)
df = df.rename(columns={'index': 'line'})
df.set_index(['element', 'line'], inplace=True)
df.energy = df.energy / 1000


df = df.sort_values('energy')
print(df)
df.to_excel("xray_lines.xlsx")
