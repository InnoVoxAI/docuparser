"""Resolução do nome/caminho final de cada arquivo (E-06/E-07, research D1).

- Sanitiza ``nome_arquivo`` e ``pasta_destino`` reusando ``sanitize`` da Fase A.
- Garante extensão ``.pdf`` (o alvo é sempre PDF).
- Fallback determinístico quando ``nome_arquivo`` vem vazio (RN-3).
- **Anti-colisão determinística**: colisões são resolvidas a partir do *conteúdo
  do mapa* (não do estado do disco), prefixando o ``id`` da URL — ``{id}_{nome}``.
  Isso torna o caminho final estável entre execuções (pré-requisito da retomada).
- :func:`settled_path` cobre a **colisão superveniente**: quando uma remessa nova
  acrescenta um arquivo homônimo, o nome calculado de uma linha **já baixada**
  passa a levar prefixo, mas o arquivo antigo continua no disco sem ele. Aceitar
  o nome base evita re-baixar (e duplicar) o que já está pronto.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from superlogica_download_map.sanitize import sanitize

if TYPE_CHECKING:
    from superlogica_file_downloader.config import Config
    from superlogica_file_downloader.map_io import MapRow

FALLBACK_FOLDER = "_A_Revisar"

# Extensões de documento preservadas no nome final (o resto é normalizado para
# ``.pdf``). Alinhado a raw_text_maker.config.SOURCE_EXTENSIONS: PDF + imagens que
# o backend-ocr processa. Um comprovante ``.jpg`` não pode virar ``.jpg.pdf``.
DOCUMENT_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
)


def url_id(url_download: str) -> str:
    """``id`` do parâmetro de query da URL de download (discriminador estável)."""
    query = parse_qs(urlparse(url_download).query)
    return (query.get("id") or [""])[0]


def ensure_document_ext(name: str) -> str:
    """Preserva uma extensão de documento conhecida; senão assume ``.pdf``.

    O alvo majoritário é PDF, mas comprovantes chegam como imagem — forçar
    ``.pdf`` em cima de ``.jpg`` (o que o código antigo fazia) corromperia o nome
    e confundiria a Fase C, que roteia por extensão.
    """
    suffix = Path(name).suffix.lower()
    return name if suffix in DOCUMENT_EXTENSIONS else f"{name}.pdf"


def base_name(row: MapRow) -> str:
    """Nome base sanitizado; fallback ``{fornecedor}_{id}.pdf`` se vazio (RN-3)."""
    nome = sanitize(row.nome_arquivo, fallback="")
    if not nome:
        forn = sanitize(row.fornecedor, fallback="fornecedor").replace(" ", "_")
        nome = f"{forn}_{url_id(row.url_download) or 'arquivo'}.pdf"
    return ensure_document_ext(nome)


def dest_dir(config: Config, row: MapRow) -> Path:
    """Diretório de destino (cria ``_A_Revisar`` quando a pasta é indeterminada)."""
    pasta = sanitize(row.pasta_destino, fallback=FALLBACK_FOLDER)
    return config.downloads_root / pasta


def assign_final_paths(config: Config, rows: list[MapRow]) -> dict[str, Path]:
    """Mapeia ``url_download`` → caminho final, resolvendo colisões deterministicamente.

    Duas linhas que cairiam no mesmo ``<pasta>/<nome>`` recebem **ambas** o
    prefixo ``{id}_`` (E-06). A decisão depende só do mapa, então é estável entre
    execuções e não é afetada pela ordem nem pelo que já está em disco.
    """
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    computed: list[tuple[MapRow, Path, str]] = []
    for row in rows:
        directory = dest_dir(config, row)
        base = base_name(row)
        groups[(str(directory), base)].append(row.url_download)
        computed.append((row, directory, base))

    paths: dict[str, Path] = {}
    for row, directory, base in computed:
        collides = len(set(groups[(str(directory), base)])) > 1
        name = f"{url_id(row.url_download) or 'x'}_{base}" if collides else base
        paths[row.url_download] = directory / name
    return paths


def base_path(config: Config, row: MapRow) -> Path:
    """Caminho que a linha teria **sem** o prefixo anti-colisão."""
    return dest_dir(config, row) / base_name(row)


def settled_path(
    assigned: Path,
    base: Path,
    *,
    exists: Callable[[Path], bool] = Path.exists,
) -> Path | None:
    """Onde a linha **já está** gravada, ou ``None`` se ainda não está.

    Prefere o caminho atribuído. Se ele não existir mas o nome base existir, a
    colisão surgiu **depois** do download (uma remessa nova trouxe um homônimo):
    o arquivo antigo fica onde está — renomeá-lo órfãozaria o ``.txt`` já
    produzido a partir dele, e re-baixá-lo criaria uma duplicata.
    """
    if exists(assigned):
        return assigned
    if base != assigned and exists(base):
        return base
    return None
