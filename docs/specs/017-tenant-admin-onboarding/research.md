# Research: Onboarding do Administrador de Tenant via Convite por Email

## R1. Existe alguma infraestrutura de email reaproveitável?

**Decision**: Não existe nada reaproveitável. Toda a infraestrutura de envio (transporte + templates + configuração) precisa ser construída do zero.

**Rationale**: Investigação direta no código descartou três hipóteses:

- `EmailSettings` (`documents/models.py:257-278`) e `EMAIL_WEBHOOK_URL` (`core/settings.py`) são para **ingestão de email de entrada** (um microserviço externo faz parsing de emails recebidos via IMAP/webhook e os transforma em documentos) — direção oposta ao que precisamos (enviar um email de saída). Nenhum código em `backend-core` conecta a IMAP ou faz POST para esse webhook.
- `boto3` (dependência já presente em `pyproject.toml` de todos os serviços) é usado **apenas** para S3 (`shared/docuparse_storage/s3.py:60`, `boto3.client("s3", ...)`). Não há nenhum uso de SES (Simple Email Service) em lugar nenhum do monorepo.
- Não existe `EMAIL_BACKEND` do Django configurado, nem SMTP, nem `django.core.mail`, nem bibliotecas como `django-ses`, `anymail`, `djoser` ou `django-rest-passwordreset` nas dependências.
- O único precedente de "conta pendente de ativação" é `register_view` (`users/auth_views.py:96-134`), que cria o usuário com `is_active=False` e espera **ativação manual por um admin** via PATCH (`users/user_views.py:83-97`) — sem token, sem link, sem email. Não é reaproveitável como mecanismo de convite (não há conceito de token de uso único em lugar nenhum do código atual).

**Alternatives considered**:
- Reaproveitar `EmailSettings`/`EMAIL_WEBHOOK_URL`: descartado — é infraestrutura de entrada, não de saída; misturar os dois conceitos no mesmo modelo confundiria a configuração por tenant de recebimento de documentos com o envio de emails transacionais da plataforma (que não é por tenant, é da plataforma).
- Reaproveitar o padrão `is_active=False` + ativação manual do `register_view`: descartado — não atende ao requisito de convite com link e token (FR-005 a FR-009 do spec); seria necessário adicionar token de qualquer forma, então não economiza trabalho, só reaproveitaria o campo `is_active` (que já é reaproveitado, ver R3).

## R2. Qual mecanismo de envio de email usar?

**Decision**: Usar o backend de email nativo do Django (`django.core.mail.send_mail`), com `EMAIL_BACKEND` configurável por variável de ambiente:
- **Dev/test**: `django.core.mail.backends.console.EmailBackend` (padrão) — o convite aparece no log/stdout, atendendo ao FR-012 sem exigir provedor externo.
- **Produção**: SMTP via `django.core.mail.backends.smtp.EmailBackend`, configurado com `EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`/`EMAIL_USE_TLS` a partir de env vars (mesmo padrão de outras integrações do projeto, ex. `BACKEND_OCR_URL`, `LANGEXTRACT_SERVICE_URL` em `core/settings.py`).

**Rationale**: O projeto já é hospedado em AWS (uso de S3 via boto3), então um backend `django-ses` seria tecnicamente coerente — mas isso adicionaria uma dependência nova e um acoplamento a um provedor específico sem que exista qualquer indício de decisão de infraestrutura de envio de email já tomada pelo time (nenhuma menção a SES, SendGrid, Mailgun, etc. em nenhum lugar do repositório). Manter o backend SMTP genérico do Django preserva a opção de qualquer provedor (incluindo Amazon SES via suas credenciais SMTP, sem precisar de uma lib extra) e é a opção padrão/menos surpreendente do framework — consistente com "não inventar integração com provedor específico" definido no pedido do usuário. Se o time decidir por SES/SendGrid mais adiante, é uma troca de biblioteca (`django-ses`/`anymail`) que não exige mudar a camada de serviço de convites, pois esta só chama `send_mail`.

**Alternatives considered**:
- `django-ses` (SES via boto3, já disponível no projeto): mais eficiente se a decisão de usar SES já estivesse tomada, mas introduziria uma dependência de infraestrutura de produção sem confirmação — melhor deixar como opção configurável futura, não como decisão desta feature.
- Construir chamada HTTP direta a um provedor (ex. SendGrid API): descartado, mesma razão acima — decisão de provedor não deveria ser hardcoded no código de convites.

