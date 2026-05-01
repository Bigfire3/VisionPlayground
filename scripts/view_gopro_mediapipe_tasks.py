#!/usr/bin/env python3
"""
Live-Viewer mit MediaPipe Tasks API (HandLandmarker).

Benötigt ein heruntergeladenes Modell unter `models/hand_landmarker.task`.
Anleitung: https://developers.google.com/mediapipe/solutions/vision/hand_landmarker
Beenden mit 'q' oder ESC.
"""
import time
import os
import sys
from pathlib import Path
import cv2
import numpy as np

try:
    from mediapipe.tasks.python.vision import hand_landmarker
    from mediapipe.tasks.python.vision.core import image as mp_image
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python.vision import RunningMode
except Exception:
    hand_landmarker = None
    mp_image = None
    BaseOptions = None
    RunningMode = None

from cam_utils import find_working_camera

MODEL_PATH = Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"


def draw_landmarks(frame, landmarks_list):
    h, w, _ = frame.shape
    for hand in landmarks_list:
        pts = [(int(lmk.x * w), int(lmk.y * h)) for lmk in hand]
        for x, y in pts:
            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
        try:
            conns = hand_landmarker.HandLandmarksConnections.HAND_CONNECTIONS
            for c in conns:
                a = pts[c.start]
                b = pts[c.end]
                cv2.line(frame, a, b, (0, 200, 0), 2)
        except Exception:
            pass


def main():
    # CLI Argument für Kamera-Index unterstützen
    pref_idx = None
    if len(sys.argv) > 1:
        try:
            pref_idx = int(sys.argv[1])
        except ValueError:
            pass

    if hand_landmarker is None or mp_image is None:
        print("Deine mediapipe-Installation unterstützt die Tasks-API nicht oder ist unvollständig.")
        print("Stelle sicher, dass `mediapipe` 0.10+ installiert ist.")
        return

    if not MODEL_PATH.exists():
        print(f"Modell nicht gefunden: {MODEL_PATH}")
        print("Lade ein HandLandmarker .task Modell herunter und lege es in 'models/hand_landmarker.task'.")
        return

    print("Suche nach funktionierender Kamera...")
    cap, idx = find_working_camera(preferred_index=pref_idx)
    if cap is None:
        print("Kamera nicht gefunden oder liefert kein Bild. Prüfe Verbindung und Webcam-Modus der GoPro.")
        return

    print(f"Benutze Kamera index {idx}")
    
    # Auflösung setzen - manche GoPros brauchen das, um aus dem Idle aufzuwachen
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Nochmal kurz warten nach dem Setzen der Auflösung
    time.sleep(0.5)

    options = hand_landmarker.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    landmarker = hand_landmarker.HandLandmarker.create_from_options(options)

    prev_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                # Kleiner Retry-Mechanismus falls ein Frame fehlt
                for _ in range(5):
                    time.sleep(0.01)
                    ret, frame = cap.read()
                    if ret: break
                
                if not ret:
                    print("Kein Frame erhalten — Verbindung prüfen.")
                    break

            # convert BGR (OpenCV) to RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_img = mp_image.Image(mp_image.ImageFormat.SRGB, rgb)

            # timestamp in ms
            ts = int(time.time() * 1000)
            result = landmarker.detect_for_video(mp_img, ts)

            if result.hand_landmarks:
                draw_landmarks(frame, result.hand_landmarks)

            # FPS
            curr_time = time.time()
            dt = curr_time - prev_time
            if dt > 0:
                fps = 1.0 / dt
                cv2.putText(frame, f"FPS: {int(fps)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            prev_time = curr_time

            cv2.imshow("GoPro MediaPipe Tasks Hands", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break
    finally:
        try:
            landmarker.close()
        except Exception:
            pass
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
