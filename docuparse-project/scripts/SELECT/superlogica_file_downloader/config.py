"""Configuração parametrizável da Fase B (FR-024).

Constantes de política de rede, assinatura de validação e colunas de saída ficam
aqui, no topo — nunca espalhadas na lógica. Caminhos são resolvidos relativos ao
diretório de trabalho (cwd), honrando "saída local" (FR-015).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# --- Política de HTTP com o Superlógica (E-09/E-10) -------------------------
# Defaults alinhados à Fase A para consistência operacional.
HTTP_PAUSE_S = 1.0
HTTP_TIMEOUT_S = 30.0
HTTP_RETRIES = 3
HTTP_BACKOFF_BASE_S = 2.0

# --- Validação de conteúdo (E-05, research D2) ------------------------------
PDF_SIGNATURE = b"%PDF"
# Aceitar imagens (JPEG/PNG/…) além de PDF: comprovantes fotografados vêm como
# imagem e a Fase C extrai o texto deles via OCR. --pdf-only restaura o antigo.
ACCEPT_IMAGES_DEFAULT = True

MAP_FORMAT_DEFAULT = "csv"

# --- Colunas de saída (contratos relatorio-final.md / fase-b-erros.md) ------
FINAL_COLUMNS: tuple[str, ...] = (
    "nome_arquivo",
    "hyperlink_origem",
    "categoria",
    "caminho_local",
    "pasta_destino",
    "fornecedor",
)
ERROR_COLUMNS: tuple[str, ...] = (
    "url_download",
    "motivo",
    "tentativas",
    "possivel_expiracao",
    "nome_arquivo",
    "pdf_origem",
)


@dataclass(frozen=True)
class Config:
    """Configuração resolvida para uma execução."""

    work_dir: Path
    map_path: Path
    downloads_root: Path
    final_csv_path: Path
    errors_path: Path
    map_format: str = MAP_FORMAT_DEFAULT
    http_pause_s: float = HTTP_PAUSE_S
    http_timeout_s: float = HTTP_TIMEOUT_S
    http_retries: int = HTTP_RETRIES
    http_backoff_base_s: float = HTTP_BACKOFF_BASE_S
    pdf_signature: bytes = PDF_SIGNATURE
    accept_images: bool = ACCEPT_IMAGES_DEFAULT


def build_config(
    work_dir: str | Path,
    *,
    map_format: str = MAP_FORMAT_DEFAULT,
    map_path: str | Path | None = None,
    downloads_root: str | Path | None = None,
    final_csv_path: str | Path | None = None,
    errors_path: str | Path | None = None,
    pause: float | None = None,
    timeout: float | None = None,
    retries: int | None = None,
    accept_images: bool = ACCEPT_IMAGES_DEFAULT,
) -> Config:
    """Constrói a configuração com caminhos relativos ao ``work_dir`` (FR-015)."""
    wd = Path(work_dir).resolve()
    ext = "json" if map_format == "json" else "csv"
    return Config(
        work_dir=wd,
        map_path=Path(map_path).resolve() if map_path else wd / f"mapa_download.{ext}",
        downloads_root=Path(downloads_root).resolve() if downloads_root else wd / "downloads",
        final_csv_path=(
            Path(final_csv_path).resolve() if final_csv_path else wd / "relatorio_final.csv"
        ),
        errors_path=Path(errors_path).resolve() if errors_path else wd / "fase_b_erros.csv",
        map_format=map_format,
        http_pause_s=pause if pause is not None else HTTP_PAUSE_S,
        http_timeout_s=timeout if timeout is not None else HTTP_TIMEOUT_S,
        http_retries=retries if retries is not None else HTTP_RETRIES,
        accept_images=accept_images,
    )
