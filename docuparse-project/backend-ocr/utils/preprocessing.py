import cv2
import numpy as np
from typing import Any, Dict, List


def decode_image(image_bytes: Any) -> np.ndarray:
    if isinstance(image_bytes, np.ndarray):
        return image_bytes

    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None or image.size == 0:
        raise ValueError("Could not decode image")

    return image


def encode_png_bytes(image: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise ValueError("Could not encode preprocessed image")
    return encoded.tobytes()


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _order_points(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = points.sum(axis=1)
    rect[0] = points[np.argmin(s)]
    rect[2] = points[np.argmax(s)]

    diff = np.diff(points, axis=1)
    rect[1] = points[np.argmin(diff)]
    rect[3] = points[np.argmax(diff)]
    return rect


def _four_point_transform(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    rect = _order_points(points)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))

    if max_width < 10 or max_height < 10:
        return image

    dst = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )

    matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, matrix, (max_width, max_height))
    return warped


def deskew_simple(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0 or len(coords) < 50:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.35:
        return image

    (h, w) = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def warp_perspective_if_photo(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 60, 180)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

    image_area = float(image.shape[0] * image.shape[1])
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = cv2.contourArea(contour)

        if len(approx) == 4 and area > image_area * 0.20:
            points = approx.reshape(4, 2).astype("float32")
            return _four_point_transform(image, points)

    return image


def crop_document_roi(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        10,
    )

    coords = cv2.findNonZero(binary)
    if coords is None:
        return image

    x, y, w, h = cv2.boundingRect(coords)
    if w < 30 or h < 30:
        return image

    area_ratio = (w * h) / float(image.shape[0] * image.shape[1])
    if area_ratio < 0.10:
        return image

    margin_x = int(w * 0.03)
    margin_y = int(h * 0.03)
    x0 = max(0, x - margin_x)
    y0 = max(0, y - margin_y)
    x1 = min(image.shape[1], x + w + margin_x)
    y1 = min(image.shape[0], y + h + margin_y)
    return image[y0:y1, x0:x1]


def crop_margins_light(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return image

    x, y, w, h = cv2.boundingRect(coords)
    if w < 30 or h < 30:
        return image

    margin = 8
    x0 = max(0, x - margin)
    y0 = max(0, y - margin)
    x1 = min(image.shape[1], x + w + margin)
    y1 = min(image.shape[0], y + h + margin)
    return image[y0:y1, x0:x1]


def apply_clahe_local_contrast(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)

    merged = cv2.merge((l_channel, a_channel, b_channel))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)


def equalize_illumination(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    background = cv2.medianBlur(gray, 31)
    normalized = cv2.divide(gray, background, scale=255)
    normalized = cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
    return normalized


def denoise_light(image: np.ndarray) -> np.ndarray:
    return cv2.bilateralFilter(image, 7, 50, 50)


def denoise_moderate(image: np.ndarray) -> np.ndarray:
    return cv2.fastNlMeansDenoisingColored(image, None, 8, 8, 7, 21)


def gaussian_light(image: np.ndarray) -> np.ndarray:
    return cv2.GaussianBlur(image, (3, 3), 0)


def sharpen_moderate(image: np.ndarray) -> np.ndarray:
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
    return cv2.filter2D(image, -1, kernel)


def enhance_blue_ink_light(image: np.ndarray) -> np.ndarray:
    # Ajuste manuscrito: realça traços de caneta azul sem destruir texto impresso.
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h_channel, s_channel, v_channel = cv2.split(hsv)

    blue_mask = ((h_channel >= 80) & (h_channel <= 135)).astype(np.uint8)
    s_channel = np.where(blue_mask > 0, np.clip(s_channel.astype(np.int16) + 35, 0, 255), s_channel).astype(np.uint8)
    v_channel = np.where(blue_mask > 0, np.clip(v_channel.astype(np.int16) + 10, 0, 255), v_channel).astype(np.uint8)

    boosted = cv2.merge((h_channel, s_channel, v_channel))
    return cv2.cvtColor(boosted, cv2.COLOR_HSV2BGR)


def _ensure_bgr(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("Invalid image provided")

    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    return image


def _resize_min_side_keep_ratio(image: np.ndarray, min_side: int = 384, max_side: int = 2048) -> np.ndarray:
    h, w = image.shape[:2]
    current_min = min(h, w)
    if current_min <= 0:
        return image

    scale = max(1.0, float(min_side) / float(current_min))
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))

    longest_side = max(new_h, new_w)
    if longest_side > max_side:
        downscale = float(max_side) / float(longest_side)
        new_w = max(1, int(round(new_w * downscale)))
        new_h = max(1, int(round(new_h * downscale)))

    if new_w == w and new_h == h:
        return image

    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)


