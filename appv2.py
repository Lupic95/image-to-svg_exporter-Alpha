import cv2
import json
import numpy as np
import tkinter as tk
from tkinter import messagebox, filedialog

aktuelles_bild = None
aktuelle_anzeige = None

buttons = [
    {'b': 0, 'g': 120, 'r': 0, 'label': 'open', 'x1': 10, 'x2': 80},
    {'b': 120, 'g': 80, 'r': 0, 'label': 'resetzoom', 'x1': 90, 'x2': 200},
    {'b': 140, 'g': 60, 'r': 0, 'label': 'canny', 'x1': 640, 'x2': 710},
    {'b': 80, 'g': 60, 'r': 190, 'label': 'export', 'x1': 720, 'x2': 790},
    {'b': 80, 'g': 60, 'r': 190, 'label': 'color picker', 'x1': 800, 'x2': 870},
    {'b': 80, 'g': 60, 'r': 190, 'label': 'addmasks', 'x1': 880, 'x2': 960},
    {'b': 68, 'g': 140, 'r': 120, 'label': 'exportmode', 'x1': 1720, 'x2': 1830},
    {'b': 0, 'g': 30, 'r': 200, 'label': 'close', 'x1': 1840, 'x2': 1910},
]

color_mode = cv2.IMREAD_COLOR_RGB
color_max_value = 255

opencv_breite, opencv_hoehe = 1920, 1080
taskleiste_breite, taskleiste_hoehe = 1920, 40
hintergrund_hoehe = opencv_hoehe - taskleiste_hoehe
taskleiste_farbe = (45, 45, 45)
fenster_name = 'openCV window to detect border and depth for svg'
fenster_modus = cv2.WINDOW_AUTOSIZE

beenden = False
greyscale = False
exportmode = False
zieht_gerade = False
exportRaster = [600, 220, 600]
groesse = 600
exportRaster_BGR = (255, 255, 255)

color_picker_aktiv = False
color = [int, int, int]
thresh = 0.000


canny_aktiv = False
canny_min = 50
canny_max = 150

masken = [{'H': color, 'S': color, 'V': color, thresh: 0.000}]

def nichts(x):
    pass


zoom_faktor = 1.0
offset_x, offset_y = 0, 0
letzte_maus_pos = (0, 0)

min_contur_length = 2

# Fenster mit fester Größe erstellen (nicht manuell skalierbar)
cv2.namedWindow(fenster_name, fenster_modus)

def wirklich_beenden():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    antwort = messagebox.askyesno(
        title='close program',
        message='Do you really want to close the program ?'
    )
    root.destroy()
    return antwort

