from __future__ import annotations

from collections.abc import Callable, Iterator

from .keys import StoredObject
from .local import LocalStorage
from .s3 import S3Storage


class RoutingStorage:
    """Storage único que escreve no backend configurado e lê despachando pelo
    esquema da URI, habilitando coexistência ``local://`` / ``s3://`` (migração
    incremental + rollback). Ver contracts/storage-uri.md.

    - ``put_bytes`` → backend de escrita (``local`` ou ``s3``).
    - ``get_bytes``/``delete`` → despacham por esquema: ``local://`` → local;
      ``s3://`` → s3; key nua → backend de escrita.

    O backend S3 pode ser fornecido de forma lazy (``s3_provider``) para que o
    modo ``local`` não construa um cliente boto3 a menos que precise ler uma URI
    ``s3://`` legada.
    """

    def __init__(
        self,
        *,
        write_scheme: str,
        local: LocalStorage,
        s3: S3Storage | None = None,
        s3_provider: Callable[[], S3Storage] | None = None,
    ) -> None:
        if write_scheme not in {"local", "s3"}:
            raise ValueError(f"unsupported write_scheme: {write_scheme!r}")
        self._write_scheme = write_scheme
        self._local = local
        self._s3 = s3
        self._s3_provider = s3_provider

    # -- API pública -------------------------------------------------------

    def put_bytes(self, key: str, content: bytes) -> StoredObject:
        return self._write_backend().put_bytes(key, content)

    def get_bytes(self, uri_or_key: str) -> bytes:
        return self._backend_for(uri_or_key).get_bytes(uri_or_key)

    def delete(self, uri_or_key: str) -> None:
        self._backend_for(uri_or_key).delete(uri_or_key)

    def exists(self, uri_or_key: str) -> bool:
        return self._backend_for(uri_or_key).exists(uri_or_key)

    def iter_keys(self, prefix: str = "") -> Iterator[str]:
        # Lista o backend de escrita (onde os objetos novos vivem). Objetos
        # legados no outro esquema não são listados aqui (por design).
        return self._write_backend().iter_keys(prefix)

    # -- Roteamento --------------------------------------------------------

    def _write_backend(self):
        return self._s3_backend() if self._write_scheme == "s3" else self._local

    def _backend_for(self, uri_or_key: str):
        if uri_or_key.startswith("s3://"):
            return self._s3_backend()
        if uri_or_key.startswith("local://"):
            return self._local
        # key nua → backend de escrita configurado
        return self._write_backend()

    def _s3_backend(self) -> S3Storage:
        if self._s3 is None:
            if self._s3_provider is None:
                raise RuntimeError(
                    "S3 storage não configurado: defina DOCUPARSE_STORAGE_BACKEND=s3 "
                    "e as variáveis S3_BUCKET/credenciais para ler ou gravar objetos s3://."
                )
            self._s3 = self._s3_provider()
        return self._s3
