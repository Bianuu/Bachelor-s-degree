# OpenCV
import cv2
# Serviciu pentru comunicarea MQTT
import mqtt_service  
# Serviciu pentru controlul motoarelor
import motor_service  
# Servicii pentru diferite moduri de functionare
import mode_smart_perie_autonom  
import mode_aspirator_autonom  
import mode_manual
# operatii pe array-uri
import numpy as np  
# serviciu pentru trimiterea alertelor si avertizarilor
import alerts_warnings_service 
import time 
# Serviciu pentru comunicarea de la Pico la Raspberry Pi
import pico_to_pi_service 

# Initializam camera video
cap = cv2.VideoCapture("/dev/video0")

# Setam parametrii pentru rezolutia si buffer-ul camerei
width, height, buffersize = 640, 480, 2

# Configuram proprietatile camerei cu valorile dorite
print(f"Setting CAP_PROP_FRAME_WIDTH to {width}")
# Setam latimea frame-ului
cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)  
print(f"Setting CAP_PROP_FRAME_HEIGHT to {height}")
# Setam inaltimea frame-ului
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)  
print(f"Setting CAP_PROP_BUFFERSIZE to {buffersize}")
# Setam dimensiunea buffer-ului
cap.set(cv2.CAP_PROP_BUFFERSIZE, buffersize)  

# Timpul ultimei rulari a ciclului de verificare senzori
last_run = 0  

# Array pentru monitorizarea senzorului IR al aspiratorului (ultimele 20 de valori)
ir_aspiraor_array = [False for i in range(0, 20)]
# Indexul curent in array-ul de valori IR
ir_aspirator_index = 0  

# Array pentru monitorizarea senzorului de umiditate (ultimele 20 de valori)
umiditate_array = [False for i in range(0, 20)]
# Indexul curent in array-ul de valori umiditate
umiditate_index = 0  

last_alert = 0  # Timpul ultimei alerte trimise

def run():
    """Functia principala care ruleaza ciclul de procesare"""
    
    # Citim un frame de la camera
    ret, frame = cap.read()

    # Verificam daca frame-ul a fost citit cu succes
    if not ret:
        print("Failed to capture frame from camera.")
        return

    # Comentariu: linia de resize este comentata
    #frame = cv2.resize(frame[0:310, 0:640], (640, 640))

    # Convertim imaginea color in tonuri de gri pentru procesare
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Aplicam thresholding binar pentru a obtine o imagine alb-negru
    ret, frame_binary = cv2.threshold(frame_gray, 125, 255, cv2.THRESH_BINARY)
    
    # Aplicam blur pentru a netezi imaginea binara
    frame_binary = cv2.blur(frame_binary, (11, 11))
    
    # Declaram variabilele globale care vor fi modificate
    global last_alert, last_run, ir_aspiraor_array, ir_aspirator_index, umiditate_array, umiditate_index
    
    # Verificam daca este timpul sa rulam ciclul de monitorizare senzori (la fiecare 1/20 secunde)
    if time.time() > last_run:
        
        # Adaugam valoarea curenta a senzorului IR in array si actualizam indexul
        ir_aspiraor_array[ir_aspirator_index] = bool(pico_to_pi_service.ir_aspirator)
        ir_aspirator_index = (ir_aspirator_index + 1) % 20  # Circular buffer

        # Verificam daca toate valorile din array sunt False (recipient aproape plin)
        if all(x == ir_aspiraor_array[0] for x in ir_aspiraor_array) and ir_aspiraor_array[0] == False:
            # Trimitem alerta doar daca au trecut 180 secunde de la ultima alerta
            if time.time() > last_alert + 180:
                print("Trimitem warning...")
                alerts_warnings_service.send_alert("Recipient aproape plin detectat", "Recipientul de la aspirator este aproape plin.")
                # Oprim modurile de functionare
                mode_manual.aspirator_mode = False
                mode_manual.perie_mode = False
                last_alert = time.time()
                
        # Adaugam valoarea curenta a senzorului de umiditate in array si actualizam indexul
        umiditate_array[umiditate_index] = bool(pico_to_pi_service.senzor_umid)
        umiditate_index = (umiditate_index + 1) % 20  # Circular buffer

        # Verificam daca toate valorile din array sunt False (umiditate detectata)
        if all(x == umiditate_array[0] for x in umiditate_array) and umiditate_array[0] == False:
            # Trimitem alerta doar daca au trecut 60 secunde de la ultima alerta
            if time.time() > last_alert + 60:
                print("Trimitem warning...")
                alerts_warnings_service.send_alert("Umiditate detectata", "Un nivel inalt de umiditate a fost detectat pe gresie.")
                # Oprim modurile de functionare
                mode_manual.aspirator_mode = False
                mode_manual.perie_mode = False
                last_alert = time.time()
        
        # Setam timpul pentru urmatoarea rulare (1/20 secunde in viitor)
        last_run = time.time() + (1 / 20)

    # Alegem modul de functionare bazat pe comanda MQTT
    if mqtt_service.mode == "manual":
        # Rulam modul manual
        mode_manual.run()
    elif mqtt_service.mode == "aspirare":
        # Rulam modul autonom pentru aspirare
        mode_aspirator_autonom.run()
    elif mqtt_service.mode == "perie":
        # Verificam daca modul perie s-a terminat si nu a fost anuntat inca
        if mode_smart_perie_autonom.state.state == mode_smart_perie_autonom.States.END and mode_smart_perie_autonom.state.has_announced_end == False:
            # Codul pentru schimbarea modului este comentat
            # mqtt_service.client.publish("set_mode", "manual")
            # mqtt_service.mode = "manual"

            # Oprim peria si aspiratorul
            motor_service.set_perie(False)
            motor_service.set_aspirator(False)

        # Rulam modul autonom pentru perie cu frame-urile procesate
        mode_smart_perie_autonom.run(frame, frame_binary)

    # Verificam senzorii de scari pentru siguranta - oprim robotul daca detectam scari
    if pico_to_pi_service.ir_scari and motor_service.last_requested_action != "backwards":
        motor_service.stop()

    # Salvam imaginile pentru monitorizare (frame original si frame binar)
    cv2.imwrite("/tmp/camera.jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    cv2.imwrite("/tmp/camerabin.jpg", frame_binary, [int(cv2.IMWRITE_JPEG_QUALITY), 50])