def bild_auswaehlen_und_laden():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)  # True, damit der Dialog im Vordergrund öffnet

    datei_pfad = filedialog.askopenfilename(
        title='choose image',
        filetypes=[
            ("Bilddateien", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp")
        ]
    )
    root.destroy()
    if not datei_pfad:
        return None

    daten = np.fromfile(datei_pfad, dtype=np.uint8)
    geladenes_bild = cv2.imdecode(daten, cv2.IMREAD_COLOR)
    if geladenes_bild is None:
        print('Error, couldnt read file')
        return None

    # Originalbild unverändert zurückgeben, damit Proportionen erhalten bleiben!
    return geladenes_bild

import json

def als_json_speichern(json_pfade):
    if not json_pfade:
        messagebox.showwarning("Export", "Keine Konturen im Raster gefunden!")
        return

    # 1. Speicherort und Dateiname abfragen
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
        
    datei_pfad = filedialog.asksaveasfilename(
        title="3D-Koordinaten als JSON für Blender speichern",
        defaultextension=".json",
        filetypes=[("JSON Datei", "*.json")]
    )
    root.destroy()
    
    if not datei_pfad:
        return

    # 2. Direkt als saubere JSON-Datei speichern
    with open(datei_pfad, "w", encoding="utf-8") as datei:
        json.dump(json_pfade, datei)


def als_svg_speichern(svg_pfade):
    if not svg_pfade:
        messagebox.showwarning("Export", "Keine Konturen im Raster gefunden!")
        return

    # 1. Speicherort und Dateiname abfragen
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    datei_pfad = filedialog.asksaveasfilename(
        title="SVG für Blender speichern",
        defaultextension=".svg",
        filetypes=[("SVG Vektorgrafik", "*.svg")]
    )
    root.destroy()

    if not datei_pfad:
        return

    # 2. SVG-Header mit deiner 0-bis-1 viewBox aufbauen
    svg_ns = "http://" + "www." + "w3.org" + "/2000/svg"
    svg_zeilen = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="{svg_ns}" viewBox="0 0 1 1" width="1000" height="1000">',
        '  <g fill="none" stroke-width="0.002" stroke-linecap="round" stroke-linejoin="round">'
    ]

    # 3. Jeden Pfad in ein SVG <path>-Element umwandeln
    for index, pfad in enumerate(svg_pfade):
        # Durchschnittliche Tiefe dieses Pfades berechnen (0.0 bis 1.0)
        #durchgängige anzahl an punkte hier könnte man erhöhen ?
        #es ist nur für dem export nicht die bestimmung des betroffenen pixels
        if len(pfad) < 2:
            continue
        avg_tiefe = round(sum(z for x, y, z in pfad) / len(pfad), 5)
        rot_wert = int(avg_tiefe * 255)

        # Pfad-Koordinaten als "M x0,y0 L x1,y1 L x2,y2 ..." formatieren
        punkte_str = " ".join(
            [f"{'M' if i == 0 else 'L'} {x:.5f} {y:.5f}" for i, (x, y, z) in enumerate(pfad)]
        )
        
        # Alle einzelnen Tiefenwerte pro Punkt als Liste für Blender mitspeichern
        tiefen_liste = ",".join([f"{z:.5f}" for x, y, z in pfad])

        svg_zeilen.append(
            f'    <path id="contour_{index}" d="{punkte_str} Z" '
            f'stroke="rgb({rot_wert}, 80, 180)" '
            f'data-avg-depth="{avg_tiefe:.5f}" '
            f'data-point-depths="{tiefen_liste}" />'
        )

    svg_zeilen.append('  </g>')
    svg_zeilen.append('</svg>')

    # 4. Datei auf die Festplatte schreiben
    with open(datei_pfad, "w", encoding="utf-8") as datei:
        datei.write("\n".join(svg_zeilen))

    messagebox.showinfo("Erfolg", f"SVG mit {len(svg_pfade)} Pfaden gespeichert!")

def mask_mode():
    global masks
    global aktuelles_bild
    global color
    bild_kopie = aktuelles_bild.copy
    cv2.cvtColor(bild_kopie, cv2.COLOR_BGR2HSV_FULL)
    aktuelle_farbe = color
    #nächste farbe ?
    # ????
    #GUI

