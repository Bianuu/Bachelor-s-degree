// Definirea pinilor pentru senzorii ultrasonici
#define ULTRASONIC_FATA_ECHO 13      // Pinul pentru echo-ul senzorului ultrasonic din fata
#define ULTRASONIC_FATA_TRIG 12      // Pinul pentru trigger-ul senzorului ultrasonic din fata

#define ULTRASONIC_STANGA_ECHO 26    // Pinul pentru echo-ul senzorului ultrasonic din stanga
#define ULTRASONIC_STANGA_TRIG 27    // Pinul pentru trigger-ul senzorului ultrasonic din stanga

#define ULTRASONIC_DREAPTA_ECHO 28   // Pinul pentru echo-ul senzorului ultrasonic din dreapta
#define ULTRASONIC_DREAPTA_TRIG 21   // Pinul pentru trigger-ul senzorului ultrasonic din dreapta

// Definirea pinilor pentru motoarele de deplasare
#define MOTOR_DREAPTA_VITEZA 6       // Pinul PWM pentru controlul vitezei motorului drept
#define MOTOR_DREAPTA_A 8            // Pinul A pentru directia motorului drept
#define MOTOR_DREAPTA_B 9            // Pinul B pentru directia motorului drept

#define MOTOR_STANGA_VITEZA 7        // Pinul PWM pentru controlul vitezei motorului stang
#define MOTOR_STANGA_A 10            // Pinul A pentru directia motorului stang
#define MOTOR_STANGA_B 11            // Pinul B pentru directia motorului stang

// Definirea pinilor pentru senzorii si actionatorii auxiliari
#define IR_SCARI 4                   // Pinul pentru senzorul infrarosu de detectare scari
#define SENZOR_UMIDITATE 2          // Pinul pentru senzorul de umiditate
#define IR_ASPIRATOR 3              // Pinul pentru senzorul infrarosu al aspiratorului
#define ASPIRATOR_TOGGLE 18         // Pinul pentru controlul aspiratorului (on/off)
#define PERIE_TOGGLE 5              // Pinul pentru controlul periei (on/off)

// Clasa pentru gestionarea senzorilor ultrasonici
class Ultrasonic {
public:
    int echo, trig;  // Pinii pentru echo si trigger

    // Constructor implicit - initializeaza pinii cu 0
    Ultrasonic() {
        this->echo = 0;
        this->trig = 0;
    }

    // Functie pentru initializarea senzorului ultrasonic
    void begin(int echo, int trig) {
        this->echo = echo;
        pinMode(echo, INPUT);  // Seteaza pinul echo ca intrare

        this->trig = trig;
        pinMode(trig, OUTPUT); // Seteaza pinul trigger ca iesire
    }

    // Functie pentru masurarea distantei cu senzorul ultrasonic
    float measure() {
        long duration;  // Variabila pentru stocarea duratei pulsului

        // Genereaza pulsul de trigger pentru senzorul ultrasonic
        digitalWrite(this->trig, LOW);   // Asigura ca trigger-ul este LOW
        delayMicroseconds(2);            // Asteapta 2 microsecunde
        digitalWrite(this->trig, HIGH);  // Trimite pulsul HIGH
        delayMicroseconds(10);           // Mentine pulsul 10 microsecunde
        digitalWrite(this->trig, LOW);   // Opreste pulsul

        // Masoara durata pulsului de la echo (cu timeout de 100ms)
        duration = pulseIn(this->echo, HIGH, 100000);

        // Converteste durata in distanta (cm) folosind viteza sunetului
        // Formula: distanta = (durata * viteza_sunet) / 2
        // Viteza sunetului: 343 m/s = 0.0343 cm/microsecunda
        return ((float)duration) * 0.034f / 2.f;
    }
};

