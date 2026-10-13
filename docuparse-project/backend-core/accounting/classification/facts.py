from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any

from condominiums.tax_ids import is_valid_tax_id, normalize_tax_id
from condominiums.text import normalize_text

if TYPE_CHECKING:
    from accounting.models import LedgerAccount

# Campo com o CNPJ/CPF de quem cobra, por schema (boleto, nota fiscal, conta de consumo).
SUPPLIER_FIELDS = ("cnpj_cpf_beneficiario", "cnpj_fornecedor", "cnpj_emissor")

_TAX_ID_IN_TEXT = re.compile(
    r"\b[0-9A-Z]{2}\.[0-9A-Z]{3}\.[0-9A-Z]{3}/[0-9A-Z]{4}-\d{2}\b"
    r"|\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"
)


@dataclass(frozen=True)
class DocumentFacts:
    """O que as regras sabem de um documento: campos extraídos e texto bruto."""

    fields: Mapping[str, Any] = field(default_factory=dict)
    raw_text: str = ""

    @cached_property
    def text(self) -> str:
        """Texto bruto e campos de texto, normalizados."""
        values = [
            self.raw_text,
            *(v for v in self.fields.values() if isinstance(v, str)),
        ]
        return normalize_text(" ".join(values))

    @cached_property
    def tax_ids_in_text(self) -> frozenset[str]:
        found = {normalize_tax_id(m) for m in _TAX_ID_IN_TEXT.findall(self.raw_text)}
        return frozenset(tax_id for tax_id in found if is_valid_tax_id(tax_id))

    def supplier_tax_id(self, payer_cnpj: str) -> str | None:
        """CNPJ/CPF de quem cobra, ignorando o do condomínio pagador.

        Prefere os campos extraídos. No texto bruto só vale um candidato único,
        porque boletos de intermediários (ex. Cora) trazem mais de um CNPJ.
        """
        for name in SUPPLIER_FIELDS:
            tax_id = normalize_tax_id(str(self.fields.get(name) or ""))
            if tax_id != payer_cnpj and is_valid_tax_id(tax_id):
                return tax_id
        candidates = self.tax_ids_in_text - {payer_cnpj}
        return next(iter(candidates)) if len(candidates) == 1 else None


@dataclass(frozen=True)
class Classification:
    ledger_account: LedgerAccount
    rule_id: str
    reason: str
