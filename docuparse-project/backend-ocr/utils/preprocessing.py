# =============================================================================
# BACKWARD-COMPAT SHIM — Fase 2 do refactor de arquitetura.
#
# A lógica foi movida para shared/preprocessing.py.
# Este arquivo existe apenas para não quebrar imports existentes, como:
#   from utils.preprocessing import decode_image, preprocess_for_paddle_engine, ...
#
# __all__ declara explicitamente que estes são re-exports intencionais,
# suprimindo hints de "symbol not accessed" no linter/type-checker.
#
# Será removido na Fase 7 (limpeza final).
# =============================================================================

from shared.preprocessing import (
    decode_image,
    encode_png_bytes,
    deskew_simple,
    warp_perspective_if_photo,
    crop_document_roi,
    crop_margins_light,
    apply_clahe_local_contrast,
    equalize_illumination,
    denoise_light,
    denoise_moderate,
    gaussian_light,
    sharpen_moderate,
    enhance_blue_ink_light,
    upscale_if_low_resolution,
    preprocess_for_trocr_region,
    preprocess_for_trocr_engine,
    preprocess_for_paddle_engine,
    preprocess_for_easyocr_engine,
    preprocess_for_deepseek_engine,
    preprocess_for_docling_engine,
    preprocess_for_llamaparse_engine,
    segment_handwritten_regions,
    segment_text_lines,
    preprocess_scanned,
    preprocess_photo,
    preprocess_handwritten,
    preprocess_digital_pdf,
    preprocess_image,
)

# Re-exports explícitos: informa linters e type-checkers que estes símbolos
# são públicos deste módulo, não imports internos não utilizados.
__all__ = [
    "decode_image",
    "encode_png_bytes",
    "deskew_simple",
    "warp_perspective_if_photo",
    "crop_document_roi",
    "crop_margins_light",
    "apply_clahe_local_contrast",
    "equalize_illumination",
    "denoise_light",
    "denoise_moderate",
    "gaussian_light",
    "sharpen_moderate",
    "enhance_blue_ink_light",
    "upscale_if_low_resolution",
    "preprocess_for_trocr_region",
    "preprocess_for_trocr_engine",
    "preprocess_for_paddle_engine",
    "preprocess_for_easyocr_engine",
    "preprocess_for_deepseek_engine",
    "preprocess_for_docling_engine",
    "preprocess_for_llamaparse_engine",
    "segment_handwritten_regions",
    "segment_text_lines",
    "preprocess_scanned",
    "preprocess_photo",
    "preprocess_handwritten",
    "preprocess_digital_pdf",
    "preprocess_image",
]
