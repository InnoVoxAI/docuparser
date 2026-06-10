# Research: Authentication, Roles and Permissions

**Feature**: 003-auth-roles-permissions
**Date**: 2026-06-08

---

## Decision 1: Mecanismo de autenticação — JWT via SimpleJWT

**Decision**: Usar JWT (JSON Web Tokens) via `djangorestframework-simplejwt`, com tokens de acesso de curta duração (15 min) e tokens de refresh de longa duração (7 dias).

**Rationale**: `djangorestframework-simplejwt==5.3.1` já está instalado no `requirements.txt` do `backend-core`. JWT é ideal para SPAs React que fazem chamadas REST — elimina necessidade de sessão no servidor e funciona bem com o proxy Vite em desenvolvimento. Refresh tokens permitem sessões longas sem reautenticar a cada requisição.

**Alternatives considered**:
- **Django Sessions + CSRF**: Funciona com Django nativo, mas exige session storage no servidor e CSRF tokens para chamadas AJAX; complexidade desnecessária para uma SPA desacoplada.
- **API Key simples**: Não tem expiração natural nem mecanismo de refresh; inadequado para autenticação de usuário interativo.
- **Auth0 / OAuth2 externo**: Introduziria dependência de serviço externo desnecessária para um sistema interno.

---

## Decision 2: Token blacklist para logout

**Decision**: Ativar o app `rest_framework_simplejwt.token_blacklist` para invalidar refresh tokens no logout.

**Rationale**: JWT é stateless por natureza, mas o logout exige alguma forma de invalidação server-side. O SimpleJWT BlacklistApp usa uma tabela de banco de dados para registrar tokens revogados — solução simples sem adicionar Redis/cache externo. O access token expira em 15 min naturalmente; apenas o refresh token precisa ser blacklistado.

**Alternatives considered**:
- **Logout somente no cliente** (deletar token do localStorage): Simples, mas o refresh token continuaria válido até expirar (7 dias). Risco de sessão persistente após logout intencional.
- **Redis blacklist customizada**: Mais performática para alta escala, mas adiciona complexidade operacional desnecessária para este sistema.

---

## Decision 3: Modelo de Permission — customizado, não Django contenttypes

**Decision**: Criar modelo `Permission` customizado no app `users` com campos `code` (único, ex: `inbox.view`) e `description` (texto legível).

**Rationale**: As permissões do Django padrão são atreladas a `ContentType` (modelo-ação, ex: `documents.add_document`), o que não mapeia bem para permissões de funcionalidade/tela como "Visualizar Inbox" ou "Gerenciar Roles". O modelo customizado é mais simples, direto e alinhado com a especificação (FR-019: permissões pré-definidas pelo sistema).

**Alternatives considered**:
- **`django.contrib.auth.Permission`**: Requer ContentTypes, nomenclatura `app_label.action_model`; confuso para permissões não-CRUD de tela.
- **Strings hardcoded nas views**: Eliminaria modelo, mas impossibilita listagem dinâmica de permissões via API e gestão no frontend.

---

## Decision 4: Modelo de Role — customizado

**Decision**: Criar modelo `Role` no app `users` com `name` (único) e `permissions` (ManyToMany → `Permission`). Sem herança de roles.

**Rationale**: O modelo de Role é simples — um conjunto nomeado de permissões. O spec define "um usuário = uma role" com permissões associadas à role, não ao usuário. Herança de roles está fora do escopo (Assumption no spec).

**Alternatives considered**:
- **`django.contrib.auth.Group`**: Similar a Role, mas usa as `auth.Permission` vinculadas a ContentTypes — mesmo problema do Decision 3.
- **Flags booleanas por permissão no modelo User**: Não escalável; adicionar novas permissões exigiria migração de schema.

---

## Decision 5: Login por e-mail (não por username)

**Decision**: Customizar o `TokenObtainPairSerializer` do SimpleJWT para aceitar `email` em vez de `username`. O campo `username` do `auth.User` é preenchido automaticamente com o email no cadastro.

**Rationale**: O spec define `User` com email como identificador primário. O modelo `auth.User` exige um campo `username` — ao usar email como username, mantemos o modelo padrão sem precisar de um User customizado. Isso evita a complexidade de uma migration que troque `AUTH_USER_MODEL`.

**Alternatives considered**:
- **Custom User model com email como `USERNAME_FIELD`**: Mais limpo semanticamente, mas exige definir `AUTH_USER_MODEL` antes de qualquer migration — em um projeto com migrations existentes, isso exigiria resetar o banco ou uma migração complexa.
- **Lookup por email + authenticate com username**: Funciona, mas expõe a inconsistência email/username para o cliente.

---

