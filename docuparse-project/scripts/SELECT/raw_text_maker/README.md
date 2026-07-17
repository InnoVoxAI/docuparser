# raw_text_maker — documento → texto bruto

Produz o **texto bruto** (`.txt`) de cada documento baixado pela **Fase B**
(`superlogica_file_downloader`). Varre `downloads/fases/downloads/<categoria>/`,
manda cada documento para o **backend-ocr** — o mesmo serviço que a aplicação usa
no fluxo principal (documento enviado → texto bruto produzido) — e grava o
resultado em `Raw Text Docs/<categoria>/<mesmo nome>.txt`.

```
downloads/fases/downloads/Manutenções/elevador avis.pdf
        ↓
downloads/fases/Raw Text Docs/Manutenções/elevador avis.txt
```

> Sem dependências novas (`requests` + `Typer` + `rich`). Não toca em banco,
> tenant nem storage: só a etapa documento → texto bruto.

## Pré-requisito

O **backend-ocr** precisa estar no ar (é ele que faz o OCR):

```bash
docker compose up -d backend-ocr    # a partir de docuparse-project/
```

O script confere isso no início e aborta com mensagem clara se não responder —
em vez de falhar documento por documento.

## Uso

A partir de `scripts/SELECT/`:

```bash
uv run python -m raw_text_maker              # usa os defaults abaixo
uv run python -m raw_text_maker --verbose    # loga cada .txt produzido
```

| Flag | Default | Uso |
|---|---|---|
| `--source-root` | `downloads/fases/downloads` | Árvore com as pastas de categoria |
| `--output-root` | `<origem>/../Raw Text Docs` | Raiz dos `.txt` |
| `--errors` | `<destino>/../raw_text_erros.csv` | Relatório de erros |
| `--ocr-url` | `$BACKEND_OCR_URL` ou `http://localhost:8080` | backend-ocr |
| `--engine` | (automático) | Força um engine (`docling`, `tesseract`, `openrouter`) |
| `--timeout` / `--retries` / `--pause` | `300.0` / `3` / `0.0` | Política de rede |
| `--formatted` | off | Regrava com texto formatado só os arquivos docling (ver abaixo) |
| `--verbose` | off | Log por documento |

Exit codes: `0` sucesso (mesmo com documentos em erro — fail-soft) · `1` fatal
(origem ausente, backend-ocr fora do ar) · `2` uso inválido · `130` interrompido.

## Progresso e retomada

A barra mostra o total, quantos já estão prontos, quantos faltam e qual documento
está sendo processado agora:

```
elevador avis.pdf   ━━━━━━━━━━━━╸────────  42/98  43% • 0:03:11 restante: 0:04:20
```

A execução é **incremental e idempotente** — rode o mesmo comando de novo:

- documento com `.txt` presente e **não vazio** é pulado (não reprocessa);
- documento sem `.txt`, com `.txt` de 0 byte, ou que falhou é re-tentado;
- a gravação é atômica (`.part` → rename), então um Ctrl-C nunca deixa um `.txt`
  pela metade que a retomada leria como pronto.

Isso importa porque um scan cai no fallback de IA e leva ~25s: a árvore inteira é
uma corrida de dezenas de minutos que vale poder interromper e continuar.

## Modo formatado (`--formatted`)

O backend-ocr produz dois textos para PDFs digitais: o **padrão** (`raw_text`) e o
**formatado** (`raw_text_formatted`), que preserva a posição espacial do texto
(colunas, tabelas). O formatado só existe no engine **docling** — scans processados
via openrouter não têm.

```bash
uv run python -m raw_text_maker --formatted
```

Este modo **regrava** os `.txt` dos arquivos docling com o texto formatado e deixa
os `.txt` dos scans (openrouter) **intactos**. Para saber quais são quais sem pagar
o custo do openrouter de novo, ele sonda localmente a camada de texto de cada PDF
(PyMuPDF): PDF com texto → docling → reenvia e sobrescreve; sem texto → scan →
mantém. A sonda é só uma otimização de custo — a garantia real está na regra de
sobrescrita: **só grava quando o backend confirma `engine_used == docling` com
formatado não-vazio**, então um arquivo openrouter nunca é sobrescrito, mesmo se a
sonda errar.

> Por que não forçar `--engine docling`? Porque o fallback por texto vazio do
> backend-ocr dispara mesmo com o engine forçado — um scan enviado ao serviço
> custaria a chamada ao openrouter (~25s + API) de qualquer jeito. A decisão de
> **não enviar** precisa ser local.

Requer PyMuPDF no ambiente (já é dependência do projeto). Importa `pymupdf`
diretamente porque o pacote `fitz` no venv é um stub que sombreia o PyMuPDF real.

## Erros

Vão para `raw_text_erros.csv` **conforme acontecem** (append + flush), com
`arquivo_origem, categoria, motivo, tentativas, ocorrido_em`. O arquivo é
truncado a cada execução: ele reflete o que **ainda** está falhando, não o
histórico. Como a run é fail-soft, um documento problemático nunca derruba os
outros.

Casos tratados: falha transitória de rede/5xx (retry com backoff exponencial),
4xx/documento corrompido (erro direto — insistir daria o mesmo resultado), OCR
sem texto (vira erro em vez de `.txt` vazio, senão a retomada daria o documento
por pronto para sempre) e colisão de nome (`recibo.pdf` e `recibo.png` disputando
`recibo.txt` — o segundo é reportado em vez de sobrescrever o primeiro).

## Testes

```bash
uvx ruff check raw_text_maker
```

## Módulos

| Módulo | Responsabilidade |
|---|---|
| `config.py` | Config parametrizável (caminhos, política HTTP, extensões aceitas) |
| `discovery.py` | Varre a árvore, mapeia documento → `.txt`, separa pendentes (retomada) |
| `ocr_client.py` | POST no backend-ocr com retry/backoff; espelha o `OCRClient` do backend-core |
| `outputs.py` | Gravação atômica `.part` → rename + relatório de erros |
| `pipeline.py` | Orquestração fail-soft + barra de progresso + resumo |
| `cli.py` | Interface Typer |
