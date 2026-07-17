"""Cliente do backend-ocr — o mesmo serviço que a aplicação usa no fluxo principal.

Espelha o contrato de ``documents/services/ocr_client.py`` (backend-core):
``POST /api/v1/process`` multipart com ``legacy_extraction=false``. A cópia é
deliberada: importar o OCRClient do backend-core arrastaria ``django.conf.settings``
(e portanto DB, tenant e storage) para dentro de um script de linha de comando,
sendo que aqui só interessa a etapa documento → texto bruto.

A escolha do texto segue ``ocr_processor.process_document_ocr``:
``raw_text or raw_text_fallback``.
"""

from __future__ import annotations

import mimetypes
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from raw_text_maker.config import Config


class ServiceUnavailable(RuntimeError):
    """backend-ocr inalcançável no preflight (fatal — nada a fazer nesta run)."""


@dataclass
class OcrOutcome:
    """Resultado de uma tentativa de extração (fail-soft)."""

    ok: bool
    raw_text: str = ""
    raw_text_formatted: str = ""
    engine: str = ""
    document_type: str = ""
    motivo: str = ""
    tentativas: int = 0


def check_service(config: Config, *, session: requests.Session | None = None) -> list[str]:
    """Preflight: confirma que o backend-ocr responde e devolve os engines.

    Sem isso, um serviço fora do ar viraria 98 falhas idênticas e lentas em vez
    de uma mensagem clara logo no começo.
    """
    http = session or requests
    url = f"{config.ocr_url}/api/v1/engines"
    try:
        response = http.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ServiceUnavailable(f"backend-ocr não respondeu em {url}: {exc}") from exc
    except ValueError as exc:
        raise ServiceUnavailable(f"resposta inválida de {url}: {exc}") from exc
    return [str(e.get("name", "")) for e in payload.get("engines", [])]


def _is_retryable(exc: requests.RequestException) -> bool:
    """Só repete o que pode mudar numa próxima tentativa.

    Timeout e falha de conexão são transitórios; 5xx pode ser sobrecarga
    momentânea. Um 4xx (arquivo inválido/vazio) daria o mesmo erro três vezes —
    e, com o timeout de 300s, insistir custa caro.
    """
    if isinstance(exc, requests.Timeout | requests.ConnectionError):
        return True
    response = getattr(exc, "response", None)
    return response is not None and response.status_code >= 500


def extract_raw_text(
    source: Path,
    config: Config,
    *,
    session: requests.Session | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> OcrOutcome:
    """Envia o documento ao backend-ocr e devolve o texto bruto (nunca levanta)."""
    http = session or requests
    url = f"{config.ocr_url}/api/v1/process"
    mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"

    tentativas = 0
    ultimo_motivo = "erro desconhecido"

    for tentativa in range(1, config.ocr_retries + 1):
        tentativas = tentativa
        try:
            # Reabre a cada tentativa: um retry precisa do stream no início.
            with open(source, "rb") as fh:
                data = {"legacy_extraction": "false"}
                if config.engine:
                    data["selected_engine"] = config.engine
                response = http.post(
                    url,
                    files={"file": (source.name, fh, mime_type)},
                    data=data,
                    timeout=config.ocr_timeout_s,
                )
            response.raise_for_status()
            result = response.json()
        except requests.RequestException as exc:
            ultimo_motivo = _describe(exc)
            if not _is_retryable(exc) or tentativa == config.ocr_retries:
                break
            sleep(config.ocr_backoff_base_s ** tentativa)  # backoff exponencial
            continue
        except ValueError as exc:  # JSON inválido — resposta corrompida
            ultimo_motivo = f"resposta não-JSON do backend-ocr: {exc}"
            break
        except OSError as exc:  # documento de origem ilegível
            return OcrOutcome(
                ok=False, motivo=f"falha ao ler o arquivo: {exc}", tentativas=tentativa
            )

        raw_text = result.get("raw_text") or result.get("raw_text_fallback") or ""
        raw_text_formatted = result.get("raw_text_formatted") or ""
        engine = str(result.get("engine_used", "unknown"))
        document_type = str(result.get("document_type", "unknown"))
        if not raw_text.strip():
            # Texto vazio não vira .txt: gravá-lo faria a retomada dar o
            # documento por pronto e nunca mais tentar. Vira erro e é reprocessado.
            return OcrOutcome(
                ok=False,
                engine=engine,
                document_type=document_type,
                motivo=f"OCR não devolveu texto (engine={engine}, tipo={document_type})",
                tentativas=tentativa,
            )
        return OcrOutcome(
            ok=True,
            raw_text=raw_text,
            raw_text_formatted=raw_text_formatted,
            engine=engine,
            document_type=document_type,
            tentativas=tentativa,
        )

    return OcrOutcome(ok=False, motivo=ultimo_motivo, tentativas=tentativas)


def _describe(exc: requests.RequestException) -> str:
    """Mensagem curta e acionável para o CSV de erros."""
    response = getattr(exc, "response", None)
    if response is not None:
        detalhe = (response.text or "").strip().replace("\n", " ")[:200]
        status = f"HTTP {response.status_code}"
        return f"{status}: {detalhe}" if detalhe else status
    if isinstance(exc, requests.Timeout):
        return "timeout aguardando o backend-ocr"
    if isinstance(exc, requests.ConnectionError):
        return "falha de conexão com o backend-ocr"
    return f"{type(exc).__name__}: {exc}"
