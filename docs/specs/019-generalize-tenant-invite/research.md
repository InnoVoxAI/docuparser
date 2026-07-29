# Research: Convite Direto de Usuários por Tenant Admin

## R1: O modelo `TenantAdminInvite` já é estruturalmente genérico — não precisa de novos campos, só de rename

`docuparse-project/backend-core/tenants/models.py:75-98` define `TenantAdminInvite` com `user` (FK), `tenant` (FK), `token_hash`, `status`, `expires_at`, `used_at`. Nenhum desses campos é específico de administrador — o papel (role) do usuário convidado já é resolvido e gravado em `UserProfile.role_ref` **antes** da criação do registro de convite (`tenants/invites.py:108-109`, `create_admin_invite`), não no próprio `TenantAdminInvite`. Ou seja, o mesmo modelo já serve, sem alteração de schema, para convite de qualquer papel.

- **Decision**: Renomear `TenantAdminInvite` → `Invite` via uma migração `RenameModel` (mantém `db_table` explícito ou aceita o rename automático do Django — ambos triviais, uma única tabela no schema público). Nenhum campo novo.
- **Rationale**: Manter o nome `TenantAdminInvite` para convites de qualquer usuário seria confuso e voltaria a duplicar conceito (a alternativa óbvia — criar `TenantUserInvite` paralelo — é exatamente o que o usuário pediu para evitar). Um rename é a menor mudança que resolve a confusão de nome sem duplicar `token_hash`/expiração/status/endpoint de ativação.
- **Alternatives considered**: (a) Criar um segundo modelo `TenantUserInvite` copiando os campos — rejeitado, duplica exatamente a infraestrutura que o usuário pediu para reaproveitar. (b) Deixar o nome `TenantAdminInvite` como está e só reutilizar via import — funciona tecnicamente, mas o nome mentiria sobre o conteúdo da tabela; rejeitado por clareza de longo prazo.

## R2: Reenvio de convite não pode mais assumir "o admin do tenant" — precisa mirar um usuário específico

`resend_admin_invite(tenant)` (`tenants/invites.py:114-131`) localiza o alvo via `UserProfile.objects.get(tenant=tenant, role_ref__name="admin")` — assume que existe exatamente um usuário-alvo por tenant (o admin). Com convite de usuário comum, um tenant pode ter **vários** convites pendentes simultâneos (vários usuários convidados, ainda não ativados) — a mesma tenant pode ter N pendências, não uma só.

- **Decision**: Generalizar a assinatura para `resend_invite(tenant, user_id)` — o chamador informa explicitamente qual usuário convidado terá o convite reenviado (o frontend já tem esse `id` disponível na listagem de usuários do tenant, que já inclui usuários com senha ainda não definida). A função de reenvio para o admin do tenant (`resend_admin_invite`, ainda usada pelo fluxo de criação de tenant) passa a ser um caso particular que chama a versão genérica com o `user_id` do admin.
- **Rationale**: Evita quebrar o contrato existente do reenvio de convite de admin (`POST /api/admin/tenants/{slug}/invites/resend/`, sem corpo) enquanto abre o caminho para reenviar convite de qualquer usuário convidado.

## R3: Bug pré-existente encontrado — `UserCreateSerializer.create()` ignora `request.tenant`

`docuparse-project/backend-core/users/serializers.py:121-135` (`UserCreateSerializer.create`, usado por `users_list_create_view` POST em `users/user_views.py:57-61`) faz `tenant = Tenant.objects.first()` — **sempre** o primeiro tenant do banco, não o tenant do admin autenticado (`request.tenant`, já resolvido pelo `JWTTenantMiddleware` a partir do claim JWT e usado corretamente no branch GET do mesmo view, linha 51). Ou seja, hoje, se um tenant admin de um tenant que não é o "primeiro" criado no banco usa a tela de criação de usuário (`UserFormModal.tsx` em modo `create`), o novo usuário é silenciosamente associado ao tenant errado.

