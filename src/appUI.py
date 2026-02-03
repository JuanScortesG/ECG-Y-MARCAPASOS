
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import time

from . import config
from .data_model import AppState
from .serial_handler import SerialReader
from .filters import ECGFilters
from .peak_detection import detect_r_peaks, calculate_bpm

class ECGApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ECG Monitor - 6 derivations")
        self.geometry("1300x850")
        self.is_running = True
        
        # Core components
        self.app_state = AppState()
        self.ecg_filters = ECGFilters()
        self.serial_reader = SerialReader(self.app_state, self.ecg_filters)
        
        # Alerta de marcapasos
        self.pacemaker_alert_active = False
        
        self._create_widgets()
        self.serial_reader.start()
        self.update_gui()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    # =====================================================
    # ---------------- UI STRUCTURE -----------------------
    # =====================================================
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding = "10")
        main_frame.pack(fill = tk.BOTH, expand = True)
        
        plot_frame = ttk.Frame(main_frame)
        plot_frame.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)
        
        sidebar_frame = ttk.Frame(main_frame, width = 320)
        sidebar_frame.pack(side = tk.RIGHT, fill = tk.Y, padx = (10, 0))
        
        self._create_plots(plot_frame)
        
        self._create_derivation_mode_panels(sidebar_frame)
        self._create_derivation_panels(sidebar_frame)
        self._create_gain_panel(sidebar_frame)
        self._create_plot_control_panel(sidebar_frame)
        self._create_peak_panel(sidebar_frame)
        self._create_status_panel(sidebar_frame)
        self.create_pacemaker_panel(sidebar_frame)
        
    # =====================================================
    # ------------------ PLOTS ----------------------------
    # =====================================================
    
    def _create_plots(self, parent):
        self.fig, (self.ax1, self.ax2) = plt.subplot(2, 1, figsize = (9, 8), sharex = True)
        self.canvas = FigureCanvasTkAgg(self.fig, master = parent)
        self.canvas.get_tk_widget().pack(fill = tk.BOTH, expand = True)
        self._setup_plots()
    
    def _setup_plots(self):
        self.ax1.set_ylabel("Raw ECG (V)")
        self.ax1.set_title("ECG Signal")
        self.ax1.grid(True, alpha = 0.3)
        
        
        self.ax2.set_xlabel("Samples")
        self.ax2.set_ylabel("Filtered ECG (V)")
        self.ax2.grid(True, alpha = 0.3)
        
        self.line_raw, = self.ax1.plot([], [], 'b-', linewidth = 1.1)
        self.line_filtered, = self.ax2.plot([], [], 'g-', linewidth = 1.3)
        self.peaks_line, = self.ax2.plot([], [], 'ro', markersize = 5)
        
        self.fig.tight_layout()
    
    # =====================================================
    # ---------------- PACEMAKER ALERT -------------------
    # =====================================================
    def _create_pacemaker_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="Pacemaker Alert", padding="10")
        panel.pack(fill=tk.X, pady=6)
        
        self.pacemaker_label = ttk.Label(panel, text="No Alert", foreground="green", font=("Arial", 12, "bold"))
        self.pacemaker_label.pack(anchor="center", pady=4)

    def update_pacemaker_alert(self):
        # Revisar si el pacemaker fue disparado
        interval = time.time() - self.serial_reader.last_r_time
        if interval > 2.0:
            self.pacemaker_alert_active = True
            self.pacemaker_label.config(text="⚠ PACEMAKER ACTIVATED ⚠", foreground="red")
        else:
            self.pacemaker_alert_active = False
            self.pacemaker_label.config(text="No Alert", foreground="green")
    
    # =====================================================
    # -------------- DERIVATION MODE ----------------------
    # =====================================================
    
    def _create_derivation_mode_panel(self, parent):
        panel = ttk.LabelFrame(parent, text = " Derivation Mode", padding = "10")
        panel.pack(fill = tk.X, pady = 6)
        ttk.Radiobutton(
            panel, text = "Analog (MUX)",
            variable = self.app_state.derivation_mode,
            value = "ANALOG"
        ).pack(anchor = "w")
        
        ttk.Radiobutton(
            panel, text = "Digital (Software)",
            variable = self.app_state.derivation_mode,
            value = "DIGITAL"
        ).pack(anchor = "w")
        
    # =====================================================
    # -------------- DERIVATION PANEL ---------------------
    # =====================================================
    
    def _create_derivation_panel(self, parent):
        panel = ttk.Labelframe(parent, text = "Derivation Selection", padding = "10")
        panel.pack(fill = tk.X, pady = 6)
        
        grid = ttk.Frame(panel)
        grid.pack()
        
        for i, label in self.app_state.mux_state_label.items():
            ttk.Button(
                grid,
                text = label,
                width = 8,
                command = lambda s = i: self.set_derivations(s)
            ).grid(row = i // 3, column = i % 3, padx = 4, pady = 4)
        
        self.current_derivation_label = ttk.Label(
            panel, text = "Current: I DERIVADA"
        )
        self.current_derivation_label.pack(pady = 4)
    
    def set_derivation(self, state):
        self.app_state.current_mux_state = state
        label = self.app_state.mux_state_label[state]
        self.current_derivation_label.config(text = f'Current: {label}')
        
        if self.app_state.derivation_mode.get() == "ANALOG":
            self.serial_reader.send_command(f'STATE_{state}')
    
    # =====================================================
    # ---------------- GAIN PANEL -------------------------
    # =====================================================
    
    def _create_gain_panel(self, parent):
        panel = ttk.LabelFrame(parent, text = "Gain Control", padding = "10")
        panel.pack(fill = tk.X, pady = 6)
        
        self.gain_label = ttk.Label(panel, text = "Gain: 1.00x")
        self.gain_label.pack()
        
        ttk.Scale(
            panel, from_ = 0.1, to = 5.0,
            orient = tk.HORIZONTAL,
            variable = self.app_state.ecg_gain,
            command = lambda v: self.gain_label.config(text = f'Gain: {float(v):.2f}x')
        ).pack(fill = "x", pady = 4)
    
    # =====================================================
    # -------------- PLOT CONTROL -------------------------
    # =====================================================
    
    def _create_plot_control_pade(self, parent):
        panel = ttk.LabelFrame(parent, text ="Plot Control", padding = "10")
        panel.pack(fill = tk.X, pady = 6)
        
        ttk.Label(panel, text = "Window Size").pack()
        ttk.Scale(
            panel, from_= 500, to = 3000,
            orient = tk.HORIZONTAL,
            variable = self.app_state.window_size
        ).pack(fill = "x")
        
        ttk.Label(panel, text = "Amplitude (V)").pack()
        ttk.Scale(
            panel, from_= 0.5, to = 5.0,
            orient = tk.HORIZONTAL,
            variable = self.app_state.y_max
        ).pack(fill = "x")
    
    # =====================================================
    # -------------- PEAK DETECTION -----------------------
    # =====================================================
    
    def _create_peak_panel(self, parent):
        panel = ttk.LabelFrame(parent, text = "peak Detection", padding = "10")
        panel.pack(fill = tk.X, pady = 6)
        
        ttk.Label(panel, text = "Threshold").pack()
        ttk.Scale(
            panel, from_= 0.1, to = 3.0,
            orient = tk.HORIZONTAL,
            variable = self.app_state.r_threshold
        ).pack(fill = "x")
        
        ttk.Label(panel, text = "Min Distance").pack()
        ttk.Scale(
            panel, from_= 20, to = 1000,
            orient = tk.HORIZONTAL,
            variable = self.app_state.r_distance
        ).pack(fill = "x")
    
    # =====================================================
    # ---------------- STATUS PANEL -----------------------
    # =====================================================
    
    def _create_status_panel(self, parent):
        panel = ttk.LabelFrame(parent, text = "System Status", padding = "10")
        panel.pack(fill = tk.X, pady = 6)
        
        self.status_labels = {}
        for label in [ "Arduino", "Samples", "BPM", "Signal Quality", "Derivation"]:
            ttk.Label(panel, text = f"{label}:").pack(anchor = "w")
            self.status_labels[label] = ttk.Label(panel, text = "N/A")
            self.status_labels[label].pack(anchor = "w")
    
    # =====================================================
    # ---------------- MAIN UPDATE ------------------------
    # =====================================================
    
    def update_gui(self):
        if not self.is_running:
            return
        
        with self.app_state.data_lock:
            x = list(self.app_state.time_buffer)
            y = self.app_state.get_current_ecg_signal()
            y_f = list(self.app_state.filtered_buffer)
        
        if y:
            self.update_plots(x, y, y_f)
        
        self.update_status()
        self.update_pacemaker_alert()
        self.after(config.REFRESH_INTERVAL, self.update_gui)
    
    def update_plots(self, x, y_raw, y_filt):
        win = self.app_state.window_size.get()
        x = x[-win:]
        y_raw = y_raw[-win:]
        y_filt = y_filt[-win:]
        
        self.line_raw.set_data(x, y_raw)
        self.line_filtered.set_data(x, y_filt)
        
        signal = y_filt if config.ENABLE_FILTERS else y_raw
        peaks = detect_r_peaks(signal, self.app_state.r_threshold.get(), self.app_state.r_distance.get())
        self.peaks_line.set_data([x[i] for i in peaks], [signal[i] for i in peaks])
        
        self.ax1.set_ylim(-self.app_state.y_max.get(), self.app_state.y_max.get())
        self.ax2.set_ylim(-self.app_state.y_max.get(), self.app_state.y_max.get())
        self.ax1.set_xlim(x[0], x[-1])
        
        self.canvas.draw()
    
    def update_status(self, y_raw):
        self.status_labels["Arduino"].config(
            text="🟢 Connected" if self.app_state.arduino_connected else "🔴 Disconnected"
        )
        
        self.status_labels["Samples"].config(text=str(self.app_state.sample_count))
        
        peaks = detect_r_peaks(y_raw, self.app_state.r_threshold.get(), self.app_state.r_distance.get())
        bpm = calculate_bpm(peaks, config.SAMPLE_RATE)
        self.status_labels["BPM"].config(text=f"{bpm:.0f}" if bpm > 0 else "Calculating")
        
        noise = np.std(y_raw[-100:]) if len(y_raw) > 100 else 0
        quality = "🟢 GOOD" if noise < 0.05 else "🟡 FAIR" if noise < 0.1 else "🔴 POOR"
        self.status_labels["Signal Quality"].config(text=quality)
        
        state = self.app_state.current_mux_state
        self.status_labels["Derivation"].config(
            text=self.app_state.mux_state_label.get(state, "Unknown")
        )
    
    def on_closing(self):
        self.is_running = False
        self.serial_reader.stop()
        self.destroy()