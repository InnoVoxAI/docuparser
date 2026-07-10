# Plano de implementação — Migração de armazenamento local → S3/MinIO

> Status: proposta (nenhum código alterado). Requer validação dos pontos em aberto (§6) antes de implementar.
> Escopo: substituir o armazenamento local não compartilhado por um storage de objetos (S3/MinIO) compartilhado entre os múltiplos backends, **sem regressão** do comportamento atual.

---

## Revisão desta versão (o que mudou em relação ao rascunho inicial)

Ao revisar o plano contra o código real, três incoerências/lacunas foram corrigidas:

1. **Desenho da abstração simplificado para um único `RoutingStorage`.** O rascunho mandava usar `get_storage()` para escrita e `resolve_for_uri()` para leitura — incoerente, porque os *workers* (ocr/layout/langextract) recebem o `storage` **injetado no bootstrap** e chamam `storage.get_bytes(uri)` **dentro do handler**. Trocar isso exigiria mexer em todo handler. Solução coerente: um único objeto `RoutingStorage` (escrita → backend configurado; leitura → despacha pelo esquema da URI). Assim, tanto os chamadores diretos quanto os workers só precisam trocar o ponto de **instanciação/wiring**, sem tocar na lógica.
2. **Contrato de `put_bytes` preservado exatamente:** assinatura `(key, content) -> StoredObject`, **sem** `content_type`. Os chamadores usam `stored.uri`, `stored.sha256`, `stored.size_bytes`. O `content_type` servido ao browser vem do **DB** (`document.content_type`), não do storage — logo o `S3Storage` não precisa (nem deve) mudar a assinatura.
3. **Dois pontos de I/O órfãos adicionais** foram catalogados: o bypass da abstração em `layout-service/api/app.py` e a escrita de export em `approved_exporter.py`.

---

## 1. Validação do diagnóstico

O diagnóstico do responsável por infra (armazenamento local não compartilhado entre backends) é **arquiteturalmente correto**, porém há uma ressalva **decisiva**: ele **não explica o sintoma atualmente reportado** ("documento não aparece na listagem"). São **dois bugs distintos**.

### (a) O sintoma atual é de rede, não de storage
O log `document_received_core_sync_failed` mostra que o documento **nem chega ao banco do backend-core**, porque a sincronização síncrona com→core falha **antes** de qualquer leitura de arquivo:

- `_sync_document_received_to_core` — `backend-com/src/backend_com/services/document_ingest.py:107-139` — faz um `POST` para o core (`/api/ocr/events/document-received`) com `timeout=2`; em falha, loga `document_received_core_sync_failed`, retorna `"failed"`, **mas o upload devolve sucesso** ("Documento recebido") ao frontend.

Como o documento nunca é persistido no core, ele não aparece na listagem (`documents_inbox_view`). **Migrar para S3 não corrige isso.** Causa provável: URL do core apontando para `127.0.0.1` em staging, timeout de 2s, ou token/SECRET_KEY inconsistente entre serviços (ver plano de rede separado).

### (b) O problema de storage é real e se manifestará assim que (a) for corrigido
Confirmado no código: **cada serviço instancia `LocalStorage` apontando para o disco do próprio pod** (`DOCUPARSE_LOCAL_STORAGE_DIR`, default `/data/storage`), e são processos/pods separados:

- backend-com **escreve** o arquivo original — `document_ingest.py:58`;
- backend-core **lê** o mesmo arquivo para servir `/file` e para OCR — `views.py:311`, `ocr_processor.py:22`;
- backend-ocr **lê** o arquivo em **outro pod** — `ocr_event_worker.py:48`.

Disco local a cada pod ⇒ o arquivo escrito pelo com **não existe** no disco do core/ocr ⇒ `FileNotFoundError` → `Http404` no `/file` e falha no OCR. Em **localhost** todos os processos compartilham o mesmo diretório físico, por isso "funciona local, quebra em staging".

