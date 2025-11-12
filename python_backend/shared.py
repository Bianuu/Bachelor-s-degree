# Comunicarea seriala cu dispozitive
import serial

# Initializam variabila globala pentru conexiunea cu microcontrollerul Pico
pico = None

# Incercam sa stabilim conexiunea cu microcontrollerul Pico
# Uneori Pico-ul ajunge pe ttyACM0 sau ttyACM1 (porturile pot varia)
try:
    # Prima incercare: conectare pe portul /dev/ttyACM0
    # Parametri conexiune:
    # - port: "/dev/ttyACM0" - primul port serial disponibil
    # - baudrate: 9600 - viteza de comunicare (biti pe secunda)
    # - timeout: 1 - timeout de 1 secunda pentru operatiile de citire
    pico = serial.Serial(port="/dev/ttyACM0", baudrate=9600, timeout=1)
    
# Daca prima incercare esueaza (portul nu este disponibil)
except serial.serialutil.SerialException as e:
    # A doua incercare: conectare pe portul /dev/ttyACM1
    # Folosim aceiasi parametri ca mai sus
    pico = serial.Serial(port="/dev/ttyACM1", baudrate=9600, timeout=1)