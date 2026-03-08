import numpy as np
import matplotlib.pyplot as plt
from spekpy import Spek

plt.figure(figsize=(25, 8))

colors = ['b', 'g', 'r', 'c', 'm']  # Define colors for better visualization

for i, (kvp,mas) in enumerate(zip((20, 40, 60, 80, 100),(.36, .36, .25, .18, .15))):
    spek_instance = Spek(kvp=kvp, th=12, dk=0.1, mas=mas, targ='W')
    spek_instance.filter("Be", .254)
    spectrum = spek_instance.get_spectrum()
    x, y = spectrum  # Assuming it returns a tuple (x, y)
    plt.plot(x, y, label=f"{kvp} kVp {mas} mAs", color=colors[i], alpha=.4)

plt.xlabel("Energy (keV)")
plt.ylabel("Intensity")
plt.title("X-ray Spectrum for Different kVp Values by spekpy: Spek(th=12, dk=0.1, targ='W')")
plt.ylim(1e3, 6e6)  # Adjusted to avoid cutting off low values
plt.xlim(0,100)
# ~ plt.yscale("log")   # Log scale for better visibility of low intensities
plt.grid()
plt.legend()
plt.tight_layout()
plt.savefig("xraytubespectra.pdf")
# ~ plt.show()
