import threading
import time
import math
import random

class FakeSerialReader:
    """
    Simula un ECG para probar la GUI sin Arduino ni ESP32
    """
    def __init__(self, app_state, ecg_filters):
        self.app_state = app_state
        self.ecg_filters = ecg_filters
        self.running = False
        self.fs = 500              # Frecuencia de muestreo simulada
        self.bpm = 60              # Ritmo cardíaco
        self.t = 0
        self.dt = 1 / self.fs

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.app_state.serial_connected = True
        self.app_state.arduino_connected = False
        print("FakeSerialReader iniciado (modo simulación)")

    def stop(self):
        self.running = False
        print("FakeSerialReader detenido")

    def send_command(self, command):
        # No hace nada, solo para compatibilidad
        print(f"[FAKE SERIAL] Comando ignorado: {command}")

    def _run(self):
        while self.running:
            ecg_value = self._synthetic_ecg(self.t)
            filtered = self.ecg_filters.process_sample(ecg_value)

            with self.app_state.data_lock:
                self.app_state.voltage_buffer.append(ecg_value)
                self.app_state.filtered_buffer.append(filtered)
                self.app_state.time_buffer.append(self.app_state.sample_count)
                self.app_state.sample_count += 1

            self.t += self.dt
            time.sleep(self.dt)

    def _synthetic_ecg(self, t):
        """
        ECG sintético con QRS marcado
        """
        hr_period = 60 / self.bpm
        phase = (t % hr_period) / hr_period

        # Componentes del ECG
        p_wave = 0.1 * math.sin(2 * math.pi * (phase - 0.2)) if 0.15 < phase < 0.25 else 0
        qrs = 1.2 * math.exp(-((phase - 0.5) ** 2) / 0.0008)
        t_wave = 0.3 * math.sin(2 * math.pi * (phase - 0.7)) if 0.6 < phase < 0.85 else 0

        noise = random.uniform(-0.02, 0.02)

        return p_wave + qrs + t_wave + noise
