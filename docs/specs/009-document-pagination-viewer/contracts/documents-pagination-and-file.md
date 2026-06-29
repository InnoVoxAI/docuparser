# Contract — Listagem paginada e arquivo do documento

Contratos afetados nesta feature. Caminhos relativos ao backend-core
(prefixo do proxy do frontend: `/api/ocr`).

---

## 1. `GET /documents` — listagem paginada (ALTERADO)

**Antes**: retornava uma **lista crua** `DocumentListSerializer[]` (corte fixo de
200), filtros `status`/`tenant`, sem busca, sem paginação.

**Depois**: retorna um **envelope paginado**.

### Auth
- `DocuparseAuthentication` (JWT) + `require_permission("inbox.view")` — inalterado.

### Query params
| Param | Tipo | Default | Regras |
|------|------|---------|--------|
| `page` | int | 1 | `≥ 1`; fora do intervalo → comportamento seguro (ver abaixo). |
| `page_size` | int | 25 | `1..25`; valores acima de 25 são reduzidos a 25. |
| `status` | string \| CSV | — | Um status ou lista separada por vírgula. |
| `tenant` | string | — | Slug do tenant. |
| `search` | string | — | `icontains` em `original_filename`, `status`, `document_type`, `channel` **e nos valores de `extraction_result.fields`**; termos de rótulo de status comuns mapeados (ex.: "aprovado"→`APPROVED`). |

### Response 200
```json
{
  "results": [
    {
      "id": "…", "status": "RECEIVED", "channel": "manual",
      "original_filename": "nota.pdf", "content_type": "application/pdf",
      "document_type": "boleto", "layout": "…",
      "received_at": "…", "updated_at": "…",
      "metadata_channel": null,
      "extraction_result": { /* … ou null */ },
      "rejection_notes": null, "decision_date": null,
      "approved_at": null, "rejected_at": null
    }
  ],
  "count": 137,
  "page": 2,
  "page_size": 25,
  "total_pages": 6
}
```

### Regras de borda
- **Vazio**: `results: []`, `count: 0`, `page: 1`, `total_pages: 0`.
- **Última página parcial**: `results` com menos de `page_size` itens.
- **`page` > `total_pages`**: retornar página vazia com `count`/`total_pages`
  corretos **ou** clampar para a última página válida (definir na implementação;
  o frontend trata ambos exibindo a posição real).
- **Ordenação**: `-received_at` (inalterada).

### Compatibilidade
- Mudança **breaking** para o cliente (lista → envelope). O frontend (controlado)
  e os handlers MSW são atualizados na mesma feature. Demais consumidores internos
  do endpoint, se houver, devem ler `results`.

### Testes (backend, antes da implementação)
- `page_size` respeita o cap 25; `page` navega corretamente; `count`/`total_pages`
  corretos; `status` (single e CSV) filtra; `search` filtra por nome/tipo/canal/
  status; vazio retorna envelope coerente; sem permissão → 403; sem auth → 401.

---

## 2. `GET /documents/{id}/file` — arquivo original (ALTERADO: auth)

**Antes**: autorização apenas por **token interno de serviço**
(`_internal_token_error`); sem checagem de permissão de usuário.

**Depois**: aceita **dois** modos de autorização:
1. **Token interno de serviço** (comportamento atual, para chamadas service-to-service).
2. **JWT de usuário** + `require_permission("inbox.view")` — quando a requisição
   vier autenticada como usuário (caso da pré-visualização na UI).

### Comportamento
- Usuário autenticado **com** permissão → 200 com o arquivo
  (`FileResponse`, `Content-Type` do documento). **Inalterado**: não força
  download na UI (consumido como blob e renderizado inline).
- Usuário autenticado **sem** permissão → 403.
- Sem auth e sem token interno → 401.
- Arquivo inexistente/indisponível → 404.
- Funciona para armazenamento local ou externo (endpoint abstrai o backing store).

### Testes (backend, antes da implementação)
- Usuário com permissão recebe 200 + bytes corretos; sem permissão → 403; token
  interno válido → 200; sem credenciais → 401; arquivo ausente → 404.

---

## 3. Frontend — consumo

- `api.get<Paginated<Document>>('/documents', { params: { page, page_size, status, search } })`.
- Preview: `api.get('/documents/{id}/file', { responseType: 'blob' })` →
  `URL.createObjectURL(blob)` → render inline (iframe/img) → `revokeObjectURL` no
  cleanup. Sem download; respeita permissão (JWT no header via interceptor).

### Testes (frontend, MSW)
- Controles de paginação: navegação, posição (página/total/contagem), reset ao
  buscar, desabilitar nos limites.
- Preview no modal: render PDF/imagem a partir do blob, informações existentes
  preservadas ao lado, estado de erro quando o arquivo não carrega.
