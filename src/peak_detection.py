"""
Peak detection and cardiac cycle analysis for ECG signals.
Includes pacemaker trigger logic.
"""

import numpy as np
import time


def detect_r_peaks(signal_data, threshold, distance):
    """
    Simple R-peak detector based on threshold and minimum distance.
    """
    if len(signal_data) < 3:
        return []

    peaks = []
    last_peak = -distance

    for i in range(1, len(signal_data) - 1):
        if (
            signal_data[i] > threshold
            and signal_data[i] > signal_data[i - 1]
            and signal_data[i] > signal_data[i + 1]
        ):
            if i - last_peak >= distance:
                peaks.append(i)
                last_peak = i

    return peaks


def calculate_bpm(peaks, sample_rate):
    """
    Calculate BPM from R-peak indices.
    """
    if len(peaks) < 2:
        return 0
    rr_intervals = [(peaks[i+1]-peaks[i])/sample_rate for i in range(len(peaks)-1)]
    avg_rr = sum(rr_intervals)/len(rr_intervals)
    bpm = 60 / avg_rr
    return bpm


# ==================================================
# NUEVO: Análisis del ciclo cardíaco (marcapasos)
# ==================================================

def analyze_cardiac_cycle(peaks, sample_rate, min_bpm=50, max_rr_interval=2.0):
    """
    Analyze cardiac rhythm to detect failures.

    Args:
        peaks (list): R-peak indices
        sample_rate (int): Hz
        min_bpm (int): Minimum safe BPM
        max_rr_interval (float): Max allowed RR interval in seconds

    Returns:
        dict: Cardiac status
    """
    status = {
        "bpm": 0,
        "asystole": False,
        "bradycardia": False,
        "pacemaker_needed": False,
        "last_rr_interval": None,
    }

    if len(peaks) < 2:
        status["asystole"] = True
        status["pacemaker_needed"] = True
        return status

    rr_intervals = np.diff(peaks) / sample_rate
    last_rr = rr_intervals[-1]
    bpm = 60 / np.mean(rr_intervals)

    status["bpm"] = bpm
    status["last_rr_interval"] = last_rr

    # Asystole: demasiado tiempo sin latido
    if last_rr > max_rr_interval:
        status["asystole"] = True
        status["pacemaker_needed"] = True

    # Bradycardia
    elif bpm < min_bpm:
        status["bradycardia"] = True
        status["pacemaker_needed"] = True

    return status