## R3. Como representar "conta sem senha ainda" sem conflitar com o campo `is_active` já usado para "usuário desativado"?

**Decision**: O usuário admin recém-criado é `is_active=True` desde o início (mantendo o significado atual de `is_active` como "conta habilitada ou desabilitada por um admin", ver `tenants/views.py:259`, `users/user_views.py:83-97`), mas com `set_unusable_password()` (API nativa do Django) em vez de `set_password(...)`. O login (`users/auth_views.py:20-33`, via `authenticate()`) já falha naturalmente para senha "unusable" sem precisar de nenhuma lógica adicional — Django trata isso de forma nativa.

**Rationale**: Reaproveita comportamento nativo do Django (`has_usable_password()`/`set_unusable_password()`) em vez de inventar um terceiro estado de conta. Evita conflito com o campo `is_active` já usado para outra finalidade (bloqueio administrativo) — importante porque `login_view` já verifica `is_active` explicitamente com uma mensagem diferente ("Conta inativa. Aguarde ativação pelo administrador.") que não deveria ser confundida com "aguardando definir senha via convite".

**Alternatives considered**:
- Usar `is_active=False` até a ativação via convite (como `register_view` já faz para self-signup): descartado — colidiria com a mensagem/semântica existente de "conta inativa = bloqueada por um admin", tornando ambíguo se uma conta inativa está aguardando convite ou foi desativada por decisão administrativa.

## R4. Onde o endpoint de ativação (público) deve viver, dado o roteamento multi-tenant?

**Decision**: `tenants` é um `SHARED_APPS` (schema público, `core/settings.py:20-33`), e o prefixo `api/admin/tenants/` já é declarado explicitamente em `core/urls.py` como servido a partir do schema público, antes de qualquer resolução de tenant (comentário: "Public URLs: accessible before tenant schema is resolved"). O novo endpoint de ativação (`POST /api/admin/tenants/invites/{token}/activate/`) e o de reenvio (`POST /api/admin/tenants/{slug}/invites/resend/`) seguem o mesmo padrão de `tenants/urls.py`, sem exigir nenhuma mudança de middleware/roteamento multi-tenant.

**Rationale**: Elimina qualquer incerteza sobre se o convite funcionaria antes do tenant existir/ser resolvido no contexto da requisição — o schema público já é o lugar correto e já está provado em produção pelos endpoints de `tenants/views.py`.

## R5. Algum outro serviço (backend-com, backend-ocr, langextract-service) depende do padrão de email fake do admin?

**Decision**: Não. Busca por `admin@`, pelo padrão de slug de tenant e por leitura do email do admin fora de `backend-core` não encontrou nenhuma dependência em `backend-com`, `backend-ocr` ou `langextract-service`. Esses serviços não conhecem o conceito de "admin de tenant" — apenas `backend-core` gerencia usuários e tenants.

**Rationale**: Sem esse achado, seria necessário coordenar mudanças em múltiplos serviços; como não há dependência, o escopo da feature se confirma restrito a `backend-core` + `frontend`, como assumido no spec.

## R6. Critérios mínimos de senha

**Decision**: `AUTH_PASSWORD_VALIDATORS` está atualmente **vazio** (`core/settings.py:162`) em todo o projeto — não existe nenhum padrão de força de senha hoje, nem no `register_view`, nem no `tenant_users_view` (POST de novo usuário). Como esta feature introduz o primeiro fluxo onde uma senha é definida por alguém fora da equipe interna (o admin do tenant, via link público), adicionar os validadores padrão do Django (`MinimumLengthValidator`, `CommonPasswordValidator`, `NumericPasswordValidator`) faz parte do escopo — é o único ponto do sistema onde uma pessoa externa define sua própria senha sem qualquer curadoria humana no meio.

**Rationale**: Evita que o novo endpoint público de ativação seja o elo mais fraco de segurança do sistema. Não estende a validação aos fluxos internos já existentes (criação de usuário por operador) para não expandir o escopo desta feature além do necessário — mas isso deve ficar registrado como débito técnico observado, não resolvido aqui.

**Alternatives considered**: Não adicionar validação nenhuma (manter paridade com o resto do sistema) — rejeitado porque o público-alvo deste endpoint específico (link recebido por email, sem revisão humana) é diferente dos fluxos internos existentes, e a ausência de qualquer validação em um endpoint público de definição de senha é um risco de segurança direto, não apenas uma inconsistência de padrão.
