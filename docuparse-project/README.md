# DocuParse Experimental

Sistema para validação de extração de dados estruturados de documentos complexos.

## Arquitetura

O projeto é dividido em 3 microserviços:

1.  **frontend**: React + Vite (Porta 5173)
2.  **backend-core**: Django (Porta 8000) - Gateway, Gestão e Autenticação.
3.  **backend-ocr**: FastAPI (Porta 8080) - Motor de IA e Extração.

## Como Rodar

1.  Certifique-se de ter o Docker e Docker Compose instalados.
2.  Na raiz do repositório, execute:

```bash
bash run-pipe.sh
```

3.  Para parar tudo:

```bash
docker compose down
```
