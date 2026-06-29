# Contract — Tipos do Frontend × Backend e Superfície de Testes

Este "contrato" tem duas faces, pois a feature é interna ao frontend:
1. **Contrato de tipos ↔ backend**: os tipos do frontend devem espelhar fielmente os endpoints existentes (sem alterá-los).
2. **Superfície de testes**: o conjunto de fluxos que a suíte automatizada (FR-024/FR-025) deve cobrir.

---

## 1. Contrato de tipos ↔ endpoints (somente leitura/uso; nada muda no backend)

| Endpoint (via proxy `/api/ocr`, `/api/auth`, `/com`) | Método | Tipo de request | Tipo de response |
|---|---|---|---|
| `/api/auth/login` | POST | `{ email: string; password: string }` | `{ access: string; refresh: string; user: User }` |
| `/api/auth/me` | GET | — | `User` |
| `/api/auth/logout` | POST | `{ refresh: string }` | `void` |
| `/api/ocr/documents` | GET | — | `Document[]` |
| `/api/ocr/documents/{id}` | GET | — | `Document` (inclui `active_field_version_number`) |
| `/api/ocr/documents/{id}/langextract` | POST | `{ schema_config_id: string }` | `ExtractionResult` |
| `/api/ocr/documents/{id}/fields` | PUT | `{ base_version_number: number \| null; fields: {name;value}[] }` | `ExtractionFieldVersion` (201) / erro 409 `{ detail; active_version_number }` / 422 |
| `/api/ocr/documents/{id}/field-versions` | GET | — | `{ results: ExtractionFieldVersion[]; count: number; active_version_number: number \| null }` |
| `/api/ocr/documents/{id}/validate` | POST | `{ decision; notes?; corrected_fields?; decided_by_id? }` | decisão de validação |
| `/api/ocr/documents/{id}/reprocess-ocr`, `/delete`, `/file` | POST/DELETE/GET | conforme uso atual | inalterado |
| `/api/ocr/schema-configs`, `/layout-configs`, `/settings/*`, `/engines` | GET/POST/PUT | conforme `SettingsView` | inalterado |
| `/api/ocr/operations/dlq/*` | GET/POST | conforme `OperationsView` | inalterado |
| usuários/roles | GET/POST/PATCH | conforme `GerenciarUsuarios`/`GerenciarRoles` | inalterado |

**Regra de aceite**: a tipagem aplicada às chamadas NÃO pode alterar endpoint, método, parâmetros ou payload. Testes de integração (MSW) verificam que as mesmas requisições são emitidas.

---

## 2. Superfície de testes (Vitest + Testing Library + MSW)

### Telas (smoke/render) — devem montar e exibir elementos-chave
- Login, Dashboard, Inbox, Validação, Aprovados, Rejeitados, Operações, Configurações, Usuários, Roles.

### Permissões
- Itens de navegação aparecem/desaparecem conforme `user.permissions` (`NAV_ITEMS`).
- `PermissionGuard` bloqueia conteúdo sem a permissão e mostra fallback/`AcessoNaoAutorizado`.

### Integrações / fluxos (com backend mockado por MSW)
- **Auth**: login persiste tokens e seta `user`; `/me` restaura sessão; logout limpa.
- **Inbox**: lista documentos; busca filtra (`filterDocuments`); seleção navega para validação.
- **Validação**: extração popula campos; editar valor; remover campo; adicionar campo; **Salvar Alterações** (confirmação → 201 nova versão; **409** mostra aviso de conflito; **422** lista vazia); **Visualizar Histórico** (modal somente leitura); Aprovar/Rejeitar.
- **Rejeitados**: modal de detalhes, reprocessar, excluir.
- **Configurações**: carregar/salvar OCR/Email/Integrações; editor de schema/exemplos.
- **Operações**: DLQ summary/events/requeue.

### Critérios de aprovação da suíte
- `npm run test` (ou `test:run`) passa 100% (FR-025).
- Cobertura: fluxos críticos (auth, validação, permissões) ≥ 90%; demais fluxos exercitados ≥ 80% (research D5).
- Executável localmente e no build/CI; um erro de tipo proposital é pego por `tsc --noEmit` (SC-003).

---

## 3. Invariantes da migração (regressão)

- Layout, estilos, posicionamento e textos **idênticos** (comparação visual antes/depois).
- Navegação por `activeView` inalterada (sem router novo).
- Nenhuma funcionalidade removida; nenhum comportamento visual alterado.
- Build de produção gerado; dev server sobe pelos scripts atuais.
