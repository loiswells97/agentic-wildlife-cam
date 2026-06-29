#!/usr/bin/env python3
"""Download the TFLite classifier model and ImageNet labels for identify_animal."""

import tarfile
import tempfile
import urllib.request
from pathlib import Path

# Old /models/tflite/... URLs now return 403; this tarball still works.
MODEL_TGZ_URL = (
    "https://storage.googleapis.com/download.tensorflow.org/models/"
    "mobilenet_v1_2018_08_02/mobilenet_v1_1.0_224_quant.tgz"
)
LABELS_URL = (
    "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt"
)

USER_AGENT = "agentic-wildlife-cam/1.0"


def download(url: str, dest: Path) -> None:
    print(f"Downloading {url} ...")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response, dest.open("wb") as out:
        out.write(response.read())
    print(f"Saved to {dest}")


def download_model(model_path: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "model.tgz"
        download(MODEL_TGZ_URL, archive)

        print("Extracting model...")
        with tarfile.open(archive, "r:gz") as tar:
            member = next(
                m for m in tar.getmembers() if m.name.endswith("mobilenet_v1_1.0_224_quant.tflite")
            )
            extracted = tar.extractfile(member)
            if extracted is None:
                raise RuntimeError("Could not extract model from archive")
            model_path.write_bytes(extracted.read())

    print(f"Model ready at {model_path}")


def main() -> None:
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)

    model_path = models_dir / "animal_classifier.tflite"
    labels_path = models_dir / "animal_labels.txt"

    if not model_path.exists():
        download_model(model_path)
    else:
        print(f"Model already exists at {model_path}")

    if not labels_path.exists():
        download(LABELS_URL, labels_path)
    else:
        print(f"Labels already exist at {labels_path}")

    print("Classifier ready.")


if __name__ == "__main__":
    main()