### Suposição a validar (bloqueante)
Os manifests reais **não estão versionados neste repo** (`k8s/hml` e `k8s/prd` vazios; Argo aponta para outro repositório). **Se** já existir um **PVC ReadWriteMany** montado no mesmo `mountPath` em todos os pods, o storage já é compartilhado e a hipótese (b) cai — restaria só o bug (a). Mesmo assim, S3/MinIO continua superior (escala horizontal, sem RWX, URLs pré-assinadas). **Confirmar o tipo de volume antes de implementar.**

### Conclusão
S3/MinIO é a solução correta para o storage compartilhado, mas **ambos os bugs precisam ser resolvidos** para o fluxo funcionar fim-a-fim. Ordem recomendada: **(a) sync com→core primeiro**, depois **(b) storage**.

---

## 2. Pontos de armazenamento local no código

A maior parte da I/O já passa por `docuparse_storage.LocalStorage` (`shared/docuparse_storage/__init__.py`). As URIs persistidas são portáveis (chaves estilo S3: `documents/{tenant}/{document}/...`) com prefixo de esquema `local://` — o que favorece a migração e o roteamento por esquema.

### Escritas (`put_bytes`) — retornam `StoredObject`
| Serviço | Local | Papel |
|---|---|---|
| backend-com | `services/document_ingest.py:58` | **Escreve o arquivo original** do upload (ponto de entrada) |
| backend-core | `documents/services/ocr_processor.py:52` | Escreve `raw_text.json` (OCR no caminho auto-process do core) |
| backend-ocr | `application/ocr_event_worker.py:73` | Escreve `raw_text.json` (OCR no worker) |

> Consumidores do retorno: `stored.uri` (persistido em `Document.raw_text_uri`/`file_uri` e propagado em eventos), `stored.sha256`, `stored.size_bytes` — ex.: `ocr_event_worker.py:86,95,96` e `ocr_processor.py:57`. **O `S3Storage.put_bytes` deve devolver um `StoredObject` idêntico.**

### Leituras (`get_bytes`)
| Serviço | Local | Papel |
|---|---|---|
| backend-core | `documents/views.py:311` | **Serve o arquivo original** (`/documents/{id}/file`, blob preview) |
| backend-core | `documents/serializers.py:165` | Lê `raw_text.json` para serializar o detalhe |
| backend-core | `documents/views.py:504-506` | Lê `raw_text.json` (view langextract) |
| backend-core | `documents/services/ocr_processor.py:22,91,178` | Lê original p/ OCR e `raw_text.json` |
| backend-ocr | `application/ocr_event_worker.py:48` | Lê o arquivo original para OCR |
| layout-service | `application/layout_event_worker.py:38` | Lê `raw_text.json` |
| langextract-service | `application/extraction_event_worker.py:41` | Lê `raw_text.json` |

### Pontos que **burlam** a abstração (órfãos — precisam de atenção especial)
1. **`layout-service/api/app.py:20-22`** — faz path cru: `request.raw_text_uri.removeprefix("local://")` + `pathlib.Path(storage_dir) / key`. **Não** usa `LocalStorage`; quebra silenciosamente com URIs `s3://`. **Correção obrigatória.**
2. **`backend-core/documents/services/approved_exporter.py:19-37`** — `export_approved_document_json` escreve em `DOCUPARSE_APPROVED_EXPORT_DIR` via `Path.write_text`, fora da abstração. É um artefato de **export** (provável pickup por ERP/integração). Se algum outro processo/backend consumir esse diretório, tem o **mesmo** problema de não-compartilhamento. **Definir escopo** (migrar para storage compartilhado ou manter como volume de export dedicado — ver §6).

### Pontos de wiring (bootstrap) dos workers — onde o storage é injetado
- `backend-ocr/application/ocr_event_worker.py:238` — `storage=LocalStorage(storage_root)`
- `layout-service/application/layout_event_worker.py:141` — `storage=LocalStorage(storage_root)`
- `langextract-service/application/extraction_event_worker.py:180` — `storage=LocalStorage(storage_root)`

> Cada worker define seu próprio `Protocol Storage` local e recebe a instância por injeção. **Basta trocar a instanciação no bootstrap** — os handlers ficam intactos.