## Decision 6: App Django separado `users` para auth

**Decision**: Criar novo app Django `users` dentro de `backend-core` para conter os modelos `Permission`, `Role`, serializers, views de autenticação e views de gestão de usuários/roles.

**Rationale**: Separar responsabilidades — `documents` cuida do pipeline OCR/validação de documentos; `users` cuida de identidade e acesso. Evita inflar o app `documents` com lógica de auth não relacionada.

**Alternatives considered**:
- **Expandir o app `documents`**: Menos arquivos para criar, mas viola SRP; `documents/models.py` já tem 234 linhas.
- **App `auth_ext`**: Nome ambíguo; `users` é mais descritivo.

---

## Decision 7: Migração do campo `UserProfile.role`

**Decision**: O campo `UserProfile.role` (atualmente `CharField` com TextChoices: OPERATOR, SUPERVISOR, ADMIN) será substituído por `role_ref = ForeignKey(Role, null=True, on_delete=PROTECT)`. A migração inclui um passo de dados para criar Roles correspondentes e associar os UserProfiles existentes.

**Rationale**: O spec exige que Roles sejam entidades dinâmicas gerenciáveis pelo admin. O CharField fixo não permite isso. A migração em dois passos (add nullable FK → data migration → set not null) é o padrão seguro do Django para esse tipo de mudança.

**Alternatives considered**:
- **Manter CharField e adicionar FK separada**: Cria duplicação e inconsistência.
- **Adicionar FK obrigatória diretamente**: Falha se houver UserProfiles existentes sem role mapeada.

---

## Decision 8: Autenticação dual — JWT para frontend, token estático para inter-serviços

**Decision**: Os endpoints existentes de documentos continuam aceitando o token estático (`DOCUPARSE_INTERNAL_SERVICE_TOKEN`) para chamadas inter-serviços (backend-com, workers). Para chamadas do frontend, os mesmos endpoints passam a aceitar JWT Bearer tokens. Uma classe de autenticação DRF customizada `DocuparseAuthentication` tentará JWT primeiro, depois verificará o token estático.

**Rationale**: Não quebrar as integrações inter-serviços existentes enquanto adiciona autenticação de usuário. A verificação de permissões (FR-016) é aplicada apenas para chamadas autenticadas via JWT; chamadas via token estático de serviços internos não passam por permission check.

**Alternatives considered**:
- **Migrar todos os endpoints para JWT imediatamente**: Quebraria backend-com e workers que usam o token estático. Exigiria refatorar múltiplos serviços fora do escopo desta feature.
- **Criar endpoints duplicados com `/v2/` para JWT**: Duplicação de código desnecessária.

---

## Decision 9: Estado de auth no frontend — Context API + localStorage

**Decision**: Usar React `Context API` para estado global de autenticação (user, permissions, loading). Tokens JWT armazenados em `localStorage`. Interceptor axios global para injetar `Authorization: Bearer <access_token>` em todas as chamadas.

**Rationale**: O frontend é uma SPA em `main.jsx` sem router library. Context API é nativa do React e não exige dependências adicionais. localStorage persiste a sessão entre recargas de página. O interceptor axios centraliza a lógica de auth em um único lugar.

**Alternatives considered**:
- **Cookies httpOnly**: Mais seguro contra XSS, mas exige configuração de CORS e SameSite no Django; mais complexo para o ambiente de desenvolvimento atual.
- **Redux ou Zustand**: Adiciona dependência; Context API é suficiente para um único estado global de auth.

---

## Decision 10: Permissões predefinidas (seed via management command)

**Decision**: Criar management command `python manage.py seed_permissions` que cria (ou atualiza) os 8 códigos de permissão definidos em FR-019. Executado uma vez no setup inicial e como parte de migrations de deploy.

**Rationale**: Permissões são pré-definidas pelo sistema (Assumption no spec). Não faz sentido criar via migration Django (migrations devem ser determinísticas e reversíveis); um management command `seed_permissions` é mais idiomático para dados iniciais.

**Alternatives considered**:
- **Fixture Django**: Funciona, mas exige sincronização manual quando permissões mudam; management command é mais explícito.
- **`data migrations`**: Tecnicamente correto, mas data migrations são difíceis de reverter e misturam dados com schema.

---

## Permissões predefinidas (FR-019)

| Código | Descrição |
|--------|-----------|
| `inbox.view` | Visualizar Inbox |
| `documents.send` | Enviar Documentos |
| `documents.validate` | Validar Documentos |
| `models.create` | Criar Modelos |
| `models.edit` | Editar Modelos |
| `operations.access` | Acessar Operações |
| `users.manage` | Gerenciar Usuários |
| `roles.manage` | Gerenciar Roles |
