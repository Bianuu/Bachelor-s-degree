# OpenCV pentru 
import cv2
# operatii numerice si pe array-uri
import numpy as np
# modul partajat
import shared
# serviciul care controleaza motoarele
import motor_service
# clase pentru tipuri de enumeratii 
from enum import Enum, IntEnum
# serviciul de comunicare dintre placa Pico si Raspberry Pi
import pico_to_pi_service
import time
# serviciul de alerte si avertismente
import alerts_warnings_service

# Variabila globala pentru a marca terminarea executiei
am_terminat = False

# Enumerare pentru directiile cardinale
class DirectionEnum(IntEnum):
    NORTH = 0  # Nord
    EAST = 1   # Est
    SOUTH = 2  # Sud
    WEST = 3   # Vest
    

# Clasa pentru gestionarea directiei robotului
class Direction():
    direction: int

    def __init__(self, dir = None):
        # Initializeaza directia cu Nord daca nu e specicata
        if dir is None:
            dir = DirectionEnum.NORTH
        
        self.direction = dir

    # Roteste robotul la stanga
    def turn_left(self):
        return Direction((self.direction - 1) % 4)
    
    # Roteste robotul la dreapta
    def turn_right(self):
        return Direction((self.direction + 1) % 4)
    
    # Returneaza offsetul de coordonate pentru directia curenta
    def get_coord_offset(self):
        match self.direction:
            case DirectionEnum.NORTH:
                return 0, -1  # Sus
            case DirectionEnum.EAST:
                return 1, 0   # Dreapta
            case DirectionEnum.SOUTH:
                return 0, 1   # Jos
            case DirectionEnum.WEST:
                return -1, 0  # Stanga
            case _:
                return 0, 0   # Default
    
    # Aplica offsetul de coordonate la coordonatele date
    def apply_coord_offset(self, dx, dy):
        ox, oy = self.get_coord_offset()
        return ox + dx, oy + dy


# Enumerare pentru starile robotului
class States(Enum):
    MOVE_FORWARD = 0      # Miscare inainte
    DECIDE_ROTATION = 1   # Decizie de rotatie

    GO_FORWARD = 2        # Executie miscare inainte

    GO_LEFT = 3           # Executie rotatie stanga
    LEFT_LOSE_VLINE = 4   # Pierdere linie verticala la stanga
    LEFT_GET_VLINE = 5    # Gasire linie verticala la stanga
    LEFT_FINISH = 6       # Finalizare rotatie stanga

    GO_RIGHT = 7          # Executie rotatie dreapta
    RIGHT_LOSE_VLINE = 8  # Pierdere linie verticala la dreapta
    RIGHT_GET_VLINE = 9   # Gasire linie verticala la dreapta
    RIGHT_FINISH = 10     # Finalizare rotatie dreapta

    END = 11              # Stare finala


