"""Helper de paginação manual por query params (feature 009).

As views de `documents/` são function-based (`@api_view`) e o DRF não tem
paginação default configurada (apenas auth). Este módulo concentra o parsing de
`page`/`page_size` (reusando o estilo de `_positive_int` de `views.py`), o
recorte do queryset e a montagem do envelope
`{results, count, page, page_size, total_pages}` esperado pelo frontend
(ver data-model.md / research D1).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 25


def parse_page(value: Any, *, default: int = 1) -> int:
    """Página solicitada (1-based). Valores inválidos/abaixo de 1 → `default`."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 1)


def parse_page_size(
    value: Any,
    *,
    default: int = DEFAULT_PAGE_SIZE,
    maximum: int = MAX_PAGE_SIZE,
) -> int:
    """Tamanho da página com cap em `maximum` (25 por RF-02). Inválido → `default`."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, 1), maximum)


@dataclass(frozen=True)
class PageResult:
    """Resultado de uma paginação: itens da página + metadados."""

    items: list[Any]
    count: int
    page: int
    page_size: int
    total_pages: int

    def envelope(self, serialized: Any) -> dict[str, Any]:
        """Monta o envelope paginado a partir dos dados já serializados."""
        return {
            "results": serialized,
            "count": self.count,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
        }


def paginate_queryset(
    queryset: Any,
    request: Any,
    *,
    default_page_size: int = DEFAULT_PAGE_SIZE,
    max_page_size: int = MAX_PAGE_SIZE,
) -> PageResult:
    """Recorta `queryset` conforme `page`/`page_size` da request.

    `count` é calculado no banco antes do slice; `total_pages` é
    `ceil(count / page_size)` (0 quando vazio). O slice
    `queryset[offset:offset + page_size]` evita carregar a base inteira.
    """
    page = parse_page(request.query_params.get("page"))
    page_size = parse_page_size(
        request.query_params.get("page_size"),
        default=default_page_size,
        maximum=max_page_size,
    )
    count = queryset.count()
    total_pages = ceil(count / page_size) if count else 0
    offset = (page - 1) * page_size
    items = list(queryset[offset:offset + page_size])
    return PageResult(
        items=items,
        count=count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
