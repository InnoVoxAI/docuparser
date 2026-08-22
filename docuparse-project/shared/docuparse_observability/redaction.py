from __future__ import annotations

# Denylist compartilhada entre o redator de spans (tracing.py) e a persistência
# de TaskExecution.payload (docuparse_orchestrator) — um único lugar decide o
# que é sensível demais pra sair do processo, span ou linha de banco.
DENYLIST_ATTRIBUTES = {"http.request.body", "http.response.body", "authorization"}
DENYLIST_SUFFIXES = ("_token", "_secret", "_password")


def is_denied(key: str) -> bool:
    lowered = key.lower()
    return lowered in DENYLIST_ATTRIBUTES or lowered.endswith(DENYLIST_SUFFIXES)