# Clasa pentru starea robotului
class RobotState():
    direction: Direction      # Directie curenta
    state: States            # Stare curenta
    rotation_choice: str     # Alegerea de rotatie
    goal_forward: float      # Obiectiv de miscare inainte
    x: int                   # Coordonata X
    y: int                   # Coordonata Y
    has_announced_end: bool  # Flag pentru anuntarea terminarii
    detection_map: list      # Harta de detectie
    tip_alerta: str         # Tipul alertei
    alerta_reason: str      # Motivul alertei
    direction_stack: list   # Stiva de directii

    def __init__(self):
        # Initializare stare robotului
        self.direction = Direction()
        self.state = States.MOVE_FORWARD
        self.rotation_choice = "forward"
        self.x = 15  # Pozitie initiala X
        self.y = 15  # Pozitie initiala Y
        self.goal_forward = 0
        self.has_announced_end = False
        self.wait_timer = 0
        self.tip_alerta = "warning"
        self.alerta_reason = "N/A"
        self.direction_stack = []

        # Initializare harta de detectie 32x32
        self.detection_map = []
        for y in range(0, 32):
            self.detection_map.insert(y, [])
            for x in range(0, 32):
                self.detection_map[y].insert(x, [])
                self.detection_map[y][x] = 0  # Nedetectat / Spatiu Gol

        # Marcheaza pozitia initiala pe harta
        self.detection_map[self.y][self.x] = 3   # Pozitia curenta
        dx, dy = self.direction.turn_left().apply_coord_offset(self.x, self.y)
        self.detection_map[dy][dx] = 2 # Pozitia stanga
        self.x, self.y = self.direction.apply_coord_offset(self.x, self.y) #Avansare

    # Afiseaza harta cu pozitia robotului
    def printMap(self):
        print("     N     ")
        print("    /\\     ")
        print("     |     ")
        print("W<------->E")
        print("     |     ")
        print("    \\/     ")
        print("     S     ")

        # Actualizeaza serviciul de alerte cu harta
        alerts_warnings_service.update_harta(self.detection_map, self.x, self.y)

        # Afiseaza harta caracter cu caracter
        for y in range(0, 32):
            for x in range(0, 32):
                if x == self.x and y == self.y:
                    print("R", end="")  # R = Robot
                else:
                    match self.detection_map[y][x]:
                        case 0:
                            print(" ", end="")  # Spatiu gol
                        case 1:
                            print("+", end="")  # Ceva detectat
                        case 2:
                            print("#", end="")  # Obstacol
                        case 3:
                            print("↑", end="")  # Directie Nord
                        case 4:
                            print("→", end="")  # Directie Est
                        case 5:
                            print("↓", end="")  # Directie Sud
                        case 6:
                            print("←", end="")  # Directie Vest
                        case _:
                            print(" ", end="")  # Default
            print("\n", end="")

    # Schimba starea robotului
    def changeState(self, new_state: States):
        print(f"[STATE CHANGE] {self.state} --> {new_state}")
        self.state = new_state
        self.wait_timer = time.time() + 0.75  # Timer de asteptare

    # Stare: Miscare inainte
    def MOVE_FORWARD(self, frame, hline, vline):
        # Verifica daca linia verticala s-a pierdut
        if not vline:
            self.changeState(States.END)
            self.tip_alerta = "alerta"
            self.alerta_reason = "Linia a fost pierduta."
            return
        
        # Verifica daca exista linie orizontala (intersectie)
        if hline:
            hline_y = (hline[1] + hline[3]) / 2 
            print(f"hline y is {hline_y}")
            # Daca linia orizontala e in zona de interes
            if 20 < hline_y and hline_y < 220:
                motor_service.stop()
                self.changeState(States.DECIDE_ROTATION)
                return        

        # Continua miscarea inainte cu corectie pe linia verticala
        motor_service.forwards_correct(vline)
        pass

    # Stare: Decizie de rotatie la intersectie
    def DECIDE_ROTATION(self, frame, hline, vline):
        # Afiseaza datele de la senzorii ultrasonici
        print(f"{pico_to_pi_service.us_left}, {pico_to_pi_service.us_front}, {pico_to_pi_service.us_right}")
        print("[MAP] ================================")
        self.printMap()
        print("[MAP] ================================")

        motor_service.stop()

        # Calculeaza coordonatele pentru directiile posibile
        fx, fy = self.direction.apply_coord_offset(self.x, self.y)  # Inainte
        lx, ly = self.direction.turn_left().apply_coord_offset(self.x, self.y)  # Stanga
        rx, ry = self.direction.turn_right().apply_coord_offset(self.x, self.y)  # Dreapta

        # Marcheaza obstacolele pe harta pe baza senzorilor ultrasonici
        if(pico_to_pi_service.us_front < 45):
            self.detection_map[fy][fx] = 2  # Obstacol in fata
        
        if(pico_to_pi_service.us_left < 25):
            self.detection_map[ly][lx] = 2  # Obstacol la stanga

        if(pico_to_pi_service.us_right < 25):
            self.detection_map[ry][rx] = 2  # Obstacol la dreapta

        # Verifica daca exista directii pe stiva (pentru intoarcere)
        if(len(self.direction_stack) > 0):
            curr_dir = self.direction.direction
            left_dir = self.direction.turn_left().direction
            right_dir = self.direction.turn_right().direction
            last_dir = self.direction_stack[-1] # Ultima directie salvata
            print(f"ULTIMA DIRECTIE DE PE STACK: {last_dir}")
            print(f"STANGA: {left_dir}")
            print(f"DREAPTA: {right_dir}")

            print(f"{last_dir == left_dir} {self.detection_map[ly][lx]}")
            print(f"{last_dir == right_dir} {self.detection_map[ry][rx]}")

            # Incearca sa se intoarca pe ultima directie din stiva
            if(last_dir == left_dir and self.detection_map[ly][lx] != 2):
                self.direction_stack.pop()  # Scoate directia din stiva
                motor_service.move_forward_steps(1350) # Se deplaseaza
                print("stanga")
                self.detection_map[self.y][self.x] = int(left_dir) + 3 # Marcheaza pe harta
                self.changeState(States.GO_LEFT)  # Schimba starea
                return
            elif(last_dir == right_dir and self.detection_map[ry][rx] != 2):
                self.direction_stack.pop()
                motor_service.move_forward_steps(1350)
                print("dreapta")
                self.detection_map[self.y][self.x] = int(right_dir) + 3
                self.changeState(States.GO_RIGHT)
                return
        
        # Caz general - alege directia pe baza hartii
        print("caz general")
        self.detection_map[self.y][self.x] = int(self.direction.direction) + 3

        # Adauga directia curenta pe stiva daca e obstacol in fata
        if(pico_to_pi_service.us_front < 45):
            print(f"ADAUGAT DIRECTIE PE STACK: {self.direction.direction}")
            self.direction_stack.append(self.direction.direction)

        # Alege directia: inainte > stanga > dreapta
        if(self.detection_map[fy][fx] == 0):
            motor_service.move_forward_steps(400)
            self.changeState(States.GO_FORWARD)
        elif(self.detection_map[ly][lx] == 0):
            motor_service.move_forward_steps(1350)
            self.changeState(States.GO_LEFT)
            print("stanga")
            self.detection_map[self.y][self.x] = int(self.direction.turn_left().direction) + 3
        elif(self.detection_map[ry][rx] == 0):
            motor_service.move_forward_steps(1350)
            self.changeState(States.GO_RIGHT)
            print("dreapta")
            self.detection_map[self.y][self.x] = int(self.direction.turn_right().direction) + 3
        else:
            # Nu mai sunt directii disponibile - termina
            self.changeState(States.END)
            self.tip_alerta = "warning"
            self.alerta_reason = "Traseul a fost terminat."
        pass

    # Stare: Executie miscare inainte
    def GO_FORWARD(self, frame, hline, vline):
        if motor_service.run_goal_steps():
            # Actualizeaza pozitia dupa miscarea inainte
            self.x, self.y = self.direction.apply_coord_offset(self.x, self.y)
            self.changeState(States.MOVE_FORWARD)
        pass

    # Stare: Inceput rotatie stanga
    def GO_LEFT(self, frame, hline, vline):
        if motor_service.run_goal_steps():
            motor_service.rotate_left_steps(700)
            self.changeState(States.LEFT_LOSE_VLINE)
        pass

    # Stare: Pierdere linie verticala la rotatie stanga
    def LEFT_LOSE_VLINE(self, frame, hline, vline):
        if not motor_service.run_goal_steps():
            return
        
        # Continua rotatia pana pierde linia verticala
        if vline:
            motor_service.rotate_left_steps(700)
            self.changeState(States.LEFT_LOSE_VLINE)
        else:
            motor_service.rotate_left_steps(700)
            self.changeState(States.LEFT_GET_VLINE)
        pass

    # Stare: Gasire linie verticala la rotatie stanga
    def LEFT_GET_VLINE(self, frame, hline, vline):
        if not motor_service.run_goal_steps():
            return

        # Continua rotatia pana gaseste din nou linia verticala
        if not vline:
            motor_service.rotate_left_steps(300)
            self.changeState(States.LEFT_GET_VLINE)
        else:
            # Calculeaza punctele de sus si jos ale liniei
            x_punct_sus = 0
            x_punct_jos = 0

            if(vline[1] > vline[3]):
                x_punct_sus = vline[0]
                x_punct_jos = vline[2]
            else:
                x_punct_sus = vline[2]
                x_punct_jos = vline[0]

            # Defineste zona de toleranta pentru alinierea liniei
            x_min = x_punct_jos - 64
            x_max = x_punct_jos + 64

            # Ajusteaza pozitia pentru a alinia linia vertical
            if x_punct_sus > x_max:
                motor_service.rotate_left_steps(100)
                self.changeState(States.LEFT_GET_VLINE)
            elif x_punct_sus < x_min:
                motor_service.rotate_right_steps(100)
                self.changeState(States.LEFT_GET_VLINE)
            else:
                # Linia e aliniata - da inapoi pentru pozitionare
                motor_service.move_backward_steps(400)
                self.changeState(States.LEFT_FINISH)
        pass

    # Stare: Finalizare rotatie stanga
    def LEFT_FINISH(self, frame, hline, vline):
        if not motor_service.run_goal_steps():
            return
        
        # Actualizeaza directia si pozitia dupa rotatie
        self.direction = self.direction.turn_left()
        self.x, self.y = self.direction.apply_coord_offset(self.x, self.y)
        self.changeState(States.MOVE_FORWARD)
        pass

    # Stare: Inceput rotatie dreapta
    def GO_RIGHT(self, frame, hline, vline):
        if motor_service.run_goal_steps():
            motor_service.rotate_right_steps(700)
            self.changeState(States.RIGHT_LOSE_VLINE)
        pass

    # Stare: Pierdere linie verticala la rotatie dreapta
    def RIGHT_LOSE_VLINE(self, frame, hline, vline):
        if not motor_service.run_goal_steps():
            return
        
        # Continua rotatia pana pierde linia verticala
        if vline:
            motor_service.rotate_right_steps(700)
            self.changeState(States.RIGHT_LOSE_VLINE)
        else:
            motor_service.rotate_right_steps(700)
            self.changeState(States.RIGHT_GET_VLINE)
        pass

    # Stare: Gasire linie verticala la rotatie dreapta
    def RIGHT_GET_VLINE(self, frame, hline, vline):
        if not motor_service.run_goal_steps():
            return

        # Continua rotatia pana gaseste din nou linia verticala
        if not vline:
            motor_service.rotate_right_steps(300)
            self.changeState(States.RIGHT_GET_VLINE)
        else:
            # Calculeaza punctele de sus si jos ale liniei
            x_punct_sus = 0
            x_punct_jos = 0

            if(vline[1] > vline[3]):
                x_punct_sus = vline[0]
                x_punct_jos = vline[2]
            else:
                x_punct_sus = vline[2]
                x_punct_jos = vline[0]

            # Defineste zona de toleranta pentru alinierea liniei
            x_min = x_punct_jos - 64
            x_max = x_punct_jos + 64

            # Ajusteaza pozitia pentru a alinia linia vertical
            if x_punct_sus > x_max:
                motor_service.rotate_left_steps(100)
                self.changeState(States.RIGHT_GET_VLINE)
            elif x_punct_sus < x_min:
                motor_service.rotate_right_steps(100)
                self.changeState(States.RIGHT_GET_VLINE)
            else:
                # Linia e aliniata - da inapoi pentru pozitionare
                motor_service.move_backward_steps(400)
                self.changeState(States.RIGHT_FINISH)
        pass

    # Stare: Finalizare rotatie dreapta
    def RIGHT_FINISH(self, frame, hline, vline):
        if not motor_service.run_goal_steps():
            return
        
        # Actualizeaza directia si pozitia dupa rotatie
        self.direction = self.direction.turn_right()
        self.x, self.y = self.direction.apply_coord_offset(self.x, self.y)
        self.changeState(States.MOVE_FORWARD)
        pass

    # Stare: Terminare executie
    def END(self, frame, hline, vline):
        if not self.has_announced_end:
            print("State machine has entered END state.")
            # Opreste toate sistemele robotului
            if self.tip_alerta == "alerta":
                alerts_warnings_service.send_alert("Traseu terminat.", self.alerta_reason, True)
            else:
                alerts_warnings_service.send_warning("Traseu terminat.", self.alerta_reason, True)
            self.has_announced_end = True
            motor_service.set_perie(False)      # Opreste peria
            motor_service.set_aspirator(False)  # Opreste aspiratorul
        pass

    # Functia principala care ruleaza masina de stari
    def run(self, frame, hline, vline):
        # Verifica timerul de asteptare
        if time.time() < self.wait_timer:
            return
        
        # Dictionar pentru maparea starilor la functii
        state_lookup = {
                States.MOVE_FORWARD: self.MOVE_FORWARD,
                States.DECIDE_ROTATION: self.DECIDE_ROTATION,
                States.GO_FORWARD: self.GO_FORWARD,
                States.GO_LEFT: self.GO_LEFT,
                States.LEFT_LOSE_VLINE: self.LEFT_LOSE_VLINE,
                States.LEFT_GET_VLINE: self.LEFT_GET_VLINE,
                States.LEFT_FINISH: self.LEFT_FINISH,
                States.GO_RIGHT: self.GO_RIGHT,
                States.RIGHT_LOSE_VLINE: self.RIGHT_LOSE_VLINE,
                States.RIGHT_GET_VLINE: self.RIGHT_GET_VLINE,
                States.RIGHT_FINISH: self.RIGHT_FINISH,
                States.END: self.END
        }

        # Executa functia corespunzatoare starii curente
        state_function = state_lookup[self.state]
        if not state_function:
            print("INVALID STATE DETECTED.")
            self.tip_alerta = "alerta"
            self.alerta_reason = "O eroare interna a fost detectata."
            self.changeState(States.END)
        else:
            state_function(frame, hline, vline)

