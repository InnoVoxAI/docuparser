# Plano de Correção: Roteamento das chamadas de API no deploy (staging/prod) — Opção A

**Branch sugerida**: `010-fix-staging-api-routing` | **Date**: 2026-07-02 | **Tipo**: Correção (bug de integração frontend↔backend no deploy)

**Contexto de origem**: erro observado ao logar em staging —
`POST https://staging.docuparser.pages.dev/api/auth/login 405 (Method Not Allowed)`.
Diagnóstico completo (incl. por que **não** é trailing slash no Django) na seção
[Causa raiz](#2-causa-raiz-evidências).

---

## 1. Summary

O frontend (SPA React/Vite, hospedado no **Cloudflare Pages**) faz as chamadas de
API usando **caminhos relativos** (`/api/ocr`, `/api/auth`, `/com/api/v1`). Esses
caminhos só funcionam em desenvolvimento porque o **proxy do Vite dev server**
encaminha `/api` e `/com` para os backends. No deploy do Cloudflare Pages **não
existe** esse proxy (nem `_redirects`, nem `_routes.json`, nem Pages Functions),
então o `POST /api/auth/login` bate no **host estático** do Pages, que só aceita
`GET`/`HEAD` e responde **`405 Method Not Allowed`**.

A **Opção A** corrige a origem do problema: fazer o bundle publicado apontar para a
**URL absoluta do backend** (via variáveis `VITE_BACKEND_CORE_URL` /
`VITE_BACKEND_COM_URL`, já intencionadas no `vite.config.ts` mas nunca ligadas),
mantendo os caminhos relativos como *fallback* em dev (proxy do Vite) e em testes
(MSW). Como isso passa a ser uma chamada **cross-origin** (Pages → backend em K8s),
é pré-requisito ter o **CORS** dos backends liberando a origem do Pages.

Abordagem técnica em três frentes:

1. **Frontend** — derivar o `baseURL` dos clientes axios a partir de
   `import.meta.env.VITE_BACKEND_CORE_URL` / `VITE_BACKEND_COM_URL`, com fallback
   relativo.
2. **Build (`vite.config.ts`)** — corrigir os **nomes divergentes** das variáveis
   derivadas por branch (hoje gera `VITE_API_BASE_URL`/`VITE_COM_BASE_URL`, que
   ninguém lê) para os nomes efetivamente consumidos.
3. **Infra/Backends** — popular `CORS_ALLOWED_ORIGINS` (backend-core Django,
   backend-com e backend-ocr) com a(s) origem(ns) do Cloudflare Pages.

---

## 2. Causa raiz (evidências)

| # | Fato | Evidência |
|---|------|-----------|
| 1 | Clientes axios usam caminho **relativo** | [main.tsx:59-63](../../../docuparse-project/frontend/src/main.tsx#L59-L63): `baseURL: '/api/ocr' | '/api/auth' | '/com/api/v1'`. Login: [main.tsx:285](../../../docuparse-project/frontend/src/main.tsx#L285) `authApi.post('/login', …)` |
| 2 | Em localhost funciona por causa do **proxy do Vite (só dev)** | [vite.config.ts:18-33](../../../docuparse-project/frontend/vite.config.ts#L18-L33): `server.proxy['/api'] → :8000`, `['/com'] → :8070` (com `rewrite` removendo `/com`) |
| 3 | **Não há** proxy na borda do Pages | Busca no repo: sem `_redirects`, `_routes.json`, `functions/` ou `public/` |
| 4 | Request morre no host **estático** do Pages | O host do erro é `staging.docuparser.pages.dev` (frontend), não `…docuparser-core.innovox.ai` (backend). Host estático ⇒ `405` para `POST` |
| 5 | Intenção de URL absoluta existe, mas **quebrada** | [vite.config.ts:5-13](../../../docuparse-project/frontend/vite.config.ts#L5-L13) deriva `VITE_API_BASE_URL`/`VITE_COM_BASE_URL`, **nomes que `src/` não lê** (declarados como `VITE_BACKEND_CORE_URL`/`VITE_BACKEND_COM_URL` em [vite-env.d.ts:4-5](../../../docuparse-project/frontend/src/vite-env.d.ts#L4-L5)) |

**Por que não é trailing slash no Django** (hipótese descartada): a rota já casa sem
barra — [core/urls.py:6](../../../docuparse-project/backend-core/core/urls.py#L6)
(`api/auth/`) + [auth_urls.py:6](../../../docuparse-project/backend-core/users/auth_urls.py#L6)
(`login`) ⇒ `/api/auth/login`, exatamente o que o frontend chama. Além disso, a
requisição **nunca chega ao Django** (morre no host do Pages), então nem
`APPEND_SLASH` (301) nem `405` do DRF poderiam se originar ali. Testar o Django
direto **funciona** — o que confirma que o Django está correto. Mudar para `login/`
sem alterar o frontend introduziria um `301` em `POST` (o navegador o reemite como
`GET`) e aí sim causaria `405` no [login_view](../../../docuparse-project/backend-core/users/auth_views.py#L17)
(`@api_view(["POST"])`). **Nenhuma alteração de rota/slash no Django faz parte deste plano.**

---

## 3. Goals / Non-Goals

**Goals**
- Login e todas as chamadas de API funcionarem no deploy do Cloudflare Pages
  (staging e produção), sem `405` e sem erro de CORS.
- Manter dev (proxy Vite) e testes (MSW) funcionando **sem regressão**.
- Centralizar a URL do backend em variáveis de ambiente de build, eliminando a
  configuração "meio-feita" e os nomes divergentes.

**Non-Goals**
- Não alterar rotas/trailing slash no Django.
- Não migrar para proxy na borda (isso é a Opção B; fora do escopo).
- Não reescrever a camada de autenticação (o fluxo por `Authorization: Bearer`
  permanece).

---

## 4. Technical Context

**Frontend**: TypeScript 5.4 + React 18 + Vite 5; cliente HTTP `axios`; testes
Vitest + Testing Library + **MSW** (handlers em caminhos relativos `/api/*`, `/com/*`).

**Hospedagem do frontend**: Cloudflare Pages (`*.docuparser.pages.dev`). Variável de
build disponível: `CF_PAGES_BRANCH`.

**Backends**:
- **backend-core** (Django/DRF) — CORS via `django-cors-headers`, lê
  `CORS_ALLOWED_ORIGINS` ([settings.py:51](../../../docuparse-project/backend-core/core/settings.py#L51), default prod `https://docuparser.innovox.ai`). URLs alvo (derivadas por branch): `https://[staging.]docuparser-core.innovox.ai`.
- **backend-com** (FastAPI) — `CORSMiddleware` lê `CORS_ALLOWED_ORIGINS` ([config.py:55-59](../../../docuparse-project/backend-com/src/backend_com/config.py#L55-L59) + [api/app.py:59-65](../../../docuparse-project/backend-com/src/backend_com/api/app.py#L59-L65)). URL alvo: `https://[staging.]docuparser-com.innovox.ai`.
- **backend-ocr** (FastAPI) — `CORSMiddleware` lê `CORS_ALLOWED_ORIGINS` ([api/app.py:82-88](../../../docuparse-project/backend-ocr/api/app.py#L82-L88)).

**Autenticação e CORS**: o frontend envia o JWT em **header** `Authorization: Bearer`
(interceptors em [main.tsx:273-280](../../../docuparse-project/frontend/src/main.tsx#L273-L280); `/me` e `/logout` mandam o header inline). **Não usa cookies** (`withCredentials` não é usado), então o modo *credentials* do CORS não é acionado — o essencial é o backend **ecoar a origem** e permitir os headers `Authorization` e `Content-Type` no preflight `OPTIONS`.

---

## 5. Design

### 5.1 Contrato de variáveis de ambiente (build do frontend)

| Variável | Consumidor | Dev (local) | Staging | Produção |
|---|---|---|---|---|
| `VITE_BACKEND_CORE_URL` | `api`, `authApi` | *(vazio)* → relativo `/api/*` (proxy Vite) | `https://staging.docuparser-core.innovox.ai` | `https://docuparser-core.innovox.ai` |
| `VITE_BACKEND_COM_URL` | `comApi` | *(vazio)* → relativo `/com/api/v1` (proxy Vite) | `https://staging.docuparser-com.innovox.ai` | `https://docuparser-com.innovox.ai` |

Regra de ouro: **se a env estiver vazia, cai no caminho relativo** (preserva dev e
testes). Se preenchida, usa **URL absoluta** do backend.

### 5.2 Comportamento por ambiente

- **Dev (localhost)**: env vazias ⇒ axios usa `/api/*` e `/com/api/v1` ⇒ proxy do
  Vite encaminha (inclusive o `rewrite` que remove `/com`). Sem mudança de
  comportamento.
- **Testes (Vitest/MSW)**: `import.meta.env` sem as vars ⇒ fallback relativo ⇒ os
  handlers MSW existentes (`/api/auth/*`, `/api/ocr`, `/com/*`) continuam casando.
- **Staging/Prod (Pages)**: env preenchidas no build ⇒ axios chama a URL absoluta do
  backend ⇒ **cross-origin** ⇒ depende de CORS liberado.

### 5.3 Mapeamento de prefixos (atenção ao `/com`)

O proxy dev mapeia `/com` → raiz do backend-com (remove `/com`) e o `baseURL` inclui
`/api/v1`. Portanto, na forma **absoluta**, o `comApi` deve ser
`${VITE_BACKEND_COM_URL}/api/v1` (**sem** `/com`). Já o `api`/`authApi` mantêm os
prefixos `/api/ocr` e `/api/auth` (o backend-core serve sob `/api/...`).

### 5.4 Separação client × proxy (evita colisão no docker-compose)

⚠️ Descoberto na implementação: o Vite expõe **qualquer** `process.env` com prefixo
`VITE_` ao `import.meta.env` do **browser**. O `docker-compose.yml` definia
`VITE_BACKEND_CORE_URL`/`VITE_BACKEND_COM_URL` com **hostnames internos do Docker**
(`http://backend-core:8000`) apenas para o **alvo do proxy** do dev server. Ao passar
a consumir esses nomes no client, o browser tentaria resolver `backend-core:8000` e
quebraria o compose.

**Decisão**: separar por camada, pelo **prefixo**:

| Papel | Variável | Prefixo | Onde é lido | Valor |
|---|---|---|---|---|
| **Client** (browser) | `VITE_BACKEND_CORE_URL` / `VITE_BACKEND_COM_URL` | `VITE_` (exposto) | `src/main.tsx` (`import.meta.env`) | Vazio em dev/compose → relativo; URL **pública** no Pages |
| **Proxy** (dev server) | `BACKEND_CORE_URL` / `BACKEND_COM_URL` | sem `VITE_` (server-side) | `vite.config.ts` `server.proxy.target` | Hostname **interno** (`backend-core:8000`) no compose; `127.0.0.1` default |

Assim, no docker-compose o client fica **relativo** (usa o proxy) e o endereço
interno **não vaza** no bundle. Isso já se alinha à convenção `BACKEND_CORE_URL`
(sem `VITE_`) usada por outros serviços do compose para comunicação server-to-server.

---

## 6. Implementação (passo a passo)

> Snippets abaixo são **ilustrativos** (alvo). Nenhuma edição foi aplicada neste plano.

### Passo 1 — Frontend: derivar `baseURL` das env vars — [main.tsx:59-63](../../../docuparse-project/frontend/src/main.tsx#L59-L63)

```ts
// Base dos backends: absoluto no deploy (Cloudflare Pages), relativo em dev/testes
// (fallback via proxy do Vite / handlers MSW).
const CORE = import.meta.env.VITE_BACKEND_CORE_URL ?? ''
const COM  = import.meta.env.VITE_BACKEND_COM_URL ?? ''

const api     = axios.create({ baseURL: `${CORE}/api/ocr` })
const authApi = axios.create({ baseURL: `${CORE}/api/auth` })
// Em dev, COM vazio → '/com/api/v1' (proxy remove o '/com'); no deploy → absoluto.
const comApi  = axios.create({ baseURL: COM ? `${COM}/api/v1` : '/com/api/v1' })
```

- Não mexer nos `.post('/login')`, `.get('/me')`, `.post('/documents/manual')` etc.:
  eles são relativos ao `baseURL` e continuam válidos.
- Interceptors de `Authorization` permanecem inalterados
  ([main.tsx:273-280](../../../docuparse-project/frontend/src/main.tsx#L273-L280)).

### Passo 2 — Build: corrigir nomes das env derivadas por branch — [vite.config.ts:5-13](../../../docuparse-project/frontend/vite.config.ts#L5-L13)

```ts
// On Cloudflare Pages, CF_PAGES_BRANCH is available at build time.
const branch = process.env.CF_PAGES_BRANCH
if (branch) {
    // K8s: main → prod (sem prefixo), demais branches → staging.
    const k8sEnv = branch === 'main' ? '' : 'staging.'
    // Usar os MESMOS nomes que o código lê; não sobrescrever override explícito.
    process.env.VITE_BACKEND_CORE_URL ??= `https://${k8sEnv}docuparser-core.innovox.ai`
    process.env.VITE_BACKEND_COM_URL  ??= `https://${k8sEnv}docuparser-com.innovox.ai`
}
```

**Mecanismo autoritativo (recomendado)**: definir `VITE_BACKEND_CORE_URL` e
`VITE_BACKEND_COM_URL` **diretamente nas variáveis de build do Cloudflare Pages**
(painel do projeto, por ambiente). A derivação por branch acima vira apenas um
*default* de conveniência (por isso o `??=`, para o valor do painel vencer).
Isso evita depender de detalhes de timing entre mutação de `process.env` no
`vite.config.ts` e a resolução de env do Vite — ver verificação no Passo 4.

**(b) Desacoplar o alvo do proxy** ([vite.config.ts](../../../docuparse-project/frontend/vite.config.ts) `server.proxy`): o proxy passa a ler `BACKEND_CORE_URL` / `BACKEND_COM_URL` (**sem** `VITE_`), não mais `VITE_BACKEND_*_URL` — ver [§5.4](#54-separação-client--proxy-evita-colisão-no-docker-compose). Sem isso, o hostname interno do Docker vaza para o bundle do browser.

```ts
'/api': { target: process.env.BACKEND_CORE_URL || 'http://127.0.0.1:8000', … }
'/com': { target: process.env.BACKEND_COM_URL  || 'http://127.0.0.1:8070', …, rewrite: p => p.replace(/^\/com/, '') }
```

### Passo 2.1 — Compose: renomear env do serviço `frontend`

[docker-compose.yml](../../../docuparse-project/docker-compose.yml) (serviço `frontend`): trocar `VITE_BACKEND_CORE_URL`/`VITE_BACKEND_COM_URL` por `BACKEND_CORE_URL`/`BACKEND_COM_URL` (alvo do proxy; o client fica relativo e é proxiado).

### Passo 3 — Infra/Backends: liberar CORS para a origem do Pages

Setar `CORS_ALLOWED_ORIGINS` (CSV) nos **três** backends, incluindo a(s) origem(ns)
do Cloudflare Pages:

```
CORS_ALLOWED_ORIGINS=https://staging.docuparser.pages.dev,https://docuparser.innovox.ai
```

- **backend-core** ([settings.py:51](../../../docuparse-project/backend-core/core/settings.py#L51)) — hoje default só `https://docuparser.innovox.ai`; precisa incluir a origem do Pages de staging.
- **backend-com** ([config.py:55-59](../../../docuparse-project/backend-com/src/backend_com/config.py#L55-L59)) e **backend-ocr** ([api/app.py:82-88](../../../docuparse-project/backend-ocr/api/app.py#L82-L88)) — hoje default é `localhost:5173`; **precisa** receber a origem real no env da infra.
- Ajustar para o **domínio de produção real** do Pages (confirmar se é
  `https://docuparser.pages.dev` ou domínio customizado) quando `main`.
- Confirmar que os headers `Authorization` e `Content-Type` são aceitos no preflight
  (FastAPI usa `allow_headers=["*"]`; `django-cors-headers` inclui `authorization`
  no default de `CORS_ALLOW_HEADERS`).

### Passo 4 — Verificação de build (garantir que a URL foi *inlined*)

Após `npm run build` com as env de staging, o valor absoluto deve aparecer no bundle:

```bash
grep -r "docuparser-core.innovox.ai" docuparse-project/frontend/dist/assets | head
```

Se **não** aparecer, a env não chegou ao build ⇒ definir no painel do Pages (Passo 2,
mecanismo autoritativo) e rebuildar.

---

## 7. Edge cases & riscos

- **Preview deployments do Pages**: o Pages gera URLs por commit/branch
  (`https://<hash>.docuparser.pages.dev`), cada uma uma **origem distinta** → CORS
  bloquearia. Se previews forem usados para teste, considerar
  `CORS_ALLOWED_ORIGIN_REGEXES` (Django) / `allow_origin_regex` (FastAPI) cobrindo
  `^https://.*\.docuparser\.pages\.dev$`, **ou** um domínio de alias estável.
- **Não quebrar testes**: manter o **fallback relativo** é obrigatório — os handlers
  MSW usam `/api/*` e `/com/*`. Rodar `npm test` antes do PR.
- **`atoms/fastapi_app.py`**: [linhas 71-77](../../../docuparse-project/backend-com/src/atoms/fastapi_app.py#L71-L77) usam `allow_origins=["*"]` **com** `allow_credentials=True` (combinação inválida pela spec de CORS). Se esse app estiver no caminho de alguma chamada do frontend, alinhá-lo ao modelo por env var; caso contrário, registrar como dívida técnica.
- **Credenciais**: o fluxo usa Bearer em header (sem cookies). Não habilitar
  `withCredentials` no axios — evita exigência de `Allow-Credentials` e o conflito
  com origens específicas.
- **Timeout de gateway**: comentário em [main.tsx:71-75](../../../docuparse-project/frontend/src/main.tsx#L71-L75) indica que chamadas longas já apareceram como "502/CORS". Independe desta correção, mas vale observar no teste de ponta a ponta.

---

## 8. Plano de validação

1. **Unit/integração (frontend)**: `npm test` (Vitest+MSW) verde — confirma fallback
   relativo intacto.
2. **Build**: `npm run build` com env de staging + `grep` do Passo 4 encontrando a
   URL absoluta no `dist`.
3. **Preflight (CORS)** direto no backend:
   ```bash
   curl -i -X OPTIONS https://staging.docuparser-core.innovox.ai/api/auth/login \
     -H "Origin: https://staging.docuparser.pages.dev" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: authorization,content-type"
   ```
   Esperado: `200/204` com `Access-Control-Allow-Origin: https://staging.docuparser.pages.dev`
   e `Access-Control-Allow-Headers` incluindo `authorization, content-type`.
4. **Ponta a ponta (staging)**: DevTools → Network no login:
   - host do request agora é `…docuparser-core.innovox.ai` (**não** `pages.dev`);
   - `OPTIONS` `200` seguido de `POST` `200`;
   - login conclui e navegação autenticada funciona.
5. Repetir um fluxo de `backend-com` (ex.: upload manual `POST /documents/manual`)
   para validar `VITE_BACKEND_COM_URL`.

## 9. Rollout & rollback

- **Rollout**: (1) PR do frontend (`main.tsx` + `vite.config.ts`); (2) setar
  `CORS_ALLOWED_ORIGINS` e `VITE_BACKEND_*_URL` na infra/painel do Pages; (3)
  redeploy do Pages; (4) validar (seção 8).
- **Ordem importa**: garantir o **CORS no backend antes/junto** do deploy do frontend
  absoluto — caso contrário, o `405` só troca por erro de CORS.
- **Abrangência**: diferente do teste "um endpoint por vez" (que era para a hipótese
  de trailing slash), esta correção resolve **login, `/api/ocr/*` e `/com/*` de uma
  vez** — todos compartilham a mesma raiz (o `baseURL`).
- **Rollback**: reverter o PR do frontend restaura o comportamento relativo (volta a
  depender de proxy). As mudanças de env/CORS na infra são aditivas e podem
  permanecer sem efeito colateral.

---

## 10. Checklist de tarefas

**Código (implementado nesta branch)**
- [x] **Frontend** — `main.tsx`: `baseURL` de `api`/`authApi`/`comApi` derivado de
      `VITE_BACKEND_CORE_URL`/`VITE_BACKEND_COM_URL` com fallback relativo.
- [x] **Build** — `vite.config.ts`: derivação por branch renomeada para
      `VITE_BACKEND_CORE_URL`/`VITE_BACKEND_COM_URL` (`??=`, não sobrescrever painel).
- [x] **Proxy** — `vite.config.ts`: alvo do proxy passa a ler `BACKEND_CORE_URL`/
      `BACKEND_COM_URL` (sem `VITE_`), desacoplado do client (§5.4).
- [x] **Compose** — `docker-compose.yml` (serviço `frontend`): env renomeada para
      `BACKEND_CORE_URL`/`BACKEND_COM_URL`.
- [x] **Testes** — `npm test` verde (28/28); build de staging embute a URL absoluta;
      build de compose não vaza hostname interno.

**Infra / manual (fora deste repositório)**
- [ ] **Pages** — (opcional) definir `VITE_BACKEND_CORE_URL`/`VITE_BACKEND_COM_URL` no
      painel do Cloudflare Pages; caso contrário, a derivação por branch já cobre.
- [ ] **Infra** — `CORS_ALLOWED_ORIGINS` com a(s) origem(ns) do Pages nos 3 backends
      (core, com, ocr) — no repo `innovox-kubernetes-deployments`.
- [ ] (Opcional) **Preview deploys** — regex de origem se previews forem usados.
- [ ] **Validação em staging** — preflight `curl` + login ponta a ponta.
- [ ] (Dívida) Avaliar `allow_origins=["*"]` + credenciais em `atoms/fastapi_app.py`.
