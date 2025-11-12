# Client MQTT pentru comunicare wireless
import paho.mqtt.client as mqtt 
# Serviciu pentru controlul motoarelor
import motor_service 
import time 
# Comunicare intre Pico si Raspberry Pi
import pico_to_pi_service  
# Servicii pentru diferite moduri de functionare
import mode_aspirator_autonom  
import mode_manual 
import mode_smart_perie_autonom  

# Var globala care stocheaza modul curent de functionare
mode = "manual"

# Functie care se executa cand clientul MQTT se conecteaza cu succes
def mqtt_on_connect(client, userdata, flags, rc):
    # Verifica daca conexiunea a fost realizata cu succes (cod 0)
    if rc == 0:
        # Se aboneaza la toate topicurile MQTT necesare pentru control
        client.subscribe("forward")  # Abonare la comenzi pentru miscarea inainte
        client.subscribe("left")  # Abonare la comenzi pentru rotirea la stanga
        client.subscribe("right")  # Abonare la comenzi pentru rotirea la dreapta
        client.subscribe("down")  # Abonare la comenzi pentru miscarea inapoi
        client.subscribe("mode")  # Abonare la schimbarea modului de functionare
        client.subscribe("aspirator_manual")  # Abonare la controlul manual al aspiratorului
        client.subscribe("perie_manual")  # Abonare la controlul manual al periei
    else:
        # Afiseaza mesaj de eroare si inchide aplicatia daca conexiunea a esuat
        print("failed to connect.")
        os.exit()

# Functie care se executa cand se primeste un mesaj MQTT
def mqtt_on_message(client, userdata, msg):     
    # Afiseaza informatii despre mesajul primit (timestamp, continut, topic, QoS)
    print(f"{time.time()} Received message: {msg.payload.decode()} on topic {msg.topic} with QoS {msg.qos}")
    
    # Declara ca folosim variabila globala mode
    global mode

    # Verifica daca mesajul este pentru controlul manual al aspiratorului
    if msg.topic == "aspirator_manual":
        # Seteaza starea aspiratorului manual pe baza mesajului primit
        mode_manual.aspirator_mode = bool(msg.payload.decode() == "true")
    
    # Verifica daca mesajul este pentru controlul manual al periei
    if msg.topic == "perie_manual":
        # Seteaza starea periei manuale pe baza mesajului primit
        mode_manual.perie_mode = bool(msg.payload.decode() == "true")

    # Verifica daca mesajul este pentru schimbarea modului de functionare
    if msg.topic == "mode":
        # Afiseaza modul selectat
        print(f"Mod select: {msg.payload.decode()}")
        # Opreste toate motoarele inainte de schimbarea modului
        motor_service.stop()
        # Actualizeaza modul curent cu cel primit
        mode = msg.payload.decode()
        
        # Reseteaza starile aspiratorului si periei
        motor_service.perie_status = False
        motor_service.aspirator_status = False

        # Configureaza robotul pe baza modului selectat
        if mode == "aspirare":
            # Mod autonom de aspirare - activeaza doar aspiratorul
            motor_service.aspirator_status = True
            # Reseteaza timer-ul pentru alertele din modul aspirator autonom
            mode_aspirator_autonom.last_alert = 0
        elif mode == "perie":
            # Mod autonom cu perie - activeaza si aspiratorul si peria
            motor_service.aspirator_status = True
            motor_service.perie_status = True
            # Initializeaza starea robotului pentru modul perie inteligenta
            mode_smart_perie_autonom.state = mode_smart_perie_autonom.RobotState()
        elif mode == "manual":
            # Mod manual - opreste toate motoarele si scrie starile
            motor_service.stop()
            motor_service.write_states()

        # Scrie starile curente ale motoarelor
        motor_service.write_states()
        
        # Iese din functie pentru a nu procesa alte comenzi
        return
    
    # Procesarea comenzilor doar daca robotul este in modul manual
    if mode == "manual":
        # Gestionarea comenzii pentru miscarea inainte
        if msg.topic == "forward":
            # Verifica daca senzorul IR detecteaza scari
            if pico_to_pi_service.ir_scari:
                # Opreste robotul daca detecteaza scari (masura de siguranta)
                motor_service.stop()
            else:
                # Misca robotul inainte daca nu sunt detectate scari
                motor_service.forwards()
        # Gestionarea comenzii pentru rotirea la stanga
        elif msg.topic == "left":
            motor_service.left()
        # Gestionarea comenzii pentru rotirea la dreapta
        elif msg.topic == "right":
            motor_service.right()
        # Gestionarea comenzii pentru miscarea inapoi
        elif msg.topic == "down":
            motor_service.backwards()

        # Opreste motoarele cand butonul este eliberat
        if msg.payload.decode() == "released":
            motor_service.stop()

# Crearea clientului MQTT
client = mqtt.Client()
# Asocierea functiilor de callback pentru conectare si primirea mesajelor
client.on_connect = mqtt_on_connect
client.on_message = mqtt_on_message
# Conectarea la brokerul MQTT local pe portul standard 1883
client.connect("localhost", 1883)
# Pornirea loop-ului MQTT in background pentru a procesa mesajele
client.loop_start()