# Instanta globala a starii robotului
state = RobotState()

# Constanta pentru cantitatea de rotatie
ROTATE_AMOUNT_STEPS = 1800

# Determina tipul unei linii pe baza coordonatelor
def get_line_type(x1, y1, x2, y2, thresh):
    dx = abs(x2 - x1)  # Diferenta pe axa X
    dy = abs(y2 - y1)  # Diferenta pe axa Y

    # Clasifica linia pe baza proportiei dx/dy
    if dy <= thresh * dx:
        return "horizontal"  # Linie orizontala
    elif dx <= thresh * dy:
        return "vertical"    # Linie verticala
    else:
        return "diagonal"    # Linie diagonala

# Calculeaza linia medie dintr-un set de linii
def get_average_line(lines, line_type=None):
    if len(lines) > 0:
        # Initializeaza suma coordonatelor
        average_line = [0, 0, 0, 0]
        
        # Sumeaza toate coordonatele liniilor
        for line in lines:
            average_line[0] = average_line[0] + line[0][0]
            average_line[1] = average_line[1] + line[0][1]
            average_line[2] = average_line[2] + line[0][2]
            average_line[3] = average_line[3] + line[0][3]
    
        # Calculeaza media
        for i in range(4):
            average_line[i] = int(average_line[i] / len(lines))

        # Cod pentru normalizarea liniilor
        """
        if line_type == "vertical":
            # Calculate average x coordinate
            avg_x = (average_line[0] + average_line[2]) // 2
            
            # Determine if line direction should be top-to-bottom or bottom-to-top
            if average_line[1] <= average_line[3]:
                return True, [avg_x, 0, avg_x, 639]
            else:
                return True, [avg_x, 639, avg_x, 0]
        elif line_type == "horizontal":
            avg_y = (average_line[1] + average_line[3]) // 2
            if average_line[0] <= average_line[2]:
                return True, [0, avg_y, 639, avg_y]
            else:
                return True, [639, avg_y, 0, avg_y]
        """

        return True, average_line

    # Nu s-au gasit linii
    return False, [0,0,0,0]