### Fora de escopo (I/O local legítima, não é estado compartilhado)
- Arquivos temporários de processamento (OCR/pdf2image/tesseract), se houver, são efêmeros por processo — não precisam ser compartilhados.

### Onde as URIs trafegam (compatibilidade, não é I/O)
- DB: `Document.file_uri` / `raw_text_uri` (`documents/models.py:64-65`, `CharField(max_length=1024)`).
- Eventos: `DocumentReceivedEvent.data.file.uri`, `OCRCompletedEvent.data.raw_text_uri` (`contracts/events/schemas.py`).
- **Manter o esquema na URI** (`local://` vs `s3://`) é o que habilita migração incremental e rollback.

> Nota: backend-ocr usa um helper local `raw_text_key()` (f-string) e o core usa `document_ocr_raw_text_key()` do pacote compartilhado. Ambos produzem **o mesmo valor** (`documents/{tenant}/{doc}/ocr/raw_text.json`) — inofensivo, mas vale unificar no helper compartilhado para evitar divergência futura.

---

## 3. Avaliação do `scripts/s3/s3.py`

**O que já resolve** (`scripts/s3/s3.py`): cliente `boto3` com `endpoint_url` opcional (compatível com **MinIO**), `ensure_bucket`, `upload_bytes(key, data, content_type)`, `download_bytes` (já entende `s3://bucket/key` **ou** key nua), `generate_presigned_url`. Cobre o núcleo do necessário.

**O que falta / não serve como está:**
- **Import de outro projeto:** `from audib.shared.config import settings` — pertence a outro repo (audib). É apenas referência; a config precisa ser reescrita no padrão docuparse.
- **Interface incompatível com `LocalStorage`:** o código chama `put_bytes`/`get_bytes` e espera `StoredObject` no retorno do put; o script usa `upload_bytes`/`download_bytes` e retorna só a string da URI.
- **Sem mapeamento de erro:** precisa converter `ClientError`/`NoSuchKey` → `FileNotFoundError`, para preservar os `except FileNotFoundError` / `Http404` existentes (ex.: `views.py:312`).
- **Sem streaming:** `.read()` carrega tudo em memória. Aceitável para os tamanhos atuais (limite de upload = 20 MB), mas atenção a PDFs grandes.
- **`ensure_bucket` cria bucket em runtime:** em produção o bucket deve ser provisionado por infra; criar on-the-fly exige permissão ampla e mascara erro de config.
- **Sem retry/timeout/`config=Config(...)`** no client boto3.
- **Dependência `boto3`/`botocore` ainda não existe** em nenhum `pyproject`/lock dos serviços — precisa ser adicionada.

**Como integrar:** **não** espalhar `S3Client` pelo código. Adaptá-lo como uma implementação `S3Storage` da **mesma interface** de `LocalStorage`, dentro do pacote compartilhado `docuparse_storage`, com `put_bytes(key, content) -> StoredObject`, `get_bytes`, `delete` — drop-in.

---

## 4. Plano de implementação (passo a passo)

### Desenho da abstração (pacote `shared/docuparse_storage/`)

```
docuparse_storage/
  __init__.py     # reexporta tudo (compat imports atuais)
  keys.py         # document_original_key, document_ocr_raw_text_key, StoredObject
  base.py         # Protocol Storage (put_bytes/get_bytes/delete)
  local.py        # LocalStorage (extraído do __init__ atual)
  s3.py           # S3Storage (adapta scripts/s3/s3.py à interface)
  routing.py      # RoutingStorage
  factory.py      # get_storage()
```

