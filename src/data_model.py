"""
This module defines the AppState class, which holds the shared state of the application.
Supports:
    - 6 ECG derivations
    - Analog (MUX-based) derivation mode
    - Digital (software-computed) derivation mode
"""

import threading
from collections import deque
import tkinter as tk
import time
import config 

class AppState:
    
    def __init__(self):
        # =====================================================
        # ---------------- DATA BUFFERS -----------------------
        # =====================================================
        self.data_lock = threading.Lock()
        
        "Buffers principales (señal mostrada)"
        self.voltage_buffer = deque(maxlen = 3000)
        self.filtered_buffer = deque(maxlen = 3000)
        self.time_buffer = deque(maxlen = 3000)
        self.sample_count = 0 
        
        # Buffers base para derivadas digitales
        self.RA_buffer = deque(maxlen = 3000)
        self.LA_buffer = deque(maxlen = 3000)
        self.LL_buffer = deque(maxlen = 3000)
        
        # =====================================================
        # --------------- CONNECTION STATUS -------------------
        # =====================================================
        self.serial_connected = False
        self.arduino_connected = False
        
        # =====================================================
        # --------------- DERIVATION MODE ---------------------
        # =====================================================
        # ANALOG  -> derivadas formadas por hardware (MUX)
        # DIGITAL -> derivadas calculadas en Python
        self.derivation_mode = tk.StringVar(value = "ANALOG")
        
        # =====================================================
        # ---------------- MUX CONTROL ------------------------
        # =====================================================
        self.mux_control_lock = threading.Lock()
        
        self.mux_state_label = {
            0: "I DERIVADA",
            1: "II DERIVADA",
            2: "III DERIVADA",
            3: "aVR",
            4: "aVL",
            5: "aVF"
        }
        self.current_mux_state = 0
        
        # =====================================================
        # -------- UI VARIABLES (AFFECT PROCESSING) -----------
        # =====================================================
        
        self.ecg_gain = tk.DoubleVar(value = 1.0)
        self.voltage_offset = tk.DoubleVar(value = 0.0)
        self.r_threshold = tk.DoubleVar(value = config.R_THRESHOLD_DEFAULT)
        self.r_distance = tk.IntVar(value = config.R_DISTANCE_DEFAULT)
        
        # =====================================================
        # -------- UI VARIABLES (DISPLAY ONLY) ----------------
        # =====================================================
        
        self.window_size = tk.IntVar(value = 1500)
        self.y_max = tk.DoubleVar(value = 3.5)
        
        # =====================================================
        # -------- CARDIAC STATE (PACEMAKER) ------------------
        # =====================================================
        self.bpm = 0.0
        self.last_rr_interval = None

        self.asystole_detected = False
        self.bradycardia_detected = False
        self.pacemaker_needed = False

        self.pacemaker_active = False
        self.last_pacemaker_pulse_time = 0.0
        
    # =========================================================
    # --------- ECG SIGNAL SELECTION (UNIFIED) ----------------
    # =========================================================
    
    def get_current_ecg_signal(self):
        """
        Returns the ECG signal to be displayed depending on the derivation mode.
        """
        if self.derivation_mode.get() == "ANALOG":
            return list(self.voltage_buffer)
        
        elif self.derivation_mode.get() == "DIGITAL":
            return self.compute_digital_derivation()
        
        return[]
    
    # =========================================================
    # --------- DIGITAL DERIVATION COMPUTATION ----------------
    # =========================================================
    
    def compute_digital_derivation(self):
        """
        Computes ECG derivations from RA, LA, LL signals.
        """
        RA = list(self.RA_buffer)
        LA = list(self.LA_buffer)
        LL = list(self.LL_buffer)
        
        if not (len(RA) == len (LA) == len (LL)):
            return[]
        
        derivation = []
        
        for i in range(len(RA)):
            if self.current_mux_state == 0:        #I
                derivation.append(
                    LA[i] - RA[i]
                    )
            
            elif self.current_mux_state == 1:      #II
                derivation.append(
                    LL[i] - RA[i]
                    )
            
            elif self.current_mux_state == 2:      #III
                derivation.append(
                    LL[i] - LA[i]
                    )
            
            elif self.current_mux_state == 3:      #aVR
                derivation.append(
                    RA[i] - (LA[i] + LL[i]) / 2
                )
            
            elif self.current_mux_state == 4:      #aVL
                derivation.append(
                    LA[i] - (RA[i] + LL[i]) / 2
                )
            
            elif self.current_mux_state == 5:      #aVF
                derivation.append(
                    LL[i] - (RA[i] + LA[i]) / 2
                )
        
        return derivation