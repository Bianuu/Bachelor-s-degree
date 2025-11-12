# Serviciu pentru comunicarea de la Pico la Raspberry Pi
import pico_to_pi_service 
# Serviciu pentru controlul motoarelor
import motor_service      
import time
# pentru definirea enumerarilor             
from enum import Enum  
# serviciu pentru trimiterea alertelor   
import alerts_warnings_service  
# comunicarea MQTT
import mqtt_service       

# Definim starile posibile ale robotului 
class States(Enum):
    MOVE_FORWARD = 0      # robotul se misca inainte
    DECIDE_DIRECTION = 1  # robotul decide in ce directie sa se roteasca
    ROTATE_LEFT = 2       # robotul se roteste la stanga
    ROTATE_RIGHT = 3      # robotul se roteste la dreapta
    MOVE_BACKWARD = 4     # robotul se misca inapoi

# Clasa gestionarea starii robotului
class RobotState():
    # starea curenta a robotului
    state: States  
    # distanta minima pentru detectarea obstacolelor              
    min_distance: int  
    # timpul cand se termina rotatia         
    finish_rotate_time: float   
    
    # Constructorul clasei - initializeaza valorile de baza
    def __init__(self):
        self.state = States.MOVE_FORWARD  # robotul incepe prin a merge inainte
        self.min_distance = 35            # distanta minima de 35 cm
        self.finish_rotate_time = 0       # nu avem rotatie activa initial
    
    # Functie schimbarea starii robotului cu afisare
    def changeState(self, new_state: States):
        print(f"[STATE CHANGE] {self.state} --> {new_state}")
        self.state = new_state
    
    # Functia pentru miscarea inainte
    def MOVE_FORWARD(self):
        # Verificam daca exista obstacole in fata, stanga sau dreapta
        if (pico_to_pi_service.us_front < self.min_distance or
            pico_to_pi_service.us_left < self.min_distance / 2 or
            pico_to_pi_service.us_right < self.min_distance / 2):
            motor_service.stop()  # oprim motoarele
            time.sleep(1)         # asteptam 1 secunda
            self.changeState(States.DECIDE_DIRECTION)  # trecem la decizia directiei
        else:
            motor_service.forwards()  # continuam sa mergem inainte
    
    # Functia pentru decizia directiei de rotatie
    def DECIDE_DIRECTION(self):
        # Setam timpul de finalizare a rotatiei la 0.5 secunde
        self.finish_rotate_time = time.time() + 0.5
        
        # Daca obstacol prea aproape in fata, mergem inapoi
        if pico_to_pi_service.us_front <= 40:
            self.finish_rotate_time = time.time() + 0.25  # timp miscare inapoi
            self.changeState(States.MOVE_BACKWARD)
        # Daca mai mult spatiu in stanga, ne rotim la stanga
        elif pico_to_pi_service.us_left > pico_to_pi_service.us_right:
            self.changeState(States.ROTATE_LEFT)
        # Altfel ne rotim la dreapta
        elif pico_to_pi_service.us_right >= pico_to_pi_service.us_left:
            self.changeState(States.ROTATE_RIGHT)
   
    # Functia pentru rotatia la dreapta
    def ROTATE_RIGHT(self):
        motor_service.left()  # activam motorul stang pentru rotatie dreapta
        # Verificam daca s-a terminat timpul de rotatie
        if(time.time() >= self.finish_rotate_time):
            motor_service.stop()  # oprim motoarele
            self.changeState(States.MOVE_FORWARD)  # reluam miscarea inainte
        pass
    
    # Functia pentru miscarea inapoi
    def MOVE_BACKWARD(self):
        motor_service.backwards()  # mergem inapoi
        # Verificam daca s-a terminat timpul de miscare inapoi
        if(time.time() >= self.finish_rotate_time):
            motor_service.stop()  # oprim motoarele
            self.changeState(States.DECIDE_DIRECTION)  # decidem din nou directia
        pass
    
    # Functia pentru rotatia la stanga
    def ROTATE_LEFT(self):
        motor_service.right()  # activam motorul drept pentru rotatie stanga
        # Verificam daca s-a terminat timpul de rotatie
        if(time.time() >= self.finish_rotate_time):
            motor_service.stop()  # oprim motoarele
            self.changeState(States.MOVE_FORWARD)  # reluam miscarea inainte
        pass
    
    # Functia principala care ruleaza logica robotului
    def run(self):
        # Comentariu pentru debug - afiseaza valorile senzorilor
        # print(f"front {pico_to_pi_service.us_front} left {pico_to_pi_service.us_left} right {pico_to_pi_service.us_right}")
        
        # Dictionarul care face legatura intre stari si functiile corespunzatoare
        state_lookup = {
            States.MOVE_FORWARD: self.MOVE_FORWARD,
            States.DECIDE_DIRECTION: self.DECIDE_DIRECTION,
            States.ROTATE_LEFT: self.ROTATE_LEFT,
            States.ROTATE_RIGHT: self.ROTATE_RIGHT,
            States.MOVE_BACKWARD: self.MOVE_BACKWARD,
        }
        
        # Obtinem functia corespunzatoare starii curente
        state_function = state_lookup[self.state]
        
        # Verificam daca starea este valida
        if not state_function:
            print("INVALID STATE DETECTED.")  # afisam eroare
            self.changeState(self.MOVE_FORWARD)  # resetam la starea de baza
        else:
            state_function()  # executam functia corespunzatoare starii

# Cream instanta globala a starii robotului
state = RobotState()

# Variabile globale pentru detectarea blocajelor
# timpul ultimei rulari
last_run = 0  
ir_scari_array = [False for i in range(0, 20)]  # ultimele 20 de citiri IR
# indexul curent in array-ul IR
ir_scari_index = 0  
# timpul ultimei alerte trimise
last_alert = 0  

# Functia principala care ruleaza continuu
def run():
    global last_alert, last_run, ir_scari_index, ir_scari_array
    
    # Executam logica la fiecare 1/20 secunde (20 Hz)
    if time.time() > last_run:
        # Salvam starea curenta a senzorului IR in array
        ir_scari_array[ir_scari_index] = bool(pico_to_pi_service.ir_scari)
        # Actualizam indexul circular (revine la 0 dupa 19)
        ir_scari_index = (ir_scari_index + 1) % 20
        
        # Verificam daca toate valorile din array sunt True (blocaj detectat)
        if all(x == ir_scari_array[0] for x in ir_scari_array) and ir_scari_array[0] == True:
            # Trimitem alerta doar daca au trecut 20 secunde de la ultima alerta
            if time.time() > last_alert + 20:
                print("Trimitem warning...")
                # Trimitem alerta de blocaj
                alerts_warnings_service.send_alert("Blocaj detectat", "Un blocaj a fost detectat in mod aspirator autonom.")
                # Comutam robotul in mod manual
                mqtt_service.client.publish("set_mode", "manual")
                mqtt_service.mode = "manual"
                # Actualizam timpul ultimei alerte
                last_alert = time.time()
       
        # Setam timpul pentru urmatoarea rulare (50ms mai tarziu)
        last_run = time.time() + (1 / 20)
    
    # Executam logica principala a robotului
    state.run()
    pass