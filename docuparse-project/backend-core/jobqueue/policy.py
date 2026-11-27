"""Política por etapa da fila de processamento.

Fica em código, não no banco: mudar o número de tentativas é uma decisão de
desenho, revisada em PR. O enqueue copia `max_attempts` para o job, de modo que
uma mudança aqui só vale para jobs novos. O backoff entre tentativas fica em
`jobqueue/backoff.py` (AR-32).
"""

from __future__ import annotations

from dataclasses import dataclass

from jobqueue.models import ProcessingJob


@dataclass(frozen=True)
class StepPolicy:
    max_attempts: int


STEP_POLICIES: dict[str, StepPolicy] = {
    ProcessingJob.Step.OCR: StepPolicy(max_attempts=5),
    ProcessingJob.Step.EXTRACTION: StepPolicy(max_attempts=5),
    # Nunca reenviar à Superlógica automaticamente: um envio que caiu no meio
    # pode ter chegado lá. Perder o heartbeat leva a ERP_FAILED (AR-34).
    ProcessingJob.Step.ERP_DISPATCH: StepPolicy(max_attempts=1),
}


def policy_for(step: str) -> StepPolicy:
    try:
        return STEP_POLICIES[step]
    except KeyError:
        raise ValueError(f"Etapa sem política na fila: {step!r}") from None
