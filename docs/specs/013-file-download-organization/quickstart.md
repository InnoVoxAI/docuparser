# Quickstart — Fase B (Download e organização)

Como executar a Fase B **depois** de a Fase A ter produzido o `mapa_download.csv`.

## Pré-requisitos

1. **Fase A concluída**: existe um `mapa_download.csv` no diretório de trabalho (tipicamente `docuparse-project/scripts/SELECT/downloads/fases/`). Ver [spec 012](../012-download-map-extraction/spec.md).
2. **Sem credenciais**: a Fase B **não** usa Google Drive/OAuth. Não é preciso `credentials.json` nem `token.json`.
3. **Dependências**: já instaladas via `uv` (a Fase B não adiciona nenhuma). Nada a instalar além do ambiente do projeto:
   ```bash
   uv sync
   ```

## Execução básica

A partir do diretório de trabalho (onde está o mapa):

```bash
cd docuparse-project/scripts/SELECT/downloads/fases
uv run python -m superlogica_file_downloader
```

Isso vai:
- ler `./mapa_download.csv`;
- para cada linha `pendente`, baixar o arquivo (GET público), validar (`%PDF`), salvar de forma atômica em `./downloads/<pasta_destino>/<nome_arquivo>`;
- appendar cada sucesso em `./relatorio_final.csv` (o **entregável**);
- atualizar a coluna `status` do mapa;
- registrar falhas em `./fase_b_erros.csv`;
- imprimir um resumo ao final.

## Opções úteis

```bash
# apontar para um mapa/saídas específicos e afrouxar a taxa:
uv run python -m superlogica_file_downloader \
  --map ./mapa_download.csv \
  --downloads-root ./downloads \
  --final-csv ./relatorio_final.csv \
  --pause 1.5 --timeout 45 --retries 5 --verbose
```

## Retomada (interromper e continuar)

A execução é **retomável**. Se for interrompida (Ctrl-C, queda de rede), basta rodar de novo o **mesmo** comando:
- linhas já `baixado` **com o arquivo presente** em disco são **puladas** (não rebaixa);
- linhas `erro` são **re-tentadas**;
- o CSV final **não** ganha duplicatas.

## Se aparecerem erros de "possível expiração" (E-04)

Se o resumo destacar erros de **possível expiração** de `accesskey`/`hash` (comum quando a Fase B roda muito depois da Fase A):

1. **Re-rode a Fase A** para renovar as URLs do mapa:
   ```bash
   uv run python -m superlogica_download_map --work-dir .
   ```
2. **Re-rode a Fase B** — ela retoma só o que faltava:
   ```bash
   uv run python -m superlogica_file_downloader
   ```

Recomendação operacional: rodar a Fase A e a Fase B **próximas no tempo**.

## Testes

```bash
# a partir de docuparse-project/scripts/SELECT/
uv run pytest superlogica_file_downloader/tests -q
uvx ruff check superlogica_file_downloader
```

Os testes de lógica pura (validação de conteúdo, anti-colisão, retomada, dedup, sinal de expiração) rodam **sem rede nem disco**; a gravação atômica é testada com `tmp_path`.

## Saídas (no diretório de trabalho)

| Arquivo/Pasta | O quê |
|---|---|
| `downloads/<pasta_destino>/<arquivo>` | Arquivos baixados e organizados |
| `relatorio_final.csv` | **Entregável central** (incremental) |
| `fase_b_erros.csv` | Falhas (com sinal de expiração) |
| `mapa_download.csv` | O mesmo mapa, com `status` atualizado |

> Tudo é local e relativo ao diretório de execução; o `downloads/` inteiro é ignorado pelo git.
