from __future__ import annotations

import models.nota_fiscal.schemas as nota_fiscal
from models.classifier import classify

# Trechos do OCR real; a conta de agua tambem passa no threshold da nota fiscal.
CONTA_AGUA_TEXT = """Qualidade da Água: www.compesa.com.br
FATURA MENSAL DE ÁGUA E ESGOTO Inicio relação: 14/09/2005
DADOS DO CLIENTE N° Contrato: 1676261 MATRÍCULA:
SITUAÇÃO ÁGUA SITUAÇÃO ESGOTO QUANTIDADE DE ECONOMIAS
HIDROMETRO DATA LEIT.ANTERIOR DATA LEIT. ATUAL TIPO DE CONSUMO(A/E)
ANÁLISES ATENDEM A LEGISLAÇÃO TURBIDEZ IBB IBBISS COR APARENTE IBB IBBISS
DESCRICÃO DOS SERVIÇOS E TARIFAS CONSUMO POR FAIXA VALOR R$
PIS 8.101,60 0,65 52,66
COFINS 8.101,60 3,00 243,05
VENCIMENTO: 15/07/2026 TOTAL A PAGAR: 8.101,60
"""

BOLETO_TEXT = """BANCO ITAU SA
341-7
34191.09990 21296.322932 83012.370009 7 12910000247555
LOCAL DE PAGAMENTO
VENCIMENTO
10/12/2025
BENEFICIARIO: BAHIANA DISTRIBUIDORA DE GAS CPF/CNPJ
DATA DOCUMENTO N. DOCUMENTO TIPO DOC. ACEITE DATA PROC. NOSSO NUMERO
USO DO BANCO CARTEIRA ESPECIE QUANTIDADE VALOR (=)VALOR DOCUMENTO
PAGADOR CONDOMINIO DO EDIFICIO RECIFE COLONIAL - CPF/CNPJ: 02315237000197
"""

NOTA_FISCAL_TEXT = """NOTA FISCAL DE SERVIÇOS ELETRÔNICA - NFS-e
TOMADOR DO SERVIÇO: CONDOMINIO DO EDIFICIO RECIFE COLONIAL
Descricao dos servicos: consultoria juridica
Valor Total R$ 10.000,00
ISS Retido: nao
"""


def test_best_margin_wins_over_first_match() -> None:
    assert nota_fiscal.is_likely(CONTA_AGUA_TEXT)
    assert classify(CONTA_AGUA_TEXT) == "conta_agua_default"


def test_each_type_still_classifies() -> None:
    assert classify(BOLETO_TEXT) == "boleto_default"
    assert classify(NOTA_FISCAL_TEXT) == "nota_fiscal_default"


def test_unrecognized_text_returns_none() -> None:
    assert classify("recibo simples sem layout conhecido") is None
    assert classify("") is None
