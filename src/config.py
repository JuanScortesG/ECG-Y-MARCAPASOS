"""
Global configuration file
ECG Monitor - ESP32 + CD4051 MUX

"""

# =========================================================
# ---------------- SERIAL CONFIGURATION -------------------
# =========================================================

# Puerto del ESP32 (CAMBIAR según tu PC)
SERIAL_PORT = "COM3"
#uv run python -c "import serial.tools.list_ports; [print(p) for p in serial.tools.list_ports.comports()]"

# Baudrate (Debe coincidir con el ESP32)
BAUDRATE = 115200

# Timeout de lectura serial (segundos)
SERIAL_TIMEOUT = 1


# =========================================================
# ---------------- SAMPLING CONFIG ------------------------
# =========================================================

# Frecuencia de muestreo del ECG (Hz)
# Debe coincidir con la frecuencia real del ADC del ESP32
SAMPLE_RATE = 500  

# Intervalo de actualización de la GUI (ms)
REFRESH_INTERVAL = 30

# Tamaño máximo del buffer circular
MAX_BUFFER_SIZE = 5000


# =========================================================
# ---------------- MUX CONFIGURATION ----------------------
# =========================================================

# Prefijo del comando enviado al ESP32
# Ejemplo enviado: "MUX:0"
MUX_COMMAND_PREFIX = "MUX:"

# Número total de derivaciones
TOTAL_DERIVATIONS = 6

# Tiempo entre cambios automáticos de derivación (segundos)
AUTO_SWITCH_INTERVAL = 5


# =========================================================
# ---------------- SIGNAL DISPLAY CONFIG ------------------
# =========================================================

# Valor máximo inicial del eje Y (Voltios)
DEFAULT_Y_MAX = 2.0

# Tamaño inicial de ventana de visualización (samples)
DEFAULT_WINDOW_SIZE = 1000

# Ganancia inicial de visualización
DEFAULT_GAIN = 1.0


# =========================================================
# ---------------- PEAK DETECTION CONFIG ------------------
# =========================================================

# Umbral inicial para detección R
DEFAULT_R_THRESHOLD = 0.8

# Distancia mínima entre picos R (samples)
DEFAULT_R_DISTANCE = 200


# =========================================================
# ---------------- SYSTEM MODES ---------------------------
# =========================================================

MODE_MANUAL = "MANUAL"
MODE_AUTO = "AUTO"

AUTO_TIMEOUT = 10          # segundos sin tocar nada → pasa a AUTO
AUTO_SWITCH_INTERVAL = 5   # cada cuántos segundos cambia derivada en AUTO

# =========================================================
# ---------------- DEBUG ----------------------------------
# =========================================================

ENABLE_DEBUG_PRINTS = False

