"""Salto 0 — listagem (recursiva) e leitura dos PDFs-lista no Google Drive.

Somente leitura (FR-003): nunca cria/move/apaga nada no Drive.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

PDF_MIME = "application/pdf"
FOLDER_MIME = "application/vnd.google-apps.folder"


@dataclass(frozen=True)
class DrivePdf:
    id: str
    name: str


def list_pdfs(service, folder_ids, *, recursive: bool = True) -> list[DrivePdf]:
    """Lista todos os PDFs das pastas (opcionalmente varrendo subpastas, E-11)."""
    found: list[DrivePdf] = []
    visited: set[str] = set()
    stack: list[str] = list(folder_ids)
    while stack:
        folder_id = stack.pop()
        if folder_id in visited:
            continue
        visited.add(folder_id)
        for entry in _list_children(service, folder_id):
            mime = entry.get("mimeType")
            if mime == PDF_MIME:
                found.append(DrivePdf(entry["id"], entry["name"]))
            elif mime == FOLDER_MIME and recursive:
                stack.append(entry["id"])
    return found


def _list_children(service, folder_id: str) -> list[dict]:
    """Itens diretos de uma pasta (paginado)."""
    children: list[dict] = []
    page_token = None
    query = f"'{folder_id}' in parents and trashed=false"
    while True:
        resp = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        children.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            return children


def download_pdf_bytes(service, file_id: str) -> bytes:
    """Baixa os bytes de um PDF-lista para leitura local (um por vez)."""
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()