- **Decision**: Corrigir como parte desta feature — a nova lógica baseada em convite passa a receber `tenant=request.tenant` explicitamente (o mesmo padrão já usado no branch GET da view), eliminando o bug como efeito colateral necessário da própria mudança (não dá para gerar convite de usuário corretamente sem saber o tenant certo).
- **Rationale**: É impossível implementar convite de usuário corretamente sem consertar isso — o bug e a feature são o mesmo ponto de código.

## R4: Achado relacionado, fora de escopo — `TenantUsersPanel.tsx` já rotula seu formulário como "Convidar", mas não envia convite nenhum

`docuparse-project/frontend/src/modules/admin/components/TenantUsersPanel.tsx:100-146` (usado na tela de administração de tenants pelo operador de plataforma, permissão `tenants.manage`) já tem um botão "Convidar" e um campo de senha em texto — mas o POST vai para `tenants/views.py::tenant_users_view`, que cria o usuário com senha em texto puro fornecida pelo operador (sem token, sem email, sem ativação). O rótulo "Convidar" é enganoso hoje.

- **Decision**: Fora de escopo desta feature. O ator dessa tela é o operador de plataforma agindo sobre qualquer tenant (`tenants.manage`), não o tenant admin agindo sobre o próprio tenant — é uma superfície diferente da descrita no spec (User Story 1 é explicitamente sobre o tenant admin). Registrado aqui para não ser esquecido, não para ser resolvido agora.
- **Rationale**: Resolver os dois pontos juntos ampliaria o escopo além do pedido original e misturaria dois atores/permissões diferentes numa só entrega. Fica como candidato a uma feature futura de cleanup, citado explicitamente (não como "cleanup genérico" — ver convenção de tasks explícitas já usada na feature 017).

## R5: Templates de email já são parametrizáveis por contexto — só precisam de uma variável a mais

`tenants/templates/tenants/emails/admin_invite_subject.txt` / `admin_invite_body.txt` (usados por `send_admin_invite_email`, `tenants/invites.py:55-77`) usam `render_to_string` com um dict de contexto (`admin_name`, `tenant_name`, `activation_link`, `expires_at`) — nenhum texto hardcoded assume "administrador" no assunto/corpo além do nome do template em si.

- **Decision**: Renomear os arquivos de template para `invite_subject.txt`/`invite_body.txt` (genéricos) e adicionar `role_display_name` ao contexto (ex.: "administrador", "operador" — nome amigável da role) para a mensagem poder dizer "Você foi convidado para acessar {tenant_name} como {role_display_name}" em vez de assumir administrador.
- **Rationale**: Reaproveita 100% da infraestrutura de envio (`send_mail`, `EMAIL_BACKEND` configurável, captura em dev via console backend) sem criar um segundo par de templates.

## R6: Reuso do endpoint de ativação — nenhuma mudança de rota necessária

`invite_activate_view` (`tenants/views.py:145-207`) e `activate_invite()` (`tenants/invites.py:134-166`) já operam inteiramente por `token_hash`, sem qualquer menção a "admin" na lógica — apenas o modelo (`TenantAdminInvite` → `Invite`, ver R1) precisa do rename.

- **Decision**: Manter a rota pública `POST /api/admin/tenants/invites/{token}/activate/` como está (mesmo endpoint serve ativação de convite de admin e de usuário comum). Nenhuma duplicação de endpoint de ativação.
- **Rationale**: É o núcleo do pedido do usuário — evitar duplicar exatamente esse tipo de endpoint.

## Resumo de decisões

| # | Decisão | Esforço |
|---|---|---|
| R1 | `RenameModel` `TenantAdminInvite` → `Invite`, sem novos campos | 1 migração |
| R2 | Generalizar reenvio para `resend_invite(tenant, user_id)` | Refactor pequeno em `invites.py` |
| R3 | Corrigir `UserCreateSerializer`/`users_list_create_view` para usar `request.tenant` | Corrigido como parte da troca senha→convite |
| R4 | `TenantUsersPanel.tsx` (operador de plataforma) fica fora de escopo | Nenhum — só registrado |
| R5 | Renomear templates de email e parametrizar por role | Rename + 1 variável de contexto |
| R6 | Endpoint de ativação pública reaproveitado sem mudança de rota | Nenhum |
