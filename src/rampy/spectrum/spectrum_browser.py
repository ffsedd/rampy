import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from pathlib import Path
from collections import deque
import functools
import logging
import argparse
from natsort import natsorted
from qq.spectrum.spectrum import Spectrum, EdsSpectrum
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

SPECTRUM_EXTS = (".msa", ".jdx", ".spx", ".csv")

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)

class MainWindow(tk.Tk):
    def __init__(self, dpath=None, fpath=None, mode="default"):
        logging.debug(f"Initializing MainWindow: dpath={dpath}, fpath={fpath}, mode={mode}")
        super().__init__()

        self.title("Spectrum Viewer")
        self.geometry("1600x1300")
        # ~ self.attributes('-fullscreen', True)

        self.fig, self.ax = plt.subplots(figsize=(8, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.browser = Browser(dpath, fpath)
        self.xlim = [None, None]
        self.ylim = [None, None]

        self.plot_all = tk.BooleanVar()
        self.plot_dervivative1 = tk.BooleanVar()
        self.plot_dervivative2 = tk.BooleanVar()
        self.plot_baseline = tk.BooleanVar()
        self.plot_smooth = tk.BooleanVar()
        self.plot_peaks = tk.BooleanVar()
        self.plot_peak_lines = tk.BooleanVar()
        self.plot_log = tk.BooleanVar()

        self.create_toolbar()
        self.create_limit_controls()
        self.create_checkboxes()
        self.toolbar.pack(side=tk.LEFT, fill=tk.X, pady=10)

        self.bind_hotkeys()
        self.bind_mouse()

        self.plotted_spectra = {}
        self.plot_initialized = False

        if hasattr(self.browser.spectrum, "plot_peak_lines"):
            self.sem()

        self.update_plot()
        logging.debug("MainWindow initialized.")

    @property
    def spectrum(self):
        return self.browser.spectrum

    def create_toolbar(self):
        
        self.toolbar = ttk.Frame(self, height=30)
        
        self.mouse_pos_label = tk.Label(self.toolbar, text="X Position: -")
        self.mouse_pos_label.pack(side=tk.RIGHT)

        for i, t in enumerate(("prev", "next", "first", "last", "sem", "reset", "peaks", "lines", "save")):
            b = tk.Button(self.toolbar, text=t, height=1, command=eval(f"self.{t}"))  
            b.pack(side=tk.LEFT)


        tk.Button(self.toolbar, text="2-6", height=1, command=self.preset2).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text="4-6", height=1, command=self.preset4).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text="5-9", height=1, command=self.preset5).pack(side=tk.LEFT)
        tk.Button(self.toolbar, text="9-13", height=1, command=self.preset9).pack(side=tk.LEFT)

    def preset2(self):
        self.reset()
        self.xlim1_input.insert(0, 2)
        self.xlim2_input.insert(0, 6)
        self.apply_limits()

    def preset4(self):
        self.reset()
        self.xlim1_input.insert(0, 4)
        self.xlim2_input.insert(0, 6)
        self.apply_limits()
        
    def preset5(self):
        self.reset()
        self.xlim1_input.insert(0, 5)
        self.xlim2_input.insert(0, 9)
        self.apply_limits()
        
    def preset9(self):
        self.reset()
        self.xlim1_input.insert(0, 9)
        self.xlim2_input.insert(0, 13)
        self.apply_limits()    

    def create_limit_controls(self):


        tk.Label(self.toolbar, text="Y lim:").pack(side=tk.LEFT)
        self.ylim1_input = tk.Entry(self.toolbar, width=5)
        self.ylim1_input.pack(side=tk.LEFT)
        self.ylim2_input = tk.Entry(self.toolbar, width=5)
        self.ylim2_input.pack(side=tk.LEFT)
        
        tk.Label(self.toolbar, text="X lim:").pack(side=tk.LEFT)
        self.xlim1_input = tk.Entry(self.toolbar, width=5)
        self.xlim1_input.pack(side=tk.LEFT)
        self.xlim2_input = tk.Entry(self.toolbar, width=5)
        self.xlim2_input.pack(side=tk.LEFT)



        tk.Button(self.toolbar, text="set", command=self.apply_limits).pack(side=tk.LEFT)


    def create_checkboxes(self):

        tk.Checkbutton(self.toolbar, text="smoo", variable=self.plot_smooth, command=self.update_plot).pack(side=tk.LEFT)
        tk.Checkbutton(self.toolbar, text="base", variable=self.plot_baseline, command=self.update_plot).pack(side=tk.LEFT)

        tk.Checkbutton(self.toolbar, text="lines", variable=self.plot_peak_lines, command=self.update_plot).pack(side=tk.LEFT)
        tk.Checkbutton(self.toolbar, text="diff", variable=self.plot_dervivative1, command=self.update_plot).pack(side=tk.LEFT)
        tk.Checkbutton(self.toolbar, text="diff2", variable=self.plot_dervivative2, command=self.update_plot).pack(side=tk.LEFT)
        tk.Checkbutton(self.toolbar, text="log", variable=self.plot_log, command=self.update_plot).pack(side=tk.LEFT)
        tk.Checkbutton(self.toolbar, text="all", variable=self.plot_all, command=self.update_plot).pack(side=tk.LEFT)

                
    def bind_hotkeys(self):
        # Bind hotkeys for navigation
        self.bind("<Left>", lambda event: self.prev())
        self.bind("<Right>", lambda event: self.next())
        self.bind("<Up>", lambda event: self.first())
        self.bind("<Down>", lambda event: self.last())
        self.bind("o", lambda event: self.open_file())
        self.bind("s", lambda event: self.sem())
        self.bind("r", lambda event: self.reset())
        self.bind("<Return>", lambda event: self.apply_limits())
        self.bind("<KP_Enter>", lambda event: self.apply_limits())
        
    def bind_mouse(self):
        # Bind the mouse wheel events to the on_mousewheel method
        self.canvas.get_tk_widget().bind("<Button-1>", self.on_l_click)
        self.canvas.get_tk_widget().bind("<B1-Motion>", self.on_l_drag)
        self.canvas.get_tk_widget().bind("<ButtonRelease-1>", self.on_l_drag_end)
        self.canvas.get_tk_widget().bind("<Button-3>", self.on_r_click)
        self.canvas.get_tk_widget().bind("<B3-Motion>", self.on_r_drag)
        self.canvas.get_tk_widget().bind("<ButtonRelease-3>", self.on_r_drag_end)
        self.canvas.get_tk_widget().bind("<Button-4>", self.on_mousewheel_up)
        self.canvas.get_tk_widget().bind("<Button-5>", self.on_mousewheel_down)
        self.canvas.get_tk_widget().bind("<Control-Button-4>", self.on_ctrl_mousewheel_up)
        self.canvas.get_tk_widget().bind("<Control-Button-5>", self.on_ctrl_mousewheel_down)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)


    def on_mouse_motion(self, event):
        # show X positon
        if event.xdata is not None:
            self.mouse_pos_label.config(text=f"{event.xdata:.3f} keV")
        else:
            self.mouse_pos_label.config(text="-------- keV")


    def on_l_click(self, event):
        # Store the starting position of the left-click drag
        self.start_x = event.x
        self.start_y = event.y

    def on_l_drag(self, event):
        # Respond to left-click drag event
        pass

    def on_l_drag_end(self, event, amount=1000):
        # Respond to the end of left-click drag event
        x1, x2, y1, y2 = self.get_limits()
        
        x_offset = event.x - self.start_x 
        y_offset = event.y - self.start_y

        # Update x-axis limits based on the drag offset
        self.xlim[0] -= x_offset * (x2-x1) / amount
        self.xlim[1] -= x_offset * (x2-x1) / amount

        # Update y-axis limits based on the drag offset
        self.ylim[0] += y_offset * (y2-y1) / amount
        self.ylim[1] += y_offset * (y2-y1) / amount

        self.update_plot()


    def on_r_click(self, event):
        # Store the starting position of the left-click drag
        self.start_x = event.x
        self.start_y = event.y

    def on_r_drag(self, event):
        # Respond to left-click drag event
        pass

    def on_r_drag_end(self, event, amount=1000):
        # Respond to the end of left-click drag event
        x1, x2, y1, y2 = self.get_limits()
        
        x_offset = event.x - self.start_x 
        y_offset = event.y - self.start_y

        self.xlim = self.zoom_range(self.ax.get_xlim(), 1-x_offset / 500)
        self.ylim[1] = self.zoom_range(self.ax.get_ylim(), 1 + y_offset / 500)[1]
        
        self.update_plot()


    def get_limits(self):
        x1, x2 = self.ax.get_xlim()
        y1, y2 = self.ax.get_ylim()
        return x1, x2, y1, y2
    
    def zoom_range(self, limits, factor):
        a1, a2 = limits
        arange = a2 - a1
        amean = (a1 + a2) / 2
        arange_new = arange * factor  
        return [amean - arange_new / 2, amean + arange_new / 2]
        
    def on_mousewheel_up(self, event):
        self.ylim[1] = self.zoom_range(self.ax.get_ylim(), .7)[1]
        self.update_plot()   
        
    def on_mousewheel_down(self, event):
        self.ylim[1] = self.zoom_range(self.ax.get_ylim(), 1.4)[1]
        self.update_plot()             
        
    def on_ctrl_mousewheel_up(self, event):
        self.xlim = self.zoom_range(self.ax.get_xlim(), .7)
        self.update_plot()


    def on_ctrl_mousewheel_down(self, event):
        self.xlim = self.zoom_range(self.ax.get_xlim(), 1.4)
        self.update_plot()
        
               
    def apply_limits(self):
        x_limit_min = self.xlim1_input.get()
        x_limit_max = self.xlim2_input.get()
        y_limit_min = self.ylim1_input.get()
        y_limit_max = self.ylim2_input.get()

        try:
            x_limit_min = float(x_limit_min) if x_limit_min else None
            x_limit_max = float(x_limit_max) if x_limit_max else None
            y_limit_min = float(y_limit_min) if y_limit_min else None
            y_limit_max = float(y_limit_max) if y_limit_max else None

            self.xlim = [x_limit_min, x_limit_max]
            self.ylim = [y_limit_min, y_limit_max]
            self.update_plot()

        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter valid numeric values for X and Y limits.")

    def update_line(self, spectrum, linestyle='dotted', linewidth=1):
        logging.debug(f"Updating a line {spectrum.path.name}")
        if spectrum.path not in self.plotted_spectra:
            line, = self.ax.plot([], [], linestyle='dotted', linewidth=1, label=spectrum.path.name)
            self.plotted_spectra[spectrum.path] = line
        line = self.plotted_spectra[spectrum.path]
        line.set_data(spectrum.x, spectrum.y)
        line.set_linestyle(linestyle)
        line.set_linewidth(linewidth)
        # ~ line.set_linewidth(1 if spectrum.path != current_path else 2)
  
    def update_plot(self):
        logging.debug("Updating plot.")

        # ~ self.ax.clear()
        s = self.browser.spectrum

        if self.plot_smooth.get():
            logging.debug("Applying smoothing.")
            s = s.smooth()

        if self.plot_baseline.get():
            logging.debug("Applying baseline correction.")
            s = s.baseline_correction()

        self.update_line(spectrum=s, linestyle='-', linewidth=3)

        if self.plot_log.get():
            logging.debug("Setting Y-axis to logarithmic scale.")
            plt.yscale("log")
        else:
            plt.yscale("linear")


        if self.plot_dervivative1.get():
            logging.debug("Plotting first derivative.")
            s.diff().plot()

        if self.plot_dervivative2.get():
            logging.debug("Plotting second derivative.")
            s.diff2().plot()



        if self.plot_all.get():
            logging.debug("Plotting all spectra in the folder.")
            for path in self.browser.fpaths:
                if path == self.browser.current_path:
                    continue
                s = self.browser.load_spectrum(path)
                self.update_line(spectrum=s, linestyle='dotted')

        self.title(str(self.browser.current_path))
        
        if not self.plot_initialized:
            
            logging.debug("Plotting grid.")
            plt.grid(color='lightgrey', linestyle=':', linewidth=1)

            self.plot_initialized = True
            logging.debug("Plot initialized---------------------------.")

        logging.debug("Plotting legend.")
        plt.legend(loc="upper right")
        logging.debug("Adjust.")
        plt.subplots_adjust(left=0.03, right=0.99, top=0.99, bottom=0.03)        
        
        logging.debug("apply limits.")        
        self.ax.set_xlim(self.xlim)
        self.ax.set_ylim(self.ylim)
        self.xlim = list(self.ax.get_xlim())
        self.ylim = list(self.ax.get_ylim())
            

        
        logging.debug("draw.")
        self.canvas.draw()
        
        logging.debug("Plot updated successfully.")

    def save(self):
        plt.savefig(f"{self.spectrum.path}_view1.pdf")

    def peaks(self):
        logging.debug("Plotting peak energy.")
        self.spectrum.plot_peaks(ax=self.ax)
        self.update_plot()

    def lines(self):
        logging.debug("Plotting peak lines.")
        self.spectrum.plot_peak_lines(ax=self.ax)
        self.update_plot()


    def open_file(self):
        logging.debug("Opening file dialog.")
        file_path = filedialog.askopenfilename(filetypes=[("Spectrum Files", "*.msa *.jdx *.spx *.csv")])
        if file_path:
            logging.debug(f"File selected: {file_path}")
            self.browser = Browser(Path(file_path).parent, fpath=file_path)
            self.update_plot()
        else:
            logging.debug("No file selected.")

    def prev(self):
        self.browser.prev()
        self.update_plot()

    def next(self):
        self.browser.next()
        self.update_plot()

    def first(self):
        self.browser.first()
        self.update_plot()

    def last(self):
        self.browser.last()
        self.update_plot()
        
    def sem(self):
        self.reset()
        self.plot_all.set(True)
        self.xlim1_input.insert(0, 1)
        self.xlim2_input.insert(0, 13)
        self.ylim1_input.insert(0, self.browser.spectrum.y.min())
        self.ylim2_input.insert(0, self.browser.spectrum.y.max())
        self.plot_dervivative1.set(0)
        self.plot_dervivative2.set(0) 
        # self.plot_baseline.set(1) 
        self.plot_smooth.set(0) 
        self.plot_peaks.set(1) 
        self.plot_peak_lines.set(1) 
        self.apply_limits()

    def reset(self):
        self.xlim1_input.delete(0, tk.END)
        self.xlim2_input.delete(0, tk.END)
        self.ylim1_input.delete(0, tk.END)
        self.ylim2_input.delete(0, tk.END)
        self.apply_limits()
                

