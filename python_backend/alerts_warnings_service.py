# comunicarea MQTT
import mqtt_service  
# generarea de numere aleatorii
import random 
# serializarea si deserializarea datelor JSON      
import json      
# operatiuni cu timp   
import time
#stivei de apeluri        
import inspect      

# Clasa - reprezentarea notificarilor
class Notification():
    type: str
    id: int
    title: str
    description: str

    # Constructorul clasei - initializeaza o noua notificare
    def __init__(self, title, description, type="alert", id=0):
        self.title = title              
        self.description = description  
        # Tipul notificarii (implicit "alert")
        self.type = type              

        # nu este furnizat un ID, genereaza unul aleatoriu
        if id == 0:
            id = random.randint(1000000, 9999999)
        
        self.id = id 

# Var globala pentru evidenta ultimei alerte trimise
last_alert_time = 0

# Functieactualizarea hartii si trimiterea prin MQTT
def update_harta(harta, rx, ry):
    # Lista care contine caracterele afisarea hartii
    harta_flat = []
    
    # Parcurge o zona de 7x7 din harta incepand de la pozitia (14,10)
    for y in range(10, 10 + 7):        # randurile 10 la 16
        for x in range(14, 14 + 7):    # coloanele 14 la 20
            char_harta = ''
            
            # Verifica daca pozitia curenta este pozitia robotului
            if rx == x and ry == y:
                char_harta = 'R'  # Marcheaza pozitia robotului cu 'R'
            else:
                # Determina caracterul corespunzator valorii din harta
                match harta[y][x]:
                    case 0:
                        char_harta = "⠀"  # Spatiu gol/invizibil
                    case 1:
                        char_harta = "+"  
                    case 2:
                        char_harta = "#"   # obstacol
                    case 3:
                        char_harta = "↑"   
                    case 4:
                        char_harta = "→"   
                    case 5:
                        char_harta = "↓"   
                    case 6:
                        char_harta = "←"  
                    case _:
                        char_harta = "⠀"  # implicita pentru cazuri necunoscute
            
            # Add caracterul la lista 
            harta_flat.append(char_harta)

    # Afiseaza lista pentru debugging
    print(harta_flat)

    # Trimite harta actualizata prin MQTT ca mesaj JSON
    mqtt_service.client.publish("update_harta", json.dumps(harta_flat))

# Functie trimiterea alertelor
def send_alert(title, message, override_timer = False):
    # Folosesc var globala pentru timpul ultimei alerte
    global last_alert_time  
    
    # Verifica daca au trecut cel putin 2 secunde de la ultima alerta sau daca este fortat
    if last_alert_time + 2 < time.time() or override_timer:
        print("send_alert called.")  # Mesaj de debugging
        
        # Obtine informatii despre functia care a apelat aceasta functie
        caller = inspect.stack()[1]
        print(f"{caller.function} {caller.filename} {caller.lineno}")  # detalii apelant
        
        # Creeaza o noua notificare de tip alerta
        notif = Notification(title, message, "alert")
        
        # Trimite notificarea prin MQTT ca mesaj JSON
        mqtt_service.client.publish("send_alerts_warnings", json.dumps(notif.__dict__))
        
        # Actualizeaza timpul ultimei alerte
        last_alert_time = time.time()
    pass  

# Functie trimiterea avertismentelor
def send_warning(title, message, override_timer = False):
    # Folosesc var globala pentru timpul ultimei alerte
    global last_alert_time 
    
    # Verifica daca au trecut cel putin 2 secunde de la ultima alerta sau daca este fortat
    if last_alert_time + 2 < time.time() or override_timer:
        print("send_warning called.")  # Mesaj de debugging
        
        # Obtine informatii despre functia care a apelat aceasta functie
        caller = inspect.stack()[1]
        print(f"{caller.function} {caller.filename} {caller.lineno}")  # detalii apelant
        
        # Creeaza o noua notificare de tip avertisment
        notif = Notification(title, message, "warn")
        
        # Trimite notificarea prin MQTT ca mesaj JSON
        mqtt_service.client.publish("send_alerts_warnings", json.dumps(notif.__dict__))
        
        # Actualizeaza timpul ultimei alerte
        last_alert_time = time.time()
    pass  