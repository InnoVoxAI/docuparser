from __future__ import annotations

from typing import Protocol, runtime_checkable

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
    """

    def put_bytes(self, key: str, content: bytes) -> StoredObject: ...

    def get_bytes(self, uri_or_key: str) -> bytes: ...

    def delete(self, uri_or_key: str) -> None: ...
