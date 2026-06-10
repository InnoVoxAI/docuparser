# =============================================================================
# SHARED: shared/validators.py
# =============================================================================
# Validações genéricas e reutilizáveis — sem dependência de domínio ou engine.
#
# Origem: extraído de utils/validate_fields.py (Fase 2 do refactor).
# A lógica original em validate_fields.py permanece intacta para backward compat.
# Na Fase 7, validate_fields.py será atualizado para importar daqui.
#
# O que há aqui:
#   - normalize_digits()      → strip para apenas dígitos
#   - validate_cnpj()         → checksum Módulo 11
#   - parse_currency_value()  → string BR → float (ex: "1.234,56" → 1234.56)
#   - is_valid_date_format()  → verifica padrão DD/MM/AAAA
#
# Regra: zero dependências internas — só stdlib.
# =============================================================================

from __future__ import annotations

import re
from typing import Any, Dict, List


def normalize_digits(value: str) -> str:
    """Remove todos os caracteres não-numéricos. Útil para limpar CNPJ, CPF, CEP."""
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def validate_cnpj(cnpj: str | None) -> bool:
    """
    Valida CNPJ pelo algoritmo oficial (Módulo 11).

    Aceita os formatos:
      - "12.345.678/0001-90"  (formatado)
      - "12345678000190"       (apenas dígitos)

    Retorna False para CNPJ nulo, com comprimento errado ou sequências repetidas.
    """
    digits = normalize_digits(cnpj or "")
    if len(digits) != 14:
        return False

    # Sequências repetidas (00000000000000, 11111111111111, ...) são inválidas.
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


def parse_currency_value(value: str) -> float | None:
    """
    Converte string de moeda brasileira para float.

    Formatos aceitos:
      - "1.234,56"  → 1234.56
      - "1234,56"   → 1234.56
      - "R$ 1.234,56" → 1234.56
      - "1234.56"   → 1234.56  (formato americano — aceito como fallback)

    Retorna None para valor vazio, não-numérico ou zero.
    """
    if not value:
        return None

    # Remove símbolo de moeda e espaços.
    cleaned = re.sub(r"R\$", "", str(value), flags=re.IGNORECASE).strip()
    cleaned = cleaned.replace(" ", "")

    if not cleaned:
        return None

    try:
        # Formato brasileiro: separador de milhar = ".", decimal = ","
        if "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        # Formato americano ou inteiro: separador decimal = "." ou sem decimal
        result = float(cleaned)
        return result if result > 0 else None
    except (ValueError, TypeError):
        return None


def is_valid_date_format(value: str) -> bool:
    """
    Verifica se a string tem formato de data DD/MM/AAAA ou DD/MM/AA.

    Não valida se a data é calendaricamente real (ex: 31/02/2024) —
    apenas verifica o padrão de formatação.
    """
    if not value:
        return False

    pattern = r"^\d{2}/\d{2}/(\d{4}|\d{2})$"
    return bool(re.match(pattern, str(value).strip()))


# =============================================================================
# CONSTANTES E FUNÇÕES AUXILIARES PARA EXTRAÇÃO DE CAMPOS
# =============================================================================

# Campos obrigatórios para NFS-e
REQUIRED_FIELDS = [
    "fornecedor",
    "tomador",
    "cnpj_fornecedor",
    "numero_nf",
    "descricao_servico",
    "valor_nf",
    "retencao",
]

# Thresholds de confiança por campo para fallback
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

# Padrões que indicam valores de cabeçalho (não devem ser valores de campo)
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


def _get_raw_text(data: Dict[str, Any]) -> str:
    """Extrai texto bruto dos dados OCR."""
    return str(data.get("raw_text") or data.get("raw_text_fallback") or "")


def _clean_line(line: str) -> str:
    """Limpa linha removendo espaços múltiplos."""
    return re.sub(r"\s+", " ", str(line or "")).strip()


def _is_header_like_value(value: str) -> bool:
    """Verifica se o valor parece ser um cabeçalho/label em vez de um valor real."""
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
