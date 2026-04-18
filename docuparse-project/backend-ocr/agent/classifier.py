from __future__ import annotations

from typing import Dict, Tuple

import cv2
import numpy as np
import logging
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Mantemos essas 3 classes para compatibilidade total com o router atual.
# O router.py já sabe resolver engine para:
# - digital_pdf
# - scanned_image
# - handwritten_complex
CLASS_DIGITAL_PDF = "digital_pdf"
CLASS_SCANNED_IMAGE = "scanned_image"
CLASS_HANDWRITTEN_COMPLEX = "handwritten_complex"


CLASSIFICATION_ENGINE_PREPROCESSING_HINTS = {
    CLASS_DIGITAL_PDF: {
        "docling": "prefer_original_pdf",
        "llamaparse": "prefer_original_pdf",
    },
    CLASS_SCANNED_IMAGE: {
        "paddle": "natural_rgb_with_clahe_and_light_deskew",
        "easyocr": "denoise_contrast_deskew_upscale",
    },
    CLASS_HANDWRITTEN_COMPLEX: {
        "easyocr": "denoise_contrast_deskew_upscale_handwritten",
        "paddle": "natural_rgb_with_clahe_and_light_deskew",
    },
}


def classify_document(filename: str, content: bytes) -> str:
    """
    Classificador robusto por múltiplos sinais (nome + estrutura do conteúdo).

    Estratégia geral (do mais barato para o mais informativo):
    1) Heurísticas rápidas por nome/extensão;
    2) Análise estrutural do conteúdo (PDF e imagem);
    3) Decisão final com regras explícitas e fallback seguro.

    Retorno: uma das classes esperadas pelo roteador atual.
    """
    filename_lower = (filename or "").lower()
    ext = _infer_extension(filename_lower, content)

    # Sinais semânticos do próprio nome do arquivo.
    # Eles não decidem sozinhos em todos os casos, mas ajudam no desempate.
    name_signals = _extract_name_signals(filename_lower)

    if ext == "pdf":
        return _classify_pdf(content, name_signals)

    if ext in {"jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp"}:
        return _classify_image(content, name_signals)

    # Se a extensão não é confiável, tentamos primeiro como PDF, depois imagem.
    # Isso reduz erro quando o arquivo vem sem extensão correta.
    if content.startswith(b"%PDF"):
        return _classify_pdf(content, name_signals)

    maybe_image = _decode_image(content)
    if maybe_image is not None:
        return _classify_image(content, name_signals)

    # Fallback conservador: desconhecido tende a fluxo OCR padrão do sistema.
    return CLASS_SCANNED_IMAGE


def get_engine_preprocessing_hints_for_class(classification: str) -> Dict[str, str]:
    return dict(CLASSIFICATION_ENGINE_PREPROCESSING_HINTS.get(classification, {}))


