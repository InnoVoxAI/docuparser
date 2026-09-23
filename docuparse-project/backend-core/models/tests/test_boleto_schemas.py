from __future__ import annotations

import models.boleto.schemas as boleto

BANESE_TEXT = """Local de pagamento
Pagável preferencialmente na rede Banese
Beneficiário
Teste Daniela de Oliveira Nome - CPF/CNPJ: 007.995.835-45
Nosso número 000004683
Vencimento 27/06/2020
Pagador Janis Joplin - CPF/CNPJ: 20.597.314/0001-20
"""


def test_score_matches_accented_keywords() -> None:
    assert boleto.score("Beneficiário Nosso número") == 2


def test_accented_boleto_without_linha_digitavel_is_likely() -> None:
    # beneficiario, nosso numero, vencimento, pagador: 4 keywords, no regex bonus.
    assert boleto.score(BANESE_TEXT) == 4
    assert boleto.is_likely(BANESE_TEXT)