- **`Storage` (Protocol):** `put_bytes(key: str, content: bytes) -> StoredObject`; `get_bytes(uri_or_key: str) -> bytes`; `delete(uri_or_key: str) -> None`.
- **`S3Storage`:** `put_bytes` retorna `StoredObject(uri=f"s3://{bucket}/{key}", key, size_bytes=len(content), sha256=...)` — **forma idêntica** ao `LocalStorage`. `get_bytes` mapeia `NoSuchKey`/`ClientError(404)` → `FileNotFoundError`. Client boto3 com timeout/retry. **Assinatura de `put_bytes` sem `content_type`** (paridade); `content_type` default `application/octet-stream` no PUT — o valor servido ao browser continua vindo de `document.content_type` no `/file`.
- **`RoutingStorage`** (peça central): implementa `Storage` e delega:
  - `put_bytes` → **backend de escrita configurado** (`local` ou `s3`, via env);
  - `get_bytes(uri)` → **despacha pelo esquema** da URI: `local://` → `LocalStorage`; `s3://` → `S3Storage`; sem esquema → backend default.
  - Isso garante **coexistência**: documentos antigos em `local://` continuam legíveis mesmo com S3 ligado (migração incremental + rollback).
- **`get_storage() -> Storage`:** lê env e retorna um `RoutingStorage` já configurado. **É a única fábrica que o código chama** (tanto para leitura quanto para escrita).

### Envs (novas)
`DOCUPARSE_STORAGE_BACKEND` (`local`|`s3`, default `local`), `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` — **sempre de env/secret**, nunca no código. Default preserva o comportamento atual (`local`).

### Ordem de execução (arquivo por arquivo)

1. **`shared/docuparse_storage/`** — refatorar em pacote: extrair `LocalStorage`; criar `S3Storage`, `RoutingStorage`, `get_storage()`. **Reexportar todos os símbolos no `__init__.py`** para não quebrar imports existentes (`from docuparse_storage import LocalStorage, document_original_key, ...`).
2. **Dependências** — adicionar `boto3` aos `pyproject.toml`/lock dos serviços com I/O: backend-com, backend-core, backend-ocr, layout-service, langextract-service.
3. **Config por serviço** — adicionar as envs de storage em: `backend-com/src/backend_com/config.py`, `backend-core/core/settings.py` (perto da linha 155), e nos bootstraps dos 3 workers.
4. **Trocar instanciações por `get_storage()`** (o `RoutingStorage` cobre leitura e escrita, sem decisão por chamada):
   - `backend-com/services/document_ingest.py:58`
   - `backend-core/documents/views.py:311`, `:504`
   - `backend-core/documents/serializers.py:165`
   - `backend-core/documents/services/ocr_processor.py:22,52,91,178`
   - Bootstraps: `backend-ocr/.../ocr_event_worker.py:238`, `layout-service/.../layout_event_worker.py:141`, `langextract-service/.../extraction_event_worker.py:180` (só o wiring; handlers intactos).
5. **Corrigir órfão 1:** `layout-service/api/app.py:20-22` — substituir o `removeprefix("local://") + Path` por `get_storage().get_bytes(request.raw_text_uri)`.
6. **Decidir órfão 2:** `approved_exporter.py:19-37` — se o export for consumido por outro backend, migrar para `get_storage().put_bytes(...)` com uma key `exports/{tenant}/{document}.json`; senão, manter em volume de export dedicado e documentar. (Ver §6.)
7. **Servir arquivo (`document_file_view`, `views.py:304`)** — **1ª fase: manter `FileResponse(BytesIO(...))`** (menor risco, preserva a autenticação atual). Avaliar `generate_presigned_url` + redirect numa fase posterior.
8. **Infra/deploy** — provisionar bucket MinIO/S3 (por infra, **não** `ensure_bucket` em runtime); injetar secrets; só remover PVC compartilhado (se existir) **após** validação.
9. **Migração de dados existentes** — script idempotente que lê `file_uri`/`raw_text_uri` com prefixo `local://` do disco, faz `put` no S3 e atualiza a URI no DB para `s3://`. Como o `RoutingStorage` despacha por esquema, roda incrementalmente **sem downtime**.

---

## 5. Estratégia de não-regressão e testes