def maus_klick(event, x, y, flags, param):
    # WICHTIG: aktuelles_bild muss hier als global deklariert sein!
    global aktuelles_bild
    global opencv_breite, opencv_hoehe, taskleiste_hoehe
    global exportRaster
    global canny_aktiv, canny_min, canny_max 
    global exportmode
    global beenden, zoom_faktor, offset_x, offset_y, zieht_gerade, letzte_maus_pos

    if event == cv2.EVENT_LBUTTONDOWN:
        if y >= hintergrund_hoehe:
            if 10 <= x <= 80:
                neues_bild = bild_auswaehlen_und_laden()
                if neues_bild is not None:
                    aktuelles_bild = neues_bild
                    zoom_faktor = 1.0
                    offset_x, offset_y = 0, 0
            elif 90 <= x <= 200:
                zoom_faktor = 1.0
                offset_x, offset_y = 0, 0
            elif 640 <= x <= 710:
                toggle_canny()    
            elif 720 <= x <= 790:
                if exportmode:
                    svg_pfade, json_pfade = extrahiere_normalisierte_kanten(aktuelles_bild, exportRaster, opencv_breite, opencv_hoehe - taskleiste_hoehe, zoom_faktor, offset_x, offset_y, canny_min, canny_max)
                    als_svg_speichern(svg_pfade)
                    als_json_speichern(json_pfade)
            elif 800 <= x <= 870:
                color_picker()
            elif 1720 <= x <= 1830:
                if exportmode:
                    exportmode = not exportmode
                else:
                    exportmode = not exportmode
                    
            elif 1840 <= x <= 1910:
                if wirklich_beenden():
                    beenden = True

    # Korrigiert: EVENT_MOUSEWHEEL (ohne H)
    elif event == cv2.EVENT_MOUSEWHEEL and y < hintergrund_hoehe:
        if flags > 0:
            zoom_faktor = min(15.0, zoom_faktor * 1.15)
        else:
            zoom_faktor = max(0.2, zoom_faktor / 1.15)
            if abs(zoom_faktor - 1.0) < 0.08:
                zoom_faktor = 1.0
                offset_x, offset_y = 0, 0

    elif event == cv2.EVENT_RBUTTONDOWN and y < hintergrund_hoehe:
        zieht_gerade = True
        letzte_maus_pos = (x, y)
    elif event == cv2.EVENT_MOUSEMOVE and zieht_gerade:
        dx = x - letzte_maus_pos[0]
        dy = y - letzte_maus_pos[1]
        offset_x += dx
        offset_y += dy
        letzte_maus_pos = (x, y)
    elif event == cv2.EVENT_RBUTTONUP:
        zieht_gerade = False

def color_picker():
    global color
    global aktuelles_bild 

    bild_kopie = aktuelles_bild.copy()
    bild_kopie.reshape[:2]
     
    hsv = cv2.cvtColor(cv2.COLOR_BGR2HSV_FULL)
    # ???


def calculate_window_middle(opencv_hintergrund):
    global exportmode, exportRaster
    # Die tatsächliche Höhe und Breite der Zeichenfläche (ohne Taskleiste) auslesen
    flaeche_hoehe, flaeche_breite = opencv_hintergrund.shape[:2]
    dicke = 2
    # Exakte Mitte der Zeichenfläche berechnen
    start_x = (flaeche_breite - groesse) // 2
    start_y = (flaeche_hoehe - groesse) // 2

    # Position in exportRaster aktualisieren, damit später der Export weiß, wo das Raster lag!
    exportRaster[0] = start_x
    exportRaster[1] = start_y

    # Rechteck von (start_x, start_y) bis (start_x + groesse, start_y + groesse) zeichnen
    if exportmode:
        cv2.rectangle(
            opencv_hintergrund,   
            (start_x, start_y),
            (start_x + groesse, start_y + groesse),
            (exportRaster_BGR),
            dicke
        )
        rx, ry, rgroesse = exportRaster
        if rgroesse > 10:
            schritt = rgroesse / 4.0
        for i in range(1, 4):
            # Vertikale Linie
            lx = int(rx + i * schritt)
            cv2.line(opencv_hintergrund, (lx, ry), (lx, ry + rgroesse), (exportRaster_BGR), 1)
            # Horizontale Linie
            ly = int(ry + i * schritt)
            cv2.line(opencv_hintergrund, (rx, ly), (rx + rgroesse, ly), (exportRaster_BGR), 1)

    return opencv_hintergrund


def toggle_canny():
    global canny_aktiv
    canny_aktiv = not canny_aktiv
    
    if canny_aktiv:
        # Zwei Schieberegler für die Canny-Schwellenwerte einblenden
        cv2.createTrackbar("Canny Min", fenster_name, canny_min, 500, nichts)
        cv2.createTrackbar("Canny Max", fenster_name, canny_max, 500, nichts)
    else:
        # Fenster neu aufbauen, um die Regler wieder auszublenden
        cv2.destroyWindow(fenster_name)
        cv2.namedWindow(fenster_name, fenster_modus)
        cv2.setMouseCallback(fenster_name, maus_klick)


cv2.setMouseCallback(fenster_name, maus_klick)



