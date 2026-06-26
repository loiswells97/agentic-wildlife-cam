#!/usr/bin/env python3
"""Download the TFLite classifier model and ImageNet labels for identify_animal."""

import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/download.tensorflow.org/models/tflite/"
    "mobilenet_v1_1.0_224_quant.tflite"
)
LABELS_URL = (
    "https://storage.googleapis.com/download.tensorflow.org/data/"
    "imagenet_mobilenet_v1_1000_labelmap.txt"
)


def download(url: str, dest: Path) -> None:
    print(f"Downloading {dest.name}...")
    urllib.request.urlretrieve(url, dest)
    print(f"Saved to {dest}")


def main() -> None:
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    model_path = models_dir / "animal_classifier.tflite"
    labels_path = models_dir / "animal_labels.txt"

    if not model_path.exists():
        download(MODEL_URL, model_path)
    else:
        print(f"Model already exists at {model_path}")

    if not labels_path.exists():
        download(LABELS_URL, labels_path)
    else:
        print(f"Labels already exist at {labels_path}")

    print("Classifier ready.")


if __name__ == "__main__":
    main()
