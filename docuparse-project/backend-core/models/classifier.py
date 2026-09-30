from __future__ import annotations

import models.boleto.schemas as _boleto
import models.contadeagua.schemas as _agua
import models.nota_fiscal.schemas as _nf

# A ordem só desempata margens iguais.
_CLASSIFIERS = (_nf, _agua, _boleto)


def classify(raw_text: str) -> str | None:
    """Retorna o schema_id cujo score mais supera o próprio threshold, ou None."""
    best_schema_id: str | None = None
    best_margin = -1
    for classifier in _CLASSIFIERS:
        margin = classifier.score(raw_text) - classifier.THRESHOLD
        if margin > best_margin and margin >= 0:
            best_schema_id, best_margin = classifier.SCHEMA_ID, margin
    return best_schema_id
