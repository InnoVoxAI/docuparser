# Quickstart: Convite Direto de Usuários por Tenant Admin

Passos manuais para validar a feature ponta a ponta em dev (backend em `docuparse-project/backend-core`, comandos via `./run_script.sh` a partir da raiz do repo).

## 1. Preparar um tenant com admin ativo

```bash
./run_script.sh python manage.py seed_data
```

Confirma que existe ao menos um tenant com um admin já ativado (senha utilizável) — necessário para logar como tenant admin no passo 2.

## 2. Logar como tenant admin

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "<admin-email-do-seed>", "password": "<senha-do-seed>"}'
```

Guardar o `access` token retornado.

## 3. Convidar um usuário comum

```bash
curl -X POST http://localhost:8000/api/users/ \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Maria Silva", "email": "maria@example.com", "role_id": "<id-da-role-operator>"}'
```

Esperado: `201`, `meta.invite_sent: true`, nenhuma senha no payload de resposta.

## 4. Capturar o email de convite (dev usa `EMAIL_BACKEND=console`)

Ver o log/stdout do servidor Django — o corpo do email deve conter um link `/ativar-conta/<token>` e mencionar o papel atribuído (não "administrador").

## 5. Ativar a conta com o token capturado

```bash
curl -X POST http://localhost:8000/api/admin/tenants/invites/<token>/activate/ \
  -H "Content-Type: application/json" \
  -d '{"password": "uma-senha-forte-o-suficiente"}'
```

Esperado: `200`, `{"email": "maria@example.com", "tenant_slug": "<slug>"}`.

## 6. Logar como o novo usuário

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "maria@example.com", "password": "uma-senha-forte-o-suficiente"}'
```

Esperado: `200` com tokens JWT — conta já aprovada, sem qualquer aprovação manual adicional.

## 7. Reenviar convite (caso de teste de expiração/perda)

```bash
curl -X POST http://localhost:8000/api/users/<user_id>/invites/resend/ \
  -H "Authorization: Bearer <access-token>"
```

Esperado: `200`, novo `expires_at`; tentar ativar o link antigo deve agora retornar `410 INVITE_EXPIRED` (invalidado pelo reenvio).

## 8. Confirmar que o auto-cadastro continua funcionando (regressão)

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "João Pendente", "email": "joao@example.com", "password": "outra-senha-forte", "tenant_slug": "<slug>"}'
```

Esperado: `201`, `is_active: false`, mensagem "Aguarde ativação pelo administrador" — comportamento idêntico ao anterior à feature, sem envio de convite (fluxo de auto-cadastro não usa `Invite`).
