import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading
import time

#import config
from data_model import AppState
from filters import ECGFilters
from peak_detection import detect_r_peaks, calculate_bpm
from .fake_serial import FakeSerialReader


# ================================
# FAKE SERIAL READER (Simulación)
# ================================
class FakeSerialReader:
    def __init__(self, app_state, ecg_filters=None):
        self.app_state = app_state
        self.ecg_filters = ecg_filters
        self.running = False
        self.sample_count = 0
        self.last_r_time = time.time()
        self.realtime_peak_buffer = []

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.simulate_data, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def simulate_data(self):
        """Genera señal ECG sintética y picos R"""
        t = 0
        fs = 200  # Frecuencia de muestreo simulada
        while self.running:
            # Señal base: onda senoidal + pico R
            ecg_signal = 0.2 * np.sin(2 * np.pi * 1 * t)  # onda suave
            if int(t*fs) % fs == 0:
                ecg_signal += 1.0  # pico R
                self.last_r_time = time.time()

            # Simular fallo de latido aleatorio cada 10 seg aprox
            if np.random.rand() < 0.01:
                self.last_r_time -= 3  # fuerza activación marcapasos

            filtered_signal = ecg_signal
            if self.ecg_filters:
                filtered_signal = self.ecg_filters.process_sample(ecg_signal)

            with self.app_state.data_lock:
                self.app_state.voltage_buffer.append(ecg_signal)
                self.app_state.filtered_buffer.append(filtered_signal)
                self.app_state.time_buffer.append(self.sample_count)
                self.sample_count += 1

            # Comprobar activación marcapasos (si no hay R por >2 seg)
            if time.time() - self.last_r_time > 2.0:
                print("⚠️ Marcapasos activado!")
                self.last_r_time = time.time()  # reinicia contador

            t += 1/fs
            time.sleep(1/fs)

# ================================
# APP PRINCIPAL
# ================================
class ECGApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ECG Monitor - 6 derivations (Simulado)")
        self.geometry("1300x850")
        self.is_running = True

        # Core components
        self.app_state = AppState()
        self.ecg_filters = ECGFilters()
        self.serial_reader = FakeSerialReader(self.app_state, self.ecg_filters)

        self._create_widgets()
        self.serial_reader.start()
        self.update_gui()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------------- UI -----------------------
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        plot_frame = ttk.Frame(main_frame)
        plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sidebar_frame = ttk.Frame(main_frame, width=320)
        sidebar_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        self._create_plots(plot_frame)
        self._create_status_panel(sidebar_frame)
    
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
    
    def _create_plots(self, parent):
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.line_raw, = self.ax1.plot([], [], 'b-', linewidth=1.1)
        self.line_filtered, = self.ax2.plot([], [], 'g-', linewidth=1.3)
        self.peaks_line, = self.ax2.plot([], [], 'ro', markersize=5)
        self.ax1.set_ylabel("Raw ECG (V)")
        self.ax1.set_title("ECG Signal")
        self.ax1.grid(True, alpha=0.3)
        self.ax2.set_xlabel("Samples")
        self.ax2.set_ylabel("Filtered ECG (V)")
        self.ax2.grid(True, alpha=0.3)
        self.fig.tight_layout()

    def _create_status_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="System Status", padding="10")
        panel.pack(fill=tk.X, pady=6)
        self.status_labels = {}
        for label in ["Samples", "BPM", "Signal Quality"]:
            ttk.Label(panel, text=f"{label}:").pack(anchor="w")
            self.status_labels[label] = ttk.Label(panel, text="N/A")
            self.status_labels[label].pack(anchor="w")

    # ---------------- GUI UPDATE -----------------
    def update_gui(self):
        if not self.is_running:
            return

        with self.app_state.data_lock:
            x = list(self.app_state.time_buffer)
            y_raw = list(self.app_state.voltage_buffer)
            y_filt = list(self.app_state.filtered_buffer)

        if y_raw:
            self.update_plots(x, y_raw, y_filt)
            self.update_status(y_raw)

        self.after(50, self.update_gui)

    def update_plots(self, x, y_raw, y_filt):
        win = min(1500, len(x))
        x = x[-win:]
        y_raw = y_raw[-win:]
        y_filt = y_filt[-win:]

        self.line_raw.set_data(x, y_raw)
        self.line_filtered.set_data(x, y_filt)

        peaks = detect_r_peaks(y_filt, 0.5, 20)  # Umbral bajo para demo
        self.peaks_line.set_data([x[i] for i in peaks], [y_filt[i] for i in peaks])

        self.ax1.set_ylim(-0.5, 2.0)
        self.ax2.set_ylim(-0.5, 2.0)
        self.ax1.set_xlim(x[0], x[-1])
        self.canvas.draw()

    def update_status(self, y_raw):
        self.status_labels["Samples"].config(text=str(len(y_raw)))
        peaks = detect_r_peaks(y_raw, 0.5, 20)
        bpm = calculate_bpm(peaks, 200)
        self.status_labels["BPM"].config(text=f"{bpm:.0f}" if bpm>0 else "Calculating")
        noise = np.std(y_raw[-100:]) if len(y_raw) > 100 else 0
        quality = "GOOD" if noise < 0.1 else "FAIR" if noise < 0.2 else "POOR"
        self.status_labels["Signal Quality"].config(text=quality)

    def on_closing(self):
        self.is_running = False
        self.serial_reader.stop()
        self.destroy()

# ================================
# EJECUTAR APP
# ================================
if __name__ == "__main__":
    app = ECGApp()
    app.mainloop()
