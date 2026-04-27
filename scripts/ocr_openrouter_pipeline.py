#!/usr/bin/env python3
"""Pipeline OCR com OpenRouter + fallback local para PDFs textuais.

Fluxo:
1) Classifica PDF com PyMuPDF (texto vs imagem).
2) PDF textual usa Docling, com fallback para PyMuPDF.
3) PDF imagem (ou imagem) usa OpenRouter (LLM com visao) para OCR.
4) Retorna resultado em JSON.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import fitz  # pymupdf
import requests
from PIL import Image

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

DocumentConverter = None


@dataclass
class PdfClassification:
    nr_pages: int
    txtblocks: int
    imgblocks: int
    docfonts: List[str]
    mode: str  # "text" | "image"


def classify_pdf(pdf_path: Path) -> PdfClassification:
    print(f"[STEP] Classificando PDF com PyMuPDF: {pdf_path.name}")
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

    mode = "text" if txtblocks > 0 and txtblocks >= imgblocks else "image"
    return PdfClassification(
        nr_pages=nr_pages,
        txtblocks=txtblocks,
        imgblocks=imgblocks,
        docfonts=docfonts,
        mode=mode,
    )


def render_pdf_pages_as_images(pdf_path: Path, dpi: int = 300) -> List[Any]:
    print(f"[STEP] Renderizando paginas do PDF em imagem (dpi={dpi}): {pdf_path.name}")
    doc = fitz.open(pdf_path.as_posix())
    images: List[Any] = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(cv2.cvtColor(np_from_pil(img), cv2.COLOR_RGB2BGR))
    doc.close()
    return images


def np_from_pil(img: Image.Image):
    import numpy as np

    return np.array(img)


def process_with_docling(path: Path) -> Dict[str, Any]:
    global DocumentConverter
    print(f"[STEP] Extraindo PDF textual com Docling: {path.name}")
    if DocumentConverter is None:
        print("[INFO] Carregando DocumentConverter do Docling...")
        from docling.document_converter import DocumentConverter as DoclingConverter

        DocumentConverter = DoclingConverter

    converter = DocumentConverter()
    result = converter.convert(path.as_posix())
    markdown = result.document.export_to_markdown()
    return {"engine": "docling", "text": markdown, "preview": markdown[:500]}


def process_text_pdf_with_pymupdf(path: Path) -> Dict[str, Any]:
    print(f"[STEP] Extraindo PDF textual com fallback PyMuPDF: {path.name}")
    doc = fitz.open(path.as_posix())
    pages: List[str] = []
    for page in doc:
        pages.append((page.get_text("text") or "").strip())
    doc.close()
    text = "\n\n".join(t for t in pages if t).strip()
    return {"engine": "pymupdf", "text": text, "preview": text[:500]}


def process_text_pdf(path: Path) -> Dict[str, Any]:
    try:
        return process_with_docling(path)
    except Exception as exc:
        print(f"[WARN] Docling falhou para {path.name}. Usando fallback PyMuPDF. Erro: {exc}")
        result = process_text_pdf_with_pymupdf(path)
        result["fallback_reason"] = str(exc)
        return result


def load_image(path: Path):
    print(f"[STEP] Carregando imagem: {path.name}")
    image = cv2.imread(path.as_posix())
    if image is None:
        pil = Image.open(path)
        image = cv2.cvtColor(np_from_pil(pil.convert("RGB")), cv2.COLOR_RGB2BGR)
    return image


def cv2_image_to_data_url(image_bgr, image_format: str = ".jpg", jpeg_quality: int = 90) -> str:
    params = []
    if image_format.lower() in (".jpg", ".jpeg"):
        params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
    ok, encoded = cv2.imencode(image_format, image_bgr, params)
    if not ok:
        raise RuntimeError("Falha ao converter imagem para bytes.")
    b64 = base64.b64encode(encoded.tobytes()).decode("ascii")
    mime = "image/jpeg" if image_format.lower() in (".jpg", ".jpeg") else "image/png"
    return f"data:{mime};base64,{b64}"


def parse_json_from_model_output(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {
        "parse_error": True,
        "raw_output": text,
    }


def ocr_with_openrouter(image_bgr, page_label: str, timeout_s: int = 120) -> Dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    model = os.getenv("OPENROUTER_MODEL", "").strip()
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    site_url = os.getenv("OPENROUTER_SITE_URL", "").strip()
    app_name = os.getenv("OPENROUTER_APP_NAME", "ocr-openrouter-pipeline").strip()

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY nao definido no .env")
    if not model:
        raise RuntimeError("OPENROUTER_MODEL nao definido no .env")

    print(f"[STEP] Executando OCR via OpenRouter na pagina/bloco: {page_label}")
    print(f"[INFO] Modelo OpenRouter: {model}")

    data_url = cv2_image_to_data_url(image_bgr, image_format=".jpg", jpeg_quality=90)

    instruction = (
        "Voce e um OCR. Extraia fielmente todo o texto visivel da imagem, preservando ordem de leitura. "
        "Retorne APENAS JSON valido com este schema: "
        '{"page":"string","extracted_text":"string","language":"string","confidence_0_1":"number",'
        '"key_values":[{"key":"string","value":"string"}]}. '
        "Se nao houver texto, retorne extracted_text vazio e confidence_0_1 0."
    )

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You are a precise OCR extraction engine."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {"type": "text", "text": f"Identificador da pagina: {page_label}"},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if site_url:
        headers["HTTP-Referer"] = site_url
    if app_name:
        headers["X-Title"] = app_name

    url = f"{base_url.rstrip('/')}/chat/completions"
    print(f"[INFO] Enviando requisicao para OpenRouter: {url}")
    response = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    if response.status_code >= 400:
        raise RuntimeError(f"OpenRouter erro HTTP {response.status_code}: {response.text[:500]}")
    body = response.json()
    content = body["choices"][0]["message"]["content"]
    parsed = parse_json_from_model_output(content)
    print(f"[STEP] Resposta OCR recebida para {page_label}")
    return {
        "provider": "openrouter",
        "model": model,
        "page": page_label,
        "result": parsed,
    }


def process_document(path: Path, timeout_s: int = 120) -> Dict[str, Any]:
    print(f"[STEP] Iniciando processamento do arquivo: {path.name}")
    suffix = path.suffix.lower()
    payload: Dict[str, Any] = {
        "file": path.name,
        "path": path.as_posix(),
        "type": "pdf" if suffix == ".pdf" else "image",
    }

    if suffix == ".pdf":
        pdf_class = classify_pdf(path)
        payload["pdf_classification"] = asdict(pdf_class)
        print(
            f"[INFO] {path.name}: PDF classificado como '{pdf_class.mode}' "
            f"com {pdf_class.txtblocks} blocos de texto e {pdf_class.imgblocks} blocos de imagem."
        )

        if pdf_class.mode == "text":
            print(f"[STEP] Roteando {path.name} para pipeline textual (Docling/PyMuPDF)")
            payload["pipeline"] = "text-extraction"
            payload["result"] = process_text_pdf(path)
        else:
            print(f"[STEP] Roteando {path.name} para pipeline OCR por imagem (OpenRouter)")
            payload["pipeline"] = "openrouter-ocr"
            pages = render_pdf_pages_as_images(path, dpi=300)
            page_results = []
            for i, image in enumerate(pages, start=1):
                page_label = f"page_{i}"
                print(f"[INFO] Processando pagina {i}/{len(pages)}")
                page_results.append(ocr_with_openrouter(image, page_label, timeout_s=timeout_s))
            payload["pages"] = page_results
    else:
        print(f"[STEP] Arquivo de imagem detectado. Usando pipeline OpenRouter OCR: {path.name}")
        payload["pipeline"] = "openrouter-ocr"
        image = load_image(path)
        payload["result"] = ocr_with_openrouter(image, "image_1", timeout_s=timeout_s)

    print(f"[STEP] Finalizado processamento do arquivo: {path.name}")
    return payload


def list_supported_inputs(input_path: Path) -> List[Path]:
    print(f"[STEP] Listando entradas suportadas em: {input_path}")
    if input_path.is_file():
        print("[INFO] Entrada unica detectada.")
        return [input_path]
    if not input_path.exists():
        raise FileNotFoundError(f"Caminho nao encontrado: {input_path}")
    supported = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
    files = [p for p in input_path.iterdir() if p.is_file() and p.suffix.lower() in supported]
    print(f"[INFO] Total de arquivos suportados encontrados: {len(files)}")
    return sorted(files, key=lambda p: p.name.lower())


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline OCR com OpenRouter")
    parser.add_argument("--input", required=True, help="Arquivo ou pasta de entrada")
    parser.add_argument("--output-dir", default="data/output_json", help="Diretorio de saida para JSON")
    parser.add_argument("--timeout", type=int, default=120, help="Timeout em segundos por chamada OpenRouter")
    args = parser.parse_args()

    if load_dotenv is not None:
        print("[STEP] Carregando variaveis de ambiente do .env")
        load_dotenv()
    else:
        print("[WARN] python-dotenv nao disponivel; usando variaveis de ambiente do sistema.")

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = list_supported_inputs(input_path)
    if not files:
        raise SystemExit("Nenhum arquivo suportado encontrado no caminho informado.")

    print(f"[STEP] Iniciando lote com {len(files)} arquivo(s)")
    for file_path in files:
        try:
            result = process_document(file_path, timeout_s=args.timeout)
            out_file = output_dir / f"{file_path.name}.openrouter_ocr.json"
            print(f"[STEP] Gravando resultado JSON: {out_file}")
            out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] {file_path.name} -> {out_file}")
        except Exception as exc:
            print(f"[ERRO] {file_path.name}: {exc}")


if __name__ == "__main__":
    main()
