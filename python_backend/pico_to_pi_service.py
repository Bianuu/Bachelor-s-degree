# Importam modulul pico din shared pentru comunicatia cu microcontrollerul
from shared import pico
# Importam struct pentru decodarea datelor binare
import struct
import time

# us_front = senzorul ultrasonic din fata
# us_left = senzorul ultrasonic din stanga  
# us_right = senzorul ultrasonic din dreapta
us_front, us_left, us_right = 0, 0, 0

# ir_scari = senzorul infrarosu pentru detectarea scarilor
# ir_aspirator = senzorul infrarosu pentru aspirator
# senzor_umid = senzorul de umiditate
ir_scari, ir_aspirator, senzor_umid = False, False, False

# motor_a_pos = pozitia motorului A
# motor_b_pos = pozitia motorului B
motor_a_pos, motor_b_pos = 0, 0

# Var pentru a memora timpul ultimei primiri de date
last_recv_run = 0

# Functia principala pentru primirea datelor de la microcontroller
def receive(log_shit=False):
    # Declaram ca folosim variabilele globale
    global last_recv_run
    
    # Obtinem timpul curent
    curr_time = time.time()
    
    # Daca este activat logging-ul, verificam daca a trecut prea mult timp
    if log_shit:
        # Daca au trecut mai mult de 10ms de la ultima primire, afisam avertisment
        if(curr_time - last_recv_run > 0.01):
            print(f"[WARNING] Last pico_to_pi_service recv took {int((curr_time - last_recv_run) * 1000)}")
    
    # Actualizam timpul ultimei primiri
    last_recv_run = curr_time
    
    # Declaram ca folosim toate variabilele globale pentru senzori si motoare
    global us_front, us_left, us_right, ir_scari, ir_aspirator, senzor_umid, motor_a_pos, motor_b_pos
    
    # Verificam daca avem cel putin 24 de bytes disponibili pentru citire
    # (1 byte header + 23 bytes date)
    if pico.in_waiting >= 24:
        # Citim header-ul pachetului (1 byte)
        packet_header = pico.read(1)
        
        # Verificam daca header-ul este 0x54 (pachet valid)
        if packet_header[0] == 0x54:
            # Citim restul datelor (23 bytes)
            byte_buffer = pico.read(23)
            
            # Decodificam senzorii ultrasonici (float, little-endian)
            # Bytes 0-3: senzorul din fata
            us_front = struct.unpack("<f", byte_buffer[0:4])[0]
            # Bytes 4-7: senzorul din stanga
            us_left = struct.unpack("<f", byte_buffer[4:8])[0]
            # Bytes 8-11: senzorul din dreapta
            us_right = struct.unpack("<f", byte_buffer[8:12])[0]
            
            # Decodificam senzorii digitali (boolean)
            # Byte 12: senzorul infrarosu pentru scari
            ir_scari = struct.unpack("<?", byte_buffer[12:13])[0]
            # Byte 13: senzorul infrarosu pentru aspirator
            ir_aspirator = struct.unpack("<?", byte_buffer[13:14])[0]
            # Byte 14: senzorul de umiditate
            senzor_umid = struct.unpack("<?", byte_buffer[14:15])[0]
            
            # Decodificam pozitiile motoarelor (long integer, little-endian)
            # Bytes 15-18: pozitia motorului A (inmultim cu -1 pentru inversarea directiei)
            motor_a_pos = struct.unpack("<l", byte_buffer[15:19])[0] * -1
            # Bytes 19-22: pozitia motorului B (inmultim cu -1 pentru inversarea directiei)
            motor_b_pos = struct.unpack("<l", byte_buffer[19:23])[0] * -1
        else:
            # Daca header-ul nu este recunoscut, afisam eroare
            print(f"unknown packet id {hex(packet_header[0])}")
        
        # Golim buffer-ul pentru a evita acumularea de date vechi
        pico.flush()