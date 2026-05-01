#!/usr/bin/env python3
"""
Finger-Cursor-Steuerung: Bewege deinen Desktop-Cursor wie mit einem Touchpad.

Nutzt MediaPipe Hand-Landmarks. Die Bewegung wird relativ (Touchpad-Style)
über das Grundgelenk des Zeigefingers gesteuert. Pinch (Daumen + Zeigefingerspitze)
löst einen Mausklick aus. Eine komplette Faust pausiert das Tracking ("Maus anheben").

Steuerung:
  q / ESC  – Beenden
  +/-      – Smoothing-Faktor anpassen
  r        – Trackpad-Position (Relativer Nullpunkt) zurücksetzen
  h        – Linke oder rechte Hand auswählen

Benötigt: opencv-python, mediapipe (>=0.10)
Kein externes Paket für Maussteuerung nötig (nutzt Win32 API via ctypes).
"""

import time
import math
import ctypes
import ctypes.wintypes
from pathlib import Path

import cv2
import numpy as np

from mediapipe.tasks.python.vision import hand_landmarker
from mediapipe.tasks.python.vision.core import image as mp_image
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import RunningMode

# ────────────────────────── Konfiguration ──────────────────────────

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"

# Pinch-Klick (Hysterese): Enger Schwellwert zum Klicken, weiterer zum Loslassen.
# Verhindert, dass der Klick beim Bewegen versehentlich abbricht.
PINCH_START = 0.04
PINCH_STOP = 0.05

# Faust-Erkennung (Tracking pausieren / Maus anheben)
# Größerer Wert = Faust wird früher/leichter erkannt.
# Kleinerer Wert = Finger müssen enger eingekrümmt werden.
FIST_THRESHOLD = 0.08

# Kamera-Einstellungen
CAM_WIDTH = 1280
CAM_HEIGHT = 720

# ────────────────────────── Win32 API ──────────────────────────

user32 = ctypes.windll.user32

# Screen dimensions
SM_CXSCREEN = 0
SM_CYSCREEN = 1
SCREEN_W = user32.GetSystemMetrics(SM_CXSCREEN)
SCREEN_H = user32.GetSystemMetrics(SM_CYSCREEN)

# Mouse event flags
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_cursor_pos() -> tuple[int, int]:
    """Holt die aktuelle absolute Bildschirmposition des Cursors."""
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_cursor_pos(x: int, y: int):
    """Setzt den Cursor auf absolute Bildschirmkoordinaten."""
    user32.SetCursorPos(x, y)


def mouse_down():
    """Hält die linke Maustaste gedrückt."""
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)


def mouse_up():
    """Lässt die linke Maustaste los."""
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


import sys
from cam_utils import find_working_camera

# Landmark_distance function remains...
def landmark_distance(lmk_a, lmk_b) -> float:
    """Euklidischer Abstand zwischen zwei normalisierten Landmarks."""
    return math.sqrt(
        (lmk_a.x - lmk_b.x) ** 2
        + (lmk_a.y - lmk_b.y) ** 2
        + (lmk_a.z - lmk_b.z) ** 2
    )


