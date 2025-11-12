import time
# Comunicarea cu Pico si Raspberry Pi
import pico_to_pi_service 
# Serviciu pentru controlul motorului
import motor_service  
# Modul partajat
import shared

def write_states(perie_status, aspirator_status):
    """
    Functie care scrie statusul periei si aspiratorului catre microcontroller
    
    Parametri:
    perie_status - statusul periei (True/False sau 1/0)
    aspirator_status - statusul aspiratorului (True/False sau 1/0)
    """
    # Cream un pachet de date pentru a trimite statusul componentelor
    # Pachetul are format: [0x7A, 0xF3, status_perie, status_aspirator, 0, 0]
    # 0x7A si 0xF3 sunt probabil header-uri/identificatori pentru tip de mesaj
    byte_buffer = bytearray([0x7A, 0xF3, perie_status, aspirator_status, 0, 0])
    
    # Trimitem pachetul catre microcontrollerul Pico prin conexiunea din shared
    shared.pico.write(byte_buffer)

# Incepem executia principala cu tratarea exceptiilor
try:
    # Bucla infinita - programul ruleaza continuu
    while True:
        # Oprim motorul
        motor_service.stop()
        
        # Setam statusul: peria oprita (False), aspiratorul pornit (True)
        write_states(False, True)
        
# Tratam exceptia KeyboardInterrupt (Ctrl+C) pentru oprirea programului
except KeyboardInterrupt:
    # Cand utilizatorul opreste programul cu Ctrl+C:
    
    # Oprim toate componentele: peria oprita (False), aspiratorul oprit (False)
    write_states(False, False)
    
    # Ne asiguram ca motorul este oprit
    motor_service.stop()
    
    # Afisam mesaj de confirmare ca programul se inchide
    print("Exiting...")