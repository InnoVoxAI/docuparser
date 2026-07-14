# superlogica_file_downloader — Fase B

Baixa e organiza os arquivos catalogados pela **Fase A** (spec 012). Consome o
`mapa_download.csv`, faz um **GET público** (sem login) em cada `url_download` do
Superlógica, valida o conteúdo, salva em `downloads/<pasta_destino>/` e produz o
**CSV final** (`relatorio_final.csv`) — o entregável do projeto.

> Spec: [`docs/specs/013-file-download-organization/`](../../../../docs/specs/013-file-download-organization/).
> Fase B **não** acessa o Google Drive nem usa OAuth. Sem dependências novas
> (só `requests` + `Typer`); reusa `sanitize` da Fase A.

## Uso

A partir de `scripts/SELECT/`, no diretório onde está o `mapa_download.csv`:

```bash
uv run python -m superlogica_file_downloader --work-dir downloads/fases
```

Flags principais (ver `contracts/cli-and-config.md`):

| Flag | Default | Uso |
|---|---|---|
| `--work-dir` | `.` | Raiz do mapa e das saídas |
| `--map` | `<wd>/mapa_download.csv` | Mapa de entrada |
| `--map-format` | `csv` | `csv` ou `json` |
| `--downloads-root` | `<wd>/downloads` | Raiz das pastas de destino |
| `--final-csv` | `<wd>/relatorio_final.csv` | CSV final (entregável) |
| `--errors` | `<wd>/fase_b_erros.csv` | Relatório de erros |
| `--pause` / `--timeout` / `--retries` | `1.0` / `30.0` / `3` | Política de rede |
| `--verbose` | off | Log linha a linha |

Exit codes: `0` sucesso (mesmo com linhas em erro — fail-soft) · `1` fatal
(mapa ausente/ilegível E-01, escrita generalizada E-08) · `2` uso inválido.

## Retomada

A execução é **retomável e idempotente**. Rode o mesmo comando de novo:

- linhas `baixado` **com o arquivo presente** são puladas (não rebaixa);
- linhas `erro` são re-tentadas;
- o CSV final não ganha duplicatas.

## Possível expiração (E-04)

Se o resumo destacar erros de **possível expiração** de `accesskey`/`hash`:

1. `uv run python -m superlogica_download_map --work-dir .` (renova as URLs);
2. `uv run python -m superlogica_file_downloader` (retoma só o que faltava).

## Testes

```bash
uv run pytest superlogica_file_downloader/tests -q
uvx ruff check superlogica_file_downloader
```

Lógica pura testada **sem rede/disco** (`requests` mockado, `sleep` injetado,
gravação atômica via `tmp_path`).

## Módulos

| Módulo | Responsabilidade |
|---|---|
| `config.py` | Config parametrizável (caminhos, política HTTP, assinatura PDF) |
| `map_io.py` | Ler/validar o mapa (E-01) e reescrever `status` atomicamente (RN-4) |
| `downloader.py` | GET público com retry/backoff/pausa (E-03/E-09/E-10) + expiração (E-04) |
| `content.py` | Validar `%PDF`/Content-Type (E-05); detectar expiração (E-04) |
| `naming.py` | Nome/caminho final + anti-colisão determinística (E-06/E-07) |
| `atomic.py` | Gravação atômica `.part` → rename (E-11) |
| `outputs.py` | CSV final incremental + dedup; relatório de erros |
| `pipeline.py` | Orquestração fail-soft + resumo (E-08/E-12) |
| `cli.py` | Interface Typer |
