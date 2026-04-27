#!/usr/bin/env python3
"""Pipeline de testes OCR local (sem Docker).

Fluxo:
1) Classifica PDF com PyMuPDF (texto vs imagem).
2) PDF textual -> Docling.
3) PDF imagem / imagem avulsa -> classifica em digitado/manuscrito/hibrido.
4) Digitado -> Tesseract com score por bloco + score global.
5) Manuscrito -> EasyOCR.
6) Hibrido -> classificador simples de blocos e OCR combinado.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import fitz  # pymupdf
import numpy as np
import pytesseract
from PIL import Image

DocumentConverter = None
easyocr = None


BBox = Tuple[int, int, int, int]  # x1, y1, x2, y2


@dataclass
class PdfClassification:
    nr_pages: int
    txtblocks: int
    imgblocks: int
    docfonts: List[str]
    mode: str  # "text" | "image"


def classify_pdf(pdf_path: Path) -> PdfClassification:
    doc = fitz.open(pdf_path.as_posix())
    txtblocks = 0
    imgblocks = 0
    docfonts: List[str] = []

    for page in doc:
        content = page.get_text("dict")
        for block in content.get("blocks", []):
            btype = block.get("type")
            if btype == 0:
                txtblocks += 1
            elif btype == 1:
                imgblocks += 1

        for font in page.get_fonts():
            font_name = font[3]
            if font_name not in docfonts:
                docfonts.append(font_name)

    nr_pages = len(doc)
    doc.close()

    # Regra conservadora: se existir volume de texto real, tratamos como "text".
    mode = "text" if txtblocks > 0 and txtblocks >= imgblocks else "image"
    return PdfClassification(
        nr_pages=nr_pages,
        txtblocks=txtblocks,
        imgblocks=imgblocks,
        docfonts=docfonts,
        mode=mode,
    )


def render_pdf_pages_as_images(pdf_path: Path, dpi: int = 300) -> List[np.ndarray]:
    doc = fitz.open(pdf_path.as_posix())
    images: List[np.ndarray] = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        else:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        images.append(arr)

    doc.close()
    return images


def get_easyocr_reader(langs: Sequence[str]) -> Any:
    global easyocr
    if easyocr is None:
        try:
            import easyocr as easyocr_module
        except Exception as exc:  # pragma: no cover - depende de runtime local
            raise RuntimeError("easyocr nao esta instalado. Rode: uv pip install easyocr") from exc
        easyocr = easyocr_module
    model_dir = Path(__file__).resolve().parent / ".easyocr_models"
    model_dir.mkdir(parents=True, exist_ok=True)
    return easyocr.Reader(
        list(langs),
        gpu=False,
        model_storage_directory=model_dir.as_posix(),
        user_network_directory=model_dir.as_posix(),
    )


def ocr_tesseract(image_bgr: np.ndarray, lang: str = "por") -> Dict[str, Any]:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(
        gray,
        lang=lang,
        config="--oem 1 --psm 6",
        output_type=pytesseract.Output.DICT,
    )

    words: List[Dict[str, Any]] = []
    confs: List[float] = []
    full_text_tokens: List[str] = []
    n = len(data["text"])

    for i in range(n):
        txt = (data["text"][i] or "").strip()
        try:
            conf = float(data["conf"][i])
        except Exception:
            conf = -1.0
        if not txt or conf < 0:
            continue
        x, y, w, h = (int(data["left"][i]), int(data["top"][i]), int(data["width"][i]), int(data["height"][i]))
        words.append({"text": txt, "confidence": conf / 100.0, "bbox": [x, y, x + w, y + h]})
        confs.append(conf / 100.0)
        full_text_tokens.append(txt)

    global_score = float(np.mean(confs)) if confs else 0.0
    return {
        "engine": "tesseract",
        "text": " ".join(full_text_tokens).strip(),
        "global_score": round(global_score, 4),
        "words": words,
    }


def ocr_easyocr(image_bgr: np.ndarray, reader: Any, min_prob: float = 0.35) -> Dict[str, Any]:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    result = reader.readtext(rgb)
    items: List[Dict[str, Any]] = []
    confs: List[float] = []
    full_text_tokens: List[str] = []

    for bbox, text, prob in result:
        p = float(prob)
        if not text or p < min_prob:
            continue
        pts = np.array(bbox, dtype=np.int32)
        x1, y1 = int(np.min(pts[:, 0])), int(np.min(pts[:, 1]))
        x2, y2 = int(np.max(pts[:, 0])), int(np.max(pts[:, 1]))
        items.append({"text": text, "confidence": p, "bbox": [x1, y1, x2, y2]})
        confs.append(p)
        full_text_tokens.append(text)

    global_score = float(np.mean(confs)) if confs else 0.0
    return {
        "engine": "easyocr",
        "text": " ".join(full_text_tokens).strip(),
        "global_score": round(global_score, 4),
        "words": items,
    }


def _bbox_iou(a: BBox, b: BBox) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def classify_image_type(image_bgr: np.ndarray, reader: Any, tesseract_lang: str = "por") -> Dict[str, Any]:
    t = ocr_tesseract(image_bgr, lang=tesseract_lang)
    e = ocr_easyocr(image_bgr, reader)

    t_score = float(t["global_score"])
    e_score = float(e["global_score"])
    t_words = len(t["words"])
    e_words = len(e["words"])

    # Heuristica:
    # - forte em Tesseract e fraco em EasyOCR => digitado
    # - forte em EasyOCR e fraco em Tesseract => manuscrito
    # - ambos relevantes => hibrido
    if t_score >= 0.55 and t_words >= 8 and (t_score - e_score) >= 0.15:
        label = "typed"
    elif e_score >= 0.45 and e_words >= 5 and (e_score - t_score) >= 0.10:
        label = "handwritten"
    elif t_words == 0 and e_words > 0:
        label = "handwritten"
    elif e_words == 0 and t_words > 0:
        label = "typed"
    else:
        label = "hybrid"

    return {
        "label": label,
        "signals": {
            "tesseract_global_score": round(t_score, 4),
            "easyocr_global_score": round(e_score, 4),
            "tesseract_words": t_words,
            "easyocr_words": e_words,
        },
        "preview": {
            "tesseract_text": t["text"][:280],
            "easyocr_text": e["text"][:280],
        },
    }


def _crop(image: np.ndarray, bbox: BBox) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    h, w = image.shape[:2]
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(x1 + 1, min(x2, w))
    y2 = max(y1 + 1, min(y2, h))
    return image[y1:y2, x1:x2]


def ocr_hybrid_by_blocks(image_bgr: np.ndarray, reader: Any, tesseract_lang: str = "por") -> Dict[str, Any]:
    t = ocr_tesseract(image_bgr, lang=tesseract_lang)
    e = ocr_easyocr(image_bgr, reader)
    typed_words = t["words"]
    easy_words = e["words"]

    typed_blocks: List[Dict[str, Any]] = []
    handwritten_blocks: List[Dict[str, Any]] = []
    final_tokens: List[str] = []
    confs: List[float] = []

    # Blocos digitados: os de Tesseract acima de confiança mínima.
    for w in typed_words:
        if float(w["confidence"]) >= 0.55:
            typed_blocks.append(w)
            final_tokens.append(w["text"])
            confs.append(float(w["confidence"]))

    # Blocos manuscritos: EasyOCR sem overlap relevante com blocos já digitados.
    typed_boxes = [tuple(w["bbox"]) for w in typed_blocks]
    for w in easy_words:
        bbox = tuple(w["bbox"])
        max_iou = max((_bbox_iou(bbox, tb) for tb in typed_boxes), default=0.0)
        if max_iou < 0.25:
            crop = _crop(image_bgr, bbox)
            # OCR dedicado no recorte manuscrito (EasyOCR).
            rec = ocr_easyocr(crop, reader, min_prob=0.30)
            txt = rec["text"].strip() or w["text"]
            score = max(float(rec["global_score"]), float(w["confidence"]))
            handwritten_blocks.append({"text": txt, "confidence": score, "bbox": list(bbox)})
            final_tokens.append(txt)
            confs.append(score)

    global_score = float(np.mean(confs)) if confs else 0.0
    return {
        "engine": "hybrid:tesseract+easyocr",
        "text": " ".join(t for t in final_tokens if t).strip(),
        "global_score": round(global_score, 4),
        "typed_blocks": typed_blocks,
        "handwritten_blocks": handwritten_blocks,
    }


def process_with_docling(path: Path) -> Dict[str, Any]:
    global DocumentConverter
    if DocumentConverter is None:
        try:
            from docling.document_converter import DocumentConverter as DoclingConverter
        except Exception as exc:  # pragma: no cover - depende de runtime local
            raise RuntimeError("docling nao esta instalado. Rode: uv pip install docling") from exc
        DocumentConverter = DoclingConverter
    converter = DocumentConverter()
    result = converter.convert(path.as_posix())
    markdown = result.document.export_to_markdown()
    return {
        "engine": "docling",
        "text": markdown,
        "preview": markdown[:500],
    }


def process_text_pdf_with_pymupdf(path: Path) -> Dict[str, Any]:
    doc = fitz.open(path.as_posix())
    page_texts: List[str] = []
    for page in doc:
        page_texts.append((page.get_text("text") or "").strip())
    doc.close()
    text = "\n\n".join(t for t in page_texts if t).strip()
    return {
        "engine": "pymupdf",
        "text": text,
        "preview": text[:500],
    }


def _parse_major_minor(version: str) -> Tuple[int, int]:
    parts = version.split(".")
    try:
        major = int(parts[0])
    except Exception:
        major = 0
    try:
        minor = int(parts[1])
    except Exception:
        minor = 0
    return major, minor


def is_docling_runtime_ready() -> Tuple[bool, str]:
    try:
        import torch  # type: ignore
        import torchvision  # type: ignore  # noqa: F401
    except Exception as exc:
        return False, f"torch/torchvision indisponiveis: {exc}"

    major, minor = _parse_major_minor(getattr(torch, "__version__", "0.0"))
    if (major, minor) < (2, 4):
        return False, f"torch {torch.__version__} (<2.4)"
    return True, "ok"


def process_text_pdf(path: Path) -> Dict[str, Any]:
    runtime_ok, reason = is_docling_runtime_ready()
    if not runtime_ok:
        print(f"[WARN] Docling desativado para {path.name}: {reason}. Usando PyMuPDF.")
        result = process_text_pdf_with_pymupdf(path)
        result["fallback_reason"] = reason
        return result

    try:
        return process_with_docling(path)
    except Exception as exc:
        print(f"[WARN] Docling falhou para {path.name}. Usando fallback PyMuPDF. Erro: {exc}")
        result = process_text_pdf_with_pymupdf(path)
        result["fallback_reason"] = str(exc)
        return result


def load_image(path: Path) -> np.ndarray:
    image = cv2.imread(path.as_posix())
    if image is None:
        # fallback Pillow para formatos menos comuns
        pil = Image.open(path)
        image = cv2.cvtColor(np.array(pil.convert("RGB")), cv2.COLOR_RGB2BGR)
    return image


def process_image_pipeline(
    image_bgr: np.ndarray,
    reader: Any,
    tesseract_lang: str = "por",
) -> Dict[str, Any]:
    kind = classify_image_type(image_bgr, reader, tesseract_lang=tesseract_lang)
    label = kind["label"]

    if label == "typed":
        extracted = ocr_tesseract(image_bgr, lang=tesseract_lang)
    elif label == "handwritten":
        extracted = ocr_easyocr(image_bgr, reader)
    else:
        extracted = ocr_hybrid_by_blocks(image_bgr, reader, tesseract_lang=tesseract_lang)

    return {
        "image_classification": kind,
        "extraction": extracted,
    }


def process_document(
    path: Path,
    tesseract_lang: str = "por",
    easyocr_langs: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    payload: Dict[str, Any] = {
        "file": path.name,
        "path": path.as_posix(),
        "type": "pdf" if suffix == ".pdf" else "image",
    }

    if suffix == ".pdf":
        pdf_class = classify_pdf(path)
        print(f"[INFO] {path.name}: PDF classificado como '{pdf_class.mode}' com {pdf_class.txtblocks} blocos de texto e {pdf_class.imgblocks} blocos de imagem.")
        payload["pdf_classification"] = asdict(pdf_class)
        if pdf_class.mode == "text":
            payload["pipeline"] = "text-extraction"
            payload["result"] = process_text_pdf(path)
        else:
            langs = easyocr_langs or ("pt", "en")
            reader = get_easyocr_reader(langs)
            pages = render_pdf_pages_as_images(path, dpi=300)
            page_results = []
            for i, image in enumerate(pages, start=1):
                page_results.append(
                    {
                        "page": i,
                        **process_image_pipeline(image, reader, tesseract_lang=tesseract_lang),
                    }
                )
            payload["pipeline"] = "image-ocr"
            payload["pages"] = page_results
    else:
        langs = easyocr_langs or ("pt", "en")
        reader = get_easyocr_reader(langs)
        image = load_image(path)
        payload["pipeline"] = "image-ocr"
        payload["result"] = process_image_pipeline(image, reader, tesseract_lang=tesseract_lang)

    return payload


def list_supported_inputs(input_path: Path) -> List[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.exists():
        raise FileNotFoundError(f"Caminho nao encontrado: {input_path}")
    supported = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
    files = [p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() in supported]
    return sorted(files, key=lambda p: p.name.lower())


def resolve_tesseract_lang(requested_lang: str) -> str:
    try:
        available = set(pytesseract.get_languages(config=""))
    except Exception:
        return requested_lang

    if requested_lang in available:
        return requested_lang
    if "eng" in available:
        print(f"[WARN] Idioma '{requested_lang}' nao encontrado no Tesseract. Usando 'eng'.")
        return "eng"
    fallback = sorted(available)[0] if available else requested_lang
    print(f"[WARN] Idioma '{requested_lang}' nao encontrado no Tesseract. Usando '{fallback}'.")
    return fallback


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline local de testes OCR")
    parser.add_argument("--input", required=True, help="Arquivo ou pasta de entrada")
    parser.add_argument("--output-dir", default="data/output_json", help="Diretorio de saida para JSON")
    parser.add_argument("--easyocr-langs", default="pt,en", help="Idiomas EasyOCR separados por virgula")
    parser.add_argument("--tesseract-lang", default="por", help="Idioma do Tesseract (ex: por, eng)")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    langs = [s.strip() for s in args.easyocr_langs.split(",") if s.strip()]
    tesseract_lang = resolve_tesseract_lang(args.tesseract_lang)

    files = list_supported_inputs(input_path)
    if not files:
        raise SystemExit("Nenhum arquivo suportado encontrado no caminho informado.")

    for file_path in files:
        try:
            result = process_document(file_path, tesseract_lang=tesseract_lang, easyocr_langs=langs)
            out_file = output_dir / f"{file_path.name}.ocr_test.json"
            out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] {file_path.name} -> {out_file}")
        except Exception as exc:
            print(f"[ERRO] {file_path.name}: {exc}")


if __name__ == "__main__":
    main()
