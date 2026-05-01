#!/usr/bin/env python3
"""
Ein kleines Script, um eine angeschlossene GoPro (als Webcam) mit OpenCV anzuzeigen.
Versucht DirectShow-Devices zuerst, dann ohne Backend.
Beenden mit Taste 'q' oder ESC.
"""
import cv2


import sys
from cam_utils import find_working_camera


def main():
    # CLI Argument für Kamera-Index unterstützen
    pref_idx = None
    if len(sys.argv) > 1:
        try:
            pref_idx = int(sys.argv[1])
        except ValueError:
            pass

    print("Suche nach funktionierender Kamera...")
    cap, idx = find_working_camera(preferred_index=pref_idx)
    if cap is None:
        print("Kamera nicht gefunden oder liefert kein Bild. Prüfe Verbindung und Webcam-Modus der GoPro.")
        return

    print(f"Benutze Kamera index {idx}")
    # Optionale Auflösung setzen (falls die Kamera das unterstützt)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Kein Frame erhalten — Verbindung prüfen.")
            break
        cv2.imshow("GoPro Live", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
