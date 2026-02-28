"""
Serial communication handler for ESP32 ECG acquisition.
Handles:
    - Binary packet decoding
    - Signal processing pipeline
    - Automatic / Manual derivation switching
"""

import serial
import time
import threading
from collections import deque
#import serial
#print(serial)
#print(serial.__file__)
#print(dir(serial))
from . import config


class SerialReader(threading.Thread):
    
    def __init__(self, app_state):
        super().__init__(daemon=True)
        self.app_state = app_state
        
        self.serial_port = None
        #serial.Serial(config.SERIAL_PORT, config.BAUDRATE)
        self.running = True
        
        #self.read_thread = None
        #self.auto_thread = None
    
    def run(self):
        while self.running:
            if self.serial_port and self.serial_port.in_waiting:
                line = self.serial_port.readline().decode().strip()
                self.app_state.add_sample(line)

    def send_mux_command(self, state):
        command = f"STATE_{state}\n"
        self.serial_port.write(command.encode())

    def stop(self):
        self.running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

    # =========================================================
    # ----------------- CONNECTION ----------------------------
    # =========================================================
    
    def connect(self):
        try:
            self.serial_port = serial.Serial(
                port=config.SERIAL_PORT,
                baudrate=config.BAUDRATE,
                timeout=config.SERIAL_TIMEOUT
            )
            
            self.app_state.serial_connected = True
            self.app_state.esp32_connected = True
            
            self.running = True
            
            # Thread lectura ECG
            self.read_thread = threading.Thread(
                target=self.read_serial,
                daemon=True
            )
            self.read_thread.start()
            
            # Thread modo automático
            self.auto_thread = threading.Thread(
                target=self.auto_mode_loop,
                daemon=True
            )
            self.auto_thread.start()
            
            print("ESP32 connected successfully")
            
        except Exception as e:
            print("Connection error:", e)
            self.app_state.serial_connected = False
            self.app_state.esp32_connected = False

    # =========================================================
    # ----------------- DISCONNECT ----------------------------
    # =========================================================
    
    def disconnect(self):
        self.running = False
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        
        self.app_state.serial_connected = False
        self.app_state.esp32_connected = False
        
        print("Disconnected")

    # =========================================================
    # ----------------- READ ECG DATA -------------------------
    # =========================================================
    
    def read_serial(self):
        """
        Reads ECG values from ESP32.
        Expected format: one value per line (e.g., 1.234)
        """
        while self.running:
            try:
                if self.serial_port.in_waiting:
                    line = self.serial_port.readline().decode().strip()
                    
                    if line:
                        voltage = float(line)
                        
                        with self.app_state.data_lock:
                            self.app_state.voltage_buffer.append(voltage)
                            self.app_state.sample_count += 1
                            
            except:
                continue

    # =========================================================
    # ----------------- SEND MUX COMMAND ----------------------
    # =========================================================
    
    def send_mux_command(self, state):
        """
        Sends derivation index (0–5) to ESP32.
        ESP32 must decode and control CD4051.
        """
        if self.serial_port and self.serial_port.is_open:
            command = f"STATE{state}\n"
            self.serial_port.write(command.encode())

    # =========================================================
    # ----------------- AUTO MODE LOOP ------------------------
    # =========================================================
    
    def auto_mode_loop(self):
        """
        Handles automatic derivation switching.
        """
        last_switch_time = time.time()
        
        while self.running:
            
            # Verificar si debe entrar en modo AUTO
            self.app_state.check_auto_mode()
            
            if self.app_state.operation_mode.get() == "AUTO":
                
                if time.time() - last_switch_time >= config.AUTO_SWITCH_INTERVAL:
                    
                    # Cambiar derivación
                    self.app_state.next_derivation()
                    
                    # Enviar comando al ESP32
                    self.send_mux_command(
                        self.app_state.current_mux_state
                    )
                    
                    last_switch_time = time.time()
            
            time.sleep(0.1)
            