def preprocess_for_trocr_region(region_image: np.ndarray) -> np.ndarray:
    # PASSO CRÍTICO: TrOCR performa melhor com imagem natural (sem binarização agressiva).
    image = _ensure_bgr(region_image)
    image = denoise_light(image)
    image = apply_clahe_local_contrast(image)
    image = enhance_blue_ink_light(image)
    image = _resize_min_side_keep_ratio(image, min_side=384, max_side=2048)
    return image


def preprocess_for_trocr_engine(image_bytes: Any, classification: str = "") -> tuple[bytes, dict]:
    image = decode_image(image_bytes)
    image = preprocess_for_trocr_region(image)

    return encode_png_bytes(image), {
        "engine_preprocessing": "trocr_handwritten",
        "classification_hint": classification,
        "steps": [
            "denoise_light",
            "clahe_local_contrast",
            "enhance_blue_ink_light",
            "resize_min_side_keep_ratio",
        ],
    }


def _boxes_overlap_or_close(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int], margin: int = 12) -> bool:
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    a_left, a_top, a_right, a_bottom = ax - margin, ay - margin, ax + aw + margin, ay + ah + margin
    b_left, b_top, b_right, b_bottom = bx, by, bx + bw, by + bh
    return not (a_right < b_left or b_right < a_left or a_bottom < b_top or b_bottom < a_top)


def _merge_two_boxes(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    x0 = min(ax, bx)
    y0 = min(ay, by)
    x1 = max(ax + aw, bx + bw)
    y1 = max(ay + ah, by + bh)
    return x0, y0, x1 - x0, y1 - y0


def _merge_candidate_boxes(boxes: List[tuple[int, int, int, int]]) -> List[tuple[int, int, int, int]]:
    if not boxes:
        return []

    merged = boxes[:]
    changed = True
    while changed:
        changed = False
        next_boxes: List[tuple[int, int, int, int]] = []
        while merged:
            base = merged.pop(0)
            idx = 0
            while idx < len(merged):
                if _boxes_overlap_or_close(base, merged[idx]):
                    base = _merge_two_boxes(base, merged.pop(idx))
                    changed = True
                else:
                    idx += 1
            next_boxes.append(base)
        merged = next_boxes

    return merged


def _is_signature_like(region_gray: np.ndarray, binary_inv: np.ndarray) -> bool:
    h, w = region_gray.shape[:2]
    if h < 18 or w < 60:
        return False

    aspect_ratio = w / max(float(h), 1.0)
    ink_density = float(np.count_nonzero(binary_inv)) / float(binary_inv.size)

    # Assinatura costuma ser horizontal, com baixa densidade de tinta e traço irregular.
    edges = cv2.Canny(region_gray, 70, 170)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)
    lap_var = float(cv2.Laplacian(region_gray, cv2.CV_64F).var())

    # Printed text lines have many connected components per unit width (one per character/stroke).
    # Signatures have few, larger irregular strokes — typically 1–4 per 100px of width.
    # This is the key discriminator: a text line "Valor: R$ 150,00" at scan resolution
    # will have ~8+ components/100px; a cursive signature will have ~1–3.
    num_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary_inv, connectivity=8)
    valid_components = sum(1 for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] >= 12)
    components_per_100px = float(valid_components) / max(1.0, w / 100.0)

    return (
        aspect_ratio >= 2.4
        and 0.01 <= ink_density <= 0.20
        and 0.01 <= edge_density <= 0.15
        and lap_var >= 25.0
        and components_per_100px <= 4.0
    )


def _classify_region(region_image: np.ndarray) -> str:
    region = _ensure_bgr(region_image)
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    binary_inv = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        11,
    )

    if _is_signature_like(gray, binary_inv):
        return "signature"

    ink_density = float(np.count_nonzero(binary_inv)) / float(binary_inv.size)
    edges = cv2.Canny(gray, 60, 180)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)
    edge_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # Heurística inicial para manuscrito: maior irregularidade e densidade de bordas.
    if (edge_variance >= 90.0 and edge_density >= 0.08) or (ink_density >= 0.22 and edge_variance >= 70.0):
        return "handwritten"

    return "printed"


