# # modul partajat
import shared
import time
# modul pentru comunicarea Pi Pico cu Raspberry Pi
import pico_to_pi_service

max_move_speed = 120  # Viteza maxima pentru miscare lineara
max_rotate_speed = 255  # Viteza maxima pentru rotatie

perie_status = False      # Statusul periei (pornita/oprita)
aspirator_status = False  # Statusul aspiratorului (pornit/oprit)

# Ultima actiune solicitata
last_requested_action = ""

def write_states():
    """Functie care trimite statusul periei si aspiratorului catre microcontroller"""
    global perie_status, aspirator_status
    # Cream pachetul de date pentru setarea statusului componentelor
    # Format: [header1, header2, stare_perie, stare_aspirator, rezervat1, rezervat2]
    byte_buffer = bytearray([0x7A, 0xF3, perie_status, aspirator_status, 0, 0])
    # Trimitem datele catre microcontroller prin conexiunea seriala
    shared.pico.write(byte_buffer)

def set_perie(status: bool):
    """Functie pentru controlul periei robotului"""
    global perie_status
    perie_status = status  # Actualizam statusul periei
    write_states()         # Trimitem noua stare 

def set_aspirator(status: bool):
    """Functie pentru controlul aspiratorului robotului"""
    global aspirator_status
    aspirator_status = status  # Actualizam statusul aspiratorului
    write_states()             # Trimitem noua stare 

def set_motors(left_speed: int, right_speed: int, left_reverse: bool, right_reverse: bool):
    """Functie pentru controlul motoarelor robotului"""
    # Limitam vitezele intre 0 si 255 pentru a evita valorile invalide
    left_speed = max(0, min(left_speed, 255))
    right_speed = max(0, min(right_speed, 255))

    # Cream pachetul de date pentru controlul motoarelor
    # Format: [header1, header2, viteza_stanga, viteza_dreapta, directie_stanga, directie_dreapta]
    byte_buffer = bytearray([0xF0, 0x0F, left_speed, right_speed, left_reverse, right_reverse])
    # Trimitem comanda catre microcontroller
    shared.pico.write(byte_buffer)

def forwards():
    """Functie pentru miscarea robotului inainte"""
    global last_requested_action
    last_requested_action = "forwards"  # Inregistram actiunea pentru debugging
    # Setam ambele motoare sa se roteasca inainte cu viteza maxima
    set_motors(max_move_speed, max_move_speed, 0, 0)

def backwards():
    """Functie pentru miscarea robotului inapoi"""
    global last_requested_action
    last_requested_action = "backwards"  # Inregistram actiunea pentru debugging
    # Setam ambele motoare sa se roteasca inapoi cu viteza maxima
    set_motors(max_move_speed, max_move_speed, 1, 1)

# Variabile globale pentru pozitiile tinta ale motoarelor
step_goal_a = 0  # Pozitia tinta pentru motorul A (stanga)
step_goal_b = 0  # Pozitia tinta pentru motorul B (dreapta)

def move_forward_steps(steps):
    """Functie pentru miscarea inainte cu un numar specific de pasi"""
    # Primim pozitia actuala a motoarelor de la microcontroller
    pico_to_pi_service.receive()
    global step_goal_a, step_goal_b
    # Calculam pozitiile tinta pentru ambele motoare
    step_goal_a = pico_to_pi_service.motor_a_pos + steps
    # Motorul B primeste 90% din pasi pentru compensarea diferentelor mecanice
    step_goal_b = pico_to_pi_service.motor_b_pos + int(steps * 0.9)

def move_backward_steps(steps):
    """Functie pentru miscarea inapoi cu un numar specific de pasi"""
    # Primim pozitia actuala a motoarelor de la microcontroller
    pico_to_pi_service.receive()
    global step_goal_a, step_goal_b
    # Calculam pozitiile tinta pentru ambele motoare (scadem pasii)
    step_goal_a = pico_to_pi_service.motor_a_pos - steps
    step_goal_b = pico_to_pi_service.motor_b_pos - int(steps * 0.9)

def rotate_right_steps(steps):
    """Functie pentru rotirea la dreapta cu un numar specific de pasi"""
    # Primim pozitia actuala a motoarelor de la microcontroller
    pico_to_pi_service.receive()
    global step_goal_a, step_goal_b
    # Pentru rotire la dreapta: motorul stang inainte, motorul drept inapoi
    step_goal_a = pico_to_pi_service.motor_a_pos + steps
    step_goal_b = pico_to_pi_service.motor_b_pos - int(steps)

def rotate_left_steps(steps):
    """Functie pentru rotirea la stanga cu un numar specific de pasi"""
    # Primim pozitia actuala a motoarelor de la microcontroller
    pico_to_pi_service.receive()
    global step_goal_a, step_goal_b
    # Pentru rotire la stanga: motorul stang inapoi, motorul drept inainte
    step_goal_a = pico_to_pi_service.motor_a_pos - steps
    step_goal_b = pico_to_pi_service.motor_b_pos + int(steps)

