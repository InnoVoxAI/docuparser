# 📘 Comandos Úteis

## 🚀 Subir a aplicação

```bash
bash run-pipe.sh
```

## 🛑 Parar a aplicação

```bash
bash stop-all.sh
```

## 📜 Verificar logs

### Logs do container

```bash
cd /docuparser/docuparse-project && docker compose logs -f backend-ocr
```

### Logs filtrados

```bash
docker compose logs -f backend-ocr | grep -E 'FIELD_SCORE_CRITICAL|LLM_SEMANTIC_DECISION|CRITICAL_FIELDS_EXTRACTED'
```

## 🐳 Parar o Docker

```bash
docker compose -f docuparse-project/docker-compose.yml down
```

## 📊 Logs (alternativa)

```bash
docker compose -f docuparse-project/docker-compose.yml logs -f backend-ocr
```

## 🏢 Multi-Tenancy (PostgreSQL schema-per-tenant)

### Aplicar migrations ao schema público (shared apps)

```bash
docker compose exec backend-ocr python manage.py migrate_schemas --shared
```

### Aplicar migrations a todos os schemas de tenants

```bash
docker compose exec backend-ocr python manage.py migrate_schemas
```

### Migrar dados existentes para schemas isolados (use --dry-run primeiro)

```bash
docker compose exec backend-ocr python manage.py migrate_to_schemas --dry-run
docker compose exec backend-ocr python manage.py migrate_to_schemas
```

### Provisionar novo tenant via API

```bash
curl -X POST http://localhost:8000/api/admin/tenants/ \
  -H "Authorization: Bearer <admin_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"slug": "nova-empresa", "name": "Nova Empresa Ltda"}'
```

### Listar tenants ativos

```bash
curl http://localhost:8000/api/admin/tenants/ \
  -H "Authorization: Bearer <admin_jwt>"
```

### Rodar testes com PostgreSQL (testes de isolamento de schema)

```bash
POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_DB=docuparse POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres \
  docker compose exec backend-ocr pytest -m tenant_db
```
