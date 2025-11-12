# Serviciu pentru comunicarea de la Pico la Raspberry Pi
import pico_to_pi_service
# serviciu pentru trimiterea alertelor si avertizarilor
import alerts_warnings_service
import time
 # Serviciu pentru controlul motoarelor
import motor_service 

# Var ultima data cand s-a executat functia principala
last_run = 0

#Stocheaza ultimele 20 de citiri de la senzorul infrarosu de pe scari
# Initializam cu False pentru toate valorile
ir_scari_array = [False for i in range(0, 20)]

# Index pozitia curenta in array-ul de citiri IR
ir_scari_index = 0

# Timpul ultimei alerte trimise (pentru a evita spam-ul de alerte)
last_alert = 0

# Var care controleaza modurile de functionare ale robotului
aspirator_mode = False  # Modul aspirator pornit/oprit
perie_mode = False      # Modul perie pornit/oprit

def run():
    # Declaram variabilele globale pe care le vom modifica in functie
    global last_alert, last_run, ir_scari_index, ir_scari_array, aspirator_mode, perie_mode
    
    # Setam statusul motoarelor in functie de modurile curente
    motor_service.aspirator_status = aspirator_mode
    motor_service.perie_status = perie_mode
    
    # Scriem starile motoarelor in sistem
    motor_service.write_states()

    # Verificam daca a trecut destul timp de la ultima executie
    if time.time() > last_run:
        # Citim starea senzorului IR si o salvam in array la pozitia curenta
        ir_scari_array[ir_scari_index] = bool(pico_to_pi_service.ir_scari)
        
        # Actualizam indexul pentru urmatoarea citire (circular, revine la 0 dupa 19)
        ir_scari_index = (ir_scari_index + 1) % 20

        # toate valorile din array sunt identice = True -> blocaj - senzorul detecteaza continuu ceva
        if all(x == ir_scari_array[0] for x in ir_scari_array) and ir_scari_array[0] == True:
            # Verificam daca au trecut cel putin 20 de secunde de la ultima alerta pentru a evita trimiterea prea multor alerte
            if time.time() > last_alert + 20:
                print("Trimitem warning...")  # Mesaj de debug in consola
                
                # Trimitem alerta de blocaj
                alerts_warnings_service.send_warning("Blocaj detectat", "Un blocaj a fost detectat in mod manual.")
                
                # Actualizam timpul ultimei alerte
                last_alert = time.time()
        
        # Setam timpul pentru urmatoarea executie (1/20 secunde = 50ms)
        # Aceasta inseamna ca functia va rula la fiecare 50ms
        last_run = time.time() + (1 / 20)

    pass