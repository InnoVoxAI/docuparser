import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from ..agent.classifier import classify_document
from ..engines.tesseract_engine import TesseractEngine
from ..main import app


client = TestClient(app)


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def _load_input_as_image_bytes(input_path: Path) -> tuple[bytes, dict]:
    suffix = input_path.suffix.lower()

    if suffix in SUPPORTED_IMAGE_EXTENSIONS:
        return input_path.read_bytes(), {
            "input_type": "image",
            "source_extension": suffix,
            "rendered_from_pdf": False,
        }

    if suffix == ".pdf":
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError(
                "PDF input requires pypdfium2. Install with: pip install pypdfium2"
            ) from exc

        pdf = pdfium.PdfDocument(str(input_path))
        if len(pdf) == 0:
            raise ValueError(f"PDF has no pages: {input_path}")

        page = pdf.get_page(0)
        bitmap = page.render(scale=2.0)
        pil_image = bitmap.to_pil()

        image_rgb = np.array(pil_image)
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        ok, encoded = cv2.imencode(".png", image_bgr)
        if not ok:
            raise ValueError("Could not convert PDF page to image bytes")

        return encoded.tobytes(), {
            "input_type": "pdf",
            "source_extension": suffix,
            "rendered_from_pdf": True,
            "rendered_page": 1,
            "pdf_page_count": len(pdf),
        }

    raise ValueError(
        f"Unsupported file extension: {suffix}. Supported: PDF and image formats {sorted(SUPPORTED_IMAGE_EXTENSIONS)}"
    )


def run_workflow(
    input_path: Path, save_preprocessed: bool = False, also_test_api: bool = False
) -> dict:
    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    original_bytes = input_path.read_bytes()
    image_bytes, input_meta = _load_input_as_image_bytes(input_path)

    classification = classify_document(input_path.name, original_bytes)

    engine = TesseractEngine()
    preprocessed = engine.preprocess_for_classification(image_bytes=image_bytes, classification=classification)

    if save_preprocessed:
        output_img = input_path.with_name(f"{input_path.stem}_preprocessed.png")
        cv2.imwrite(str(output_img), preprocessed)

    ocr_result = engine.process({"original": image_bytes, "preprocessed": preprocessed})

    api_result = None
    if also_test_api:
        mime_type = "application/pdf" if input_path.suffix.lower() == ".pdf" else "image/png"
        with input_path.open("rb") as file_handle:
            response = client.post(
                "/process",
                files={"file": (input_path.name, file_handle, mime_type)},
            )
        api_result = {
            "status_code": response.status_code,
            "response_json": response.json() if response.status_code == 200 else None,
            "response_text": response.text if response.status_code != 200 else None,
        }

    return {
        "input_file": str(input_path),
        "input_meta": input_meta,
        "classification": classification,
        "preprocessing": {
            "status": "ok",
            "shape": list(preprocessed.shape),
            "dtype": str(preprocessed.dtype),
        },
        "ocr_engine": "tesseract",
        "ocr_result": ocr_result,
        "api_current_flow": api_result,
        "note": (
            "This script validates the same classify + preprocess + Tesseract flow used by the API router."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a simple OCR flow: classify -> preprocess -> Tesseract"
    )
    parser.add_argument(
        "--input-path",
        default="",
        help="Input file path (supports PDF and image files)",
    )
    parser.add_argument(
        "--save-preprocessed",
        action="store_true",
        help="Save preprocessed image next to input image",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional output JSON file path",
    )
    parser.add_argument(
        "--also-test-api",
        action="store_true",
        help="Also run current /process API flow with TestClient for comparison",
    )
    args = parser.parse_args()

    # if args.input_path:
    #     input_path = Path(args.input_path).expanduser().resolve()
    # else:
        
    input_path = Path(
        "/home/gpcmoura/Documents/Work/InnoVox/Repositories/docuparser/docuparse-project/backend-ocr/tests/pdf/Recibo  digitalizado com manuscrito assinatura.pdf"
    )

    result = run_workflow(
        input_path=input_path,
        save_preprocessed=args.save_preprocessed,
        also_test_api=args.also_test_api,
    )

    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    print(output_json)

    if args.output_json:
        output_path = Path(args.output_json).expanduser().resolve()
    else:
        output_dir = Path(__file__).resolve().parent / "results"
        engine_name = str(result.get("ocr_engine", "unknown")).strip().lower()
        engine_folder = {
            "tesseract": "Tesseract",
            "easyocr": "EasyOCR",
            "docling": "Docling",
            "deepseek": "DeepSeek",
            "llamaparse": "LlamaParse",
        }.get(engine_name, engine_name.capitalize() if engine_name else "Unknown")
        output_dir = output_dir / engine_folder
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}_{engine_name}_result.json"

    output_path.write_text(output_json, encoding="utf-8")
    print(f"\nSaved output JSON to: {output_path}")


if __name__ == "__main__":
    main()
