# Endpoints chamados pelo frontend

Levantamento dos endpoints HTTP consumidos pelo frontend (`docuparse-project/frontend`).

## Clients HTTP

Definidos em [`src/shared/lib/http.ts`](../src/shared/lib/http.ts):

| Client | baseURL | Backend | Auth |
|---|---|---|---|
| `api` | `${VITE_BACKEND_CORE_URL}/api/ocr` | backend-core (OCR / documentos / admin / operations) | JWT via interceptor |
| `authApi` | `${VITE_BACKEND_CORE_URL}/api/auth` | backend-core (auth) | — |
| `adminApi` | `${VITE_BACKEND_CORE_URL}/api/admin` | backend-core (tenants) | JWT via interceptor |
| `comApi` | `${VITE_BACKEND_COM_URL}/api/v1` (dev: `/com/api/v1` via proxy do Vite) | backend-com (upload / poll) | JWT via interceptor |

O token (`access_token` do `localStorage`) é anexado como `Authorization: Bearer` em `api`, `comApi` e `adminApi`.

---

## backend-core — `/api/auth` (`authApi`)

| Método | Path | Origem |
|---|---|---|
| POST | `/register` | [`RegisterForm.tsx:26`](../src/modules/auth/components/RegisterForm.tsx#L26) |
| POST | `/login` | [`context.tsx:41`](../src/modules/auth/context.tsx#L41) |
| POST | `/logout` | [`context.tsx:52`](../src/modules/auth/context.tsx#L52) |

## backend-core — `/api/admin` (`adminApi`)

| Método | Path | Origem |
|---|---|---|
| GET | `/tenants/` | [`TenantsView.tsx:31`](../src/modules/admin/components/TenantsView.tsx#L31) |
| POST | `/tenants/` | [`TenantsView.tsx:49`](../src/modules/admin/components/TenantsView.tsx#L49) |
| PATCH | `/tenants/{slug}/` (ativar/desativar) | [`TenantsView.tsx:88`](../src/modules/admin/components/TenantsView.tsx#L88) |
| POST | `/tenants/{slug}/invites/resend/` | [`TenantsView.tsx:107`](../src/modules/admin/components/TenantsView.tsx#L107) |
| GET | `/tenants/{slug}/users/` | [`TenantUsersPanel.tsx:19`](../src/modules/admin/components/TenantUsersPanel.tsx#L19) |
| POST | `/tenants/{slug}/users/` | [`TenantUsersPanel.tsx:40`](../src/modules/admin/components/TenantUsersPanel.tsx#L40) |
| POST | `/tenants/{slug}/switch/` | [`context.tsx:69`](../src/modules/auth/context.tsx#L69) |
| POST | `/tenants/invites/{token}/activate/` | [`tenantActivation.service.ts:5`](../src/modules/tenant-activation/services/tenantActivation.service.ts#L5) |

## backend-core — `/api/ocr` (`api`)

### Documentos

| Método | Path | Origem |
|---|---|---|
| GET | `/documents` (paginado, `params`) | [`useDocumentsQuery.ts:14`](../src/modules/documents/hooks/useDocumentsQuery.ts#L14), [`useDocumentCount.ts:10`](../src/modules/documents/hooks/useDocumentCount.ts#L10) |
| GET | `/documents/{id}` | [`AppLayout.tsx:50`](../src/app/AppLayout.tsx#L50), [`useReferenceDocumentLoader.ts:26`](../src/modules/settings/hooks/useReferenceDocumentLoader.ts#L26), [`documents/utils.ts:21`](../src/modules/documents/utils.ts#L21) (polling da extração) |
| GET | `/documents/{id}/file` (blob) | [`DocumentBlobPreview.tsx:33`](../src/shared/components/DocumentBlobPreview.tsx#L33); link direto `<a href>` em [`ValidationDocumentPreview.tsx:14`](../src/modules/documents/components/ValidationDocumentPreview.tsx#L14) |
| GET | `/documents/{id}/pipeline` | [`useProcessPipelineQuery.ts:9`](../src/modules/processes/hooks/useProcessPipelineQuery.ts#L9) |
| GET | `/documents/{id}/field-versions` | [`useFieldVersioning.ts:77`](../src/modules/documents/hooks/useFieldVersioning.ts#L77) |
| PUT | `/documents/{id}/fields` | [`useFieldVersioning.ts:41`](../src/modules/documents/hooks/useFieldVersioning.ts#L41) |
| POST | `/documents/{id}/langextract` | [`useFieldExtraction.ts:99`](../src/modules/documents/hooks/useFieldExtraction.ts#L99) |
| POST | `/documents/{id}/reprocess-ocr` | [`useDocumentMutations.ts:25`](../src/modules/documents/hooks/useDocumentMutations.ts#L25) |
| POST | `/documents/{id}/validate` | [`useDocumentMutations.ts:36`](../src/modules/documents/hooks/useDocumentMutations.ts#L36) |
| DELETE | `/documents/{id}/delete` | [`useDocumentMutations.ts:30`](../src/modules/documents/hooks/useDocumentMutations.ts#L30) |

### Processos / estatísticas

| Método | Path | Origem |
|---|---|---|
| GET | `/processes` (paginado) | [`useProcessesQuery.ts:25`](../src/modules/processes/hooks/useProcessesQuery.ts#L25) |
| GET | `/processes/stats` | [`useProcessStatsQuery.ts:8`](../src/modules/processes/hooks/useProcessStatsQuery.ts#L8) |

### Settings / schemas / layouts / classificação

| Método | Path | Origem |
|---|---|---|
| GET / PATCH | `/settings/email` | [`EmailSettingsPanel.tsx:42`](../src/modules/settings/components/EmailSettingsPanel.tsx#L42), [`:58`](../src/modules/settings/components/EmailSettingsPanel.tsx#L58) |
| GET / PATCH | `/settings/ocr` | [`OcrSettingsPanel.tsx:38`](../src/modules/settings/components/OcrSettingsPanel.tsx#L38), [`:57`](../src/modules/settings/components/OcrSettingsPanel.tsx#L57) |
| GET / PATCH | `/settings/integrations` | [`IntegrationSettingsPanel.tsx:22`](../src/modules/settings/components/IntegrationSettingsPanel.tsx#L22), [`:39`](../src/modules/settings/components/IntegrationSettingsPanel.tsx#L39) |
| GET | `/schema-configs` | [`useSchemasQuery.ts:7`](../src/modules/settings/hooks/useSchemasQuery.ts#L7) |
| POST / PATCH | `/schema-configs` · `/schema-configs/{id}` | [`useSchemaMutations.ts:31`](../src/modules/settings/hooks/useSchemaMutations.ts#L31), [`:30`](../src/modules/settings/hooks/useSchemaMutations.ts#L30) |
| DELETE | `/schema-configs/{id}` | [`useSchemaMutations.ts:36`](../src/modules/settings/hooks/useSchemaMutations.ts#L36) |
| GET | `/layout-configs` | [`useLayoutsQuery.ts:7`](../src/modules/settings/hooks/useLayoutsQuery.ts#L7) |
| POST | `/layout-configs` | [`useLayoutMutations.ts:17`](../src/modules/settings/hooks/useLayoutMutations.ts#L17) |
| POST | `/classify-text` | [`useAutoClassification.ts:36`](../src/modules/settings/hooks/useAutoClassification.ts#L36), [`useFieldExtraction.ts:59`](../src/modules/documents/hooks/useFieldExtraction.ts#L59) |

### Admin (users / roles / permissions) — via `/api/ocr`

| Método | Path | Origem |
|---|---|---|
| GET | `/users` | [`useUsersQuery.ts:9`](../src/modules/admin/hooks/useUsersQuery.ts#L9) |
| POST | `/users` | [`useUserMutations.ts:20`](../src/modules/admin/hooks/useUserMutations.ts#L20) |
| PATCH | `/users/{id}` (edição e toggle ativo) | [`useUserMutations.ts:24`](../src/modules/admin/hooks/useUserMutations.ts#L24), [`:28`](../src/modules/admin/hooks/useUserMutations.ts#L28) |
| POST | `/users/{id}/invites/resend/` | [`useUserMutations.ts:32`](../src/modules/admin/hooks/useUserMutations.ts#L32) |
| GET | `/roles` | [`useRolesQuery.ts:9`](../src/modules/admin/hooks/useRolesQuery.ts#L9), [`TenantUsersPanel.tsx:20`](../src/modules/admin/components/TenantUsersPanel.tsx#L20) |
| POST | `/roles` | [`useRoleMutations.ts:12`](../src/modules/admin/hooks/useRoleMutations.ts#L12) |
| PATCH | `/roles/{id}` | [`useRoleMutations.ts:16`](../src/modules/admin/hooks/useRoleMutations.ts#L16) |
| DELETE | `/roles/{id}` | [`useRoleMutations.ts:20`](../src/modules/admin/hooks/useRoleMutations.ts#L20) |
| GET | `/permissions` | [`usePermissionsQuery.ts:9`](../src/modules/admin/hooks/usePermissionsQuery.ts#L9) |

### Operations / DLQ — via `/api/ocr`

| Método | Path | Origem |
|---|---|---|
| GET | `/operations/dlq/summary` | [`useDlqSummaryQuery.ts:9`](../src/modules/operations/hooks/useDlqSummaryQuery.ts#L9) |
| GET | `/operations/dlq/events` | [`useDlqEventsQuery.ts:9`](../src/modules/operations/hooks/useDlqEventsQuery.ts#L9) |
| POST | `/operations/dlq/requeue` | [`useRequeueMutation.ts:16`](../src/modules/operations/hooks/useRequeueMutation.ts#L16) |

## backend-com — `/api/v1` (`comApi`)

| Método | Path | Origem |
|---|---|---|
| POST | `/documents/manual` (multipart: `file`, `sender`) | [`UploadView.tsx:39`](../src/modules/upload/components/UploadView.tsx#L39) |
| POST | `/email/poll?tenant_id=` | [`EmailSettingsPanel.tsx:89`](../src/modules/settings/components/EmailSettingsPanel.tsx#L89) |
| POST | `/whatsapp/poll?tenant_id=` | [`useWhatsAppPoll.ts:22`](../src/modules/settings/hooks/useWhatsAppPoll.ts#L22) |

## Observações

- **Não há endpoint de refresh de token** no frontend. O `refresh_token` só é salvo/enviado no `/logout` e recebido no `switch`/`activate` de tenant.
- `WhatsAppSettingsPanel.tsx` exibe a URL `.../api/v1/whatsapp/webhook` apenas como texto informativo — não é chamada.
- Em dev, `comApi` usa o proxy do Vite (`/com` → backend-com). Em produção, URLs absolutas via `VITE_BACKEND_CORE_URL` / `VITE_BACKEND_COM_URL`.

---

## Caminho principal disparado após upload de um arquivo pela UI

Cenário: usuário na rota **`/upload`** ([`UploadRoute.tsx`](../src/modules/upload/routes/UploadRoute.tsx), guardada por `documents.send`) seleciona um PDF/imagem e clica em **Enviar**.

### 1. Chamada de upload (frontend → backend-com)

```
POST  {COM}/api/v1/documents/manual        (multipart/form-data: file[, sender])
```

- Disparada por `submitUpload` em [`UploadView.tsx:39`](../src/modules/upload/components/UploadView.tsx#L39).
- Resposta: `{ document_id }` — exibido como "Documento recebido: &lt;id&gt;".
- Em caso de erro: mensagem de `readError` (nenhuma outra chamada).

### 2. Refresh das listagens (callback `onUploaded`)

No sucesso, `UploadView` chama `onUploaded()` → `refreshData()` de [`AppLayout.tsx:43`](../src/app/AppLayout.tsx#L43), que:

1. Incrementa `refreshSignal` (contexto do `Outlet`), forçando as queries paginadas montadas a refazerem a página atual:
   - `GET {CORE}/api/ocr/documents`  — se a lista de documentos (Inbox/Aprovados/Rejeitados) estiver montada ([`useDocumentsQuery.ts:66`](../src/modules/documents/hooks/useDocumentsQuery.ts#L66)).
   - `GET {CORE}/api/ocr/processes`  — se a Visão Geral de Processos estiver montada ([`useProcessesQuery.ts:79`](../src/modules/processes/hooks/useProcessesQuery.ts#L79)).
2. Se há `selectedDocumentId` **e** o usuário tem `inbox.view`:
   - `GET {CORE}/api/ocr/documents/{selectedDocumentId}` ([`AppLayout.tsx:50`](../src/app/AppLayout.tsx#L50)).

> A rota `/upload` não monta nenhuma lista paginada, então na prática o passo 2 costuma resultar apenas na atualização do `refreshSignal` (sem nova requisição), a menos que o usuário navegue para o Dashboard/Inbox em seguida.

### 3. Acompanhamento do processamento (sob demanda, ao abrir o documento)

O processamento em si é **assíncrono no backend** (o `POST /documents/manual` publica o evento `document.received` no event bus e sincroniza o status com o backend-core — ver `backend-com/services/document_ingest.py`). O frontend só observa o progresso quando o usuário abre o documento:

| Ação na UI | Endpoint |
|---|---|
| Abrir a aba de pipeline do processo | `GET {CORE}/api/ocr/documents/{id}/pipeline` ([`useProcessPipelineQuery.ts:9`](../src/modules/processes/hooks/useProcessPipelineQuery.ts#L9)) |
| Tela de Validação carrega o documento selecionado | `GET {CORE}/api/ocr/documents/{id}` ([`AppLayout.tsx:71`](../src/app/AppLayout.tsx#L71)) |
| Preview do arquivo original | `GET {CORE}/api/ocr/documents/{id}/file` ([`DocumentBlobPreview.tsx:33`](../src/shared/components/DocumentBlobPreview.tsx#L33)) |
| Rodar extração de campos (langextract) | `POST {CORE}/api/ocr/documents/{id}/langextract` + polling `GET /documents/{id}` ([`useFieldExtraction.ts:99`](../src/modules/documents/hooks/useFieldExtraction.ts#L99), [`documents/utils.ts:21`](../src/modules/documents/utils.ts#L21)) |
| Reprocessar OCR | `POST {CORE}/api/ocr/documents/{id}/reprocess-ocr` ([`useDocumentMutations.ts:25`](../src/modules/documents/hooks/useDocumentMutations.ts#L25)) |
| Aprovar / rejeitar (validação) | `POST {CORE}/api/ocr/documents/{id}/validate` ([`useDocumentMutations.ts:36`](../src/modules/documents/hooks/useDocumentMutations.ts#L36)) |

### Resumo do caminho feliz

```
UI (/upload) ──POST {COM}/api/v1/documents/manual──▶ backend-com
                                                     │  publica evento document.received
                                                     │  sincroniza status → backend-core
                                                     ▼
                                          (pipeline assíncrono: OCR → layout → langextract)

frontend (onUploaded → refreshData):
   ├─ refreshSignal++  →  GET {CORE}/api/ocr/documents   (se lista montada)
   │                      GET {CORE}/api/ocr/processes   (se Visão Geral montada)
   └─ GET {CORE}/api/ocr/documents/{id}   (se houver documento selecionado + inbox.view)

depois, ao abrir o documento:
   GET /documents/{id}/pipeline · GET /documents/{id} · GET /documents/{id}/file
   POST /documents/{id}/langextract (+ polling) · POST /documents/{id}/validate
```
