"""Motor de classificação. Os fatos vêm de documentos reais da cliente
(docs_por_plano_de_contas), com pessoas físicas anonimizadas."""

from __future__ import annotations

from condominiums.models import Condominium
from django.db import connection
from django.test import TestCase
from tenants.models import Tenant

from accounting.classification import DocumentFacts, classify
from accounting.models import LedgerAccount, SupplierRule

CONDOMINIUM_CNPJ = "11222333000181"
COMPESA = "09.769.035/0001-64"
HECOL = "15.551.751/0001-73"
CORA = "37.880.206/0001-63"
UNION = "08.078.021/0001-31"
ELECTRICIAN_CPF = "111.444.777-35"
MANAGER_CPF = "529.982.247-25"

WATER_BILL = DocumentFacts(
    fields={"cnpj_emissor": COMPESA, "nome_emissor": "COMPESA"},
    raw_text="FATURA MENSAL DE ÁGUA E ESGOTO\nCONDOMINIO DO EDIFICIO EXEMPLO",
)
PEST_CONTROL_BOLETO = DocumentFacts(
    fields={
        "cnpj_cpf_beneficiario": HECOL,
        "beneficiario_nome": "Hecol Saude Ambiental",
        "descricao": "Contrato Parcela 5/12",
    },
    raw_text=f"Beneficiário Hecol Saude Ambiental CNPJ {HECOL}\n"
    f"Intermediado por: Cora Sociedade de Crédito Direto CNPJ {CORA}",
)
SOCIAL_SECURITY_DARF = DocumentFacts(
    fields={"cnpj_cpf_beneficiario": "11.222.333/0001-81"},
    raw_text="""Documento de Arrecadação de Receitas Federais
CNPJ 11.222.333/0001-81 CONDOMINIO DO EDIFICIO EXEMPLO
Código Denominação Principal
1082 CONTR PREV DESCONTA SEGURADO-EMPREGADO/AVULSO 1.778,35
     01 CP SEGURADOS - EMPREGADOS/AVULSO
1138 CONTRIB PREVIDENCIÁRIA EMPRESA/EMPREGADOR 4.741,20
     01 CP PATRONAL - EMPREGADOS/AVULSOS""",
)
INCOME_TAX_DARF = DocumentFacts(
    raw_text="""Documento de Arrecadação de Receitas Federais
CNPJ 11.222.333/0001-81 CONDOMINIO DO EDIFICIO EXEMPLO
0561 IRRF - RENDIMENTO DO TRABALHO ASSALARIADO 312,40""",
)
FGTS_GUIDE = DocumentFacts(
    raw_text="""GFD - Guia do FGTS Digital
CPF/CNPJ do Empregador 11.222.333 CONDOMINIO DO EDIFICIO EXEMPLO
Valor a recolher 1.896,44""",
)


def _receipt(name: str, cpf: str, service: str) -> DocumentFacts:
    return DocumentFacts(
        raw_text=f"""RECIBO
R$ 500,00
Recebi do condomínio Exemplo, CNPJ 11.222.333/0001-81, a importância de
R$ 500,00 referente a {service}.
{name}
CPF: {cpf}"""
    )


