from typing import Any, Dict, List, Tuple
import re
import unicodedata
import logging


logger = logging.getLogger(__name__)


REQUIRED_FIELDS = [
    "fornecedor",
    "tomador",
    "cnpj_fornecedor",
    "numero_nf",
    "descricao_servico",
    "valor_nf",
    "retencao",
]


FIELD_VALIDATION_KEYS = {
    "fornecedor": "fornecedor_ok",
    "tomador": "tomador_ok",
    "cnpj_fornecedor": "cnpj_fornecedor_valido",
    "cnpj_tomador": "cnpj_tomador_valido",
    "numero_nf": "numero_nf_valido",
    "descricao_servico": "descricao_ok",
    "valor_nf": "valor_valido",
    "retencao": "retencao_ok",
}


# Ajuste semântico: termos de cabeçalho que não devem virar valor de campo.
HEADER_VALUE_PATTERNS = [
    r"^tomador\s+do\s+servi[çc]o",
    r"^emitente\s+da\s+nfs-?e",
    r"^prestador\s+do\s+servi[çc]o",
    r"^cnpj\s*/\s*cpf\s*/\s*nif$",
    r"^nome\s*/\s*nome\s*empresarial$",
    r"^descri[çc][aã]o\s+do\s+servi[çc]o$",
    r"^valor\s+do\s+servi[çc]o$",
    r"^valor\s+total\s+da\s+nfs-?e$",
    r"^inscri[çc][aã]o\s+municipal$",
    r"^telefone$",
    r"^e-?mail$",
    r"^endere[çc]o$",
    r"^munic[íi]pio$",
    r"^cep$",
]


# Ajuste semântico: thresholds por campo para fallback orientado por qualidade de campo.
FIELD_CONFIDENCE_THRESHOLDS = {
    "fornecedor": 0.65,
    "tomador": 0.75,
    "cnpj_fornecedor": 0.85,
    "cnpj_tomador": 0.80,
    "numero_nf": 0.70,
    "descricao_servico": 0.65,
    "valor_nf": 0.75,
    "retencao": 0.55,
}


LOW_CONFIDENCE_THRESHOLD = 0.75


# Ajuste semântico: termos típicos de razão social/nome empresarial para priorização do tomador.
COMPANY_HINT_TOKENS = [
    "condominio",
    "edificio",
    "associados",
    "advogados",
    "ltda",
    "s/a",
    "me",
    "epp",
    "empresa",
    "comercio",
    "servicos",
]


DYNAMIC_FIELD_LABEL_STOPWORDS = {
    "nfs-e",
    "nfse",
    "danfse",
    "servico prestado",
    "tributacao municipal",
    "tributacao federal",
    "informacoes complementares",
}


NOISY_EXTRACTION_CLASSES = {"scanned_image", "handwritten_complex"}
NOISY_EXTRACTION_ENGINES = {
    "paddle",
    "paddleocr",
    "easyocr",
    "trocr",
    "handwritten_region",
    "handwritten_region_pipeline",
    "tesseract",
}


def _normalize_digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _validate_cnpj(cnpj: str | None) -> bool:
    digits = _normalize_digits(cnpj or "")
    if len(digits) != 14:
        return False

    if len(set(digits)) == 1:
        return False

    def _calc_digit(base: str, weights: List[int]) -> str:
        total = sum(int(num) * weight for num, weight in zip(base, weights))
        remainder = total % 11
        digit = 0 if remainder < 2 else 11 - remainder
        return str(digit)

    first = _calc_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = _calc_digit(digits[:12] + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])

    return digits[-2:] == f"{first}{second}"


def _get_raw_text(data: Dict[str, Any]) -> str:
    return str(data.get("raw_text") or data.get("raw_text_fallback") or "")


def _extract_line_value_by_labels(raw_text: str, labels: List[str]) -> str:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    for line in lines:
        lowered = line.lower()
        if any(label in lowered for label in labels):
            parts = re.split(r"[:\-]\s*", line, maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()

            for label in labels:
                idx = lowered.find(label)
                if idx >= 0:
                    candidate = line[idx + len(label):].strip(" :-")
                    if candidate:
                        return candidate

    return ""


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", str(line or "")).strip()


def _is_header_like_value(value: str) -> bool:
    cleaned = _clean_line(value)
    if not cleaned:
        return True

    lowered = cleaned.lower()
    for pattern in HEADER_VALUE_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return True

    # Ajuste semântico: linha curta e com tokens de metadado tende a ser cabeçalho.
    header_tokens = ["serviço", "servico", "cnpj", "cpf", "nif", "emissão", "tributação", "municipal"]
    token_hits = sum(1 for token in header_tokens if token in lowered)
    words = lowered.split()
    if len(words) <= 6 and token_hits >= 2 and not re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", cleaned):
        return True

    return False


def _is_probable_name_line(value: str) -> bool:
    cleaned = _clean_line(value)
    if not cleaned or _is_header_like_value(cleaned):
        return False

    if re.fullmatch(r"[-–—]+", cleaned):
        return False

    if re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}", cleaned):
        return False

    letters = len(re.findall(r"[A-Za-zÀ-ÿ]", cleaned))
    digits = len(re.findall(r"\d", cleaned))
    if letters < 6 or letters <= digits:
        return False

    lowered = cleaned.lower()
    # Ajuste semântico: rejeita rótulos cadastrais comuns que não são nome da parte.
    if any(
        re.search(pattern, lowered, flags=re.IGNORECASE)
        for pattern in [
            r"^inscri[çc][aã]o\s+municipal$",
            r"^telefone$",
            r"^e-?mail$",
            r"^endere[çc]o$",
            r"^munic[íi]pio$",
            r"^cep$",
        ]
    ):
        return False

    return True


def _find_first_cnpj(value: str) -> str:
    match = re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}", value or "")
    return match.group(0) if match else ""


