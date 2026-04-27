# README — olmOCR (via Docker)

Este documento descreve como subir e usar o serviço `olmOCR` localmente em modo CPU, usando o `docker-compose` criado em `scripts/docker-compose.yml`.

**Pré-requisitos**
- Docker Desktop instalado no macOS
- Imagem `alleninstituteforai/olmocr:latest-with-model` já baixada (ex.: `docker pull alleninstituteforai/olmocr:latest-with-model`)
- Arquivo de variáveis de ambiente: `scripts/.env` (já incluído no repositório)

**Variáveis importantes no `scripts/.env`**
- `OLMOCR_DOCKER_IMAGE` — imagem Docker a usar (padrão: `alleninstituteforai/olmocr:latest-with-model`)
- `OLMOCR_DOCKER_CONTAINER` — nome do container (padrão: `olmocr_api`)
- `OLMOCR_DOCKER_PORT` — porta exposta (padrão: `8010`)
- `OLMOCR_REQUIRE_GPU` — defina `false` para forçar modo CPU
- `OLMOCR_DOCKER_RUN_CMD` — template de `docker run` usado por scripts (opcional)

**Subir com docker compose (modo CPU)**

1. Abra um terminal e vá para a pasta `scripts`:

```bash
cd scripts
```

2. Suba o serviço (modo foreground):

```bash
docker compose up --build
```

3. Para subir em background (detached):

```bash
docker compose up -d --build
```

4. Caso precise forçar arquitetura (Apple Silicon):

```bash
PLATFORM=linux/amd64 docker compose up --build
```

ou para tentar usar arm64 nativo (quando a imagem suportar):

```bash
PLATFORM=linux/arm64 docker compose up --build
```

Obs.: forçar `linux/amd64` usa emulação e será significativamente mais lento.

**Verificar status e logs**

- Verificar containers em execução:

```bash
docker ps
```

- Ver logs do container:

```bash
docker logs -f ${OLMOCR_DOCKER_CONTAINER:-olmocr_api}
```

- Testar endpoint da API (exemplo):

```bash
curl -sS http://localhost:${OLMOCR_DOCKER_PORT:-8010}/v1 | jq .
```

Se o endpoint retornar algo similar a `{"message":...}` ou `200`, o serviço está no ar.

**Como usar com `ocr_olmocr_pipeline.py`**

- O pipeline já lê `OLMOCR_API_BASE` e `OLMOCR_API_KEY` do `scripts/.env`. Por padrão o `OLMOCR_API_BASE` é `http://localhost:8010/v1`.
- Para usar o helper `--ensure-container` (se implementado), o script pode invocar `docker compose up -d` antes de tentar a requisição.

Exemplo de execução do pipeline (supondo venv ativo):

```bash
cd scripts
python ocr_olmocr_pipeline.py --input ../data/input --output-dir ../data/output_json --prompt "Extraia texto e retorne JSON com campos-chave." --ensure-container
```

Se você preferir, suba o container manualmente com `docker compose up -d` e execute o pipeline sem `--ensure-container`.

**Problemas comuns e soluções**

- Container falha com erro relacionado a GPU / CUDA: certifique-se que `OLMOCR_REQUIRE_GPU=false` no `scripts/.env` e que você não está passando flags de GPU no `docker run`.
- Erro de arquitetura (binário não encontrado / exec format error): tente `PLATFORM=linux/arm64` ou `PLATFORM=linux/amd64` conforme sua máquina e disponibilidade da imagem. Use amd64 apenas se necessário (mais lento).
- Se a imagem oficialmente requer CUDA e não há fallback CPU, procure por uma tag `-cpu` ou compile a partir do `Dockerfile` alterando a configuração de runtime (pode ser necessário editar o Dockerfile do projeto upstream).

**Performance e recomendações**

- Rodar modelos grandes em CPU no macOS será lento e consome muita RAM/CPU. Para testes rápidos e pequenos conjuntos de arquivos serve, mas para produção use GPU em servidor apropriado.
- Para desenvolvimento local, considere alternativas leves (ex.: `ollama`, `llama.cpp`, ou modelos CPU-friendly) caso a experiência com `olmOCR` em CPU seja insuficiente.

**Se quiser que eu automatize mais**

- Posso adicionar ao `ocr_olmocr_pipeline.py` um helper `--ensure-container` que execute `docker compose up -d` automaticamente, e outro comando para parar o container (`docker compose down`). Quer que eu implemente isso?

---
Arquivo criado automaticamente pelo assistente para o pipeline `ocr_olmocr_pipeline.py`.
