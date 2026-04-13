import cv2
import numpy as np
from typing import Any


def decode_image(image_bytes: Any) -> np.ndarray:
    if isinstance(image_bytes, np.ndarray):
        return image_bytes

    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None or image.size == 0:
        raise ValueError("Could not decode image")

    return image


# -------------------------------
# PIPELINES ESPECÍFICOS
# -------------------------------

def preprocess_scanned(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    denoised = cv2.fastNlMeansDenoising(gray, None, 20, 7, 21)

    thresh = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        2
    )

    return thresh


def preprocess_photo(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    denoised = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)

    thresh = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        2
    )

    # Deskew
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = thresh.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)

    deskewed = cv2.warpAffine(thresh, M, (w, h))

    resized = cv2.resize(deskewed, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    return resized


def preprocess_handwritten(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # manuscrito precisa preservar traços finos
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    thresh = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,  # invertido funciona melhor para manuscrito
        25,
        10
    )

    return thresh


def preprocess_digital_pdf(image: np.ndarray) -> np.ndarray:
    # PDF digital geralmente já é limpo
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    return gray

#MAIN

def preprocess_image(image_bytes: Any, classification: str) -> np.ndarray:
    image = decode_image(image_bytes)

    if classification == "digital_pdf":
        return preprocess_digital_pdf(image)

    elif classification == "scanned_image":
        return preprocess_scanned(image)

    elif classification == "photo":
        return preprocess_photo(image)

    elif classification == "handwritten":
        return preprocess_handwritten(image)

    else:
        # fallback seguro
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return gray