def _classify_pdf(content: bytes, name_signals: Dict[str, bool]) -> str:
    """
    Classifica PDFs usando combinação de:
    - presença de camada textual real;
    - características visuais de página renderizada (estrutura de tabela, densidade de arestas);
    - sinais de manuscrito/complexidade.
    """
    try:
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(content)
        page_count = len(pdf)
        if page_count == 0:
            return CLASS_SCANNED_IMAGE

        # Amostragem curta para manter latência baixa no início do pipeline.
        pages_to_sample = min(page_count, 2)
        text_chars_total = 0
        table_score_total = 0.0
        handwriting_score_total = 0.0
        image_like_pages = 0

        for page_idx in range(pages_to_sample):
            page = pdf.get_page(page_idx)

            # 1) Camada textual do PDF (quando existe texto digital embutido).
            text_page = page.get_textpage()
            text = text_page.get_text_bounded() or ""
            text_chars_total += len(text.strip())

            # 2) Renderiza página para análise visual rápida com OpenCV.
            rendered = page.render(scale=1.5)
            rgb_image = np.array(rendered.to_pil())
            bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
            visual_features = _extract_visual_features(bgr_image)

            table_score_total += visual_features["table_score"]
            handwriting_score_total += visual_features["handwriting_score"]
            if visual_features["is_image_like"]:
                image_like_pages += 1

        logger.info(f"text_chars_total : {text_chars_total:.3f}")

        logger.info(f"table_score_total total: {table_score_total:.3f}")
        logger.info(f"handwriting_score_total total: {handwriting_score_total:.3f}")
        logger.info(f"image_like_pages total: {image_like_pages}")

        avg_table_score = table_score_total / pages_to_sample
        avg_handwriting_score = handwriting_score_total / pages_to_sample
        image_like_ratio = image_like_pages / pages_to_sample

        logger.info(f"Score table: {avg_table_score:.3f}")
        logger.info(f"Score handwriting: {avg_handwriting_score:.3f}")
        logger.info(f"Image-like page ratio: {image_like_ratio:.2f}")

        # Guarda de alta confiança para PDF digital estruturado:
        # quando existe muito texto extraível + sinais de estrutura tabular,
        # classificamos como digital para evitar falso positivo de manuscrito.
        if (
            text_chars_total >= 800
            and image_like_ratio <= 0.25
            and (
                avg_table_score >= 0.015
                or name_signals["table"]
            )
            and not name_signals["handwritten"]
        ):
            logger.info(f"\nLinha 1 CLASS_DIGITAL_PDF by text_chars_total: {text_chars_total}\n")
            return CLASS_DIGITAL_PDF

        # Decisor explícito:
        # A) Fortes sinais de manuscrito/complexidade -> handwritten_complex.
        #    Requeremos um limiar mais alto para reduzir falso-positivo em PDFs
        #    com estrutura tabular densa (ex.: nota fiscal bem formatada).
        if name_signals["handwritten"] or (
            avg_handwriting_score >= 0.68 and text_chars_total < 900
        ):
            logger.info(f"\nLinha 1 PDF classified as HANDWRITTEN_COMPLEX by handwriting_score: {avg_handwriting_score:.3f}\n")
            return CLASS_HANDWRITTEN_COMPLEX

        # B) PDF digital estruturado (texto + grade/tabular) tende a ser documento
        #    impresso/computadorizado, não manuscrito.
        if (
            text_chars_total >= 60
            and avg_table_score >= 0.030
            and avg_handwriting_score < 0.62
        ):
            logger.info(f"\nLinha 2 CLASS_DIGITAL_PDF by text_chars_total: {text_chars_total}\n")
            return CLASS_DIGITAL_PDF

        # C) PDF com texto digital significativo e sem forte sinal de complexidade.
        if text_chars_total >= 120 and avg_handwriting_score < 0.58:
            logger.info(f"\nLinha 3 CLASS_DIGITAL_PDF by text_chars_total: {text_chars_total}\n")
            return CLASS_DIGITAL_PDF

        # C.1) PDF com baixo texto extraível e sinal de arquivo escaneado/fotografado.
        #      Este caso cobre PDFs que "empacotam" uma foto do documento,
        #      onde o parser extrai poucos caracteres e poderia cair no fallback digital.
        #      Regra focada para reduzir impacto em outros tipos de PDF.
        if name_signals["scanned"] and text_chars_total < 80:
            if name_signals["mixed"] or avg_handwriting_score >= 0.38:
                logger.info(
                    "\nLinha 3.1 PDF classified as HANDWRITTEN_COMPLEX (low text + scanned signal): %.3f\n",
                    avg_handwriting_score,
                )
                return CLASS_HANDWRITTEN_COMPLEX

            logger.info("\nLinha 3.1 PDF classified as SCANNED_IMAGE (low text + scanned signal)\n")
            return CLASS_SCANNED_IMAGE

        # D) PDF predominantemente imagem (escaneado/foto embutida).
        if text_chars_total < 40 and image_like_ratio >= 0.5:
            # Se também houver indícios de manuscrito/complexidade, sobe categoria.
            if name_signals["mixed"] or avg_handwriting_score >= 0.62:
                logger.info(f"\nLinha 2 PDF classified as HANDWRITTEN_COMPLEX by handwriting_score: {avg_handwriting_score:.3f}\n")
                return CLASS_HANDWRITTEN_COMPLEX
            return CLASS_SCANNED_IMAGE

        # E) Casos híbridos (texto + imagem, formulário, assinatura etc.).
        #    Exigimos sinal mais forte para manuscrito quando houver estrutura tabular,
        #    evitando classificar nota fiscal limpa como complexa.
        if (
            (name_signals["mixed"] and avg_handwriting_score >= 0.56)
            or avg_handwriting_score >= 0.62
        ):
            logger.info(f"Linha 3 PDF classified as HANDWRITTEN_COMPLEX by handwriting_score: {avg_handwriting_score:.3f}")
            return CLASS_HANDWRITTEN_COMPLEX

        # F) Padrão para PDF sem sinais fortes de complexidade.
        #    Tabela sozinha não muda categoria, mas pode orientar engine futuramente.
        _ = avg_table_score  # Mantido para extensões futuras de roteamento.
        logger.info(f"\nLinha 4 CLASS_DIGITAL_PDF by text_chars_total: {text_chars_total}\n")
        return CLASS_DIGITAL_PDF

    except Exception:
        # Fallback resiliente: se falhar parsing PDF, inferimos por sinais do nome.
        if name_signals["handwritten"] or name_signals["mixed"]:
            logger.info("Linha 4 PDF classified as HANDWRITTEN_COMPLEX by name signal fallback")
            return CLASS_HANDWRITTEN_COMPLEX
        return CLASS_SCANNED_IMAGE


