"""Local animal image classifier using TFLite."""

import os
from pathlib import Path

import numpy as np
from PIL import Image

_interpreter = None
_labels: list[str] | None = None

MODEL_PATH = os.getenv("ANIMAL_CLASSIFIER_MODEL", "models/animal_classifier.tflite")
LABELS_PATH = os.getenv("ANIMAL_CLASSIFIER_LABELS", "models/animal_labels.txt")
CONFIDENCE_THRESHOLD = float(os.getenv("ANIMAL_CLASSIFIER_THRESHOLD", "0.25"))
INPUT_SIZE = int(os.getenv("ANIMAL_CLASSIFIER_INPUT_SIZE", "224"))


def _load_model():
    global _interpreter, _labels
    if _interpreter is not None:
        return

    try:
        from tflite_runtime.interpreter import Interpreter
    except ImportError:
        from tensorflow.lite import Interpreter

    model_path = Path(MODEL_PATH)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Classifier model not found at {model_path}. "
            "Run: python scripts/setup_classifier.py"
        )

    _interpreter = Interpreter(model_path=str(model_path))
    _interpreter.allocate_tensors()

    labels_path = Path(LABELS_PATH)
    if labels_path.exists():
        _labels = []
        for line in labels_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            # ImageNet label files use "id: name" or "id name"
            if ":" in line:
                _labels.append(line.split(":", 1)[1].strip())
            elif " " in line and line.split()[0].isdigit():
                _labels.append(" ".join(line.split()[1:]))
            else:
                _labels.append(line)


def _preprocess(image_path: str, input_details: dict) -> np.ndarray:
    image = Image.open(image_path).convert("RGB").resize((INPUT_SIZE, INPUT_SIZE))
    array = np.array(image)

    if input_details["dtype"] == np.float32:
        array = (array.astype(np.float32) / 127.5) - 1.0

    return np.expand_dims(array, axis=0)


def _get_probabilities(output_details: dict) -> np.ndarray:
    output = _interpreter.get_tensor(output_details["index"])[0]

    scale, zero_point = output_details["quantization"]
    if scale > 0:
        output = (output.astype(np.float32) - zero_point) * scale

    if output.min() < 0 or output.max() > 1:
        output = output.astype(np.float32)
        output = np.exp(output - output.max())
        output /= output.sum()

    return output


def classify_image(image_path: str) -> dict:
    """Classify an image and return animal name and confidence."""
    _load_model()

    input_details = _interpreter.get_input_details()[0]
    output_details = _interpreter.get_output_details()[0]

    input_data = _preprocess(image_path, input_details)
    _interpreter.set_tensor(input_details["index"], input_data)
    _interpreter.invoke()

    probabilities = _get_probabilities(output_details)
    index = int(np.argmax(probabilities))
    confidence = float(probabilities[index])

    if _labels and index < len(_labels):
        animal = _labels[index]
    else:
        animal = f"class_{index}"

    if confidence < CONFIDENCE_THRESHOLD:
        animal = "unknown"

    return {"animal": animal, "confidence": round(confidence, 3)}
