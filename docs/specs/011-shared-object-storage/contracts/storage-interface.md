# Contrato — Interface `Storage`

Interface interna que todos os serviços consomem via `docuparse_storage`. Todas as implementações (`LocalStorage`, `S3Storage`, `RoutingStorage`) DEVEM respeitar este contrato de forma intercambiável.

## Tipo de retorno

```python
@dataclass(frozen=True)
class StoredObject:
    uri: str          # "local://<key>" ou "s3://<bucket>/<key>"
    key: str          # "documents/{tenant}/{document}/..."
    size_bytes: int
    sha256: str       # hex sha256 do conteúdo
```

## Métodos

```python
class Storage(Protocol):
    def put_bytes(self, key: str, content: bytes) -> StoredObject: ...
    def get_bytes(self, uri_or_key: str) -> bytes: ...
    def delete(self, uri_or_key: str) -> None: ...
```

### `put_bytes(key, content) -> StoredObject`
- **MUST** validar a key (não-absoluta, sem `..`, não-vazia) antes de gravar.
- **MUST** retornar `StoredObject` com `uri` no esquema do backend de escrita, `size_bytes == len(content)` e `sha256` do conteúdo.
- Assinatura **NÃO** inclui `content_type` (paridade com o código atual; o `content_type` servido ao usuário vem do DB).
- Em falha de gravação, **MUST** propagar exceção — nunca retornar sucesso parcial.

### `get_bytes(uri_or_key) -> bytes`
- Aceita URI com esquema (`local://…`, `s3://…`) **ou** key nua (resolvida no backend default).
- **MUST** levantar `FileNotFoundError` quando o objeto não existe (inclui mapeamento de `NoSuchKey`/404 do S3).
- **MUST** propagar (não engolir) falhas de conexão/credencial como exceção distinta de `FileNotFoundError`.

### `delete(uri_or_key) -> None`
- Idempotente (remover inexistente não é erro), preservando o comportamento atual de `LocalStorage.delete(..., missing_ok=True)`.

## Implementações

| Implementação | Escrita | Leitura | Observações |
|---|---|---|---|
| `LocalStorage` | disco (`root/key`) | `root/key` | comportamento atual, inalterado |
| `S3Storage` | `put_object(bucket, key)` | `get_object`; mapeia 404→`FileNotFoundError` | boto3 lazy import; timeout/retry configurados |
| `RoutingStorage` | delega ao backend configurado | despacha por esquema da URI | único objeto retornado por `get_storage()` |

## `get_storage() -> Storage`
- Único ponto de instanciação no código de aplicação.
- Lê a config de env (ver `storage-config.md`) e retorna um `RoutingStorage`.
- **MUST** preservar comportamento local quando `DOCUPARSE_STORAGE_BACKEND` está ausente ou `local`.
