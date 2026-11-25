"""Espera crescente e limite de tentativas do reenvio ao ERP."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.utils import timezone

# Marcador gravado antes do POST ao ERP: mostra que um envio pode ter sido aceito.
STARTED_KEY = "send_started_at"
# Impressão digital do que foi enviado: detecta o documento corrigido depois de um envio
# sem resposta, quando a reconciliação não consegue achar a despesa pelos dados novos.
FINGERPRINT_KEY = "send_draft_fingerprint"

MAX_ATTEMPTS = 5
# Espera, em minutos, depois da 1ª, 2ª, 3ª e das demais falhas retentáveis.
BACKOFF_MINUTES = (1, 5, 15, 60)


def next_retry_at(retry_count: int, now: datetime | None = None) -> datetime | None:
    """Quando o reenvio manual fica liberado; None quando as tentativas se esgotaram."""
    if retry_count >= MAX_ATTEMPTS:
        return None
    now = now or timezone.now()
    index = min(max(retry_count, 1), len(BACKOFF_MINUTES)) - 1
    return now + timedelta(minutes=BACKOFF_MINUTES[index])