class ClassificationTests(TestCase):
    def setUp(self) -> None:
        connection.set_tenant(
            Tenant.objects.create(slug="rules", name="Administradora")
        )
        self.condominium = Condominium.objects.create(
            name="Edifício Exemplo", cnpj=CONDOMINIUM_CNPJ
        )
        self.water = self._account("2.1.01", "Água")
        self.pest_control = self._account("2.3.04", "Dedetização")
        self.maintenance = self._account("2.3.01", "Manutenções")
        self.social_security = self._account(
            "2.4.01", "Inss", nature=LedgerAccount.Nature.INSS
        )
        self.fgts = self._account("2.4.02", "Fgts", nature=LedgerAccount.Nature.FGTS)
        self.individual_services = self._account(
            "2.5.01",
            "Prestação Serviço P-física",
            nature=LedgerAccount.Nature.SERVICO_PESSOA_FISICA,
        )

    def _account(self, code: str, name: str, nature: str = "") -> LedgerAccount:
        return LedgerAccount.objects.create(
            condominium=self.condominium, code=code, name=name, nature=nature
        )

    def _supplier(self, tax_id: str, account: LedgerAccount, keyword: str = ""):
        digits = tax_id.replace(".", "").replace("/", "").replace("-", "")
        return SupplierRule.objects.create(
            condominium=self.condominium,
            supplier_tax_id=digits,
            keyword=keyword,
            ledger_account=account,
        )

    # ── casos do ticket ──────────────────────────────────────────────────────
    def test_utility_company_goes_to_its_supplier_account(self) -> None:
        self._supplier(COMPESA, self.water)
        result = classify(WATER_BILL, self.condominium)
        assert result.ledger_account == self.water
        assert result.rule_id == "supplier"

    def test_social_security_darf_goes_to_inss_account(self) -> None:
        result = classify(SOCIAL_SECURITY_DARF, self.condominium)
        assert result.ledger_account == self.social_security
        assert result.rule_id == "inss"

    def test_pest_control_boleto_ignores_payment_intermediary(self) -> None:
        self._supplier(HECOL, self.pest_control)
        result = classify(PEST_CONTROL_BOLETO, self.condominium)
        assert result.ledger_account == self.pest_control

    def test_unregistered_individual_receipt_goes_to_individual_services(self) -> None:
        receipt = _receipt("Fulano de Tal", MANAGER_CPF, "gerente administrativo")
        result = classify(receipt, self.condominium)
        assert result.ledger_account == self.individual_services
        assert result.rule_id == "recibo_pessoa_fisica"

    # ── regras de conteúdo ───────────────────────────────────────────────────
    def test_non_social_security_darf_is_not_inss(self) -> None:
        assert classify(INCOME_TAX_DARF, self.condominium) is None

    def test_fgts_guide_goes_to_fgts_account(self) -> None:
        assert classify(FGTS_GUIDE, self.condominium).ledger_account == self.fgts

    def test_alimony_receipt_is_not_a_service(self) -> None:
        receipt = _receipt("Beltrana", MANAGER_CPF, "pensão alimentícia")
        assert classify(receipt, self.condominium) is None

    def test_content_rule_needs_an_account_marked_with_the_nature(self) -> None:
        self.social_security.nature = ""
        self.social_security.save()
        assert classify(SOCIAL_SECURITY_DARF, self.condominium) is None

    # ── cadastro de fornecedores ─────────────────────────────────────────────
    def test_registered_individual_wins_over_receipt_rule(self) -> None:
        self._supplier(ELECTRICIAN_CPF, self.maintenance)
        receipt = _receipt("Ciclano", ELECTRICIAN_CPF, "serviço de eletricista")
        result = classify(receipt, self.condominium)
        assert result.ledger_account == self.maintenance
        assert result.rule_id == "supplier"

    def test_keyword_splits_charges_from_the_same_supplier(self) -> None:
        dues = self._account("2.6.01", "Contribuição Associativa")
        staff = self._account("2.6.02", "Pessoal")
        self._supplier(UNION, dues, keyword="MEN")
        self._supplier(UNION, staff, keyword="CAS")
        monthly = DocumentFacts(
            fields={"cnpj_cpf_beneficiario": UNION, "numero_documento": "MEN202605"}
        )
        assistance = DocumentFacts(
            fields={"cnpj_cpf_beneficiario": UNION, "numero_documento": "CAS 202606"}
        )
        assert classify(monthly, self.condominium).ledger_account == dues
        assert classify(assistance, self.condominium).ledger_account == staff

    def test_keyword_rule_falls_back_to_rule_without_keyword(self) -> None:
        self._supplier(UNION, self.maintenance)
        self._supplier(UNION, self.water, keyword="MEN")
        other = DocumentFacts(fields={"cnpj_cpf_beneficiario": UNION})
        assert classify(other, self.condominium).ledger_account == self.maintenance

    def test_inactive_rule_or_account_is_skipped(self) -> None:
        rule = self._supplier(COMPESA, self.water)
        rule.is_active = False
        rule.save()
        assert classify(WATER_BILL, self.condominium) is None
        rule.is_active = True
        rule.save()
        self.water.is_active = False
        self.water.save()
        assert classify(WATER_BILL, self.condominium) is None

    def test_rules_from_another_condominium_do_not_apply(self) -> None:
        other = Condominium.objects.create(name="Outro")
        other_water = LedgerAccount.objects.create(
            condominium=other, code="2.1.01", name="Água"
        )
        SupplierRule.objects.create(
            condominium=other,
            supplier_tax_id="09769035000164",
            ledger_account=other_water,
        )
        assert classify(WATER_BILL, self.condominium) is None

    def test_unknown_supplier_is_left_unclassified(self) -> None:
        assert classify(WATER_BILL, self.condominium) is None

    def test_custom_rule_list_extends_the_engine(self) -> None:
        class AlwaysMaintenance:
            rule_id = "always"

            def apply(self, facts, condominium):
                from accounting.classification import Classification

                return Classification(self.account, self.rule_id, "teste")

        rule = AlwaysMaintenance()
        rule.account = self.maintenance
        result = classify(WATER_BILL, self.condominium, rules=[rule])
        assert result.ledger_account == self.maintenance
