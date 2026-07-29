# Quickstart: Onboarding do Administrador de Tenant via Convite por Email

## Rodando localmente (dev)

1. Sem configurar nenhum provedor de email, o backend usa o console backend do Django por padrão — o convite aparece no log do `runserver`/`run_script.sh`.
2. Criar um tenant via `POST /api/admin/tenants/` informando `slug`, `name`, `admin_name`, `admin_email`.
3. Verificar no log de saída do backend o corpo do email de convite (contém o link com o token).
4. Copiar o link e fazer `POST /api/admin/tenants/invites/{token}/activate/` com `{"password": "..."}`.
5. Fazer login normalmente em `POST /api/auth/login` com o `admin_email` e a senha definida.

## Variáveis de ambiente novas

| Variável | Default | Descrição |
|---|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` | Backend de envio; trocar para `django.core.mail.backends.smtp.EmailBackend` em produção. |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `EMAIL_USE_TLS` | vazio | Configuração SMTP, só relevante se `EMAIL_BACKEND` for o SMTP backend. |
| `DEFAULT_FROM_EMAIL` | `no-reply@docuparse.local` | Remetente dos emails transacionais. |
| `TENANT_ADMIN_INVITE_TTL_HOURS` | `72` | Prazo de validade do convite, em horas. |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | Usado para montar o link de ativação enviado no email. |

## Variáveis removidas/depreciadas

- `ADMIN_PASSWORD` deixa de ser exigida pelo endpoint `POST /api/admin/tenants/` (a validação de "must be set" é removida de `_provision_tenant`). Continua existindo apenas para uso opcional do `seed_data.py` em ambientes locais (ver tasks de remoção) — se ausente, o comando passa a gerar uma senha aleatória por tenant automaticamente em vez de falhar.

## Rodando os testes

```bash
./run_script.sh backend-core pytest tenants/tests/test_invites.py -v
./run_script.sh backend-core pytest tenants/tests/test_provisioning.py -v
cd docuparse-project/frontend && npm test -- TenantCreateForm
```
