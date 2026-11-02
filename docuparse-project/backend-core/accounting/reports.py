"""Taxa de automação: quanto da classificação chegou certa sem o analista tocar."""

from __future__ import annotations

from dataclasses import dataclass

from documents.models import Document, DocumentEvent

from accounting.models import DocumentClassification


@dataclass
class AutomationReport:
    documents: int = 0
    with_condominium: int = 0
    automatic: int = 0  # conta sugerida e mantida
    corrected: int = 0  # o sistema sugeriu, o analista trocou
    manual_only: int = 0  # sem sugestão, o analista escolheu
    without_account: int = 0

    @property
    def rate(self) -> float:
        """Das que têm conta, quantas o sistema acertou sozinho."""
        decided = self.automatic + self.corrected + self.manual_only
        return self.automatic / decided if decided else 0.0


def automation_report() -> AutomationReport:
    report = AutomationReport(documents=Document.objects.count())
    report.with_condominium = Document.objects.exclude(condominium=None).count()
    suggested = set(
        DocumentEvent.objects.filter(
            event_type="document.classified", payload__data__origin="automatic"
        )
        .filter(payload__data__applied=True)
        .exclude(payload__data__ledger_account=None)
        .values_list("document_id", flat=True)
    )
    classified = set()
    for classification in DocumentClassification.objects.all():
        classified.add(classification.document_id)
        if classification.origin == DocumentClassification.Origin.AUTOMATIC:
            report.automatic += 1
        elif classification.document_id in suggested:
            report.corrected += 1
        else:
            report.manual_only += 1
    report.without_account = report.with_condominium - len(classified)
    return report
