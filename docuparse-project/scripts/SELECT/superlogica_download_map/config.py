"""Configuração parametrizável da Fase A (FR-024).

Nada de decisões provisórias hardcoded no meio da lógica: IDs das pastas do
Drive, dicionário de famílias de categorias, tolerâncias e política de HTTP
vivem aqui. Caminhos de saída são resolvidos relativos ao diretório de trabalho.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# --- Google Drive -----------------------------------------------------------
# Pastas designadas (links fornecidos pelo humano):
#   https://drive.google.com/drive/folders/<ID>
#
# A lista é acumulativa: cada remessa nova entra aqui e o mapa cresce por append
# (o MapWriter deduplica por url_download, que é estável entre execuções). Para
# processar só uma pasta sem re-resolver as antigas, use ``--folder-id``.
DRIVE_FOLDER_IDS: tuple[str, ...] = (
    "1uJ6cZYbThBxiKcfcMmrlS-9dn-aVJfzr",  # Itens do plano de contas
    "13r1wG8rj8YFvYefPoDYhFg-aVESRZMgE",  # Relatório com as despesas individuais classificadas
    "1qxZn3yINwegQnx3QU79d-Z3GV_ZHTMl8",  # 2ª Remessa de plano de contas (Jeane)
)
DRIVE_FOLDER_URLS: tuple[str, ...] = tuple(
    f"https://drive.google.com/drive/folders/{fid}" for fid in DRIVE_FOLDER_IDS
)
# Somente leitura (precisa ler os bytes dos PDFs).
DRIVE_SCOPES: tuple[str, ...] = ("https://www.googleapis.com/auth/drive.readonly",)

# --- Classificação de categoria (Seção 6) -----------------------------------
# Separador estrito categoria/complemento: espaço-hífen-espaço.
CATEGORY_SEP = " - "
FALLBACK_FOLDER = "_A_Revisar"

# Regras de família (ordenadas; a PRIMEIRA que casar vence — via re.search, ou
# seja, casam em QUALQUER posição da chave). Casam contra a CHAVE CANÔNICA
# (minúscula, sem acento/pontuação) da categoria_bruta.
#
# Calibrado a partir de categorias_encontradas.csv (recon real do condomínio).
# Ordem: (1) ruído de extração → _A_Revisar; (2) famílias específicas antes das
# genéricas. Ajuste conforme necessário e rode --recon de novo.
FAMILY_RULES: tuple[tuple[str, str], ...] = (
    # (1) Ruído de extração: fragmentos de complemento capturados como categoria
    # (datas, parcelas, meses, e restos que começam com preposição). → revisão.
    (r"^\d", FALLBACK_FOLDER),                       # 2025, "2025 2026", "1 de 3"
    (r"\bparc\b", FALLBACK_FOLDER),                  # "parc 10 10", "parc jan a maio..."
    (r"^(janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b",
     FALLBACK_FOLDER),                               # "maio", "junho 26"
    (r"^(de|do|da|e|para|com|sem)\b", FALLBACK_FOLDER),  # "de bombas", "e esgoto", "do poco"
    (r"^(art|contrato|substituicao|impermeabilizacao|corretiva)\b", FALLBACK_FOLDER),

    # (2) Famílias reais
    (r"constru|reforma|obra", "Construção-Reformas"),
    (r"manut", "Manutenções"),
    (r"elevador", "Manutenções"),
    (r"bomba", "Manutenções"),
    (r"agua mineral", "Água Mineral"),               # consumo (antes da regra genérica de água)
    (r"hidraul|esgoto|\bpoco\b|agua", "Água"),
    (r"energia|eletrica", "Energia"),                # NÃO pega "eletronica" nem "elevador"
    (r"cftv|portaria|vigi|eletronic", "Segurança"),
    (r"^seguro", "Seguros"),                         # "Seguro ..." (≠ Segurança)
    (r"funcionario|salario|laboral", "Pessoal"),
    (r"administr|condominial|obrigatorio condominio|boleto|telefone|internet", "Administração"),
    (r"piscina", "Piscina"),
    (r"aliment", "Alimentação"),
    (r"combustivel", "Combustível"),
    (r"transporte", "Transporte"),
    (r"dedetiz", "Dedetização"),
)

# --- Heurística de cruzamento no PDF (Seção 5.2) ----------------------------
# Tolerância vertical como fração da altura média de linha.
Y_TOLERANCE_RATIO = 0.5

# --- Política de HTTP com o Superlógica (E-10) ------------------------------
HTTP_RETRIES = 3
HTTP_BACKOFF_BASE_S = 2.0
HTTP_PAUSE_S = 1.0
HTTP_TIMEOUT_S = 30.0

RECURSIVE_DEFAULT = True
MAP_FORMAT_DEFAULT = "csv"


@dataclass(frozen=True)
class Config:
    """Configuração resolvida para uma execução."""

    work_dir: Path
    credentials_file: Path
    token_file: Path
    map_path: Path
    report_path: Path
    categories_path: Path
    downloads_root: Path
    map_format: str = MAP_FORMAT_DEFAULT
    recursive: bool = RECURSIVE_DEFAULT
    drive_folder_ids: tuple[str, ...] = DRIVE_FOLDER_IDS
    drive_scopes: tuple[str, ...] = DRIVE_SCOPES
    family_rules: tuple[tuple[str, str], ...] = FAMILY_RULES
    y_tolerance_ratio: float = Y_TOLERANCE_RATIO
    http_retries: int = HTTP_RETRIES
    http_backoff_base_s: float = HTTP_BACKOFF_BASE_S
    http_pause_s: float = HTTP_PAUSE_S
    http_timeout_s: float = HTTP_TIMEOUT_S


def build_config(
    work_dir: str | Path,
    *,
    map_format: str = MAP_FORMAT_DEFAULT,
    recursive: bool = RECURSIVE_DEFAULT,
    credentials: str | Path | None = None,
    folder_ids: Sequence[str] | None = None,
) -> Config:
    """Constrói a configuração com caminhos relativos ao ``work_dir`` (FR-018).

    ``folder_ids`` sobrescreve :data:`DRIVE_FOLDER_IDS` — útil para varrer só uma
    remessa nova sem re-resolver os hyperlinks das pastas já mapeadas.
    """
    wd = Path(work_dir).resolve()
    ext = "json" if map_format == "json" else "csv"
    creds = Path(credentials).resolve() if credentials else wd / "credentials.json"
    return Config(
        work_dir=wd,
        credentials_file=creds,
        token_file=wd / "token.json",
        map_path=wd / f"mapa_download.{ext}",
        report_path=wd / "fase_a_relatorio.csv",
        categories_path=wd / "categorias_encontradas.csv",
        downloads_root=wd / "downloads",
        map_format=map_format,
        recursive=recursive,
        drive_folder_ids=tuple(folder_ids) if folder_ids else DRIVE_FOLDER_IDS,
    )
