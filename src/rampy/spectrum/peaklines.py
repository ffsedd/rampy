import pandas as pd

# Replace 'data/peak_lines.tsv' with your file path
file_path = 'data/peak_lines.tsv'

# Load the tab-separated file into a pandas dataframe
df = pd.read_csv(file_path, sep='\t')

# Display the first few rows of the dataframe to ensure it's loaded correctly


df_sorted = df.sort_values(by='Energy')

print(df)
output_file = 'data/peak_lines_copy_by_energy.tsv'
df_sorted.to_csv(output_file, sep='\t', index=False)
