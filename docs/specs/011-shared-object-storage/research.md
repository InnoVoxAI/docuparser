# Phase 0 — Research & Decisões

Feature: Armazenamento de objetos compartilhado entre backends (`011-shared-object-storage`)

Este documento resolve as clarificações pendentes da spec e registra as decisões técnicas que orientam o design. Onde uma confirmação de infraestrutura ainda é necessária, adota-se um **default seguro que não bloqueia a implementação** e registra-se a dependência.

---

## D-01 — Padrão de integração do storage: adaptar `scripts/s3/s3.py` como `S3Storage` atrás da interface existente

- **Decision**: Não usar `S3Client` diretamente no código de aplicação. Criar `S3Storage` no pacote `docuparse_storage` com o **mesmo contrato** de `LocalStorage` (`put_bytes(key, content) -> StoredObject`, `get_bytes(uri_or_key) -> bytes`, `delete(uri_or_key)`), reaproveitando a lógica boto3 do script de referência.
- **Rationale**: A maioria da I/O já passa por `docuparse_storage`; manter o contrato torna a troca um drop-in e preserva os consumidores de `StoredObject` (`stored.uri/sha256/size_bytes`). Evita espalhar o SDK pelo código (testabilidade, reversibilidade).
- **Alternatives considered**: (a) chamar boto3 direto nos serviços — rejeitado: acopla, dificulta teste/rollback; (b) trocar assinatura para incluir `content_type` — rejeitado: quebraria chamadores; o `content_type` servido vem do DB (`document.content_type`), não do storage.

## D-02 — `RoutingStorage` único para leitura por esquema e escrita por config

- **Decision**: Um objeto `RoutingStorage` implementa `Storage` e: **escreve** no backend configurado por env (`local` ou `s3`); **lê** despachando pelo esquema da URI (`local://` → `LocalStorage`; `s3://` → `S3Storage`; sem esquema → backend default). `get_storage()` retorna esse objeto e é o **único** ponto de instanciação.
- **Rationale**: Os workers (ocr/layout/langextract) recebem `storage` **injetado no bootstrap** e chamam `storage.get_bytes(uri)` **dentro do handler**. Um objeto único que roteia por esquema permite trocar só o wiring, sem tocar handlers, e habilita coexistência `local://`/`s3://` (migração incremental + rollback).
- **Alternatives considered**: `get_storage()` p/ escrita + `resolve_for_uri()` p/ leitura — rejeitado: exigiria alterar cada handler dos workers; incoerente com a injeção existente.

## D-03 — Seleção por ambiente com default `local` (sem regressão)

- **Decision**: `DOCUPARSE_STORAGE_BACKEND` (`local`|`s3`), **default `local`**. Sem configuração adicional, comportamento idêntico ao atual. `boto3` importado de forma **lazy** (só quando backend=`s3`), então serviços em modo local não precisam da dependência em runtime.
- **Rationale**: FR-002/FR-003 e SC-007 exigem paridade no default e ativação explícita por ambiente. Import lazy (já presente no `scripts/s3/s3.py`, que faz `import boto3` dentro do `__init__`) reduz superfície de dependência.
- **Alternatives considered**: default `s3` — rejeitado: força big-bang e regressão em dev local; detectar backend pela presença de `S3_ENDPOINT_URL` — rejeitado: implícito demais, dificulta rollback determinístico.

## D-04 — Mapeamento de erros: "não encontrado" vs "indisponível", sem sucesso silencioso

- **Decision**: `S3Storage.get_bytes` mapeia `NoSuchKey`/`ClientError(404)` → `FileNotFoundError` (preserva os `except FileNotFoundError`/`Http404` existentes, ex. `views.py:312`). Demais `ClientError`/`EndpointConnectionError`/credencial inválida → exceção propagada (não engolida). Nenhum caminho de escrita deve registrar `Document` sem o `put_bytes` ter concluído com sucesso.
- **Rationale**: FR-006/FR-007 e SC-005. Distinguir 404 de falha de conexão é o que evita "documento fantasma" e dá diagnóstico correto.
- **Alternatives considered**: tratar tudo como `FileNotFoundError` — rejeitado: mascara indisponibilidade/credencial como "não existe".

