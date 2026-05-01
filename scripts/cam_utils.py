import time
import cv2
import numpy as np

def find_working_camera(max_index=8, preferred_index=None):
    """
    Sucht nach einer funktionierenden Kamera, die auch tatsächlich Bilder liefert.
    Probiert verschiedene Backends aus.
    """
    if preferred_index is not None:
        indices = [preferred_index]
    else:
        indices = range(max_index)

    # CAP_MSMF ist oft stabiler/moderner auf Windows für Webcams
    # CAP_DSHOW ist der Klassiker
    # CAP_ANY lässt OpenCV entscheiden
    backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    
    for backend in backends:
        for i in indices:
            cap = cv2.VideoCapture(i, backend)
            if cap.isOpened():
                # GoPro und andere Webcams brauchen einen Moment zum Initialisieren
                time.sleep(0.5)
                ret, frame = cap.read()
                if ret and frame is not None:
                    # Prüfen, ob das Bild nicht komplett schwarz/leer ist
                    # np.mean > 1.0 ist ein grober Check für "da ist Licht"
                    if np.mean(frame) > 1.0:
                        return cap, i
                cap.release()
    
    return None, None