// Functie pentru maparea unei valori dintr-un interval in altul (versiunea float)
float fmap(float x, float in_min, float in_max, float out_min, float out_max) {
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

// Functie pentru limitarea unei valori intr-un interval specificat
float fclamp(float x, float min, float max) {
    if(x < min) return min;  // Daca valoarea e mai mica decat minimul, returneaza minimul
    if(x > max) return max;  // Daca valoarea e mai mare decat maximul, returneaza maximul
    return x;                // Altfel returneaza valoarea originala
}

// Clasa pentru gestionarea motoarelor cu encoder rotativ
class Motor {
public:
    int enable, a, b, rotary_a, rotary_b;  // Pinii pentru controlul motorului si encoder
    float targetValue = 0.0f;              // Valoarea tinta pentru viteza motorului (0-1)
    bool direction = false;                // Directia de rotatie (false=inainte, true=inapoi)
    long position = 0;                     // Pozitia curenta a motorului (din encoder)
    bool last_rotary_a, last_rotary_b;     // Ultimele stari ale encoder-ului pentru detectia schimbarii

    // Constructor implicit - initializeaza toate valorile
    Motor() {
        this->enable = 0;
        this->a = 0;
        this->b = 0;
        this->rotary_a = 0;
        this->rotary_b = 0;
        this->targetValue = 0.0f;
        this->direction = false;
        this->position = 0;
        this->last_rotary_a = false;
        this->last_rotary_b = false;
    }

    // Functie pentru initializarea motorului cu pinii specificati
    void begin(int enable, int a, int b, int rotary_a, int rotary_b) {
        // Configureaza pinul enable (PWM pentru viteza)
        this->enable = enable;
        pinMode(enable, OUTPUT);
        digitalWrite(this->enable, false);
        
        // Configureaza pinul A pentru directie
        this->a = a;
        pinMode(a, OUTPUT);
        digitalWrite(this->a, false);

        // Configureaza pinul B pentru directie
        this->b = b;
        pinMode(b, OUTPUT);
        digitalWrite(this->b, false);

        // Configureaza pinul A al encoder-ului
        this->rotary_a = rotary_a;
        pinMode(rotary_a, INPUT);
        this->last_rotary_a = digitalRead(this->rotary_a);

        // Configureaza pinul B al encoder-ului
        this->rotary_b = rotary_b;
        pinMode(rotary_b, INPUT);
        this->last_rotary_b = digitalRead(this->rotary_b);
    }

    // Functie principala care ruleaza motorul si citeste encoder-ul
    void run() {
        unsigned long currTime = millis();  // Timpul curent
        
        // Seteaza viteza motorului folosind PWM (0-255)
        analogWrite(this->enable, 255 * this->targetValue);
        
        // Seteaza directia motorului
        digitalWrite(this->a, this->direction);   // Un pin primeste directia
        digitalWrite(this->b, !this->direction);  // Celalalt pin primeste directia inversa

        // Citeste encoder-ul pentru a determina pozitia
        bool rot_a = digitalRead(this->rotary_a);
        if(this->last_rotary_a != rot_a) {  // Daca pinul A s-a schimbat
            bool rot_b = digitalRead(this->rotary_b);
            if(rot_b == rot_a) {
                this->position++;  // Incrementeaza pozitia (sens orar)
            } else {
                this->position--;  // Decrementeaza pozitia (sens antiorar)
            }
            this->last_rotary_a = rot_a;  // Actualizeaza ultima stare
        }
    }

    // Functie pentru setarea vitezei motorului (0.0 - 1.0)
    void setSpeed(float x) {
        this->targetValue = x;
    }

    // Functie pentru setarea directiei motorului
    void setDirection(bool x) {
        this->direction = x;
    }
};

// Declararea obiectelor pentru senzorii ultrasonici
Ultrasonic us_front;  // Senzorul ultrasonic din fata
Ultrasonic us_left;   // Senzorul ultrasonic din stanga
Ultrasonic us_right;  // Senzorul ultrasonic din dreapta

// Declararea obiectelor pentru motoare
Motor motor_left;   // Motorul stang
Motor motor_right;  // Motorul drept

// Variabile pentru gestionarea trimiterii mesajelor de update
unsigned long lastTimer_UpdateMessage = 0;   // Timpul ultimului mesaj trimis
#define UPDATE_MESSAGE_DELAY (1000 / 20)     // Delay-ul dintre mesaje (50ms = 20Hz)

// Functie pentru trimiterea mesajelor de status catre calculatorul principal
void SendUpdateMessage() {
    unsigned long currTime = millis();
    // Verifica daca a trecut suficient timp de la ultimul mesaj
    if(lastTimer_UpdateMessage + UPDATE_MESSAGE_DELAY > currTime)
        return;
    
    // Citeste distantele de la senzorii ultrasonici
    float front = us_front.measure();   // Distanta din fata
    float left = us_left.measure();     // Distanta din stanga
    float right = us_right.measure();   // Distanta din dreapta

    // Citeste senzorii digitali
    bool ir_scara = digitalRead(IR_SCARI);           // Senzorul pentru detectarea scarilor
    bool ir_aspirator = digitalRead(IR_ASPIRATOR);   // Senzorul infrarosu al aspiratorului
    bool senzor_umiditate = digitalRead(SENZOR_UMIDITATE);  // Senzorul de umiditate

    char byteBuffer[24];  // Buffer pentru datele care vor fi trimise (24 bytes)
    
    // ID-ul pachetului pentru identificare
    byteBuffer[0] = 0x54;

    // Converteste si copiaza distanta din fata (4 bytes - float)
    for(int i = 0; i < 4; i++)
        byteBuffer[i + 1] = ((char*)&front)[i];

    // Converteste si copiaza distanta din stanga (4 bytes - float)
    for(int i = 0; i < 4; i++)
        byteBuffer[i + 5] = ((char*)&left)[i];

    // Converteste si copiaza distanta din dreapta (4 bytes - float)
    for(int i = 0; i < 4; i++) 
        byteBuffer[i + 9] = ((char*)&right)[i];
    
    // Copiaza valorile senzorilor digitali (1 byte fiecare)
    byteBuffer[13] = (char)ir_scara;
    byteBuffer[14] = (char)ir_aspirator;
    byteBuffer[15] = (char)senzor_umiditate;

    // Converteste si copiaza pozitia motorului stang (4 bytes - long)
    for(int i = 0; i < 4; i++)
        byteBuffer[16 + i] = ((char*)&motor_left.position)[i];

    // Converteste si copiaza pozitia motorului drept (4 bytes - long)
    for(int i = 0; i < 4; i++)
        byteBuffer[20 + i] = ((char*)&motor_right.position)[i];

    // Trimite toate datele prin portul serial
    Serial.write(byteBuffer, 24);

    // Actualizeaza timpul ultimului mesaj trimis
    lastTimer_UpdateMessage = currTime;
}

// Functia de setup - se executa o singura data la pornirea Arduino-ului
void setup() {
    // Initializeaza comunicarea seriala la 9600 baud
    Serial.begin(9600);

    // Configureaza pinii pentru controlul aspiratorului si periei ca iesiri
    pinMode(ASPIRATOR_TOGGLE, OUTPUT);
    pinMode(PERIE_TOGGLE, OUTPUT);

    // Configureaza pinii pentru senzori ca intrari
    pinMode(IR_SCARI, INPUT);
    pinMode(IR_ASPIRATOR, INPUT);
    pinMode(SENZOR_UMIDITATE, INPUT);

    // Seteaza frecventa PWM la 100Hz pentru motoare
    analogWriteFreq(100);
    
    // Initializeaza senzorii ultrasonici cu pinii corespunzatori
    us_front.begin(ULTRASONIC_FATA_ECHO, ULTRASONIC_FATA_TRIG);
    us_left.begin(ULTRASONIC_STANGA_ECHO, ULTRASONIC_STANGA_TRIG);
    us_right.begin(ULTRASONIC_DREAPTA_ECHO, ULTRASONIC_DREAPTA_TRIG);

    // Initializeaza motoarele cu pinii corespunzatori
    // Atentie: pare sa fie o inversare in nume - motor_left foloseste pinii DREAPTA
    motor_left.begin(MOTOR_DREAPTA_VITEZA, MOTOR_DREAPTA_B, MOTOR_DREAPTA_A, 14, 22);
    motor_right.begin(MOTOR_STANGA_VITEZA, MOTOR_STANGA_A, MOTOR_STANGA_B, 17, 16);
}

// Functia loop - se executa continuu dupa setup
void loop() {
    // Verifica daca au sosit cel putin 6 bytes prin portul serial
    if(Serial.available() >= 6) {
        char incomingBytes[6];  // Buffer pentru datele primite
        
        // Citeste 6 bytes din portul serial
        for(int i = 0; i < 6; i++)
            incomingBytes[i] = (char)Serial.read();

        // Verifica daca primii 2 bytes sunt header-ul pentru comanda motoarelor
        if(incomingBytes[0] == 0xF0 && incomingBytes[1] == 0x0F) {
            // Extrage parametrii pentru motoare din mesaj
            float motor_a_speed = incomingBytes[2] / 255.f;    // Viteza motorului A (0-1)
            float motor_b_speed = incomingBytes[3] / 255.f;    // Viteza motorului B (0-1)
            bool motor_a_reverse = (bool)incomingBytes[4];     // Directia motorului A
            bool motor_b_reverse = (bool)incomingBytes[5];     // Directia motorului B

            // Actualizeaza directia motorului stang daca s-a schimbat
            if(motor_left.direction != motor_a_reverse)
                motor_left.setDirection(motor_a_reverse);

            // Actualizeaza viteza motorului stang daca s-a schimbat
            if(motor_left.targetValue != motor_a_speed)
                motor_left.setSpeed(motor_a_speed);

            // Actualizeaza directia motorului drept daca s-a schimbat
            if(motor_right.direction != motor_b_reverse)
                motor_right.setDirection(motor_b_reverse);
            
            // Actualizeaza viteza motorului drept daca s-a schimbat
            if(motor_right.targetValue != motor_b_speed)
                motor_right.setSpeed(motor_b_speed);
                
        // Verifica daca primii 2 bytes sunt header-ul pentru comanda aspirator/perie
        }else if(incomingBytes[0] == 0x7A && incomingBytes[1] == 0xF3) {
            // Controleaza aspiratorul si peria pe baza comenzilor primite
            digitalWrite(ASPIRATOR_TOGGLE, incomingBytes[2]);  // Porneste/opreste aspiratorul
            digitalWrite(PERIE_TOGGLE, incomingBytes[3]);      // Porneste/opreste peria
        }
    }

    // Trimite mesajul de update cu statusul robotului
    SendUpdateMessage();

    // Ruleaza motoarele (actualizeaza PWM si citeste encoder-ii)
    motor_left.run();
    motor_right.run();
}