class Browser:
    def __init__(self, dpath=".", fpath=None):
        logging.debug(f"Initializing Browser: dpath={dpath}, fpath={fpath}")
        self.dir = Path(fpath).parent if fpath else Path(dpath)
        self.cached_spectra = {}
        self.fpaths = self.find_files()

        if fpath:
            fpath = Path(fpath)
            idx = self.fpaths.index(fpath)
            self.fpaths.rotate(-idx)
        self.load_index(0)

    def find_files(self):
        logging.debug(f"Finding spectrum files in directory: {self.dir}")
        fpaths = deque(natsorted([f for f in self.dir.glob("*.*") if f.suffix.lower() in SPECTRUM_EXTS]))
        if not fpaths:
            logging.warning(f"No spectrum files found in directory: {self.dir}")
        logging.debug(f"Found {len(fpaths)} files.")
        return fpaths


    def load_index(self, index):
        logging.debug(f"Loading spectrum at index {index}.")
        self.current_path = self.fpaths[index]
        self.spectrum = self.load_spectrum(self.current_path)
        
    @functools.lru_cache(maxsize=100, typed=False)
    def load_spectrum(self, path):
        """Load spectrum from the cache or file."""
        logging.debug(f"Loading spectrum: {path}")
        return Spectrum.create(path=path)
        
    def first(self):
        self.find_files()
        self.load_index(0)

    def last(self):
        self.find_files()
        self.load_index(-1)

    def next(self):
        self.fpaths.rotate(-1)
        self.load_index(0)

    def prev(self):
        self.fpaths.rotate(1)
        self.load_index(0)

    def load_index(self, index):
        self.current_path = self.fpaths[index]
        self.spectrum = self.load_spectrum(self.current_path)


def parse_args():
    parser = argparse.ArgumentParser(description="Spectrum Browser")
    parser.add_argument("dpath", nargs="?", default=".", help="Directory containing spectrum files")
    parser.add_argument("-f", "--fpath", help="File to open")
    parser.add_argument("--mode", choices=["sem", "default"], default="default", help="Set the initial mode (default or sem)")
    return parser.parse_args()

if __name__ == "__main__":
    logging.basicConfig(format='!%(levelno)s [%(module)10s%(lineno)4d] %(message)s', level=10)
    plt.set_loglevel (level = 'warning')
    args = parse_args()
    app = MainWindow(dpath=args.dpath, fpath=args.fpath, mode=args.mode)
    app.mainloop()