# executarea pas cu pas a miscarii motoarelor pana cand ating tinta
def run_goal_steps() -> bool:
    """Functie care executa miscarea catre pozitiile tinta setate anterior"""
    global last_requested_action
    last_requested_action = "run_steps"  # Inregistram actiunea pentru debugging
    
    # Primim pozitiile actuale ale motoarelor
    pico_to_pi_service.receive()
    global step_goal_a, step_goal_b
    motor_a_pos = pico_to_pi_service.motor_a_pos
    motor_b_pos = pico_to_pi_service.motor_b_pos

    # Viteza pentru executarea pasilor
    max_rotate_speed = 120

    # Initializam parametrii motoarelor
    left_speed, right_speed, left_reverse, right_reverse = 0, 0, False, False

    # Controlul motorului A (stanga)
    # Daca pozitia actuala este mai mica decat tinta cu mai mult de 50 de pasi
    if(motor_a_pos < step_goal_a - 50):
        left_speed = max_rotate_speed  # Mergem inainte
        left_reverse = False
    # Daca pozitia actuala este mai mare decat tinta cu mai mult de 50 de pasi
    elif(step_goal_a + 50 < motor_a_pos):
        left_speed = max_rotate_speed  # Mergem inapoi
        left_reverse = True
    
    # Controlul motorului B (dreapta) 
    if(motor_b_pos < step_goal_b - 50):
        right_speed = max_rotate_speed  # Mergem inainte
        right_reverse = False
    elif(step_goal_b + 50 < motor_b_pos):
        right_speed = max_rotate_speed  # Mergem inapoi
        right_reverse = True

    # Aplicam setarile calculate la motoare
    set_motors(left_speed, right_speed, left_reverse, right_reverse)
    
    # Verificam daca am ajuns la destinatie (ambele motoare oprite)
    if left_speed == right_speed and right_speed == 0:
        return True  # Miscarea s-a terminat
    
    return False  # Miscarea inca nu s-a terminat

def forwards_correct(vline):
    """Functie pentru miscarea inainte cu corectie bazata pe linia detectata"""
    global max_move_speed, max_rotate_speed, last_requested_action
    last_requested_action = "forwards_correct"  # Inregistram actiunea

    if vline:  # Daca avem o linie detectata
        # Calculam pozitia medie a liniei pe axa X (normalizata intre -1 si 1)
        average_x = (((vline[0] + vline[2]) / 2) / 320) - 1
        x_dev_lim = 0.015  # Limita de deviere acceptabila

        # Setam vitezele de baza pentru ambele motoare
        motor_left, motor_right = max_move_speed, max_move_speed
        
        # Corectia pentru deviere la stanga
        if average_x < -x_dev_lim:
            motor_right = 255  # Crestem viteza motorului drept
        # Corectia pentru deviere la dreapta
        elif x_dev_lim < average_x:
            motor_left = 255   # Crestem viteza motorului stang

        # Aplicam setarile (mergem inainte)
        set_motors(motor_left, motor_right, False, False)
    else:
        # Daca nu avem linie detectata, mergem inainte cu viteza normala
        motor_left, motor_right = max_move_speed, max_move_speed
        set_motors(motor_left, motor_right, True, True)  # Mergem inapoi pentru a cauta linia

def backwards_correct(vline):
    """Functie pentru miscarea inapoi cu corectie bazata pe linia detectata"""
    global max_move_speed, max_rotate_speed, last_requested_action
    last_requested_action = "backwards_correct"  # Inregistram actiunea
    
    if vline:  # Daca avem o linie detectata
        # Calculam pozitia medie a liniei
        average_x = (vline[0] + vline[2]) / 2
        x_dev_lim = 0.015  # Limita de deviere acceptabila

        # Setam vitezele de baza pentru miscare inapoi
        motor_left, motor_right = 150, 150
        
        # Corectia pentru deviere la stanga
        if average_x < -x_dev_lim:
            print("CORRECTING LEFT")  # Mesaj de debugging
            motor_right = 255  # Crestem viteza motorului drept
        # Corectia pentru deviere la dreapta
        elif x_dev_lim < average_x:
            print("CORRECTING RIGHT")  # Mesaj de debugging
            motor_left = 255   # Crestem viteza motorului stang
            
        # Aplicam setarile (mergem inapoi)
        set_motors(motor_left, motor_right, True, True)
    else:
        # Daca nu avem linie detectata, mergem inapoi cu viteza normala
        motor_left, motor_right = 150, 150
        set_motors(motor_left, motor_right, True, True)

def left():
    """Functie pentru rotirea robotului la stanga"""
    global last_requested_action
    last_requested_action = "left"  # Inregistram actiunea

    # Rotire la stanga: motorul stang inapoi, motorul drept inainte
    set_motors(max_rotate_speed, max_rotate_speed, 0, 1)

def right():
    """Functie pentru rotirea robotului la dreapta"""
    global last_requested_action
    last_requested_action = "left"  # aici e "right", dar am ajustat din frontend

    # Rotire la dreapta: motorul stang inainte, motorul drept inapoi
    set_motors(max_rotate_speed, max_rotate_speed, 1, 0)

def stop():
    """Functie pentru oprirea tuturor motoarelor robotului"""
    # Setam viteza 0 pentru ambele motoare, fara reversare
    set_motors(0, 0, 0, 0)