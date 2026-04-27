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
