import numpy as np
import matplotlib.pyplot as plt
from spekpy import Spek

# Constants
RESOLUTION = 0.1  # kV
TARGET = "W"  # Tungsten target
ANODE_ANGLE = 12  # spekpy default anode angle
FILTER = ("Be", 0.254)  # Beryllium filter with thickness 0.254 mm

# X-ray tube settings (kVp, mAs)
tube_settings = [
    (20, 0.36),
    (40, 0.36),
    (60, 0.25),
    (80, 0.18),
    (100, 0.15)
]

# Create the plot
plt.figure(figsize=(25, 8))

# Loop through each tube setting and plot the spectrum
for kvp, mas in tube_settings:
    spek_instance = Spek(kvp=kvp, mas=mas, dk=RESOLUTION, th=ANODE_ANGLE, targ=TARGET)
    spek_instance.filter(*FILTER)
    x, y = spek_instance.get_spectrum()
    plt.plot(x, y, label=f"{kvp} kVp {mas} mAs", alpha=0.4)

# Plot customization
plt.xlabel("Energy (keV)")
plt.ylabel("Intensity")

# Dynamically set the title with the current values
plt.title(f"X-ray Spectrum for Different kVp Values by spekpy: "
          f"Spek(th={ANODE_ANGLE}, dk={RESOLUTION}, targ='{TARGET}')")

plt.ylim(1e3, 6e6)  # Adjust y-axis to avoid cutting off low values
plt.xlim(0, 100)
# plt.yscale("log")  # Option to use log scale for better visibility of low intensities
plt.grid()
plt.legend()

# Final adjustments and save
plt.tight_layout()
plt.savefig("xraytubespectra.pdf")
plt.show()
