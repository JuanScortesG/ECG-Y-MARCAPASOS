
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import time

from . import config
from .data_model import AppState
from .serial_handler import SerialReader
from .peak_detection import detect_r_peaks, calculate_bpm

class ECGApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ECG Monitor - 6 derivations")
        self.geometry("1300x850")
        self.previous_mux_state = None
        self.is_running = True
        
        # Core components
        self.app_state = AppState()
        self.serial_reader = SerialReader(self.app_state)
        
        # Alerta de marcapasos
        self.pacemaker_alert_active = False
        
        self._create_widgets()
        self.serial_reader.start()
        self.update_gui()
        self.previous_mux_state = self.app_state.current_mux_state
        
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
        
        self._create_derivation_panel(sidebar_frame)
        self._create_gain_panel(sidebar_frame)
        self._create_mode_panel(sidebar_frame)
        self._create_status_panel(sidebar_frame)
        self._create_pacemaker_panel(sidebar_frame)
        
    # =====================================================
    # ------------------ PLOTS ----------------------------
    # =====================================================
    
    def _create_plots(self, parent):

        self.fig, self.ax = plt.subplots(figsize=(9, 6))

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.ax.set_title("ECG Signal")
        self.ax.set_ylabel("Voltage (V)")
        self.ax.set_xlabel("Samples")
        self.ax.grid(True, alpha=0.3)

        self.line, = self.ax.plot([], [], linewidth=1.3)
        self.peaks_line, = self.ax.plot([], [], 'ro', markersize=5)

        self.fig.tight_layout()
    
    # =====================================================
    # ---------------- PACEMAKER ALERT -------------------
    # =====================================================
    def _create_pacemaker_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="Pacemaker Alert", padding="10")
        panel.pack(fill=tk.X, pady=6)
        
        self.pacemaker_label = ttk.Label(panel, text="No Alert", foreground="green", font=("Arial", 12, "bold"))
        self.pacemaker_label.pack()

    def update_pacemaker_alert(self, peaks):
        if len(peaks) == 0:
            self.pacemaker_label.config(text="⚠ PACEMAKER ACTIVATED ⚠", foreground="red")
        
        else:
            self.pacemaker_label.config(text="No Alert", foreground="green")
    
    # =====================================================
    # -------------- DERIVATION PANEL ---------------------
    # =====================================================
    
    def _create_derivation_panel(self, parent):

        panel = ttk.LabelFrame(parent, text="Derivation Control", padding="10")
        panel.pack(fill=tk.X, pady=6)

        self.current_derivation_label = ttk.Label(
            panel,
            text="Current: I DERIVADA",
            font=("Arial", 11, "bold")
        )
        self.current_derivation_label.pack(pady=4)

        ttk.Button(
            panel,
            text="Next Derivation",
            command=self.next_derivation_manual
        ).pack(fill="x", pady=4)

    def next_derivation_manual(self):

        self.app_state.next_derivation()
        self.app_state.last_manual_action_time = time.time()
        self.app_state.operation_mode.set(config.MODE_MANUAL)

        state = self.app_state.current_mux_state
        self.serial_reader.send_mux_command(state)

        self.update_derivation_label()

    def update_derivation_label(self):

        state = self.app_state.current_mux_state
        label = self.app_state.mux_state_label[state]
        self.current_derivation_label.config(text=f"Current: {label}")
    
    # =====================================================
    # ---------------- MODE PANEL -------------------------
    # =====================================================

    def _create_mode_panel(self, parent):

        panel = ttk.LabelFrame(parent, text="Operation Mode", padding="10")
        panel.pack(fill=tk.X, pady=6)

        self.mode_label = ttk.Label(
            panel,
            text="MANUAL",
            foreground="blue",
            font=("Arial", 11, "bold")
        )
        self.mode_label.pack()

    def update_mode_display(self):

        mode = self.app_state.operation_mode.get()

        if mode == config.MODE_AUTO:
            self.mode_label.config(text="AUTO", foreground="red")
        else:
            self.mode_label.config(text="MANUAL", foreground="blue")
    
    # =====================================================
    # ---------------- GAIN PANEL -------------------------
    # =====================================================
    
    def _create_gain_panel(self, parent):
        panel = ttk.LabelFrame(parent, text = "Gain", padding = "10")
        panel.pack(fill = tk.X, pady = 6)
        
        self.gain_label = ttk.Label(panel, text = "Gain: 1.00x")
        self.gain_label.pack()
        
        ttk.Scale(
            panel, from_ = 0.5, to = 5.0,
            orient = tk.HORIZONTAL,
            variable = self.app_state.ecg_gain,
            command = lambda v: self.gain_label.config(text = f'Gain: {float(v):.2f}x')
        ).pack(fill = "x", pady = 4)
    
    # =====================================================
    # -------------- PLOT CONTROL -------------------------
    # =====================================================
    
    def _create_plots(self, parent):

        self.fig, self.ax = plt.subplots(figsize=(9, 6))
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.ax.set_title("ECG Signal")
        self.ax.set_ylabel("Voltage (V)")
        self.ax.set_xlabel("Samples")
        self.ax.grid(True, alpha=0.3)
        
        self.line, = self.ax.plot([], [], linewidth=1.3)
        self.peaks_line, = self.ax.plot([], [], 'ro', markersize=5)
        
        self.fig.tight_layout()

    
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

        panel = ttk.LabelFrame(parent, text="System Status", padding="10")
        panel.pack(fill=tk.X, pady=6)

        self.status_labels = {}

        for label in ["ESP32", "Samples", "BPM", "Derivation"]:
            ttk.Label(panel, text=f"{label}:").pack(anchor="w")
            self.status_labels[label] = ttk.Label(panel, text="N/A")
            self.status_labels[label].pack(anchor="w")

    def update_status(self, y_raw):

        self.status_labels["ESP32"].config(
            text="🟢 Connected" if self.app_state.esp32_connected else "🔴 Disconnected"
        )

        self.status_labels["Samples"].config(
            text=str(self.app_state.sample_count)
        )

        peaks = detect_r_peaks(
            y_raw,
            self.app_state.r_threshold.get(),
            self.app_state.r_distance.get()
        )

        bpm = calculate_bpm(peaks, config.SAMPLE_RATE)

        self.status_labels["BPM"].config(
            text=f"{bpm:.0f}" if bpm > 0 else "Calculating"
        )

        state = self.app_state.current_mux_state
        self.status_labels["Derivation"].config(
            text=self.app_state.mux_state_label[state]
        )

        return peaks
    
    # =====================================================
    # ---------------- MAIN UPDATE ------------------------
    # =====================================================
    
    def update_gui(self):

        if not self.is_running:
            return

        with self.app_state.data_lock:
            x = list(self.app_state.time_buffer)
            y = self.app_state.get_current_signal()

        if len(y) > 0:

            win = self.app_state.window_size.get()

            x = x[-win:]
            y = y[-win:]

            y = np.array(y) * self.app_state.ecg_gain.get()

            self.line.set_data(x, y)

            self.ax.set_ylim(
                -self.app_state.y_max.get(),
                self.app_state.y_max.get()
            )

            self.ax.set_xlim(x[0], x[-1])

            peaks = detect_r_peaks(
                y,
                self.app_state.r_threshold.get(),
                self.app_state.r_distance.get()
            )

            self.peaks_line.set_data(
                [x[i] for i in peaks],
                [y[i] for i in peaks]
            )

            self.canvas.draw()

            peaks = self.update_status(y)
            self.update_pacemaker_alert(peaks)

        # ===== AUTO MODE LOGIC =====
        # Revisar modo automático
        self.app_state.check_auto_mode()

# Detectar cambio de derivada
        if self.app_state.current_mux_state != self.previous_mux_state:
    
            # Enviar comando al ESP32
            self.serial_reader.send_mux_command(
            f"STATE_{self.app_state.current_mux_state}"
        )
    
            # Actualizar estado guardado
            self.previous_mux_state = self.app_state.current_mux_state

        self.update_mode_display()

        self.after(config.REFRESH_INTERVAL, self.update_gui)

    # =====================================================
    # ---------------- CLOSE APP --------------------------
    # =====================================================

    def on_closing(self):
        self.is_running = False
        self.serial_reader.stop()
        self.destroy()
        import sys
        sys.exit(0)
        

# ================================
# EJECUTAR APP
# ================================
if __name__ == "__main__":
    app = ECGApp()
    app.mainloop()