def segment_handwritten_regions(image: np.ndarray) -> List[Dict[str, Any]]:
    # PASSO CRÍTICO: segmenta regiões para aplicar OCR especializado por tipo.
    source = _ensure_bgr(image)
    gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY)

    binary_inv = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        35,
        9,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 5))
    connected = cv2.morphologyEx(binary_inv, cv2.MORPH_CLOSE, kernel, iterations=1)
    connected = cv2.dilate(connected, np.ones((3, 3), dtype=np.uint8), iterations=1)

    contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    image_area = float(source.shape[0] * source.shape[1])
    min_area = max(220.0, image_area * 0.0009)
    max_area = image_area * 0.95

    raw_boxes: List[tuple[int, int, int, int]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = float(w * h)
        if area < min_area or area > max_area:
            continue
        if w < 20 or h < 14:
            continue
        raw_boxes.append((x, y, w, h))

    merged_boxes = _merge_candidate_boxes(raw_boxes)
    merged_boxes = sorted(merged_boxes, key=lambda box: (box[1], box[0]))[:80]

    regions: List[Dict[str, Any]] = []
    for idx, (x, y, w, h) in enumerate(merged_boxes):
        x0 = max(0, x - 4)
        y0 = max(0, y - 4)
        x1 = min(source.shape[1], x + w + 4)
        y1 = min(source.shape[0], y + h + 4)
        cropped = source[y0:y1, x0:x1]
        if cropped.size == 0:
            continue

        region_type = _classify_region(cropped)
        regions.append(
            {
                "id": idx + 1,
                "type": region_type,
                "bbox": {
                    "x": int(x0),
                    "y": int(y0),
                    "width": int(x1 - x0),
                    "height": int(y1 - y0),
                },
                "image": cropped,
            }
        )

    if regions:
        return regions

    # Fallback resiliente: se não segmentar, processa a página inteira como manuscrita.
    return [
        {
            "id": 1,
            "type": "handwritten",
            "bbox": {
                "x": 0,
                "y": 0,
                "width": int(source.shape[1]),
                "height": int(source.shape[0]),
            },
            "image": source,
        }
    ]


def segment_text_lines(region_image: np.ndarray, min_line_height: int = 8, gap_threshold: int = 2) -> List[np.ndarray]:
    """Split a region into individual line crops via horizontal projection for line-level OCR."""
    image = _ensure_bgr(region_image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, binary_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h_proj = np.sum(binary_inv > 0, axis=1)

    kernel_size = max(1, min_line_height // 2)
    smoothed = np.convolve(h_proj, np.ones(kernel_size) / kernel_size, mode="same")
    in_text = smoothed > gap_threshold

    line_slices: List[tuple] = []
    start = None
    for row_idx in range(len(in_text)):
        if in_text[row_idx] and start is None:
            start = row_idx
        elif not in_text[row_idx] and start is not None:
            if row_idx - start >= min_line_height:
                line_slices.append((start, row_idx))
            start = None
    if start is not None and len(in_text) - start >= min_line_height:
        line_slices.append((start, len(in_text)))

    if not line_slices:
        return [image]

    lines: List[np.ndarray] = []
    for y0, y1 in line_slices:
        margin = 3
        y0_m = max(0, y0 - margin)
        y1_m = min(image.shape[0], y1 + margin)
        line_crop = image[y0_m:y1_m, :]
        if line_crop.size > 0:
            lines.append(line_crop)

    return lines if lines else [image]


def upscale_if_low_resolution(image: np.ndarray, min_side: int = 1200, max_scale: float = 2.0) -> np.ndarray:
    h, w = image.shape[:2]
    current_min = min(h, w)

    if current_min >= min_side:
        return image

    scale = _clip01(min_side / max(1.0, float(current_min)))
    if scale < 1.0:
        return image
    scale = min(max_scale, min_side / max(1.0, float(current_min)))
    if scale <= 1.01:
        return image

    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


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


def preprocess_for_paddle_engine(image_bytes: Any, classification: str = "") -> tuple[bytes, dict]:
    image = decode_image(image_bytes)

    if classification in {"handwritten_complex", "handwritten"}:
        # Ajuste manuscrito: pipeline preserva traço fino e tinta azul.
        image = warp_perspective_if_photo(image)
        image = deskew_simple(image)
        image = enhance_blue_ink_light(image)
        image = apply_clahe_local_contrast(image)
        image = denoise_light(image)
        image = sharpen_moderate(image)
        image = upscale_if_low_resolution(image, min_side=1350, max_scale=2.2)

        return encode_png_bytes(image), {
            "engine_preprocessing": "paddleocr_handwritten",
            "classification_hint": classification,
            "steps": [
                "warp_perspective_if_photo",
                "deskew_simple",
                "enhance_blue_ink_light",
                "clahe_local_contrast",
                "denoise_light",
                "sharpen_moderate",
                "upscale_if_low_resolution",
            ],
        }

    image = warp_perspective_if_photo(image)
    image = deskew_simple(image)
    image = apply_clahe_local_contrast(image)
    image = denoise_light(image)
    image = equalize_illumination(image)
    image = gaussian_light(image)
    image = upscale_if_low_resolution(image, min_side=1100, max_scale=1.8)

    return encode_png_bytes(image), {
        "engine_preprocessing": "paddleocr",
        "classification_hint": classification,
        "steps": [
            "warp_perspective_if_photo",
            "deskew_simple",
            "clahe_local_contrast",
            "denoise_light",
            "equalize_illumination",
            "gaussian_light",
            "upscale_if_low_resolution",
        ],
    }


def preprocess_for_easyocr_engine(image_bytes: Any, classification: str = "") -> tuple[bytes, dict]:
    image = decode_image(image_bytes)

    if classification in {"handwritten_complex", "handwritten"}:
        # Ajuste manuscrito: EasyOCR com preprocess direcionado a assinatura/anotações.
        image = warp_perspective_if_photo(image)
        image = deskew_simple(image)
        image = enhance_blue_ink_light(image)
        image = denoise_light(image)
        image = apply_clahe_local_contrast(image)
        image = sharpen_moderate(image)
        image = upscale_if_low_resolution(image, min_side=1500, max_scale=2.4)

        return encode_png_bytes(image), {
            "engine_preprocessing": "easyocr_handwritten",
            "classification_hint": classification,
            "steps": [
                "warp_perspective_if_photo",
                "deskew_simple",
                "enhance_blue_ink_light",
                "denoise_light",
                "clahe_local_contrast",
                "sharpen_moderate",
                "upscale_if_low_resolution",
            ],
        }

    image = denoise_moderate(image)
    image = apply_clahe_local_contrast(image)
    image = deskew_simple(image)
    image = sharpen_moderate(image)
    image = upscale_if_low_resolution(image, min_side=1400, max_scale=2.0)

    return encode_png_bytes(image), {
        "engine_preprocessing": "easyocr",
        "classification_hint": classification,
        "steps": [
            "denoise_moderate",
            "clahe_local_contrast",
            "deskew_simple",
            "sharpen_moderate",
            "upscale_if_low_resolution",
        ],
    }


def preprocess_for_deepseek_engine(image_bytes: Any, classification: str = "") -> tuple[bytes, dict]:
    image = decode_image(image_bytes)

    image = warp_perspective_if_photo(image)
    image = deskew_simple(image)
    image = crop_document_roi(image)
    image = apply_clahe_local_contrast(image)
    image = denoise_light(image)
    image = upscale_if_low_resolution(image, min_side=1300, max_scale=2.0)

    return encode_png_bytes(image), {
        "engine_preprocessing": "deepseek",
        "classification_hint": classification,
        "steps": [
            "warp_perspective_if_photo",
            "deskew_simple",
            "crop_document_roi",
            "clahe_local_contrast",
            "denoise_light",
            "upscale_if_low_resolution",
        ],
    }


def preprocess_for_docling_engine(image_bytes: Any, classification: str = "") -> tuple[bytes, dict]:
    image = decode_image(image_bytes)
    image = deskew_simple(image)
    image = crop_margins_light(image)

    return encode_png_bytes(image), {
        "engine_preprocessing": "docling_image_fallback",
        "classification_hint": classification,
        "steps": [
            "deskew_simple",
            "crop_margins_light",
        ],
    }


def preprocess_for_llamaparse_engine(image_bytes: Any, classification: str = "") -> tuple[bytes, dict]:
    image = decode_image(image_bytes)
    image = deskew_simple(image)
    image = crop_margins_light(image)

    return encode_png_bytes(image), {
        "engine_preprocessing": "llamaparse_image_fallback",
        "classification_hint": classification,
        "steps": [
            "deskew_simple",
            "crop_margins_light",
        ],
    }

#MAIN

def preprocess_image(image_bytes: Any, classification: str) -> np.ndarray:
    image = decode_image(image_bytes)

    if classification == "digital_pdf":
        return preprocess_digital_pdf(image)

    elif classification == "scanned_image":
        return preprocess_scanned(image)

    elif classification == "photo":
        return preprocess_photo(image)

    elif classification in {"handwritten", "handwritten_complex"}:
        return preprocess_handwritten(image)

    else:
        # fallback seguro
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return gray