def _classify_image(content: bytes, name_signals: Dict[str, bool]) -> str:
    """
    Classifica arquivos de imagem por sinais visuais e semânticos.

    Regras principais:
    - manuscrito explícito por nome -> handwritten_complex;
    - imagem com traços irregulares/baixa linearidade -> tende a manuscrito/complexo;
    - caso contrário -> scanned_image.
    """
    image = _decode_image(content)
    if image is None:
        if name_signals["handwritten"] or name_signals["mixed"]:
            logger.info("Linha 5 IMAGE classified as HANDWRITTEN_COMPLEX by name signal fallback")
            return CLASS_HANDWRITTEN_COMPLEX
        return CLASS_SCANNED_IMAGE

    visual_features = _extract_visual_features(image)

    if name_signals["handwritten"]:
        logger.info(f"Linha 6 IMAGE classified as HANDWRITTEN_COMPLEX by handwriting_score: {visual_features['handwriting_score']:.3f}")
        return CLASS_HANDWRITTEN_COMPLEX

    # Documento com fotografia/manuscrito/mistura tende a ter score de manuscrito maior.
    if name_signals["mixed"] and visual_features["handwriting_score"] >= 0.40:
        logger.info(f"Linha 7 IMAGE classified as HANDWRITTEN_COMPLEX by handwriting_score: {visual_features['handwriting_score']:.3f}")
        return CLASS_HANDWRITTEN_COMPLEX

    if visual_features["handwriting_score"] >= 0.60:
        logger.info(f"Linha 8 IMAGE classified as HANDWRITTEN_COMPLEX by handwriting_score: {visual_features['handwriting_score']:.3f}")
        return CLASS_HANDWRITTEN_COMPLEX

    return CLASS_SCANNED_IMAGE


def _extract_name_signals(filename_lower: str) -> Dict[str, bool]:
    """Extrai indícios semânticos do nome para auxiliar o decisor."""
    handwritten_tokens = {
        "manuscrito",
        "handwritten",
        "assinatura",
        "signature",
        "anotacao",
        "anotação",
    }
    scanned_tokens = {
        "scan",
        "scanned",
        "digitalizado",
        "foto",
        "image",
        "camera",
        "print",
    }
    table_tokens = {
        "tabela",
        "table",
        "invoice",
        "fatura",
        "nota",
        "extrato",
        "statement",
    }
    mixed_tokens = {
        "misto",
        "mixed",
        "hibrido",
        "híbrido",
        "completo",
        "complex",
    }

    tokens = set(filename_lower.replace("-", " ").replace("_", " ").split())
    full_name = filename_lower

    def has_any(candidates: set[str]) -> bool:
        return any(token in tokens for token in candidates) or any(token in full_name for token in candidates)

    return {
        "handwritten": has_any(handwritten_tokens),
        "scanned": has_any(scanned_tokens),
        "table": has_any(table_tokens),
        "mixed": has_any(mixed_tokens),
    }


