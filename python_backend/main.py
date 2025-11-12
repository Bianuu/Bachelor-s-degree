# interacționa cu sistemul de operare (fisiere, directoare, variabile de mediu)
import os
# OpenCV 
import cv2  
import time 
# comunicarea prin porturi seriale
import serial  
# operatii pe array-uri
import numpy as np  
# Serviciu pentru controlul motoarelor
import motor_service 
# Serviciu pentru gestionarea modurilor de functionare 
import mode_service 
# Serviciu pentru comunicarea MQTT 
import mqtt_service 
# Serviciu pentru comunicarea de la Pico la Raspberry Pi
import pico_to_pi_service  

# Functie determina tipul unei linii pe baza coordonatelor
def get_line_type(x1, y1, x2, y2, thresh):
    # diferentelor absolute pe axele x si y
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    # Determinarea tipului de linie pe baza pragului
    if dy <= thresh * dx:
        return "horizontal"  # Linie orizontala
    elif dx <= thresh * dy:
        return "vertical"    # Linie verticala
    else:
        return "diagonal"    # Linie diagonala

# Functie calculeaza linia medie dintr-un set de linii
def get_average_line(lines):
    # Verificarea daca exista linii de procesat
    if len(lines) > 0:
        # Initializarea liniei medii cu valori zero
        average_line = [0, 0, 0, 0]
        
        # Suma coordonatelor tuturor liniilor
        for line in lines:
            average_line[0] = average_line[0] + line[0][0]  # x1
            average_line[1] = average_line[1] + line[0][1]  # y1
            average_line[2] = average_line[2] + line[0][2]  # x2
            average_line[3] = average_line[3] + line[0][3]  # y2
    
        # Calcularea mediei pentru fiecare coordonata
        for i in range(4):
            average_line[i] = int(average_line[i] / len(lines))
        
        # Returnarea liniei medii calculate cu succes
        return True, average_line

    # Returnarea valorilor implicite daca nu exista linii
    return False, [0,0,0,0]

# oprirea periei si aspiratorului
motor_service.set_perie(False)  
motor_service.set_aspirator(False)  

# Bucla principala de functionare
try:
    while True:
        # Primirea datelor de la Pico
        pico_to_pi_service.receive()
        # Rularea modului curent de functionare
        mode_service.run()
except KeyboardInterrupt:
    # Capturarea intreruperii de la tastatura (Ctrl+C)
    print("Exiting...")

# Eliberarea resurselor la iesirea din program
# Eliberarea camerei video
mode_service.cap.release()

# Oprirea si deconectarea serviciului MQTT
mqtt_service.client.loop_stop()  
mqtt_service.client.disconnect() 