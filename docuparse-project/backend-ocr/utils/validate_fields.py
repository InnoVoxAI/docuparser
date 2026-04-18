from typing import Any, Dict, List, Tuple
import re


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


def extract_critical_fields(data: Dict[str, Any]) -> Dict[str, str]:
    fields, _ = extract_critical_fields_with_confidence(data)
    return fields


def extract_critical_fields_with_confidence(data: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, float]]:
    raw_text = _get_raw_text(data)
    entities = data.get("entities") if isinstance(data.get("entities"), dict) else {}
    document_info = data.get("document_info") if isinstance(data.get("document_info"), dict) else {}
    totals = data.get("totals") if isinstance(data.get("totals"), dict) else {}

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


def compute_field_pipeline_quality(
    data: Dict[str, Any],
    override_fields: Dict[str, str] | None = None,
    override_ocr_confidence: float | None = None,
    override_field_confidence: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    if override_fields:
        fields = override_fields
        field_confidence = dict(override_field_confidence or {})
    else:
        fields, field_confidence = extract_critical_fields_with_confidence(data)

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

    return {
        "fields": fields,
        "field_confidence": {k: round(float(v), 4) for k, v in field_confidence.items()},
        "low_confidence_fields": low_confidence_fields,
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
        "deepseek": "paddle",
        "paddle": "easyocr",
        "docling": "llamaparse",
        "tesseract": "easyocr",
    }

    normalized_primary = primary_engine.lower().strip()
    if normalized_primary in {"paddle_deepseek", "paddle_easyocr"}:
        normalized_primary = "paddle"

    candidate = preferred.get(classification)
    if not candidate:
        return None

    if candidate == normalized_primary:
        return alternatives.get(candidate)

    return candidate