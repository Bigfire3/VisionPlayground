# GoPro Live View with OpenCV (Windows)

Kurzanleitung, um die GoPro als Webcam mit Python/OpenCV anzuzeigen.

Voraussetzungen
- GoPro im Webcam-USB-Modus angeschlossen und eingeschaltet.
- Python 3.8+ installiert.

Installation

```powershell
python -m pip install -r requirements.txt
```

Ausführen

```powershell
python scripts/view_gopro.py
```

Hinweise
- Falls mehrere Kameras angeschlossen sind, sucht das Script automatisch nach einem verfügbaren Kamera-Index.
- Wenn kein Bild erscheint: Windows-Geräte-Manager prüfen, ob die GoPro als Kamera erkannt wird.
- Beenden mit `q` oder ESC.

MediaPipe Hand-Tracking

Es gibt zwei Optionen:

- Klassische API (ältere 0.8.x Releases): kann direkt `mp.solutions.hands` verwenden.
- Neue Tasks-API (0.10+): verwendet ein `.task` Modell (empfohlen für aktuelle Versionen).

Tasks-API (empfohlen)

1. Lade das `hand_landmarker.task` Modell herunter. Du kannst das Script zum Herunterladen verwenden (setze `HAND_LANDMARKER_MODEL_URL` Umgebungsvariable auf die Modell-URL):

```powershell
python scripts/download_hand_model.py
```

Alternativ lege das Modell manuell unter `models/hand_landmarker.task` ab.

2. Starte das Tasks-Beispiel:

```powershell
python scripts/view_gopro_mediapipe_tasks.py
```

Das Script nutzt das Tasks-API, benötigt das .task-Modell und zeichnet einfache Landmarken/Verbindungen. Beende mit `q` oder ESC.

---

## Finger Cursor Control (Maus per Hand steuern)

Verwandelt die Kamera in ein virtuelles, schwebendes Trackpad! Du kannst deinen Windows-Mauszeiger durch Handbewegungen steuern.

```powershell
python scripts/finger_cursor_control.py
```

**Features:**
- **Relatives Tracking (Trackpad-Modus)**: Funktioniert überall im Bild, ohne starre "Region of Interest". Die Maus bewegt sich extrem flüssig basierend auf der Bewegung deiner Hand.
- **Klicken & Drag-and-Drop**: Zeigefinger und Daumen zusammenführen (Pinch). Ein intelligenter Doppelklick-Stabilisator sorgt für fehlerfreies Klicken in Windows.
- **Maus anheben / Pausieren**: Schließe deine Hand zu einer festen Faust (alle Finger eng eingekrümmt). Das Tracking pausiert, und du kannst die Hand neu positionieren (wie wenn du eine physische Maus anhebst).
- **Glättung (Smoothing)**: Die Empfindlichkeit kann live mit den Tasten `+` und `-` angepasst werden.

**Steuerung im Fenster:**
- `h`: Wechsel zwischen linker und rechter Hand
- `r`: Trackpad-Position (Relativer Nullpunkt) zurücksetzen
- `+` / `-`: Smoothing erhöhen/verringern
- `q` / `ESC`: Beenden