def draw_debug_overlay(frame, landmarks_list, smooth_pos, pinch_active):
    """Zeichnet Debug-Informationen aufs Kamerabild."""
    h, w, _ = frame.shape

    for hand in landmarks_list:
        pts = [(int(lmk.x * w), int(lmk.y * h)) for lmk in hand]

        # Alle Landmarks zeichnen
        for i, (px, py) in enumerate(pts):
            color = (0, 255, 0)
            radius = 3
            if i == 8:  # INDEX_FINGER_TIP
                color = (0, 0, 255)
                radius = 8
            elif i == 4:  # THUMB_TIP
                color = (255, 0, 0)
                radius = 6
            cv2.circle(frame, (px, py), radius, color, -1)

        # Verbindungslinien
        try:
            conns = hand_landmarker.HandLandmarksConnections.HAND_CONNECTIONS
            for c in conns:
                a = pts[c.start]
                b = pts[c.end]
                cv2.line(frame, a, b, (0, 200, 0), 1)
        except Exception:
            pass

    # Cursor-Position anzeigen
    if smooth_pos is not None:
        sx, sy = smooth_pos
        info = f"Cursor: ({sx}, {sy}) / Screen: {SCREEN_W}x{SCREEN_H}"
        cv2.putText(frame, info, (10, h - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Pinch-Status
    if pinch_active:
        cv2.putText(frame, "CLICK!", (w // 2 - 50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)


# ────────────────────────── Hauptschleife ──────────────────────────

def main():
    # CLI Argument für Kamera-Index unterstützen
    pref_idx = None
    if len(sys.argv) > 1:
        try:
            pref_idx = int(sys.argv[1])
        except ValueError:
            pass

    if not MODEL_PATH.exists():
        print(f"Modell nicht gefunden: {MODEL_PATH}")
        print("Lade das HandLandmarker .task Modell herunter und lege es in 'models/hand_landmarker.task'.")
        return

    print("Suche nach funktionierender Kamera...")
    cap, idx = find_working_camera(preferred_index=pref_idx)
    if cap is None:
        print("Kamera nicht gefunden oder liefert kein Bild. Prüfe Verbindung und Webcam-Modus der GoPro.")
        return

    print(f"Kamera gefunden (Index {idx})")
    print(f"Bildschirm: {SCREEN_W} x {SCREEN_H}")
    print("Modus: Relatives Trackpad (Maus-ähnlich)")
    print(f"Pinch (Start/Stop): {PINCH_START:.3f} / {PINCH_STOP:.3f}")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    
    # Kurz warten nach dem Setzen der Auflösung
    time.sleep(0.5)

    options = hand_landmarker.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = hand_landmarker.HandLandmarker.create_from_options(options)

    # Trackpad-Zustand (Relatives Tracking)
    prev_px: float | None = None
    prev_py: float | None = None
    cursor_x_float: float | None = None
    cursor_y_float: float | None = None
    
    # Generelles Smoothing
    smoothing = 0.90
    
    # Hand-Auswahl: None = erste gefundene, "Left" oder "Right"
    target_handedness = "Right" 

    # Zustand für Drag & Drop (Maus gedrückt halten)
    is_mouse_down = False
    last_click_time = 0.0

    prev_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Kein Frame erhalten.")
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp_image.Image(mp_image.ImageFormat.SRGB, rgb)
            ts = int(time.time() * 1000)
            result = landmarker.detect_for_video(mp_img, ts)

            pinch_active = False
            cursor_screen_pos = None

            if result.hand_landmarks:
                # Suche die gewünschte Hand (Links/Rechts)
                hand_idx = None
                if result.handedness:
                    for i, h_info in enumerate(result.handedness):
                        if h_info[0].category_name == target_handedness:
                            hand_idx = i
                            break
                
                # Nur weitermachen, wenn die richtige Hand gefunden wurde
                if hand_idx is not None:
                    hand = result.hand_landmarks[hand_idx]
                    index_tip = hand[8]
                    thumb_tip = hand[4]

                    index_mcp = hand[5]
                    
                    # 1. "Maus anheben" (Reset / Pause) -> KOMPLETTE FAUST
                    # Wir prüfen, ob ALLE Finger eng zur Handfläche eingekrümmt sind.
                    # Der Daumen ist anatomisch etwas weiter weg, daher bekommt er einen kleinen Offset (+0.02).
                    thumb_curled = landmark_distance(hand[4], hand[2]) < (FIST_THRESHOLD + 0.02)
                    index_curled = landmark_distance(hand[8], hand[5]) < FIST_THRESHOLD
                    middle_curled = landmark_distance(hand[12], hand[9]) < FIST_THRESHOLD
                    ring_curled = landmark_distance(hand[16], hand[13]) < FIST_THRESHOLD
                    pinky_curled = landmark_distance(hand[20], hand[17]) < FIST_THRESHOLD

                    if thumb_curled and index_curled and middle_curled and ring_curled and pinky_curled:
                        prev_px = None
                        prev_py = None
                        if is_mouse_down:
                            mouse_up()
                            is_mouse_down = False
                    else:
                        # Für die Cursor-Bewegung nehmen wir das Grundgelenk (MCP, Landmark 5).
                        px = index_mcp.x
                        py = index_mcp.y

                        if prev_px is None or cursor_x_float is None or cursor_y_float is None:
                            # Trackpad neu ansetzen: Initiale Position holen
                            prev_px = px
                            prev_py = py
                            cx, cy = get_cursor_pos()
                            cursor_x_float = float(cx)
                            cursor_y_float = float(cy)
                        else:
                            # Smoothing auf die Rohdaten anwenden
                            smooth_px = prev_px * smoothing + px * (1.0 - smoothing)
                            smooth_py = prev_py * smoothing + py * (1.0 - smoothing)

                            # Relative Bewegung berechnen (Delta)
                            dx_cam = -(smooth_px - prev_px)
                            dy_cam = smooth_py - prev_py
                            
                            prev_px = smooth_px
                            prev_py = smooth_py

                            # Basis-Sensitivität
                            base_dx = dx_cam * SCREEN_W * 1.2
                            base_dy = dy_cam * SCREEN_H * 1.2

                            # Doppelklick-Stabilisator
                            speed = math.hypot(base_dx, base_dy)
                            current_t = time.time()
                            # Nach jedem Klick frieren wir den Cursor für 400ms ein, außer du machst 
                            # eine sehr starke, bewusste Bewegung. So bleibt er beim Doppelklick perfekt stehen.
                            if (current_t - last_click_time) < 0.40:
                                if speed < 15.0: # Sehr hohe Toleranz gegen Zittern beim Doppelklick
                                    base_dx = 0.0
                                    base_dy = 0.0

                            # Leichte Beschleunigung bei schnellen Bewegungen
                            accel = 1.0
                            if speed > 5.0:
                                accel = min(2.5, 1.0 + (speed - 5.0) * 0.05)

                            final_dx = base_dx * accel
                            final_dy = base_dy * accel

                            # Subpixel-Genauigkeit addieren
                            cursor_x_float += final_dx
                            cursor_y_float += final_dy

                            # An den Bildschirmrand clippen
                            cursor_x_float = max(0.0, min(float(SCREEN_W - 1), cursor_x_float))
                            cursor_y_float = max(0.0, min(float(SCREEN_H - 1), cursor_y_float))

                            final_x = int(cursor_x_float)
                            final_y = int(cursor_y_float)
                            cursor_screen_pos = (final_x, final_y)

                            # Cursor bewegen
                            set_cursor_pos(final_x, final_y)

                        # Drag & Drop: Maus gedrückt halten (mit Hysterese)
                        dist = landmark_distance(index_tip, thumb_tip)
                        current_t = time.time()
                        
                        if not is_mouse_down:
                            if dist < PINCH_START:
                                pinch_active = True
                                mouse_down()
                                is_mouse_down = True
                                last_click_time = current_t
                            else:
                                pinch_active = False
                        else:
                            if dist > PINCH_STOP:
                                pinch_active = False
                                mouse_up()
                                is_mouse_down = False
                                last_click_time = current_t
                            else:
                                pinch_active = True

            else:
                # Keine Hände erkannt -> Maus loslassen und Tracking pausieren
                if is_mouse_down:
                    mouse_up()
                    is_mouse_down = False
                prev_px = None
                prev_py = None

            # Debug-Overlay
            draw_debug_overlay(
                frame,
                result.hand_landmarks if result.hand_landmarks else [],
                cursor_screen_pos,
                pinch_active,
            )

            # FPS
            curr_time = time.time()
            fps = 1.0 / (curr_time - prev_time) if curr_time != prev_time else 0.0
            prev_time = curr_time
            cv2.putText(frame, f"FPS: {int(fps)}  Smooth: {smoothing:.2f}  Hand: {target_handedness}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow("Finger Cursor Control", frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q') or key == 27:
                break
            elif key == ord('h'):
                target_handedness = "Left" if target_handedness == "Right" else "Right"
                print(f"Gewünschte Hand gewechselt zu: {target_handedness}")
            elif key == ord('+') or key == ord('='):
                smoothing = min(0.98, smoothing + 0.05)
                print(f"Smoothing: {smoothing:.2f}")
            elif key == ord('-'):
                smoothing = max(0.0, smoothing - 0.05)
                print(f"Smoothing: {smoothing:.2f}")
            elif key == ord('r'):
                # Position resetten
                prev_px = None
                prev_py = None
                print("Trackpad-Position zurückgesetzt.")

    finally:
        # Sicherheitshalber Maus loslassen beim Beenden
        if 'is_mouse_down' in locals() and is_mouse_down:
            mouse_up()
            
        try:
            landmarker.close()
        except Exception:
            pass
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