def _infer_extension(filename_lower: str, content: bytes) -> str:
    """Infere extensão com fallback por assinatura de bytes."""
    if "." in filename_lower:
        ext = filename_lower.rsplit(".", maxsplit=1)[-1]
        if ext:
            return ext

    if content.startswith(b"%PDF"):
        return "pdf"

    return ""


def _decode_image(content: bytes) -> np.ndarray | None:
    """Decodifica bytes de imagem com OpenCV de forma segura."""
    arr = np.frombuffer(content, dtype=np.uint8)
    if arr.size == 0:
        return None

    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return image


def _extract_visual_features(image_bgr: np.ndarray) -> Dict[str, float | bool]:
    """
    Extrai um conjunto pequeno de features visuais robustas e baratas.

    Features:
    - edge_density: quantidade de bordas (Canny);
    - line_density: quantidade de linhas retas (Hough), útil para docs impressos/tabelas;
    - table_score: força de linhas horizontais/verticais (estrutura tabular);
    - handwriting_score: proxy para traço irregular e baixa linearidade.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    # Normalização para reduzir impacto de contraste/iluminação.
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    edges = cv2.Canny(gray, threshold1=80, threshold2=180)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)

    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=120,
        minLineLength=max(30, int(min(gray.shape[:2]) * 0.15)),
        maxLineGap=8,
    )
    line_count = 0 if lines is None else len(lines)
    line_density = float(line_count) / max(1.0, (gray.shape[0] * gray.shape[1]) / 10000.0)

    # Score de tabela: interseção de linhas horizontais + verticais após binarização.
    bin_img = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        10,
    )
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, gray.shape[1] // 30), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, gray.shape[0] // 30)))
    h_lines = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, v_kernel)
    table_mask = cv2.bitwise_or(h_lines, v_lines)
    table_score = float(np.count_nonzero(table_mask)) / float(table_mask.size)

    # Heurística de manuscrito:
    # - manuscrito costuma ter menos linhas longas e mais traço irregular/disperso.
    # - usamos uma combinação leve de sinais para não depender de um único critério.
    contour_count, _ = _count_components(bin_img)

    # Normalização robusta:
    # a contagem de componentes cresce muito em documentos digitais com muito texto.
    # Se usado "cru", isso satura o score para 1.0 indevidamente.
    contour_density_raw = float(contour_count) / max(1.0, (gray.shape[0] * gray.shape[1]) / 10000.0)
    contour_density = _clip01(contour_density_raw / 10.0)

    line_density_norm = _clip01(line_density / 1.2)
    table_score_norm = _clip01(table_score / 0.08)
    edge_density_norm = _clip01((edge_density - 0.01) / 0.15)

    handwriting_score = _clip01(
        (edge_density_norm * 0.35) +
        (contour_density * 0.40) -
        (line_density_norm * 0.35) -
        (table_score_norm * 0.25)
    )

    is_image_like = edge_density > 0.015 and line_density < 0.25

    return {
        "edge_density": edge_density,
        "line_density": line_density,
        "table_score": table_score,
        "handwriting_score": handwriting_score,
        "is_image_like": is_image_like,
    }


def _count_components(binary_image: np.ndarray) -> Tuple[int, np.ndarray]:
    """Conta componentes conectados úteis para medir fragmentação de traços."""
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_image, connectivity=8)

    # Ignora componente de fundo e ruído muito pequeno.
    valid = 0
    for idx in range(1, num_labels):
        area = stats[idx, cv2.CC_STAT_AREA]
        if area >= 12:
            valid += 1

    return valid, labels


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