# Detecteaza liniile in imaginea binara
def run_detect(frame, frame_binary):
    # Detectia liniilor cu transformata Hough
    lines = cv2.HoughLinesP(frame_binary, rho=1, theta=np.pi/180, threshold=60, minLineLength=150)
    
    # Daca nu s-au gasit linii, opreste motoarele
    if lines is None:
        motor_service.stop()
        return False, None, False, None
    
    # Separarea liniilor pe tipuri
    hlines = []  # Linii orizontale
    vlines = []  # Linii verticale
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        line_type = get_line_type(x1, y1, x2, y2, 0.7)
        if line_type == "horizontal":
            hlines.append(line)
        elif line_type == "vertical":
            vlines.append(line)
    
    # Calculeaza liniile medii pentru fiecare tip
    hret, hline = get_average_line(hlines, "horizontal")
    vret, vline = get_average_line(vlines, "vertical")

    # Seteaza la None daca nu s-au gasit linii
    if not hret:
        hline = None
    
    if not vret:
        vline = None

    return hret, hline, vret, vline

# Functia principala de executie
def run(frame, frame_binary):
    # Primeste datele de la microcontroler
    pico_to_pi_service.receive()

    # Detecteaza liniile in imagine
    hret, hline, vret, vline = run_detect(frame, frame_binary)
    
    # Deseneaza linia orizontala detectata
    if hret:
        cv2.line(frame, (hline[0], hline[1]),  (hline[2], hline[3]), (255, 0, 255), 5) 
    
    # Deseneaza linia verticala detectata
    if vret:
        cv2.line(frame, (vline[0], vline[1]),  (vline[2], vline[3]), (255, 255, 0), 5) 

    # Ruleaza masina de stari cu liniile detectate
    state.run(frame, hline, vline)

    return frame_binary