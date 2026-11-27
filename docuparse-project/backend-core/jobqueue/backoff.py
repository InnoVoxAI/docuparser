"""Intervalo entre tentativas de um job transitório (AR-32).

30 s, 2 min, 8 min e 30 min (dali em diante, sempre 30 min), com ±20% de
jitter para que vários documentos que falharam juntos (ex.: o backend-ocr fora
do ar) não voltem todos no mesmo segundo. O número de tentativas fica na
política da etapa (`jobqueue/policy.py`); aqui só se calcula a espera.
"""

from __future__ import annotations

import random

BASE_DELAYS_SECONDS: tuple[int, ...] = (30, 120, 480, 1800)
JITTER = 0.2


def backoff_seconds(attempts: int, *, rng: random.Random | None = None) -> float:
    """Espera antes da próxima tentativa, dado quantas já foram feitas.

    `attempts` é o valor do job depois do claim que falhou: 1 após a primeira
    tentativa, 2 após a segunda, e assim por diante.
    """
    if attempts < 1:
        raise ValueError(f"attempts deve ser >= 1, recebido {attempts}")
    base = BASE_DELAYS_SECONDS[min(attempts, len(BASE_DELAYS_SECONDS)) - 1]
    return base * (rng or random).uniform(1 - JITTER, 1 + JITTER)
