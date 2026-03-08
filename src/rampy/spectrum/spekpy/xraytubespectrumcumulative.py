import numpy as np
import matplotlib.pyplot as plt
from spekpy import Spek

plt.figure(figsize=(16, 8))

colors = ['b', 'g', 'r', 'c', 'm']  # Define colors for better visualization

for i, kvp in enumerate((20, 40, 60, 80, 100)):
    spek_instance = Spek(kvp=kvp, th=12, mas=.3, dk=0.5, targ='W')
    spectrum = spek_instance.get_spectrum()
    x, y = spectrum  # Assuming it returns a tuple (x, y)

    # Cumulative sum of intensity values up to each kVp
    cumulative_y = np.cumsum(y)  # Sum of all y values up to each point
    plt.plot(x, cumulative_y, label=f"Cumulative {kvp} kVp", color=colors[i])

plt.xlabel("Energy (keV)")
plt.ylabel("Cumulative Intensity")
plt.title("Cumulative X-ray Spectrum for Different kVp Values")
plt.yscale("log")  # Log scale for better visibility of low intensities
plt.grid()
plt.legend()
plt.tight_layout()
plt.savefig("cumulative_xray_spectra.pdf")
plt.show()
