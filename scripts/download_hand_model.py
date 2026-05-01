#!/usr/bin/env python3
"""
Lädt das MediaPipe HandLandmarker .task Modell herunter und speichert es nach `models/hand_landmarker.task`.

Standard-URL ist leer — setze `MODEL_URL` auf die gewünschte Download-URL.
Beispiel-Download-Quelle (manuell prüfen): https://github.com/google/mediapipe-models

Benutzung:
    python scripts/download_hand_model.py

Wenn ein Proxy/Authentifizierung nötig ist, setze entsprechende Umgebungsvariablen.
"""
import os
import sys
from pathlib import Path
try:
    import requests
except Exception:
    requests = None

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_PATH = MODEL_DIR / "hand_landmarker.task"
# TODO: set a valid URL for the model release you want to download
MODEL_URL = os.environ.get("HAND_LANDMARKER_MODEL_URL", "")


def download_with_requests(url: str, dest: Path):
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


def download_with_urllib(url: str, dest: Path):
    import urllib.request
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)


def main():
    if MODEL_URL == "":
        print("Kein Modell-URL konfiguriert.")
        print("Setze die Umgebungsvariable HAND_LANDMARKER_MODEL_URL oder editiere MODEL_URL in diesem Script.")
        print("Siehe: https://github.com/google/mediapipe-models für verfügbare Modelle.")
        sys.exit(1)

    print(f"Lade Modell von: {MODEL_URL}")
    try:
        if requests is not None:
            download_with_requests(MODEL_URL, MODEL_PATH)
        else:
            download_with_urllib(MODEL_URL, MODEL_PATH)
    except Exception as e:
        print("Fehler beim Herunterladen des Modells:", e)
        sys.exit(2)

    print(f"Modell gespeichert nach: {MODEL_PATH}")


if __name__ == "__main__":
    main()
