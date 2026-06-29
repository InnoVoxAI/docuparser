# Correção — `invalid internal service token`

> Documento de alto nível sobre o bug de autenticação interna que impedia o uso
> da aplicação em staging, sua causa raiz e os ajustes realizados.

## 1. Resumo executivo

Em staging, logo após o login, a aplicação exibia **`invalid internal service token`**
e o **upload de documentos falhava**. Em localhost funcionava normalmente.

A diferença era a variável `DOCUPARSE_INTERNAL_SERVICE_TOKEN`: **vazia em
localhost, configurada em staging**. O código tratava a *presença* dessa variável
como gatilho de uma verificação que **só aceitava o token interno** e **rejeitava
o JWT do usuário** — exatamente as chamadas que o navegador faz.

A correção **centraliza a autenticação no backend**: os dois back-ends passam a
aceitar **o JWT do usuário OU o token interno de serviço**, e o frontend deixa de
manipular qualquer segredo (passa a enviar apenas o JWT do próprio usuário).

## 2. Sintomas

- Ao logar: `GET /api/ocr/schema-configs` e `/api/ocr/layout-configs` → **401**.
- Ao enviar documento: `POST /api/v1/documents/manual` → **401**; o documento
  "recebido" nunca aparecia na Inbox.
- Apenas em **staging**; em **localhost** tudo funcionava.

## 3. Causa raiz

O envio de uma requisição passa por gates de autenticação diferentes. Com o
token configurado (staging), **três** pontos estavam desalinhados:

| # | Caminho | Serviço | Como o caller se autentica | Problema |
|---|---------|---------|----------------------------|----------|
| A | Frontend → `/api/ocr/*` | backend-core | JWT do usuário | O gate exigia o token interno e **rejeitava o JWT** |
| B | Frontend → `/api/v1/documents/manual` | backend-com | (antes) token interno via `VITE_…` | O frontend não tinha o token → **401**; e expor o token no navegador seria inseguro |
| C | backend-com → `/api/ocr/events/document-received` | backend-core | token interno | Falhava quando os tokens divergiam entre serviços (sync silenciosamente perdido) |

Detalhe técnico do gate A/C: a autenticação padrão (`JWTAuthentication`) sequer
deixava o token interno chegar à verificação — rejeitava antes. E a função de
verificação só liberava com o token interno exato, nunca com um usuário
autenticado.

**Por que só em staging:** com a variável vazia (localhost), o gate ficava
"aberto" (modo dev) e nada era exigido. Com a variável preenchida (staging), o
gate passava a exigir credencial — mas só aceitava a credencial errada para o
caso do frontend.

## 4. O que foi alterado

Princípio: **autenticar pela identidade que o caller apresenta** (JWT do usuário
ou token de serviço), nunca pela mera presença de um segredo no servidor; e
**nenhum segredo no frontend**.

### backend-core
- Autenticação padrão passou a ser a `DocuparseAuthentication`, que resolve
  **JWT do usuário OU token interno** sem rejeitar antes da verificação.
- O gate `_internal_token_error` passou a liberar quando há **usuário
  autenticado (JWT)** ou **token de serviço**; só retorna 401 sem credencial
  válida. Sem token configurado, mantém o acesso aberto (dev/local).

### backend-com
- Novo `_authenticate_caller`: aceita **JWT do usuário** (verificado com a
  `SECRET_KEY` compartilhada, via `pyjwt`) **OU** o token interno de serviço.
  Aplicado aos endpoints de usuário (upload, email/poll, whatsapp/poll).
- Removido um `print/raise` de debug que vazava o valor do token.
- Passou a ler `SECRET_KEY` (mesma do backend-core) e ganhou a dependência `pyjwt`.

### frontend
- O cliente do backend-com (`comApi`) passou a enviar o **JWT do usuário** (como
  já fazia para o backend-core), via interceptor.
- Removido todo uso de `VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN` — **nenhum segredo
  embutido no bundle**.

### configuração / infra
- `SECRET_KEY` documentada no `.env` (compartilhado por todos os services); deve
  ter o **mesmo valor** em backend-core e backend-com (é com ela que o JWT é
  assinado e verificado).
- `DOCUPARSE_INTERNAL_SERVICE_TOKEN` continua existindo **apenas entre os
  back-ends** (sync serviço↔serviço), com o mesmo valor; saiu do frontend.
- `Dockerfile` do backend-com atualizado para instalar o `pyjwt`.

## 5. Resultado

Com o token configurado (como em staging):

| Caller | Credencial | Resultado |
|--------|-----------|-----------|
| Usuário logado (frontend) | JWT | ✅ 200 |
| Serviço interno (langextract / backend-com) | token interno | ✅ 200 |
| Sem credencial / token divergente | — | ❌ 401 |

Login, listagem e upload funcionam; o token interno **não trafega mais pelo
navegador**.

## 6. Pré-requisitos de configuração (staging)

1. `SECRET_KEY` com o **mesmo valor** em backend-core e backend-com (env
   compartilhado já garante; usar valor forte, não o default de dev).
2. `DOCUPARSE_INTERNAL_SERVICE_TOKEN` com o **mesmo valor** entre os back-ends.
3. Imagem do **backend-com rebuildada** (dependência nova: `pyjwt`).

## 7. Validação

- Testes automatizados:
  - backend-core: `documents.tests.test_api.InternalServiceTokenGateTests`
    (JWT→200, token de serviço→200, sem credencial→401, sem token→aberto).
  - backend-com: `tests/test_backend_com_app.py`
    (JWT válido→200, token de serviço→200, JWT expirado/chave errada→401).
- Subir a stack (rebuild do backend-com) e, logado, enviar um documento: deve
  aparecer na Inbox, sem `401` no console.

```bash
docker compose up -d --build backend-com
docker compose up -d --force-recreate backend-core frontend
```
