import cv2
import numpy as np

# Globale Variablen (sauber initialisiert)
color = {'h': 0, 's': 255, 'v': 255}
aktuelles_bild = None  # Wird in der Schleife mit dem aktuellen Frame befüllt

def nothing(x):
    pass

# Maus-Callback: Greift beim Linksklick den HSV-Wert ab
def pick_color(event, x, y, flags, param):
    global color, aktuelles_bild
    
    if event == cv2.EVENT_LBUTTONDOWN and aktuelles_bild is not None:
        # 1. BGR-Pixel an Mausposition (y = Zeile, x = Spalte!) auslesen
        bgr_pixel = aktuelles_bild[y, x]
        
        # 2. Einzelnen Pixel in HSV umwandeln
        hsv_pixel = cv2.cvtColor(np.uint8([[bgr_pixel]]), cv2.COLOR_BGR2HSV)[0][0]
        
        # 3. Global speichern
        color['h'] = int(hsv_pixel[0])
        color['s'] = int(hsv_pixel[1])
        color['v'] = int(hsv_pixel[2])
        
        # 4. Trackbars automatisch auf den gepickten Wert schieben
        cv2.setTrackbarPos("H", "HSV Picker", color['h'])
        cv2.setTrackbarPos("S", "HSV Picker", color['s'])
        cv2.setTrackbarPos("V", "HSV Picker", color['v'])
        print(f"Gepickt: {color}")

# Fenster & Trackbars erstellen
cv2.namedWindow("Hauptbild")
cv2.setMouseCallback("Hauptbild", pick_color) # Pipette an Hauptbild binden

cv2.namedWindow("HSV Picker")
cv2.createTrackbar("H", "HSV Picker", 0, 179, nothing)
cv2.createTrackbar("S", "HSV Picker", 255, 255, nothing)
cv2.createTrackbar("V", "HSV Picker", 255, 255, nothing)
cv2.createTrackbar("Toleranz", "HSV Picker", 15, 50, nothing) # Für deine Maske

# Beispiel-Webcam (oder lade hier dein Bild)
cap = cv2.VideoCapture(0)
vorschau = np.zeros((150, 300, 3), np.uint8)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Global verfügbar machen, damit die Mausfunktion darauf zugreifen kann
    aktuelles_bild = frame.copy()

    # Trackbars auslesen (falls du nach dem Klick manuell feinjustieren willst)
    color['h'] = cv2.getTrackbarPos("H", "HSV Picker")
    color['s'] = cv2.getTrackbarPos("S", "HSV Picker")
    color['v'] = cv2.getTrackbarPos("V", "HSV Picker")
    tol = cv2.getTrackbarPos("Toleranz", "HSV Picker")

    # --- 1. Farb-Visualisierung neben/unter den Trackbars ---
    vorschau[:] = [color['h'], color['s'], color['v']]
    vorschau_bgr = cv2.cvtColor(vorschau, cv2.COLOR_HSV2BGR)
    # Text mit aktuellen Werten ins Vorschaufenster schreiben
    cv2.putText(vorschau_bgr, f"H:{color['h']} S:{color['s']} V:{color['v']}", 
                (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imshow("HSV Picker", vorschau_bgr)

    # --- 2. Masken-Funktion mit Toleranz ---
    hsv_frame = cv2.cvtColor(aktuelles_bild, cv2.COLOR_BGR2HSV)
    
    # Untere und obere Grenzen berechnen (mit Begrenzung auf gültige HSV-Bereiche)
    lower = np.array([max(0, color['h'] - tol), max(0, color['s'] - 50), max(0, color['v'] - 50)])
    upper = np.array([min(179, color['h'] + tol), min(255, color['s'] + 50), min(255, color['v'] + 50)])
    
    maske = cv2.inRange(hsv_frame, lower, upper)

    # Fenster anzeigen
    cv2.imshow("Hauptbild", aktuelles_bild)
    cv2.imshow("Maske", maske)

    if cv2.waitKey(1) & 0xFF == 27: # ESC zum Beenden
        break

cap.release()
cv2.destroyAllWindows()