def _unique_preserve_order(values: List[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for item in values:
        cleaned = _clean_line(item)
        if not cleaned:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _extract_regex_candidates(raw_text: str, pattern: str, group: int | None = None) -> List[str]:
    if not raw_text:
        return []

    regex = re.compile(pattern, flags=re.IGNORECASE)
    candidates: List[str] = []
    for match in regex.finditer(raw_text):
        if group is None:
            candidates.append(match.group(0))
        else:
            candidates.append(match.group(group))

    return _unique_preserve_order(candidates)


def _extract_currency_candidates(raw_text: str) -> List[str]:
    if not raw_text:
        return []

    # Prioriza valores monetários com centavos para reduzir falsos positivos.
    regex = re.compile(
        r"(?:(R\$)\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})",
        flags=re.IGNORECASE,
    )

    candidates: List[str] = []
    for match in regex.finditer(raw_text):
        currency_symbol = match.group(1)
        value = str(match.group(2) or "").strip().replace(" ", "")
        if not value:
            continue

        # Evita capturar fragmentos de CPF/CNPJ quando decimal usa ponto sem símbolo monetário.
        if "," not in value and "." in value and not currency_symbol:
            continue

        if "," in value:
            left, right = value.split(",", maxsplit=1)
            value = f"{left.replace('.', '')},{right}"

        candidates.append(value)

    return _unique_preserve_order(candidates)


def _extract_cnpj_candidates(raw_text: str) -> List[str]:
    candidates = _extract_regex_candidates(
        raw_text,
        r"(\d{2}[\.\s]?\d{3}[\.\s]?\d{3}/?\d{4}-?\d{2}|\b\d{14}\b)",
        group=1,
    )
    valid = [value for value in candidates if _validate_cnpj(value)]
    return _unique_preserve_order(valid or candidates)


def _extract_labeled_line_candidates(raw_text: str, label_patterns: List[str], max_items: int = 8) -> List[str]:
    if not raw_text:
        return []

    lines = [_clean_line(line) for line in raw_text.splitlines() if _clean_line(line)]
    compiled = [re.compile(pattern, flags=re.IGNORECASE) for pattern in label_patterns]

    results: List[str] = []
    for line in lines:
        if not any(regex.search(line) for regex in compiled):
            continue

        parts = re.split(r"[:\-–—]\s*", line, maxsplit=1)
        if len(parts) == 2 and parts[1].strip():
            results.append(parts[1].strip())
            if len(results) >= max_items:
                break
            continue

        for regex in compiled:
            matched = regex.search(line)
            if not matched:
                continue
            candidate = line[matched.end():].strip(" :-–—")
            if candidate:
                results.append(candidate)
            break

        if len(results) >= max_items:
            break

    return _unique_preserve_order(results)


def _extract_probable_name_candidates(raw_text: str, max_items: int = 6) -> List[str]:
    lines = [_clean_line(line) for line in raw_text.splitlines() if _clean_line(line)]
    if not lines:
        return []

    stop_tokens = {
        "recibo",
        "indeniz",
        "importancia",
        "importância",
        "anyscanner",
        "valor",
        "retenc",
        "reembolso",
        "nota fiscal",
        "nfs-e",
    }

    candidates: List[Tuple[str, float]] = []
    for line in lines[:40]:
        lowered = line.lower()
        if any(token in lowered for token in stop_tokens):
            continue
        if len(line) > 90:
            continue
        if not _is_probable_name_line(line):
            continue
        candidates.append((line, _score_name_candidate(line)))

    candidates.sort(key=lambda item: item[1], reverse=True)
    return _unique_preserve_order([line for line, _ in candidates[:max_items]])


def extract_fields_candidates(raw_text: str, max_candidates_per_field: int = 8) -> Dict[str, List[str]]:
    """Extrai candidatos de campos críticos via regex + heurísticas sobre raw_text."""
    text = str(raw_text or "")
    if not text.strip():
        return {}

    fornecedor_labels = [
        r"\bprestador\b",
        r"\bfornecedor\b",
        r"\bemitente\b",
        r"\brazao\s+social\b",
        r"\bnome\s+empresarial\b",
        r"\bnome\s*[:\-–—]",
    ]
    tomador_labels = [
        r"\btomador\b",
        r"\bcliente\b",
        r"\bdestinat[áa]rio\b",
        r"\bbenefici[áa]rio\b",
        r"\bsegurado\b",
        r"\bnome\s*[:\-–—]",
    ]
    descricao_labels = [
        r"\bdescri[çc][aã]o\b",
        r"\bhist[óo]rico\b",
        r"\breferente\s+a\b",
        r"\bobserva[çc][aã]o\b",
    ]

    fornecedor_candidates = _extract_labeled_line_candidates(text, fornecedor_labels, max_items=max_candidates_per_field)
    tomador_candidates = _extract_labeled_line_candidates(text, tomador_labels, max_items=max_candidates_per_field)
    descricao_candidates = _extract_labeled_line_candidates(text, descricao_labels, max_items=max_candidates_per_field)

    if not fornecedor_candidates or not tomador_candidates:
        names = _extract_probable_name_candidates(text, max_items=min(6, max_candidates_per_field))
        if not fornecedor_candidates:
            fornecedor_candidates = names
        if not tomador_candidates:
            tomador_candidates = names

    if not descricao_candidates:
        lines = [_clean_line(line) for line in text.splitlines() if _clean_line(line)]
        long_lines = [line for line in lines if 60 <= len(line) <= 600 and not _is_header_like_value(line)]
        long_lines.sort(key=len, reverse=True)
        descricao_candidates = _unique_preserve_order(long_lines[: min(3, max_candidates_per_field)])

    cnpj_candidates = _extract_cnpj_candidates(text)

    numero_nf_patterns = [
        r"\bnf\s*(?:e|nfs-?e)?\b\s*[:\-–—]?\s*([0-9]{4,})",
        r"\bnota\s+fiscal\b\s*[:\-–—]?\s*([0-9]{4,})",
        r"\bn[úu]mero\b\s*[:\-–—]?\s*([0-9]{4,})",
        r"\brecibo\b\s*(?:n[º°o]?|numero)?\s*[:\-–—]?\s*([0-9]{4,})",
    ]
    numero_nf_candidates: List[str] = []
    for pattern in numero_nf_patterns:
        numero_nf_candidates.extend(_extract_regex_candidates(text, pattern, group=1))
    numero_nf_candidates = [
        value for value in _unique_preserve_order(numero_nf_candidates)
        if 4 <= len(_normalize_digits(value)) <= 12
    ][:max_candidates_per_field]

    valor_candidates = _extract_currency_candidates(text)[:max_candidates_per_field]

    retencao_patterns = [
        r"\breten[cç][aã]o\b\s*[:\-–—]?\s*(?:R\$\s*)?(\d+[\.,]\d{2}|0[\.,]00)\b",
        r"\biss\b\s*(?:retido)?\s*[:\-–—]?\s*(?:R\$\s*)?(\d+[\.,]\d{2}|0[\.,]00)\b",
    ]
    retencao_candidates: List[str] = []
    for pattern in retencao_patterns:
        retencao_candidates.extend(_extract_regex_candidates(text, pattern, group=1))

    lowered = text.lower()
    if any(token in lowered for token in ["sem retenção", "sem retencao", "nao retido", "não retido", "isento"]):
        retencao_candidates.append("0,00")

    retencao_candidates = _unique_preserve_order(retencao_candidates)
    if not retencao_candidates and valor_candidates:
        retencao_candidates = valor_candidates[: min(3, max_candidates_per_field)]

    return {
        "fornecedor": fornecedor_candidates[:max_candidates_per_field],
        "tomador": tomador_candidates[:max_candidates_per_field],
        "cnpj_fornecedor": cnpj_candidates[:max_candidates_per_field],
        "numero_nf": numero_nf_candidates[:max_candidates_per_field],
        "descricao_servico": descricao_candidates[:max_candidates_per_field],
        "valor_nf": valor_candidates[:max_candidates_per_field],
        "retencao": retencao_candidates[:max_candidates_per_field],
    }


def _nfse_lines(raw_text: str) -> List[str]:
    return [_clean_line(line) for line in (raw_text or "").splitlines() if _clean_line(line)]


def _slice_block(lines: List[str], start_pattern: str, end_patterns: List[str]) -> List[str]:
    start_idx = -1
    for idx, line in enumerate(lines):
        if re.search(start_pattern, line, flags=re.IGNORECASE):
            start_idx = idx
            break

    if start_idx < 0:
        return []

    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        if any(re.search(pattern, lines[idx], flags=re.IGNORECASE) for pattern in end_patterns):
            end_idx = idx
            break

    return lines[start_idx:end_idx]


def _extract_nfse_structured_context(raw_text: str) -> Dict[str, Any]:
    lines = _nfse_lines(raw_text)
    if not lines:
        return {}

    full_text = "\n".join(lines).lower()
    if "nfs-e" not in full_text and "danfse" not in full_text and "nfse" not in full_text:
        return {}

    # Ajuste por bloco: separa regiões semânticas da NFS-e para reduzir captura genérica.
    emitente_block = _slice_block(lines, r"emitente\s+da\s+nfs-?e", [r"tomador\s+do\s+servi[çc]o", r"intermedi[áa]rio"])
    tomador_block = _slice_block(lines, r"tomador\s+do\s+servi[çc]o", [r"intermedi[áa]rio", r"servi[çc]o\s+prestado"])
    servico_block = _slice_block(lines, r"servi[çc]o\s+prestado", [r"tributa[çc][ãa]o\s+municipal", r"tributa[çc][ãa]o\s+federal"])
    municipal_block = _slice_block(lines, r"tributa[çc][ãa]o\s+municipal", [r"tributa[çc][ãa]o\s+federal", r"informa[çc][õo]es\s+complementares"])
    federal_block = _slice_block(lines, r"tributa[çc][ãa]o\s+federal", [r"informa[çc][õo]es\s+complementares"])

    return {
        "lines": lines,
        "emitente_block": emitente_block,
        "tomador_block": tomador_block,
        "servico_block": servico_block,
        "municipal_block": municipal_block,
        "federal_block": federal_block,
    }


def _score_name_candidate(value: str) -> float:
    cleaned = _clean_line(value)
    if not _is_probable_name_line(cleaned):
        return 0.0

    lowered = cleaned.lower()
    words = [word for word in re.split(r"\s+", lowered) if word]
    uppercase_chars = len(re.findall(r"[A-ZÀ-Ý]", cleaned))
    alpha_chars = max(1, len(re.findall(r"[A-Za-zÀ-ÿ]", cleaned)))
    uppercase_ratio = uppercase_chars / alpha_chars

    score = 0.0
    if len(words) >= 2:
        score += 0.20
    if len(cleaned) >= 18:
        score += 0.15
    if uppercase_ratio >= 0.70:
        score += 0.25
    if any(token in lowered for token in COMPANY_HINT_TOKENS):
        score += 0.35

    return max(0.0, min(1.0, score))


def _extract_party_name_from_block(block: List[str], role: str) -> Tuple[str, float]:
    if not block:
        return "", 0.0

    # Ajuste semântico: para emitente, prioriza rótulo explícito de nome empresarial.
    if role == "emitente":
        for idx, line in enumerate(block):
            if re.search(r"nome\s*/\s*nome\s*empresarial", line, flags=re.IGNORECASE):
                for offset in range(1, 4):
                    probe_idx = idx + offset
                    if probe_idx < len(block) and _is_probable_name_line(block[probe_idx]):
                        candidate = block[probe_idx]
                        return candidate, max(0.92, _score_name_candidate(candidate))

    cnpj_idx = -1
    for idx, line in enumerate(block):
        if _find_first_cnpj(line):
            cnpj_idx = idx
            break

    if cnpj_idx >= 0:
        # Ajuste semântico: em NFS-e, o nome costuma vir logo após o CNPJ no bloco da parte.
        best_name = ""
        best_score = 0.0
        for probe_idx in range(cnpj_idx + 1, min(len(block), cnpj_idx + 7)):
            candidate = block[probe_idx]
            candidate_score = _score_name_candidate(candidate)
            if candidate_score > best_score:
                best_name = candidate
                best_score = candidate_score

        if best_name:
            return best_name, max(0.75, best_score)

    best_name = ""
    best_score = 0.0
    for line in block:
        candidate_score = _score_name_candidate(line)
        if candidate_score > best_score:
            best_name = line
            best_score = candidate_score

    if best_name:
        return best_name, max(0.62, best_score)

    return "", 0.0


def _extract_party_cnpj_from_block(block: List[str]) -> str:
    if not block:
        return ""

    for line in block:
        found = _find_first_cnpj(line)
        if found:
            return found

    return ""


def _extract_numero_nf_structured(lines: List[str]) -> str:
    for idx, line in enumerate(lines):
        if re.search(r"n[úu]mero\s+da\s+nfs-?e", line, flags=re.IGNORECASE):
            for probe_idx in range(idx + 1, min(len(lines), idx + 4)):
                probe = lines[probe_idx]
                if re.fullmatch(r"[A-Za-z0-9./-]{1,25}", probe) and not _is_header_like_value(probe):
                    return probe
    return ""


def _extract_descricao_servico_structured(servico_block: List[str]) -> str:
    if not servico_block:
        return ""

    collected: List[str] = []
    in_description = False
    for line in servico_block:
        if re.search(r"descri[çc][ãa]o\s+do\s+servi[çc]o", line, flags=re.IGNORECASE):
            in_description = True
            continue

        if not in_description:
            continue

        # Ajuste por bloco: para no próximo cabeçalho semântico para evitar poluir descrição.
        if re.search(r"tributa[çc][ãa]o|valor\s+do\s+servi[çc]o|valor\s+total", line, flags=re.IGNORECASE):
            break

        if _is_header_like_value(line):
            continue

        collected.append(line)
        if len(" ".join(collected)) >= 450:
            break

    return " ".join(collected).strip()


def _extract_valor_nf_structured(municipal_block: List[str], all_lines: List[str]) -> str:
    candidate_lines = [*municipal_block, *all_lines]
    labels = [
        r"valor\s+total\s+da\s+nfs-?e",
        r"valor\s+l[íi]quido\s+da\s+nfs-?e",
        r"valor\s+do\s+servi[çc]o",
    ]

    for idx, line in enumerate(candidate_lines):
        if any(re.search(label, line, flags=re.IGNORECASE) for label in labels):
            joined = line
            if idx + 1 < len(candidate_lines):
                joined = f"{line} {candidate_lines[idx + 1]}"
            match = re.search(r"R\$\s*([\d\.]+,\d{2}|\d+\.\d{2}|\d+)", joined, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()

    return ""


def _extract_retencao_structured(municipal_block: List[str], federal_block: List[str]) -> str:
    if not municipal_block and not federal_block:
        return ""

    evidences: List[str] = []
    lines = [*municipal_block, *federal_block]
    for idx, line in enumerate(lines):
        lowered = line.lower()
        if "reten" not in lowered and "retido" not in lowered and "issqn" not in lowered:
            continue

        # Ajuste semântico: evita duplicar linha de status isolada (ex.: "Não Retido").
        if re.fullmatch(r"n[ãa]o\s+retido|retido", lowered.strip()):
            continue

        if _is_header_like_value(line):
            continue

        joined = line
        if idx + 1 < len(lines):
            next_line = lines[idx + 1]
            # Ajuste por bloco: evita anexar próximo cabeçalho ao valor de retenção.
            if not re.search(r"^tributa[çc][ãa]o|^informa[çc][õo]es\s+complementares", next_line, flags=re.IGNORECASE):
                joined = f"{line} {next_line}"

        # Ajuste semântico: só guarda evidência quando há status/valor associado.
        if re.search(r"n[ãa]o\s+retido|retido|R\$\s*[\d\.]+,\d{2}|\d+,\d{2}", joined, flags=re.IGNORECASE):
            evidences.append(_clean_line(joined))

    return " | ".join(evidences[:3]).strip()


def _semantic_value_or_empty(value: str) -> str:
    cleaned = _clean_line(value)
    if _is_header_like_value(cleaned):
        return ""
    return cleaned


def _extract_cnpj_from_text(raw_text: str, preferred_labels: List[str]) -> str:
    cnpj_pattern = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}")
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    for line in lines:
        lowered = line.lower()
        if any(label in lowered for label in preferred_labels):
            match = cnpj_pattern.search(line)
            if match:
                return match.group(0)

    match = cnpj_pattern.search(raw_text)
    return match.group(0) if match else ""


def _extract_numero_nf(raw_text: str, document_info: Dict[str, Any]) -> str:
    doc_number = str(document_info.get("number") or "").strip()
    if doc_number:
        return doc_number

    patterns = [
        r"(?:n[úu]mero\s*(?:da\s*)?(?:nfs-?e|nfse|nota\s*fiscal)|n[º°o]?\s*(?:da\s*)?(?:nfs-?e|nfse|nota\s*fiscal))\s*[:#\-]?\s*([A-Za-z0-9./-]+)",
        r"(?:nota\s*fiscal\s*n[º°o]?|nf\s*n[º°o]?)\s*[:#\-]?\s*([A-Za-z0-9./-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""


def _extract_valor_nf(raw_text: str, totals: Dict[str, Any]) -> str:
    grand_total = totals.get("grand_total")
    if grand_total not in (None, ""):
        return str(grand_total)

    patterns = [
        r"(?:valor\s*(?:total)?\s*(?:da\s*)?nota|valor\s*(?:da\s*)?nfs-?e)\s*[:\-]?\s*(R\$\s*)?([\d\.]+,\d{2}|\d+\.\d{2}|\d+)",
        r"(?:total\s*a\s*pagar|valor\s*líquido)\s*[:\-]?\s*(R\$\s*)?([\d\.]+,\d{2}|\d+\.\d{2}|\d+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw_text, flags=re.IGNORECASE)
        if match:
            return match.group(2).strip()

    return ""


def _extract_descricao_servico(raw_text: str) -> str:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "descrição" in lowered and "serv" in lowered:
            parts = re.split(r"[:\-]\s*", line, maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                return parts[1].strip()

            if index + 1 < len(lines):
                return lines[index + 1]

    return ""


def _extract_retencao(raw_text: str) -> str:
    retention_terms = ["reten", "iss", "inss", "pis", "cofins", "csll", "irrf"]
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    retention_lines = [line for line in lines if any(term in line.lower() for term in retention_terms)]
    if retention_lines:
        return " | ".join(retention_lines[:4])

    return ""


def _normalize_ocr_numeric_noise(value: str) -> str:
    table = str.maketrans({
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "S": "5",
        "s": "5",
        "B": "8",
        "Q": "0",
    })
    return str(value or "").translate(table)


def _format_cnpj_from_digits(digits: str) -> str:
    if len(digits) != 14:
        return ""
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _extract_valid_cnpjs_from_text(value: str) -> List[str]:
    raw = _normalize_ocr_numeric_noise(value)
    candidates: List[str] = []

    punct_pattern = re.compile(r"\b\d{2}[\./\s-]?\d{3}[\./\s-]?\d{3}[\./\s-]?\d{4}[\./\s-]?\d{2}\b")
    for match in punct_pattern.findall(raw):
        digits = _normalize_digits(match)
        if len(digits) == 14 and _validate_cnpj(digits):
            formatted = _format_cnpj_from_digits(digits)
            if formatted and formatted not in candidates:
                candidates.append(formatted)

    dense_pattern = re.compile(r"\b\d{14}\b")
    for match in dense_pattern.findall(raw):
        digits = _normalize_digits(match)
        if len(digits) == 14 and _validate_cnpj(digits):
            formatted = _format_cnpj_from_digits(digits)
            if formatted and formatted not in candidates:
                candidates.append(formatted)

    return candidates


def _extract_noisy_name_from_lines(lines: List[str], label_patterns: List[str]) -> str:
    for idx, line in enumerate(lines):
        lowered = line.lower()
        if not any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in label_patterns):
            continue

        for probe_idx in range(idx, min(len(lines), idx + 4)):
            probe = _clean_line(lines[probe_idx])
            if not probe:
                continue
            if any(re.search(pattern, probe, flags=re.IGNORECASE) for pattern in label_patterns):
                probe = re.sub(r"^.*?(?:[:\-])\s*", "", probe).strip()
            if _is_probable_name_line(probe):
                return probe

    for line in lines:
        if _is_probable_name_line(line):
            return line

    return ""


def _extract_noisy_cnpj_by_labels(lines: List[str], label_patterns: List[str]) -> str:
    for idx, line in enumerate(lines):
        lowered = line.lower()
        if not any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in label_patterns):
            continue

        window = " ".join(lines[idx:min(len(lines), idx + 3)])
        candidates = _extract_valid_cnpjs_from_text(window)
        if candidates:
            return candidates[0]

    return ""


def _extract_noisy_numero_documento(lines: List[str], raw_text: str, document_info: Dict[str, Any]) -> str:
    doc_number = str(document_info.get("number") or "").strip()
    if doc_number:
        return doc_number

    number_patterns = [
        r"(?:recibo|nf|nfs-?e|nota\s*fiscal)\s*(?:n[º°o]?|numero)?\s*[:#\-]?\s*([A-Za-z0-9./-]{1,30})",
        r"numero\s*(?:do\s*)?(?:recibo|documento|nf|nfs-?e)?\s*[:#\-]?\s*([A-Za-z0-9./-]{1,30})",
    ]

    for line in lines:
        candidate_line = _normalize_ocr_numeric_noise(line)
        for pattern in number_patterns:
            match = re.search(pattern, candidate_line, flags=re.IGNORECASE)
            if match:
                candidate = _clean_line(match.group(1))
                if (
                    candidate
                    and any(char.isdigit() for char in candidate)
                    and len(candidate) <= 25
                    and not _is_header_like_value(candidate)
                ):
                    return candidate

    full_text = _normalize_ocr_numeric_noise(raw_text)
    for pattern in number_patterns:
        match = re.search(pattern, full_text, flags=re.IGNORECASE)
        if match:
            candidate = _clean_line(match.group(1))
            if (
                candidate
                and any(char.isdigit() for char in candidate)
                and len(candidate) <= 25
                and not _is_header_like_value(candidate)
            ):
                return candidate

    return ""


def _extract_noisy_valor_nf(raw_text: str, totals: Dict[str, Any]) -> str:
    grand_total = totals.get("grand_total")
    if grand_total not in (None, ""):
        return str(grand_total)

    normalized_text = _normalize_ocr_numeric_noise(raw_text)
    amount_pattern = re.compile(r"\b([\d]{1,3}(?:\.[\d]{3})*,\d{2}|\d+\.\d{2})\b")
    best_candidate = ""
    best_score = -1.0

    for match in amount_pattern.finditer(normalized_text):
        candidate = match.group(1)
        amount = _parse_currency(candidate)
        if amount is None or amount <= 0.0:
            continue

        start = max(0, match.start() - 40)
        end = min(len(normalized_text), match.end() + 40)
        context = normalized_text[start:end].lower()

        score = float(amount)
        if re.search(r"(?:r\$|rs|r5)", context, flags=re.IGNORECASE):
            score += 10000.0
        if any(token in context for token in ["importancia", "valor", "reembolso", "total"]):
            score += 2500.0
        if any(token in context for token in ["cpf", "pix", "celular", "telefone"]):
            score -= 9000.0

        if score > best_score:
            best_score = score
            best_candidate = candidate

    return best_candidate


def _extract_noisy_descricao(raw_text: str, lines: List[str]) -> str:
    normalized_text = _clean_line(raw_text)
    if not normalized_text:
        return ""

    match = re.search(
        r"(?:referente\s+a|referente\s+ao|descricao(?:\s+do\s+servico)?)\s*[:\-]?\s*(.+)",
        normalized_text,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = match.group(1)
        candidate = re.split(
            r"(?:\ba\s+quitacao\b|\btitular\b|\bconta\s+pix\b|\bcpf\b|\brecife\b\s*,?\s*\d{1,2}\b)",
            candidate,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        candidate = _clean_line(candidate)
        if len(candidate) >= 20:
            return candidate[:420].strip()

    for line in lines:
        lowered = line.lower()
        if any(token in lowered for token in ["reembolso", "indeniza", "manutenc", "prest", "servi"]):
            token_idx = min(
                [idx for idx in [lowered.find("reembolso"), lowered.find("indeniza"), lowered.find("manutenc"), lowered.find("prest"), lowered.find("servi")] if idx >= 0] or [0]
            )
            candidate = _clean_line(line[max(0, token_idx - 20):token_idx + 260])
            if len(candidate) >= 20 and sum(ch.isalpha() for ch in candidate) >= 12:
                return candidate[:420].strip()

    best_line = ""
    for line in lines:
        cleaned = _clean_line(line)
        if len(cleaned) < 20:
            continue
        if _is_header_like_value(cleaned):
            continue
        if _find_first_cnpj(cleaned):
            continue
        alpha_count = sum(char.isalpha() for char in cleaned)
        if alpha_count < 12:
            continue
        if len(cleaned) > len(best_line):
            best_line = cleaned

    return best_line[:420].strip()


def _extract_noisy_retencao(raw_text: str, lines: List[str]) -> str:
    retention_terms = ["reten", "retido", "iss", "inss", "pis", "cofins", "csll", "irrf"]
    evidences: List[str] = []
    for line in lines:
        lowered = line.lower()
        if not any(term in lowered for term in retention_terms):
            continue
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        if len(cleaned) > 240:
            match = re.search(r"((?:n[ãa]o\s+retido|retido).{0,120})", cleaned, flags=re.IGNORECASE)
            if match:
                cleaned = _clean_line(match.group(1))
        evidences.append(cleaned)

    if evidences:
        return " | ".join(evidences[:3]).strip()

    lowered_text = raw_text.lower()
    if "não retido" in lowered_text or "nao retido" in lowered_text:
        return "Não Retido"
    if "retido" in lowered_text:
        return "Retido"

    return ""


def _extract_noisy_fields_for_scanned_or_handwritten(
    raw_text: str,
    entities: Dict[str, Any],
    document_info: Dict[str, Any],
    totals: Dict[str, Any],
) -> Tuple[Dict[str, str], Dict[str, float]]:
    lines = [_clean_line(line) for line in raw_text.splitlines() if _clean_line(line)]

    fornecedor_name = _extract_noisy_name_from_lines(
        lines,
        label_patterns=[r"fornecedor", r"prestador", r"emitente", r"benefici[áa]rio", r"empresa"],
    )
    tomador_name = _extract_noisy_name_from_lines(
        lines,
        label_patterns=[r"tomador", r"destinat[áa]rio", r"cliente", r"pagador", r"favorecido"],
    )

    cnpj_fornecedor = _extract_noisy_cnpj_by_labels(
        lines,
        label_patterns=[r"fornecedor", r"prestador", r"emitente", r"benefici[áa]rio"],
    )
    cnpj_tomador = _extract_noisy_cnpj_by_labels(
        lines,
        label_patterns=[r"tomador", r"destinat[áa]rio", r"cliente", r"pagador"],
    )

    if not cnpj_fornecedor:
        all_cnpjs = _extract_valid_cnpjs_from_text(raw_text)
        if all_cnpjs:
            cnpj_fornecedor = all_cnpjs[0]
            if len(all_cnpjs) > 1:
                cnpj_tomador = cnpj_tomador or all_cnpjs[1]

    if not tomador_name:
        condominio_match = re.search(r"(condom[íi]nio[^,\n]{5,140})", raw_text, flags=re.IGNORECASE)
        if condominio_match:
            tomador_name = _clean_line(condominio_match.group(1))

    fields = {
        "fornecedor": fornecedor_name or str(entities.get("fornecedor") or entities.get("issuer") or "").strip(),
        "tomador": tomador_name or str(entities.get("tomador") or entities.get("recipient") or "").strip(),
        "cnpj_fornecedor": cnpj_fornecedor or str(entities.get("cnpj_fornecedor") or entities.get("issuer_cnpj") or "").strip(),
        "cnpj_tomador": cnpj_tomador or str(entities.get("cnpj_tomador") or entities.get("recipient_cnpj") or "").strip(),
        "numero_nf": _extract_noisy_numero_documento(lines, raw_text, document_info),
        "descricao_servico": _extract_noisy_descricao(raw_text, lines),
        "valor_nf": _extract_noisy_valor_nf(raw_text, totals),
        "retencao": _extract_noisy_retencao(raw_text, lines),
    }

    confidence = {
        "fornecedor": 0.70 if fields["fornecedor"] else 0.0,
        "tomador": 0.68 if fields["tomador"] else 0.0,
        "cnpj_fornecedor": 0.90 if _validate_cnpj(fields["cnpj_fornecedor"]) else 0.0,
        "cnpj_tomador": 0.88 if _validate_cnpj(fields["cnpj_tomador"]) else 0.0,
        "numero_nf": 0.64 if fields["numero_nf"] else 0.0,
        "descricao_servico": 0.62 if len(fields["descricao_servico"]) > 10 else 0.0,
        "valor_nf": 0.86 if _parse_currency(fields["valor_nf"]) not in (None, 0.0) else 0.0,
        "retencao": 0.58 if fields["retencao"] else 0.0,
    }

    return fields, confidence


def _is_noisy_extraction_context(classification: str, engine_name: str) -> bool:
    normalized_classification = str(classification or "").strip().lower()
    normalized_engine = str(engine_name or "").strip().lower()
    return (
        normalized_classification in NOISY_EXTRACTION_CLASSES
        or normalized_engine in NOISY_EXTRACTION_ENGINES
    )


def _is_low_quality_ocr_text(value: str, min_alpha: int = 10, min_alpha_ratio: float = 0.45) -> bool:
    cleaned = _clean_line(value)
    if not cleaned:
        return True

    alpha_count = sum(char.isalpha() for char in cleaned)
    if alpha_count < min_alpha:
        return True

    alnum_count = sum(char.isalnum() for char in cleaned)
    if alnum_count <= 0:
        return True

    alpha_ratio = alpha_count / max(1.0, float(alnum_count))
    return alpha_ratio < float(min_alpha_ratio)


def _apply_noisy_field_enrichment(
    fields: Dict[str, str],
    field_confidence: Dict[str, float],
    raw_text: str,
    entities: Dict[str, Any],
    document_info: Dict[str, Any],
    totals: Dict[str, Any],
    classification: str,
    engine_name: str,
) -> Tuple[Dict[str, str], Dict[str, float]]:
    if not _is_noisy_extraction_context(classification, engine_name):
        return fields, field_confidence

    noisy_fields, noisy_confidence = _extract_noisy_fields_for_scanned_or_handwritten(
        raw_text=raw_text,
        entities=entities,
        document_info=document_info,
        totals=totals,
    )

    for field_name in [*REQUIRED_FIELDS, "cnpj_tomador"]:
        current_value = str(fields.get(field_name) or "").strip()
        noisy_value = str(noisy_fields.get(field_name) or "").strip()

        should_replace = False
        if not current_value:
            should_replace = bool(noisy_value)
        elif _is_header_like_value(current_value):
            should_replace = bool(noisy_value)
        elif field_name in {"cnpj_fornecedor", "cnpj_tomador"} and not _validate_cnpj(current_value):
            should_replace = bool(noisy_value and _validate_cnpj(noisy_value))
        elif field_name == "retencao" and len(current_value) > 240:
            should_replace = bool(noisy_value)
        elif field_name == "descricao_servico" and _is_low_quality_ocr_text(current_value):
            should_replace = bool(noisy_value)
        elif field_name == "valor_nf":
            current_amount = _parse_currency(current_value)
            noisy_amount = _parse_currency(noisy_value)
            if noisy_amount is not None and (current_amount is None or noisy_amount > current_amount):
                should_replace = True

        if should_replace:
            fields[field_name] = noisy_value
            field_confidence[field_name] = max(
                float(field_confidence.get(field_name, 0.0)),
                float(noisy_confidence.get(field_name, 0.0)),
            )

    logger.info(
        "NOISY_EXTRACTION_APPLIED | classification=%s | engine=%s | filled_fields=%s",
        classification or "unknown",
        engine_name or "unknown",
        [field for field in REQUIRED_FIELDS if str(fields.get(field) or "").strip()],
    )

    return fields, field_confidence


def _parse_currency(value: str | float | int | None) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    normalized = str(value).strip()
    if not normalized:
        return None

    normalized = normalized.replace("R$", "").replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")

    try:
        return float(normalized)
    except ValueError:
        return None


def _pick_best_candidate(candidates: List[Tuple[str, float]]) -> Tuple[str, float]:
    for value, confidence in candidates:
        normalized = _semantic_value_or_empty(value)
        if normalized:
            return normalized, max(0.0, min(1.0, float(confidence)))
    return "", 0.0


def _normalize_dynamic_field_key(label: str) -> str:
    normalized = unicodedata.normalize("NFD", str(label or "").lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")

    if not normalized:
        return ""

    if normalized[0].isdigit():
        normalized = f"campo_{normalized}"

    return normalized[:64]


def _is_dynamic_label_candidate(label: str) -> bool:
    cleaned = _clean_line(label)
    if len(cleaned) < 2 or len(cleaned) > 80:
        return False

    lowered = cleaned.lower()
    lowered_normalized = unicodedata.normalize("NFD", lowered)
    lowered_normalized = "".join(
        char for char in lowered_normalized if unicodedata.category(char) != "Mn"
    )

    if lowered_normalized in DYNAMIC_FIELD_LABEL_STOPWORDS:
        return False

    if re.fullmatch(r"[\d\W_]+", cleaned):
        return False

    if sum(1 for char in cleaned if char.isalpha()) < 2:
        return False

    return True


def _insert_dynamic_field(result: Dict[str, str], key: str, value: str) -> None:
    if key not in result:
        result[key] = value
        return

    if result[key] == value:
        return

    suffix = 2
    while f"{key}_{suffix}" in result:
        if result[f"{key}_{suffix}"] == value:
            return
        suffix += 1

    result[f"{key}_{suffix}"] = value


def _is_dynamic_value_plausible(field_key: str, field_value: str) -> bool:
    value = _clean_line(field_value)
    if not value:
        return False

    # Descarta ruído típico de OCR (ex.: "e" isolado em labels com NFS-e).
    if len(value) == 1 and value.isalpha():
        return False

    key = str(field_key or "").lower()
    digits = _normalize_digits(value)

    if "chave_de_acesso" in key and len(digits) < 20:
        return False

    if "cnpj" in key and digits and len(digits) != 14:
        return False

    if "numero_da_nfs" in key and len(digits) == 0:
        return False

    return True


def _extract_dynamic_fields_from_raw_text(raw_text: str, max_fields: int) -> Dict[str, str]:
    extracted: Dict[str, str] = {}
    if not raw_text.strip():
        return extracted

    label_colon_pattern = re.compile(
        r"^([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\s()/%\-.]{1,80})\s*:\s*(.+)$"
    )
    label_dash_pattern = re.compile(
        r"^([A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\s()/%\-.]{1,80})\s+-\s+(.+)$"
    )

    for raw_line in raw_text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue

        match = label_colon_pattern.match(line)
        if not match:
            match = label_dash_pattern.match(line)
        if not match:
            continue

        label = _clean_line(match.group(1))
        value = _clean_line(match.group(2))

        if not value or _is_header_like_value(value):
            continue

        if not _is_dynamic_label_candidate(label):
            continue

        key = _normalize_dynamic_field_key(label)
        if not key:
            continue

        if not _is_dynamic_value_plausible(key, value):
            continue

        if len(value) > 500:
            value = value[:500].strip()

        _insert_dynamic_field(extracted, key, value)
        if len(extracted) >= max_fields:
            break

    return extracted


def _normalize_search_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", str(value or "").lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _extract_nfse_access_key(lines: List[str], start_idx: int) -> str:
    for probe_idx in range(start_idx, min(len(lines), start_idx + 5)):
        digits = _normalize_digits(lines[probe_idx])
        if len(digits) >= 44:
            return digits

        inline_match = re.search(r"\b\d{44}\b", lines[probe_idx])
        if inline_match:
            return inline_match.group(0)

    return ""


def _is_probable_multiline_label(label: str) -> bool:
    cleaned = _clean_line(label)
    if not _is_dynamic_label_candidate(cleaned):
        return False

    if ":" in cleaned or re.search(r"\s+-\s+", cleaned):
        return False

    # Linha predominantemente numérica tende a ser valor, não rótulo.
    digits = _normalize_digits(cleaned)
    if digits and len(digits) >= max(8, int(len(cleaned) * 0.4)):
        return False

    if re.search(r"R\$\s*[\d\.,]+", cleaned, flags=re.IGNORECASE):
        return False

    return True


def _extract_dynamic_fields_for_docling_digital_pdf(raw_text: str, max_fields: int) -> Dict[str, str]:
    extracted: Dict[str, str] = {}
    lines = [_clean_line(line) for line in raw_text.splitlines() if _clean_line(line)]
    if not lines:
        return extracted

    for idx, line in enumerate(lines):
        if len(extracted) >= max_fields:
            break

        normalized_line = _normalize_search_text(line)
        if "chave de acesso" in normalized_line and ("nfs-e" in normalized_line or "nfse" in normalized_line):
            access_key = _extract_nfse_access_key(lines, idx)
            if access_key:
                _insert_dynamic_field(extracted, "chave_de_acesso_da_nfs_e", access_key)

    for idx, line in enumerate(lines):
        if len(extracted) >= max_fields:
            break

        if not _is_probable_multiline_label(line):
            continue

        key = _normalize_dynamic_field_key(line)
        if not key:
            continue

        value = ""
        for probe_idx in range(idx + 1, min(len(lines), idx + 4)):
            candidate = _clean_line(lines[probe_idx])
            if not candidate:
                continue

            if _is_probable_multiline_label(candidate):
                break

            if _is_header_like_value(candidate):
                continue

            value = candidate
            break

        if not value:
            continue

        if len(value) > 500:
            value = value[:500].strip()

        if not _is_dynamic_value_plausible(key, value):
            continue

        _insert_dynamic_field(extracted, key, value)

    return extracted


def _extract_dynamic_fields_from_structured_sources(data: Dict[str, Any], max_fields: int) -> Dict[str, str]:
    extracted: Dict[str, str] = {}

    for source_name in ["document_info", "entities", "totals"]:
        source_data = data.get(source_name)
        if not isinstance(source_data, dict):
            continue

        for field_name, field_value in source_data.items():
            if isinstance(field_value, (dict, list, tuple, set)):
                continue

            value = _clean_line(field_value)
            if not value:
                continue

            key = _normalize_dynamic_field_key(field_name)
            if not key:
                continue

            if not _is_dynamic_value_plausible(key, value):
                continue

            _insert_dynamic_field(extracted, key, value)
            if len(extracted) >= max_fields:
                return extracted

    return extracted


def extract_dynamic_document_fields(
    data: Dict[str, Any],
    base_fields: Dict[str, str] | None = None,
    classification: str | None = None,
    engine_name: str | None = None,
    max_fields: int = 120,
) -> Dict[str, str]:
    dynamic_fields: Dict[str, str] = {}

    if isinstance(base_fields, dict):
        for field_name, field_value in base_fields.items():
            key = str(field_name or "").strip()
            value = _clean_line(field_value)
            if key and value:
                dynamic_fields[key] = value

    raw_text = _get_raw_text(data)

    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    resolved_classification = str(classification or meta.get("document_type") or "").strip().lower()
    resolved_engine_name = str(engine_name or meta.get("engine") or "").strip().lower()

    if resolved_classification == "digital_pdf" and resolved_engine_name == "docling":
        from_docling_pdf = _extract_dynamic_fields_for_docling_digital_pdf(
            raw_text,
            max_fields=max_fields,
        )
        for field_name, field_value in from_docling_pdf.items():
            if len(dynamic_fields) >= max_fields:
                break
            _insert_dynamic_field(dynamic_fields, field_name, field_value)

    from_text = _extract_dynamic_fields_from_raw_text(raw_text, max_fields=max_fields)
    for field_name, field_value in from_text.items():
        if len(dynamic_fields) >= max_fields:
            break
        _insert_dynamic_field(dynamic_fields, field_name, field_value)

    if len(dynamic_fields) < max_fields:
        from_structured = _extract_dynamic_fields_from_structured_sources(
            data,
            max_fields=max_fields - len(dynamic_fields),
        )
        for field_name, field_value in from_structured.items():
            if len(dynamic_fields) >= max_fields:
                break
            _insert_dynamic_field(dynamic_fields, field_name, field_value)

    return dynamic_fields


def extract_critical_fields(data: Dict[str, Any]) -> Dict[str, str]:
    fields, _ = extract_critical_fields_with_confidence(data)
    return fields


def extract_critical_fields_with_confidence(data: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, float]]:
    raw_text = _get_raw_text(data)
    entities = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    document_info = data.get("document_info") if isinstance(data.get("document_info"), dict) else {}
    totals = data.get("totals") if isinstance(data.get("totals"), dict) else {}
    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    resolved_classification = str(meta.get("document_type") or meta.get("classification") or "").strip().lower()
    resolved_engine_name = str(meta.get("engine") or "").strip().lower()

    # Ajuste por contexto: em NFS-e usamos blocos semânticos para priorizar valor real do campo.
    structured = _extract_nfse_structured_context(raw_text)
    lines = structured.get("lines", []) if isinstance(structured, dict) else []
    emitente_block = structured.get("emitente_block", []) if isinstance(structured, dict) else []
    tomador_block = structured.get("tomador_block", []) if isinstance(structured, dict) else []
    servico_block = structured.get("servico_block", []) if isinstance(structured, dict) else []
    municipal_block = structured.get("municipal_block", []) if isinstance(structured, dict) else []
    federal_block = structured.get("federal_block", []) if isinstance(structured, dict) else []

    emitente_name, emitente_name_conf = _extract_party_name_from_block(emitente_block, role="emitente")
    fornecedor, fornecedor_conf = _pick_best_candidate([
        (emitente_name, emitente_name_conf),
        (str(entities.get("issuer") or entities.get("fornecedor") or entities.get("prestador") or ""), 0.84),
        (_extract_line_value_by_labels(raw_text, ["fornecedor", "prestador", "emitente", "emissor"]), 0.58),
    ])

    tomador_name, tomador_name_conf = _extract_party_name_from_block(tomador_block, role="tomador")
    tomador, tomador_conf = _pick_best_candidate([
        (tomador_name, tomador_name_conf),
        (str(entities.get("recipient") or entities.get("tomador") or entities.get("destinatario") or ""), 0.84),
        (_extract_line_value_by_labels(raw_text, ["tomador", "destinatário", "destinatario", "cliente"]), 0.58),
    ])

    cnpj_fornecedor, cnpj_fornecedor_conf = _pick_best_candidate([
        (_extract_party_cnpj_from_block(emitente_block), 0.97),
        (str(entities.get("cnpj_fornecedor") or entities.get("issuer_cnpj") or ""), 0.88),
        (_extract_cnpj_from_text(raw_text, ["fornecedor", "prestador", "emitente", "emissor"]), 0.56),
    ])

    cnpj_tomador, cnpj_tomador_conf = _pick_best_candidate([
        (_extract_party_cnpj_from_block(tomador_block), 0.97),
        (str(entities.get("cnpj_tomador") or entities.get("recipient_cnpj") or ""), 0.88),
        (_extract_cnpj_from_text(raw_text, ["tomador", "destinatário", "destinatario", "cliente"]), 0.56),
    ])

    if cnpj_fornecedor and cnpj_tomador and _normalize_digits(cnpj_fornecedor) == _normalize_digits(cnpj_tomador):
        cnpj_tomador = ""

    numero_nf, numero_nf_conf = _pick_best_candidate([
        (_extract_numero_nf_structured(lines), 0.94),
        (str(document_info.get("number") or ""), 0.86),
        (_extract_numero_nf(raw_text, document_info), 0.60),
    ])

    descricao_servico, descricao_conf = _pick_best_candidate([
        (_extract_descricao_servico_structured(servico_block), 0.92),
        (_extract_descricao_servico(raw_text), 0.62),
    ])

    valor_nf, valor_nf_conf = _pick_best_candidate([
        (_extract_valor_nf_structured(municipal_block, lines), 0.92),
        (str(totals.get("grand_total") or ""), 0.86),
        (_extract_valor_nf(raw_text, totals), 0.58),
    ])

    retencao, retencao_conf = _pick_best_candidate([
        (_extract_retencao_structured(municipal_block, federal_block), 0.82),
        (_extract_retencao(raw_text), 0.48),
    ])

    fields = {
        "fornecedor": fornecedor,
        "tomador": tomador,
        "cnpj_fornecedor": cnpj_fornecedor,
        "cnpj_tomador": cnpj_tomador,
        "numero_nf": numero_nf,
        "descricao_servico": descricao_servico,
        "valor_nf": valor_nf,
        "retencao": retencao,
    }

    field_confidence = {
        "fornecedor": fornecedor_conf,
        "tomador": tomador_conf,
        "cnpj_fornecedor": cnpj_fornecedor_conf,
        "cnpj_tomador": cnpj_tomador_conf,
        "numero_nf": numero_nf_conf,
        "descricao_servico": descricao_conf,
        "valor_nf": valor_nf_conf,
        "retencao": retencao_conf,
    }
    # fields, field_confidence = _apply_noisy_field_enrichment(
    #     fields=fields,
    #     field_confidence=field_confidence,
    #     raw_text=raw_text,
    #     entities=entities,
    #     document_info=document_info,
    #     totals=totals,
    #     classification=resolved_classification,
    #     engine_name=resolved_engine_name,
    # )

    return fields, field_confidence


def validate_fields(fields: Dict[str, str]) -> Dict[str, bool]:
    fornecedor = str(fields.get("fornecedor") or "").strip()
    tomador = str(fields.get("tomador") or "").strip()
    cnpj_fornecedor = str(fields.get("cnpj_fornecedor") or "").strip()
    cnpj_tomador = str(fields.get("cnpj_tomador") or "").strip()
    numero_nf = str(fields.get("numero_nf") or "").strip()
    descricao_servico = str(fields.get("descricao_servico") or "").strip()
    retencao = str(fields.get("retencao") or "").strip()
    valor_nf = _parse_currency(fields.get("valor_nf"))

    validation = {
        # Ajuste semântico: rejeita cabeçalhos capturados como valor de campo.
        "fornecedor_ok": len(fornecedor) > 2 and not _is_header_like_value(fornecedor),
        "tomador_ok": len(tomador) > 2 and not _is_header_like_value(tomador),
        "cnpj_fornecedor_valido": _validate_cnpj(cnpj_fornecedor),
        "cnpj_tomador_valido": _validate_cnpj(cnpj_tomador) if cnpj_tomador else False,
        "numero_nf_valido": bool(numero_nf) and not _is_header_like_value(numero_nf),
        "descricao_ok": len(descricao_servico) > 10 and not _is_header_like_value(descricao_servico),
        "valor_valido": valor_nf is not None and valor_nf > 0,
        "retencao_ok": len(retencao) > 0 and not _is_header_like_value(retencao),
    }

    validation["required_fields_present"] = {
        field_name: bool(str(fields.get(field_name) or "").strip())
        for field_name in REQUIRED_FIELDS
    }
    validation["cnpj_tomador_validado"] = validation["cnpj_tomador_valido"]

    return validation


def extract_avg_confidence(data: Dict[str, Any]) -> float | None:
    if not isinstance(data, dict):
        return None

    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    candidates = [
        meta.get("avg_confidence"),
        meta.get("average_confidence"),
        meta.get("confidence"),
        data.get("avg_confidence"),
    ]

    for candidate in candidates:
        if candidate is None:
            continue

        try:
            value = float(candidate)
        except (TypeError, ValueError):
            continue

        if 0.0 <= value <= 1.0:
            value *= 100.0

        return max(0.0, min(100.0, value))

    return None


def _normalize_confidence_ratio(confidence: float | int | str | None) -> float:
    try:
        value = float(confidence or 0.0)
    except (TypeError, ValueError):
        return 0.0

    if value > 1.0:
        value = value / 100.0

    return max(0.0, min(1.0, value))


def compute_field_score(field_name: str, value: str, confidence: float, validation: bool) -> float:
    _ = field_name
    score = 0.0

    if str(value or "").strip():
        score += 0.4

    score += _normalize_confidence_ratio(confidence) * 0.4

    if bool(validation):
        score += 0.2

    return round(max(0.0, min(1.0, score)), 4)


def get_low_confidence_critical_fields(
    fields: Dict[str, str],
    field_confidence: Dict[str, float],
    validation: Dict[str, Any],
    threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> Tuple[Dict[str, str], Dict[str, float]]:
    low_conf_fields: Dict[str, str] = {}
    field_scores: Dict[str, float] = {}

    for field_name in REQUIRED_FIELDS:
        validation_key = FIELD_VALIDATION_KEYS.get(field_name, "")
        field_validation_ok = bool(validation.get(validation_key))
        score = compute_field_score(
            field_name=field_name,
            value=str(fields.get(field_name) or ""),
            confidence=float(field_confidence.get(field_name, 0.0)),
            validation=field_validation_ok,
        )
        field_scores[field_name] = score

        if score < float(threshold):
            low_conf_fields[field_name] = str(fields.get(field_name) or "")

    return low_conf_fields, field_scores


def should_run_llm(low_conf_fields: Dict[str, str]) -> bool:
    return bool(low_conf_fields)


def compute_field_pipeline_quality(
    data: Dict[str, Any],
    override_fields: Dict[str, str] | None = None,
    override_ocr_confidence: float | None = None,
    override_field_confidence: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    resolved_classification = str(meta.get("document_type") or meta.get("classification") or "").strip().lower()
    resolved_engine_name = str(meta.get("engine") or "").strip().lower()
    raw_text = _get_raw_text(data)
    entities = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    document_info = data.get("document_info") if isinstance(data.get("document_info"), dict) else {}
    totals = data.get("totals") if isinstance(data.get("totals"), dict) else {}

    if override_fields:
        fields = override_fields
        field_confidence = dict(override_field_confidence or {})
    else:
        fields, field_confidence = extract_critical_fields_with_confidence(data)

    # fields, field_confidence = _apply_noisy_field_enrichment(
    #     fields=fields,
    #     field_confidence=field_confidence,
    #     raw_text=raw_text,
    #     entities=entities,
    #     document_info=document_info,
    #     totals=totals,
    #     classification=resolved_classification,
    #     engine_name=resolved_engine_name,
    # )

    for field_name in [*REQUIRED_FIELDS, "cnpj_tomador"]:
        field_confidence.setdefault(field_name, 0.0)

    # Ajuste semântico: valor que parece cabeçalho recebe confiança 0 no nível do campo.
    for field_name, field_value in fields.items():
        if _is_header_like_value(str(field_value or "")):
            field_confidence[field_name] = 0.0

    validation = validate_fields(fields)

    validation_flags = [
        bool(value)
        for key, value in validation.items()
        if key != "required_fields_present" and isinstance(value, bool)
    ]
    field_score = (sum(validation_flags) / len(validation_flags)) if validation_flags else 0.0

    detected_ocr_confidence = extract_avg_confidence(data)
    # Ajuste de robustez: quando engine não retorna confiança média, usa média de confiança por campo.
    if override_ocr_confidence is not None:
        ocr_confidence_pct = override_ocr_confidence
    elif detected_ocr_confidence is not None:
        ocr_confidence_pct = detected_ocr_confidence
    else:
        ocr_confidence_pct = (sum(field_confidence.values()) / max(1, len(field_confidence))) * 100.0

    ocr_confidence = max(0.0, min(100.0, float(ocr_confidence_pct))) / 100.0
    final_score = (0.4 * ocr_confidence) + (0.6 * field_score)

    required_present = validation.get("required_fields_present", {})
    missing_required = any(not bool(required_present.get(field_name)) for field_name in REQUIRED_FIELDS)
    critical_invalid = any(
        not bool(validation.get(key))
        for key in ["cnpj_fornecedor_valido", "valor_valido", "numero_nf_valido"]
    )

    low_confidence_fields = [
        field_name
        for field_name in [*REQUIRED_FIELDS, "cnpj_tomador"]
        if float(field_confidence.get(field_name, 0.0)) < float(FIELD_CONFIDENCE_THRESHOLDS.get(field_name, 0.55))
    ]
    critical_low_confidence = any(
        field_name in low_confidence_fields
        for field_name in ["tomador", "cnpj_fornecedor", "numero_nf", "valor_nf"]
    )

    low_conf_critical_fields, field_scores = get_low_confidence_critical_fields(
        fields=fields,
        field_confidence=field_confidence,
        validation=validation,
        threshold=LOW_CONFIDENCE_THRESHOLD,
    )
    llm_decision = should_run_llm(low_conf_critical_fields)

    logger.warning(
        "FIELD_SCORE_CRITICAL | threshold=%.2f | scores=%s | low_conf_fields=%s | run_llm=%s",
        float(LOW_CONFIDENCE_THRESHOLD),
        field_scores,
        list(low_conf_critical_fields.keys()),
        llm_decision,
    )

    return {
        "fields": fields,
        "field_confidence": {k: round(float(v), 4) for k, v in field_confidence.items()},
        "low_confidence_fields": low_confidence_fields,
        "critical_field_scores": field_scores,
        "low_confidence_critical_fields": low_conf_critical_fields,
        "llm_should_run": llm_decision,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "validation": validation,
        "ocr_confidence": round(ocr_confidence, 4),
        "field_score": round(field_score, 4),
        "final_score": round(final_score, 4),
        "fallback_needed": critical_invalid or missing_required or critical_low_confidence or final_score < 0.85,
    }


def merge_fields_by_validation(
    primary_fields: Dict[str, str],
    fallback_fields: Dict[str, str],
    fallback_validation: Dict[str, Any],
) -> Tuple[Dict[str, str], List[str]]:
    merged = dict(primary_fields)
    fields_from_fallback: List[str] = []

    for field_name, validation_key in FIELD_VALIDATION_KEYS.items():
        fallback_value = str(fallback_fields.get(field_name) or "").strip()
        if not fallback_value:
            continue

        fallback_valid = bool(fallback_validation.get(validation_key))
        primary_empty = not str(primary_fields.get(field_name) or "").strip()

        if fallback_valid or primary_empty:
            merged[field_name] = fallback_value
            fields_from_fallback.append(field_name)

    for field_name in REQUIRED_FIELDS:
        merged.setdefault(field_name, "")

    merged.setdefault("cnpj_tomador", str(primary_fields.get("cnpj_tomador") or "").strip())
    return merged, fields_from_fallback


def merge_field_confidence(
    primary_confidence: Dict[str, float],
    fallback_confidence: Dict[str, float],
    fields_from_fallback: List[str],
) -> Dict[str, float]:
    merged = dict(primary_confidence or {})

    # Ajuste de fallback por campo: usa confiança do fallback só para campos efetivamente substituídos.
    for field_name in fields_from_fallback:
        merged[field_name] = float(fallback_confidence.get(field_name, merged.get(field_name, 0.0)))

    for field_name in [*REQUIRED_FIELDS, "cnpj_tomador"]:
        merged.setdefault(field_name, 0.0)

    return merged


def resolve_field_fallback_engine(classification: str, primary_engine: str) -> str | None:
    preferred = {
        "digital_pdf": "llamaparse",
        "scanned_image": "easyocr",
        "handwritten_complex": "easyocr",
    }
    alternatives = {
        "llamaparse": "docling",
        "easyocr": "tesseract",
        "trocr": "easyocr",
        "deepseek": "paddle",
        "paddle": "easyocr",
        "handwritten_region": "easyocr",
        "docling": "llamaparse",
        "tesseract": "easyocr",
    }

    normalized_primary = primary_engine.lower().strip()
    if normalized_primary in {"paddle_deepseek", "paddle_easyocr"}:
        normalized_primary = "paddle"
    if normalized_primary in {"handwritten_region_pipeline", "handwritten_region"}:
        normalized_primary = "handwritten_region"

    candidate = preferred.get(classification)
    if not candidate:
        return None

    if candidate == normalized_primary:
        return alternatives.get(candidate)

    return candidate