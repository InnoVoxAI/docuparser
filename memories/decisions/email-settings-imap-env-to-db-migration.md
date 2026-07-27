---
title: Plano — migrar imap_reader_password/poll_limit/mark_as_read de env para EmailSettings por tenant
type: note
permalink: decisions/email-settings-imap-env-to-db-migration
tags: [backend-core, backend-com, email, imap, security, planned]
---

# Plano — migrar config IMAP de env para `EmailSettings` por tenant

Status: **planejado, não implementado**. Pedido em 2026-07-27; usuário pediu
plano detalhado (incluindo senha com criptografia at-rest) e para tratar em
outro momento — nenhum código foi alterado por este plano.

## Por que isso existe

Hoje `backend-com` lê `imap_reader_password`, `imap_reader_poll_limit`,
`imap_reader_mark_as_read` do `.env` (globais, um valor pra todos os
tenants) em `backend-com/config.py`. Host/porta/pasta/usuário IMAP já
migraram para o modelo `EmailSettings` (por tenant, `backend-core`) há um
tempo — esses três ficaram para trás. `backend-com/services/imap_polling.py`
já busca o resto via `fetch_email_settings_from_core()`
(`GET /settings/email`) e só combina com os 3 valores de env em
`poll_configured_imap_once()`.

Trava encontrada ao planejar: o texto da própria UI
(`EmailSettingsPanel.tsx:107`) documenta que a senha foi deixada de fora do
banco *de propósito* ("continua fora do banco e deve estar em
DOCUPARSE_IMAP_PASSWORD no servidor"), e não existe nenhuma infra de
criptografia em `backend-core` (sem Fernet, sem `EncryptedField`, nada). Por
isso o trabalho foi dividido em duas partes independentes.

## Parte A — `poll_limit` + `mark_as_read` (sem segredo, direto)

Sem complicação de segurança — mesmo padrão de `imap_host`/`imap_port` que
já existe.

1. **Model** (`backend-core/documents/models.py`, classe `EmailSettings`):
   adicionar `poll_limit = models.PositiveIntegerField(default=10)` e
   `mark_as_read = models.BooleanField(default=False)`.
2. **Migration**: `manage.py makemigrations documents` — `AddField` com
   `default=` faz backfill automático nas linhas existentes (é tenant-app,
   roda por schema via `migrate_schemas`/`manage.py migrate` do
   django-tenants). Não precisa de migration de dados à parte.
3. **Serializer** (`documents/serializers.py::EmailSettingsSerializer`):
   incluir `"poll_limit"` e `"mark_as_read"` em `fields`.
4. **View** (`documents/views.py::email_settings_view`): adicionar os dois
   nomes nos dois lugares onde os campos são copiados manualmente (o loop de
   `setattr` e o `update_fields` do `.save()`).
5. **backend-com** (`services/imap_polling.py`):
   - `EmailCaptureSettings` (dataclass): adicionar `poll_limit: int` e
     `mark_as_read: bool`.
   - `email_settings_from_payload()`: ler `payload.get("poll_limit")` /
     `payload.get("mark_as_read")` (defaults 10 / False, mesmo padrão dos
     outros campos).
   - `poll_configured_imap_once()`: trocar
     `limit=settings.imap_poll_limit, mark_as_read=settings.imap_mark_as_read`
     por `limit=email_settings.poll_limit, mark_as_read=email_settings.mark_as_read`
     (o `email_settings` já é resultado de `fetch_email_settings_from_core`,
     só precisa parar de sobrescrever com os valores globais de env).
   - `config.py`: remover `imap_poll_limit` e `imap_mark_as_read` de
     `Settings` (só `imap_password` continua, ver Parte B).
   - `api/app.py::_log_startup_config`: remover as linhas de log de
     `imap_poll_limit`/`imap_mark_as_read` (que agora não existem mais em
     `settings`).
6. **Frontend**:
   - `schemas/emailSettingsSchema.ts`: adicionar `poll_limit: z.number().min(1).max(100)`
     e `mark_as_read: z.boolean()` ao schema e a `EMAIL_SETTINGS_DEFAULTS`
     (10 / false).
   - `components/EmailAccountFields.tsx` (não lido em detalhe ainda — conferir
     layout atual antes de adicionar): novo input numérico (poll_limit) e
     checkbox (mark_as_read), mesmo padrão dos outros campos IMAP.
7. **`.env.example` / docs**: remover `imap_reader_poll_limit` e
   `imap_reader_mark_as_read` (viram config por tenant, não fazem mais
   sentido como env global). Manter `imap_reader_password` e
   `DOCUPARSE_IMAP_TIMEOUT_SECONDS` (timeout de conexão, não é "setting" de
   tenant, fica de fora deste escopo). Atualizar
   `docuparse-project/docs/backend-com/email_reader.md` e
   `docs/resources/resources.md`, que ainda documentam o esquema antigo.

## Parte B — senha com criptografia at-rest (mais trabalho, deferido)

### Problema central: endpoint compartilhado

`GET/PATCH /settings/email` (`email_settings_view`) é o **mesmo endpoint**
usado tanto pelo frontend (usuário via JWT) quanto por `backend-com`
(`fetch_email_settings_from_core`, via `DOCUPARSE_INTERNAL_SERVICE_TOKEN`).
A autenticação (`DocuparseAuthentication`) resolve as duas credenciais no
mesmo `request.user`/`request.auth`; `_internal_token_error` só checa "algum
dos dois é válido", não diferencia o caller depois disso.

Isso importa porque **a senha decriptada só pode ir para o caller
serviço-a-serviço** (`backend-com`, que precisa dela pra login IMAP) — nunca
para o caller-usuário (frontend), que só deve poder *escrever* uma senha
nova, nunca *ler* a atual.

### Infra nova necessária

- Dependência nova: `cryptography` (Fernet) em
  `backend-core/pyproject.toml` — hoje não existe nenhuma lib de
  criptografia no projeto.
- Env var nova: `DOCUPARSE_SECRETS_KEY` (chave Fernet, gerada com
  `Fernet.generate_key()`), obrigatória em prod, só relevante para
  `backend-core`. Entra em `.env.example` (seção backend-core) e no bloco
  `environment` do `backend-core` no `docker-compose.yml`, junto de
  `ADMIN_PASSWORD`/`DEFAULT_TENANT_SLUG`/etc. (`:?` obrigatório, sem
  default).
  - **Perda da chave = perda de todas as senhas IMAP armazenadas**
    (irreversível). Rotação de chave invalida todo o ciphertext existente
    (sem plano de re-encriptação neste escopo — precisaria re-digitar as
    senhas por tenant se a chave rodar). Documentar isso no runbook de ops,
    mesmo nível de cuidado que `SECRET_KEY`.
  - Decisão: chave **separada** de `SECRET_KEY` (não reaproveitar) — propósitos
    diferentes (assinatura de JWT vs. cifra de dados), rotação independente
    desejável.
- Módulo novo, ex. `backend-core/documents/services/secrets.py`:
  `encrypt_secret(plaintext: str) -> str` / `decrypt_secret(token: str) -> str`,
  construindo `Fernet(settings.DOCUPARSE_SECRETS_KEY.encode())` sob demanda.
  Falhar explicitamente (erro claro, não engolir exceção) se
  `DOCUPARSE_SECRETS_KEY` não estiver configurada e alguém tentar
  gravar/ler uma senha — nunca cair em plaintext silenciosamente.

### Model

`EmailSettings`: adicionar `password_encrypted = models.TextField(blank=True, default="")`
(guarda o token Fernet, que já é ASCII-safe base64 — `TextField` evita as
particularidades de `BinaryField` entre bancos). Migration puramente
aditiva, sem risco pras linhas existentes.

### Serializer / view — separar o que cada caller vê

- `EmailSettingsSerializer` (o que o **frontend** vê): continua **sem** campo
  de senha no `Meta.fields` — igual hoje. Isso já garante que o GET do
  usuário nunca inclui a senha, decriptada ou não.
- Campo de escrita à parte (não fica no `Meta.fields` do serializer
  model-based, é tratado manualmente na view, igual aos outros campos do
  loop de PATCH): aceitar `password` opcional no `request.data` do PATCH.
  - Semântica: **vazio/ausente = não mexe na senha atual** (evita que o
    formulário do frontend, que nunca recebe a senha de volta, apague o
    valor salvo ao reenviar o form com o campo em branco). Só uma string
    não-vazia sobrescreve (`config.password_encrypted = encrypt_secret(valor)`).
  - Sem "botão limpar senha" nesta primeira versão — se precisar, seria um
    valor sentinela explícito (`{"password": null}` vs. `""` vs. ausente),
    fica de fora do escopo inicial.
- GET: branch explícito por tipo de caller —
  `is_service_caller = getattr(request, "auth", None) == "service_token"`.
  Só quando `is_service_caller` é `True`, adicionar ao payload de resposta
  `"password": decrypt_secret(config.password_encrypted) if config.password_encrypted else ""`.
  Caller-usuário (JWT) recebe só o `EmailSettingsSerializer.data` de sempre.

### backend-com

- `EmailCaptureSettings` (dataclass): adicionar `password: str`.
- `email_settings_from_payload()`: ler `payload.get("password", "")`.
- `poll_configured_imap_once()`: usar `email_settings.password` em vez de
  `settings.imap_password`.
- `config.py`: remover `imap_password` de `Settings` (a Parte A já removeu
  `imap_poll_limit`/`imap_mark_as_read` — depois desta parte, `Settings` não
  tem mais nada de IMAP).
- `api/app.py`: o bloco inteiro `_log_startup_config` relacionado a
  senha (linhas ~44-74 hoje, incluindo o `DOCUPARSE_IMAP_PASSWORD` que já
  era código morto) vira obsoleto — `backend-com` não guarda mais nenhuma
  senha em env. Remover ou reduzir a um log genérico de config.
- `.env.example` / `docker-compose.yml`: remover `imap_reader_password`
  (junto com `imap_reader_poll_limit`/`imap_reader_mark_as_read` da Parte A —
  a seção IMAP inteira some do `.env`).

### Frontend (parte da Parte B, não da A)

- `EmailSettingsPanel.tsx`: atualizar o texto de `ConfigIntro` (linha ~107)
  — não é mais verdade que a senha "continua fora do banco". Novo texto
  tipo: "senha é armazenada de forma criptografada; deixe em branco para
  manter a senha atual".
- `schemas/emailSettingsSchema.ts`: adicionar `password: z.string().optional()`
  (default `''`). **Nunca** popular esse campo a partir do GET — como o
  backend não devolve senha pro usuário, isso já é natural, mas vale um
  comentário explícito no código pra próxima pessoa não "consertar" isso
  achando que é bug.
- `EmailAccountFields.tsx`: novo `<input type="password">`, placeholder
  "Deixe em branco para manter a senha atual".
- Submit do PATCH: se o campo `password` estiver vazio, não enviar a chave
  no payload (ou enviar `""` e confiar na semântica "vazio = no-op" do
  backend, documentada acima — escolher uma das duas e ser consistente).

### Testes a cobrir

- Roundtrip `encrypt_secret`/`decrypt_secret`.
- PATCH com `password` novo → `password_encrypted` muda; GET como
  service-caller devolve o valor decriptado igual ao enviado.
- GET como JWT-user **nunca** inclui a chave `password` na resposta (nem
  vazia, nem decriptada) — teste de regressão importante pra não vazar.
- PATCH sem `password` (ou `password=""`) preserva o valor já salvo.
- `backend-com`: atualizar `test_backend_com_app.py` (testes de IMAP hoje
  fazem `monkeypatch` em env/`config.settings` — trocar pra injetar via
  `EmailCaptureSettings`/mock do `fetch_email_settings_from_core`).

## Ordem sugerida

1. Parte A isolada (PR pequeno, sem superfície de segurança nova) —
   destrava remover 2 env vars.
2. Parte B em PR separado (dependência nova, migration, branch de
   serializer por tipo de caller, UX de frontend) — maior superfície,
   revisão mais cuidadosa.

## Docs a atualizar junto (mencionadas em CLAUDE.md: sempre documentar)

- `docuparse-project/docs/backend-com/email_reader.md` (lista as vars antigas
  `imap_reader_*` completas, já desatualizada mesmo antes deste plano).
- `docs/resources/resources.md` (linha ~127, tabela de recursos externos).
- `docuparse-project/docs/TECHNICAL.md` (linhas ~925-933).
- `.env.example` raiz (`/docuparser/.env.example`) — já reorganizado em
  2026-07-27 (ver commit da mesma sessão), mas vai precisar de mais um
  ajuste quando cada parte deste plano for implementada.