## D-05 — Servir arquivo: manter `FileResponse(BytesIO)` na fase 1

- **Decision**: `document_file_view` continua lendo bytes via `get_storage().get_bytes(file_uri)` e devolvendo `FileResponse(BytesIO(content), content_type=document.content_type, filename=...)`. `content_type` continua vindo do **DB**. Streaming/`generate_presigned_url` ficam como otimização de fase posterior.
- **Rationale**: FR-009/SC-002 exigem comportamento idêntico ao usuário final; a menor mudança preserva auth e headers. 20 MB cabe no orçamento de 2 GB/container.
- **Alternatives considered**: presigned URL + redirect agora — rejeitado na fase 1: mudaria o modelo de auth (o interceptor injeta JWT; presigned exporia a URL) e o comportamento observável.

---

## Resolução das clarificações da spec

### C-01 — Existe PVC ReadWriteMany compartilhado em todos os pods?
- **Status**: confirmação de infra pendente (manifests fora deste repo). **Não bloqueia.**
- **Decision**: Prosseguir com S3/MinIO independentemente. Se um RWX já existir, o S3 continua sendo a solução superior (escala horizontal, sem RWX, presigned) e o modo `local` sobre RWX permanece disponível como fallback via a mesma abstração. O design é válido nos dois cenários.
- **Ação**: registrar como pergunta de deploy no quickstart; não é pré-requisito de código.

### C-02 — Endpoint, bucket, região e origem dos segredos
- **Decision**: Config 100% por env: `S3_ENDPOINT_URL` (MinIO), `S3_BUCKET`, `S3_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`. Origem = **k8s Secret** (padrão do cluster) montado como env; valores concretos fornecidos por infra no deploy. Nunca no código (FR-008).
- **Ação**: contrato de env definido em `contracts/storage-config.md`; valores reais são responsabilidade de infra.

### C-03 — Política de retenção/lifecycle
- **Decision**: A aplicação **não** aplica expiração automática; arquivo original e `raw_text.json` são **persistentes**. Lifecycle/retention (se houver) é gerido por **bucket policy** no lado de infra, fora do código. O único delete existente (fluxo de exclusão de documento) permanece inalterado.
- **Ação**: documentar; sem trabalho de código nesta feature.

### C-04 — Export para ERP (`approved_exporter`) é lido por outro backend?
- **Decision**: **Fora do escopo desta feature.** A spec limita os artefatos ao arquivo original e ao `raw_text.json`. `approved_exporter.py` (`DOCUPARSE_APPROVED_EXPORT_DIR`) permanece em volume de export dedicado por ora; migrá-lo para o storage compartilhado é um follow-up condicionado à confirmação de consumo cross-backend.
- **Ação**: registrar como follow-up explícito; **não** alterar `approved_exporter.py` nesta feature.

### C-05 — Tamanho típico/máximo e streaming vs. in-memory
- **Decision**: Teto conhecido = 20 MB (`DOCUPARSE_MAX_UPLOAD_BYTES`). Fase 1 usa leitura in-memory (paridade com hoje), aceitável dentro de 2 GB/container. Streaming/presigned adiado até haver evidência de necessidade (perfil típico ainda não medido).
- **Ação**: `SC-004` cobre o teste de 20 MB; otimização fica como follow-up.

---

## Riscos e mitigações (resumo)
- **Órfão `layout-service/api/app.py`** faz path cru com `removeprefix("local://")` → quebraria com `s3://`. Mitigação: substituir por `get_storage().get_bytes(...)` (tarefa obrigatória).
- **Divergência de key**: backend-ocr usa `raw_text_key()` local; core usa `document_ocr_raw_text_key()`. Mesmo valor hoje; unificar no helper compartilhado para evitar drift.
- **`boto3` em 5 serviços**: alinhar versão; import lazy evita exigir a lib no modo local.
- **Leitura pós-escrita cross-serviço**: S3 é read-after-write para novos objetos (consistente); atenção a fluxos que leem imediatamente após gravar (coberto por teste de integração — SC-003).
- **Dependência externa**: o sintoma "não aparece na listagem" é o bug de rede com→core (fora de escopo); comunicar que esta feature **não** o resolve isoladamente.
