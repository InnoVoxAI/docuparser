from __future__ import annotations

from typing import Iterator, Protocol, runtime_checkable

from .keys import StoredObject


@runtime_checkable
class Storage(Protocol):
    """Contrato de storage de objetos, implementado por LocalStorage, S3Storage
    e RoutingStorage de forma intercambiável (ver contracts/storage-interface.md).

    Regras:
      - ``put_bytes`` valida a key e devolve um ``StoredObject`` cuja ``uri`` traz
        o esquema do backend de escrita (``local://`` ou ``s3://``). Assinatura
        SEM ``content_type`` (paridade com o código atual; o content_type servido
        ao usuário vem do banco).
      - ``get_bytes`` aceita URI com esquema OU key nua e levanta
        ``FileNotFoundError`` quando o objeto não existe (inclui 404/NoSuchKey do
        S3). Falhas de conexão/credencial devem propagar como exceção distinta.
      - ``delete`` é idempotente (remover inexistente não é erro).
      - ``exists`` devolve ``True``/``False`` sem baixar o objeto (HEAD no S3);
        falhas de conexão/credencial propagam (não confundir com "não existe").
      - ``iter_keys`` lista as keys do backend de escrita sob ``prefix`` (para
        reconciliação banco ↔ storage). Não aceita URI com esquema — sempre keys.
    """

    def put_bytes(self, key: str, content: bytes) -> StoredObject: ...

    def get_bytes(self, uri_or_key: str) -> bytes: ...

    def delete(self, uri_or_key: str) -> None: ...

    def exists(self, uri_or_key: str) -> bool: ...

    def iter_keys(self, prefix: str = "") -> Iterator[str]: ...
