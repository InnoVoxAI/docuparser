# Contract: CLI e Configuração da Fase B

Interface de linha de comando do downloader e a configuração parametrizável (FR-024). Espelha as convenções da CLI da Fase A para consistência operacional.

## Invocação

```bash
# a partir do diretório de trabalho (onde está o mapa_download.csv da Fase A):
python -m superlogica_file_downloader [OPÇÕES]
```

Entrypoint: `superlogica_file_downloader/__main__.py` → `cli.app` (Typer).

## Flags

| Flag | Default | Semântica |
|---|---|---|
| `--work-dir PATH` | cwd | Raiz de entrada/saídas; todos os caminhos default são relativos a ela |
| `--map PATH` | `<work-dir>/mapa_download.csv` | Mapa de entrada (Fase A) |
| `--map-format [csv\|json]` | `csv` | Formato do mapa (espelha a Fase A) |
| `--downloads-root PATH` | `<work-dir>/downloads` | Raiz das pastas de destino |
| `--final-csv PATH` | `<work-dir>/relatorio_final.csv` | Caminho do CSV final (entregável) |
| `--errors PATH` | `<work-dir>/fase_b_erros.csv` | Caminho do relatório de erros |
| `--pause FLOAT` | `1.0` | Pausa (s) entre requisições (E-09) |
| `--timeout FLOAT` | `30.0` | Timeout (s) por requisição |
| `--retries INT` | `3` | Tentativas antes de marcar erro (E-10) |
| `--verbose` | off | Log linha a linha do progresso |

> **Sem** flags de credenciais/OAuth: a Fase B **não** acessa o Google Drive (FR-003).

## Códigos de saída

| Código | Significado |
|---|---|
| `0` | Execução concluída (mesmo com linhas em `erro` — fail-soft). Resumo impresso. |
| `1` | Falha **fatal**: mapa ausente/ilegível ou colunas essenciais faltando (E-01), ou falha de escrita generalizada (permissão/espaço — E-08). |
| `2` | Erro de uso da CLI (flag inválida) — padrão do Typer. |

## Configuração (`config.py`)

`Config` (frozen dataclass) + `build_config(work_dir, ...)` resolvendo caminhos relativos ao `work_dir`. Constantes no topo (nunca espalhadas na lógica): defaults de HTTP (`HTTP_PAUSE_S=1.0`, `HTTP_TIMEOUT_S=30.0`, `HTTP_RETRIES=3`, `HTTP_BACKOFF_BASE_S=2.0`), assinatura de validação (`PDF_SIGNATURE=b"%PDF"`), nomes de arquivo default, e as colunas do CSV final. Valores alinhados com a Fase A onde aplicável.

## Resumo final (stdout, FR-022)

Ao encerrar, imprimir:
- total de linhas no mapa;
- **baixadas** com sucesso (novas nesta execução);
- **puladas** (já concluídas + presentes em disco);
- **com erro**, quebrado por motivo/tipo;
- onde ficaram: raiz de downloads, CSV final, relatório de erros;
- **se houver erros de possível expiração (E-04)**: destacar a recomendação de re-rodar a Fase A para renovar as URLs e depois re-rodar a Fase B (que retoma só o que falta).