- **Feature flag por env:** default `DOCUPARSE_STORAGE_BACKEND=local` ⇒ o deploy do código **não muda comportamento**. S3 é ligado por ambiente.
- **Coexistência de esquemas:** `RoutingStorage` mantém dados `local://` legados legíveis mesmo com S3 ligado. Rollback = voltar a flag para `local` (mantendo as credenciais S3 configuradas para ainda ler o que já foi para `s3://`).
- **Testes unitários:** `S3Storage` contra **MinIO** (ou `moto`) validando **contrato idêntico** ao `LocalStorage` — mesmo `StoredObject`, mesmo comportamento de `get_bytes`, `NoSuchKey → FileNotFoundError`. Parametrizar os testes de storage existentes para os dois backends.
- **Teste do `RoutingStorage`:** dispatch correto por esquema (`local://`, `s3://`, key nua).
- **Casos a testar (fim-a-fim):**
  - Upload (com) → objeto aparece no bucket com a key esperada.
  - Servir `/documents/{id}/file` a partir de **outro pod/serviço** — o teste-chave do problema multi-backend.
  - Pipeline cross-serviço: com → core(sync) → ocr → layout → langextract lendo os artefatos entre pods.
  - PDF/imagem **grande** (até 20 MB) — memória e timeout.
  - **Falha de conexão/credencial** — erro explícito e propagado (nada de "documento fantasma" sem arquivo).
  - Documento legado `local://` continua abrindo com S3 ligado.
- **Rollback:** flag `→ local`; **nenhum schema de DB muda** (URIs são `CharField`); reverter o deploy é seguro.

---

## 6. Riscos e pontos em aberto

### Perguntas a esclarecer antes de implementar
1. **Existe PVC ReadWriteMany compartilhado em staging?** (manifests fora deste repo) — decide se (b) realmente procede.
2. **Endpoint e credenciais do MinIO/S3:** `S3_ENDPOINT_URL`, `S3_BUCKET`, região, chaves — origem dos secrets (k8s Secret? Vault?).
3. **Retenção:** original e `raw_text.json` são persistentes (servidos/relidos depois) — confirmar lifecycle/expiração.
4. **Tamanho típico/máximo** dos documentos — define streaming vs. in-memory e uso de presigned URL.
5. **Bucket provisionado por infra** ou criado pela app? (recomendado: infra).
6. **`approved_exporter` / `DOCUPARSE_APPROVED_EXPORT_DIR`:** esse export é consumido por outro backend/ERP? Se sim, precisa ir para storage compartilhado; se não, mantém volume dedicado. (Órfão 2.)
7. **Confirmar que o bug (a) sync com→core será corrigido** — sem isso, a migração de storage não altera o sintoma reportado.

### Riscos
- Tratar S3 como solução do "não listado" e **não** corrigir o sync HTTP → o problema persiste.
- Esquecer os órfãos (`layout/api/app.py`, `approved_exporter.py`) → falha isolada só nesses caminhos.
- Credenciais/endpoint errados → falha silenciosa vira documento sem arquivo; garantir logs/erros explícitos.
- `boto3` novo em 5 serviços → alinhar versão e lock.
- Latência entre escrita e leitura cross-serviço (S3 é read-after-write para novos objetos; ok, mas atenção a fluxos que leem imediatamente após a escrita).

---

## Apêndice — resumo dos toques por arquivo

| Arquivo | Ação |
|---|---|
| `shared/docuparse_storage/*` | Refatorar em pacote; adicionar `S3Storage`, `RoutingStorage`, `get_storage()` |
| `backend-com/.../config.py` | Envs de storage |
| `backend-com/.../document_ingest.py:58` | `LocalStorage(...)` → `get_storage()` |
| `backend-core/core/settings.py` | Envs de storage |
| `backend-core/.../views.py:311,504` | → `get_storage()` |
| `backend-core/.../serializers.py:165` | → `get_storage()` |
| `backend-core/.../ocr_processor.py:22,52,91,178` | → `get_storage()` |
| `backend-core/.../approved_exporter.py:37` | Decidir escopo (órfão 2) |
| `backend-ocr/.../ocr_event_worker.py:238` | wiring → `get_storage()` |
| `layout-service/.../layout_event_worker.py:141` | wiring → `get_storage()` |
| `layout-service/api/app.py:20-22` | Corrigir bypass (órfão 1) |
| `langextract-service/.../extraction_event_worker.py:180` | wiring → `get_storage()` |
| `pyproject.toml` (5 serviços) | Adicionar `boto3` |
