#!/usr/bin/env python3
"""Pipeline OCR com olmOCR em container (API OpenAI-compatible).

Regras:
1) classify_pdf para decidir texto vs imagem.
2) PDF textual: Docling com fallback PyMuPDF.
3) PDF imagem ou arquivo de imagem: envia para API do container olmOCR.
4) Salva JSON no diretorio indicado.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shlex
import subprocess
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
    print(f"[STEP] Classificando PDF: {pdf_path.name}")
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
            fname = font[3]
            if fname not in docfonts:
                docfonts.append(fname)

    nr_pages = len(doc)
    doc.close()
    mode = "text" if txtblocks > 0 and txtblocks >= imgblocks else "image"
    return PdfClassification(nr_pages, txtblocks, imgblocks, docfonts, mode)


def process_with_docling(path: Path) -> Dict[str, Any]:
    global DocumentConverter
    print(f"[STEP] Extraindo texto com Docling: {path.name}")
    if DocumentConverter is None:
        from docling.document_converter import DocumentConverter as DoclingConverter

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
    print(f"[STEP] Extraindo texto com fallback PyMuPDF: {path.name}")
    doc = fitz.open(path.as_posix())
    pages: List[str] = []
    for page in doc:
        pages.append((page.get_text("text") or "").strip())
    doc.close()
    text = "\n\n".join([p for p in pages if p]).strip()
    return {
        "engine": "pymupdf",
        "text": text,
        "preview": text[:500],
    }


def process_text_pdf(path: Path) -> Dict[str, Any]:
    try:
        return process_with_docling(path)
    except Exception as exc:
        print(f"[WARN] Docling falhou para {path.name}. Motivo: {exc}")
        out = process_text_pdf_with_pymupdf(path)
        out["fallback_reason"] = str(exc)
        return out


def np_from_pil(img: Image.Image):
    import numpy as np

    return np.array(img)


def load_image(path: Path):
    print(f"[STEP] Carregando imagem: {path.name}")
    image = cv2.imread(path.as_posix())
    if image is None:
        pil = Image.open(path)
        image = cv2.cvtColor(np_from_pil(pil.convert("RGB")), cv2.COLOR_RGB2BGR)
    return image


def render_pdf_pages_as_images(pdf_path: Path, dpi: int = 300):
    print(f"[STEP] Renderizando PDF como imagem (dpi={dpi}): {pdf_path.name}")
    doc = fitz.open(pdf_path.as_posix())
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(cv2.cvtColor(np_from_pil(img), cv2.COLOR_RGB2BGR))
    doc.close()
    return pages


def to_data_url(image_bgr, ext: str = ".jpg", quality: int = 92) -> str:
    params = []
    if ext.lower() in [".jpg", ".jpeg"]:
        params = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    ok, enc = cv2.imencode(ext, image_bgr, params)
    if not ok:
        raise RuntimeError("Nao foi possivel codificar a imagem para envio.")
    b64 = base64.b64encode(enc.tobytes()).decode("ascii")
    mime = "image/jpeg" if ext.lower() in [".jpg", ".jpeg"] else "image/png"
    return f"data:{mime};base64,{b64}"


def parse_json_response(content: str) -> Dict[str, Any]:
    txt = content.strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.lower().startswith("json"):
            txt = txt[4:].strip()
    try:
        parsed = json.loads(txt)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {"parse_error": True, "raw_output": content}


def list_supported_inputs(input_path: Path) -> List[Path]:
    print(f"[STEP] Lendo entradas de: {input_path}")
    if input_path.is_file():
        return [input_path]
    if not input_path.exists():
        raise FileNotFoundError(f"Caminho nao encontrado: {input_path}")
    supported = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
    files = [f for f in input_path.iterdir() if f.is_file() and f.suffix.lower() in supported]
    files = sorted(files, key=lambda p: p.name.lower())
    print(f"[INFO] Arquivos suportados encontrados: {len(files)}")
    return files


def docker_is_running(container_name: str) -> bool:
    cmd = ["docker", "ps", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return False
    return container_name in proc.stdout.splitlines()


def ensure_olmocr_container_running(
    container_name: str,
    image_name: str,
    api_port: int,
    model_name: str,
    run_cmd_template: str,
    require_gpu: bool,
) -> None:
    if docker_is_running(container_name):
        print(f"[INFO] Container '{container_name}' ja esta em execucao.")
        return

    print(f"[STEP] Subindo container '{container_name}' com imagem '{image_name}'")
    # Servidor OpenAI-compatible via vLLM dentro do container.
    container_cmd = run_cmd_template.format(model=shlex.quote(model_name), port=8000)
    run_cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        f"{api_port}:8000",
        image_name,
        "-c",
        container_cmd,
    ]
    if require_gpu:
        run_cmd[8:8] = ["--gpus", "all"]
    proc = subprocess.run(run_cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            "Falha ao iniciar container olmOCR. "
            f"CMD={' '.join(run_cmd)} "
            f"STDOUT={proc.stdout.strip()} STDERR={proc.stderr.strip()}"
        )
    print(f"[INFO] Container iniciado: {proc.stdout.strip()}")


def ocr_with_olmocr_api(
    image_bgr,
    prompt: str,
    model: str,
    api_base: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    timeout_s: int,
    extra_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    image_data_url = to_data_url(image_bgr, ".jpg", 92)
    print(f"[STEP] Enviando requisicao OCR para API olmOCR: {api_base.rstrip('/')}/chat/completions")

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an OCR extraction model. Return only valid JSON."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            },
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }

    if extra_params:
        payload.update(extra_params)

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"{api_base.rstrip('/')}/chat/completions"
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    if resp.status_code >= 400:
        raise RuntimeError(f"Erro HTTP {resp.status_code} na API olmOCR: {resp.text[:600]}")

    body = resp.json()
    content = body["choices"][0]["message"]["content"]
    parsed = parse_json_response(content)
    return {
        "provider": "olmocr-container-api",
        "model": model,
        "api_base": api_base,
        "result": parsed,
        "raw_message": content,
    }


def process_document(
    path: Path,
    prompt: str,
    model: str,
    api_base: str,
    api_key: str,
    max_tokens: int,
    temperature: float,
    top_p: float,
    timeout_s: int,
    extra_params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    print(f"[STEP] Processando arquivo: {path.name}")
    suffix = path.suffix.lower()
    output: Dict[str, Any] = {
        "file": path.name,
        "path": path.as_posix(),
        "type": "pdf" if suffix == ".pdf" else "image",
    }

    if suffix == ".pdf":
        pdf_class = classify_pdf(path)
        output["pdf_classification"] = asdict(pdf_class)
        print(
            f"[INFO] {path.name}: modo={pdf_class.mode} "
            f"(txtblocks={pdf_class.txtblocks}, imgblocks={pdf_class.imgblocks})"
        )
        if pdf_class.mode == "text":
            output["pipeline"] = "text-extraction"
            output["result"] = process_text_pdf(path)
        else:
            output["pipeline"] = "olmocr-api"
            pages = render_pdf_pages_as_images(path, dpi=300)
            page_results = []
            for i, page_img in enumerate(pages, start=1):
                print(f"[INFO] OCR pagina {i}/{len(pages)}")
                page_results.append(
                    {
                        "page": i,
                        **ocr_with_olmocr_api(
                            page_img,
                            prompt=prompt,
                            model=model,
                            api_base=api_base,
                            api_key=api_key,
                            max_tokens=max_tokens,
                            temperature=temperature,
                            top_p=top_p,
                            timeout_s=timeout_s,
                            extra_params=extra_params,
                        ),
                    }
                )
            output["pages"] = page_results
    else:
        output["pipeline"] = "olmocr-api"
        image = load_image(path)
        output["result"] = ocr_with_olmocr_api(
            image,
            prompt=prompt,
            model=model,
            api_base=api_base,
            api_key=api_key,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            timeout_s=timeout_s,
            extra_params=extra_params,
        )
    print(f"[STEP] Arquivo finalizado: {path.name}")
    return output


def parse_extra_params(raw: str) -> Optional[Dict[str, Any]]:
    if not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--extra-params invalido: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("--extra-params deve ser um JSON objeto.")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline OCR com olmOCR (container API)")
    parser.add_argument("--input", required=True, help="Arquivo ou pasta de entrada")
    parser.add_argument("--output-dir", required=True, help="Diretorio de saida para JSON")
    parser.add_argument(
        "--prompt",
        default=(
            "Extraia fielmente todo o texto da imagem e retorne APENAS JSON valido no formato: "
            '{"extracted_text":"string","language":"string","confidence_0_1":0.0,'
            '"key_values":[{"key":"string","value":"string"}]}'
        ),
        help="Prompt enviado para o modelo OCR na API do container",
    )
    parser.add_argument("--max-tokens", type=int, default=3000, help="max_tokens da chamada de OCR")
    parser.add_argument("--temperature", type=float, default=0.0, help="temperature da chamada de OCR")
    parser.add_argument("--top-p", type=float, default=1.0, help="top_p da chamada de OCR")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout (segundos) por requisicao")
    parser.add_argument("--extra-params", default="", help="JSON string com parametros extras para payload")
    parser.add_argument(
        "--ensure-container",
        action="store_true",
        help="Se definido, tenta subir o container do olmOCR automaticamente",
    )
    args = parser.parse_args()

    if load_dotenv is not None:
        print("[STEP] Carregando variaveis do .env")
        load_dotenv()

    api_base = os.getenv("OLMOCR_API_BASE", "http://localhost:8010/v1").strip()
    api_key = os.getenv("OLMOCR_API_KEY", "").strip()
    model = os.getenv("OLMOCR_MODEL", "allenai/olmOCR-2-7B-1025-FP8").strip()
    docker_image = os.getenv("OLMOCR_DOCKER_IMAGE", "alleninstituteforai/olmocr:latest-with-model").strip()
    docker_container = os.getenv("OLMOCR_DOCKER_CONTAINER", "olmocr_api").strip()
    docker_port = int(os.getenv("OLMOCR_DOCKER_PORT", "8010").strip())
    docker_run_cmd = os.getenv(
        "OLMOCR_DOCKER_RUN_CMD",
        "vllm serve {model} --host 0.0.0.0 --port {port}",
    ).strip()
    docker_require_gpu = os.getenv("OLMOCR_REQUIRE_GPU", "1").strip().lower() not in {"0", "false", "no"}

    if args.ensure_container:
        ensure_olmocr_container_running(
            container_name=docker_container,
            image_name=docker_image,
            api_port=docker_port,
            model_name=model,
            run_cmd_template=docker_run_cmd,
            require_gpu=docker_require_gpu,
        )

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    files = list_supported_inputs(input_path)
    if not files:
        raise SystemExit("Nenhum arquivo suportado encontrado na entrada.")

    extra_params = parse_extra_params(args.extra_params)
    print(f"[STEP] Iniciando processamento de {len(files)} arquivo(s)")

    for file_path in files:
        try:
            result = process_document(
                file_path,
                prompt=args.prompt,
                model=model,
                api_base=api_base,
                api_key=api_key,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                top_p=args.top_p,
                timeout_s=args.timeout,
                extra_params=extra_params,
            )
            out_file = output_dir / f"{file_path.name}.olmocr.json"
            print(f"[STEP] Gravando JSON de saida: {out_file}")
            out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] {file_path.name} -> {out_file}")
        except Exception as exc:
            print(f"[ERRO] {file_path.name}: {exc}")


if __name__ == "__main__":
    main()