def extrahiere_normalisierte_kanten(original_bild, raster, ziel_b, ziel_h, zoom, off_x, off_y, c_min, c_max):

    if original_bild is None:
        return []

    orig_h, orig_b = original_bild.shape[:2]
    rx, ry, r_groesse = raster

    # 1. Skalierung und Position wie in ansicht_berechnen ermitteln
    basis_skala = min(ziel_b / orig_b, ziel_h / orig_h)
    gesamt_skala = basis_skala * zoom

    neue_b = int(orig_b * gesamt_skala)
    neue_h = int(orig_h * gesamt_skala)
    pos_x = (ziel_b - neue_b) // 2 + off_x
    pos_y = (ziel_h - neue_h) // 2 + off_y

    # 2. Bildschirm-Raster auf echte Originalbild-Pixel zurückrechnen
    orig_x1 = max(0, int((rx - pos_x) / gesamt_skala))
    orig_y1 = max(0, int((ry - pos_y) / gesamt_skala))
    orig_x2 = min(orig_b, int((rx + r_groesse - pos_x) / gesamt_skala))
    orig_y2 = min(orig_h, int((ry + r_groesse - pos_y) / gesamt_skala))

    if orig_x2 <= orig_x1 or orig_y2 <= orig_y1:
        print("Raster liegt außerhalb des Bildes!")
        return []

    # Ausschnitt aus dem unveränderten Originalbild holen
    roi_bild = original_bild[orig_y1:orig_y2, orig_x1:orig_x2]
    roi_h, roi_b = roi_bild.shape[:2]

    # 3. Canny & Konturen direkt auf den Originaldaten berechnen
    #und den Vorgang wollte chatGPT wissen, ich verrate ihn aber nicht
    grau = cv2.cvtColor(roi_bild, cv2.COLOR_BGR2GRAY)
    weich = cv2.GaussianBlur(grau, (5, 5), 0)
    kanten = cv2.Canny(weich, c_min, c_max)
    konturen, _ = cv2.findContours(kanten, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    svg_pfade = []
    json_pfade = []
    # 4. Jeden Punkt auf 0.0 bis 1.0 normalisieren und R-Tiefe anhängen
   
    for kontur in konturen:
        # Zu winzige Rausch-Konturen (unter 5 Punkte) überspringen
        if len(kontur) < min_contur_length:
            continue
         # auf der x achse benachtebarte pixel als extrusionsdicke normalisieren
        pfad_punkte = []
        json_punkte = []
        for punkt in kontur:
            px, py = punkt[0]
            #hier ohne reshape von links nach rechts iterieren - 2D Bild schräge kontur
       
            #er nimmt den ursprungspunkt
            #und extrrahiert von dort aus eine BGR Matrix mit dem Verhältnis
            #des eingangsmaterials
            #HIER IST ES WERTVOLL er soll auf fünf nachkomma stellen runden
            #alle punkte in der kontur - normalisierung des ROT
            norm_x = round(px / roi_b, 5)
            norm_y = round(py / roi_h, 5)
            # er nimm sich das n
            tiefe_z = round(int(roi_bild[py, px, 2]) / 255.0, 5) # Rot-Kanal als Tiefe

            pfad_punkte.append((norm_x, norm_y, tiefe_z))
            json_punkte.append((norm_x, norm_y, tiefe_z))   
        svg_pfade.append(pfad_punkte)
        json_pfade.append(pfad_punkte)
    #print(svg_pfade)
    
    return svg_pfade, json_pfade
###dass ist der einstieg und wichtigste Weg -> Es bestimmt was das eigentliche ist was 
###es ist dass was man sieht, canny logik hier rein und ein Array auf machen ?
def ansicht_berechnen(bild, ziel_b, ziel_h, zoom, off_x, off_y, masken):
    canvas = np.zeros((ziel_h, ziel_b, 3), dtype=np.uint8)
    if bild is None:
        return canvas

    arbeits_bild = bild.copy()

    orig_h, orig_b = arbeits_bild.shape[:2]
    basis_skala = min(ziel_b / orig_b, ziel_h / orig_h)
    gesamt_skala = basis_skala * zoom

    neue_b = max(1, int(orig_b * gesamt_skala))
    neue_h = max(1, int(orig_h * gesamt_skala))

    if canny_aktiv:
        interp = cv2.INTER_NEAREST
    else:
        interp = cv2.INTER_AREA if gesamt_skala < 1.0 else cv2.INTER_LINEAR



    skaliert = cv2.resize(arbeits_bild, (neue_b, neue_h), interpolation=interp)

    pos_x = (ziel_b - neue_b) // 2 + off_x
    pos_y = (ziel_h - neue_h) // 2 + off_y

    dst_x1 = max(0, pos_x)
    dst_y1 = max(0, pos_y)
    dst_x2 = min(ziel_b, pos_x + neue_b)
    dst_y2 = min(ziel_h, pos_y + neue_h)

    src_x1 = max(0, -pos_x)
    src_y1 = max(0, -pos_y)
    src_x2 = src_x1 + (dst_x2 - dst_x1)
    src_y2 = src_y1 + (dst_y2 - dst_y1)

    if dst_x2 > dst_x1 and dst_y2 > dst_y1:
        canvas[dst_y1:dst_y2, dst_x1:dst_x2] = skaliert[src_y1:src_y2, src_x1:src_x2]

    for maske in masken:
        print(maske)
        #CODE ?
        

    
    return canvas

# Main Loop
while not beenden:
    anzeige_quelle = aktuelles_bild

    if aktuelles_bild is not None and canny_aktiv:
        # Aktuelle Reglerwerte auslesen
        canny_min = cv2.getTrackbarPos("Canny Min", fenster_name)
        canny_max = cv2.getTrackbarPos("Canny Max", fenster_name)
        # Graustufen -> leichtes Weichzeichnen (gegen Bildrauschen) -> Canny
        grau = cv2.cvtColor(aktuelles_bild, cv2.COLOR_BGR2GRAY)
        weich = cv2.GaussianBlur(grau, (5, 5), 0)
        kanten = cv2.Canny(weich, canny_min, canny_max)
        # Zurück auf 3 Kanäle wandeln, damit ansicht_berechnen & vstack funktionieren

        anzeige_quelle = cv2.cvtColor(kanten, cv2.COLOR_GRAY2BGR)




    opencv_hintergrund = ansicht_berechnen(
        anzeige_quelle, opencv_breite, hintergrund_hoehe, zoom_faktor, offset_x, offset_y, masken
    )

     #exportmodus für den quadratischen export zum abschätzen von Proportionen
    if aktuelles_bild is not None and exportmode:
        calculate_window_middle(opencv_hintergrund)

       


    taskleiste = np.full((taskleiste_hoehe, taskleiste_breite, 3), taskleiste_farbe, dtype=np.uint8)

    for button in buttons:
        farbe = (0, 180, 0) if (button['label'] == 'canny' and canny_aktiv) else (button['b'], button['g'], button['r'])
        farbe = (0, 225, 0) if (button['label'] == 'exportmode' and exportmode) else (button['b'], button['g'], button['r'])
        cv2.rectangle(
            taskleiste,
            (button['x1'], 5),
            (button['x2'], taskleiste_hoehe - 5),
            (button['b'], button['g'], button['r']),
            -1
        )
        cv2.putText(
            taskleiste,
            button['label'],
            (button['x1'] + 10, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1
        )

    # Text auf Y=26 gesetzt, damit er in der 40px hohen Taskleiste sichtbar ist
    zoom_text = f"Zoom: {int(zoom_faktor * 100)}% (Mausrad: Zoom | Rechtsklick: Verschieben)"
    cv2.putText(taskleiste, zoom_text, (220, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

    gesamt_fenster = np.vstack((opencv_hintergrund, taskleiste))
    cv2.imshow(fenster_name, gesamt_fenster)

    if cv2.waitKey(20) & 0xFF == 27:
        if wirklich_beenden():
            beenden = True
    if cv2.getWindowProperty(fenster_name, cv2.WND_PROP_VISIBLE) < 1:
        if wirklich_beenden():
            beenden = True

cv2.destroyAllWindows()
