# Quickstart — Fase A: gerar o mapa de download

Guia operacional para configurar, executar e re-executar a Fase A. Ela **descobre e cataloga** os arquivos a baixar; **não baixa** nada (isso é a Fase B).

## 1. Pré-requisitos

- Python 3.13 + `uv` (já usado no repo).
- Um `credentials.json` OAuth 2.0 do tipo **"Desktop app"** (Google Cloud Console), com acesso às duas pastas do Drive. Para esta instalação, ele já está em:
  `docuparse-project/scripts/SELECT/downloads/fases/credentials.json`
- Pastas do Drive (leitura):
  1. https://drive.google.com/drive/folders/1uJ6cZYbThBxiKcfcMmrlS-9dn-aVJfzr
  2. https://drive.google.com/drive/folders/13r1wG8rj8YFvYefPoDYhFg-aVESRZMgE

## 2. Instalar dependências

```bash
uv add google-api-python-client google-auth-oauthlib google-auth-httplib2 beautifulsoup4 lxml
# pymupdf, requests, typer já estão no pyproject
```

## 3. Garantir que segredos não vão para o git

`downloads/` já é ignorado pelo `.gitignore` (cobre credentials/token/saídas). Como defesa em profundidade, confirme que `credentials.json` e `token.json` estão ignorados:

```bash
git check-ignore -v docuparse-project/scripts/SELECT/downloads/fases/credentials.json
```

## 4. Passada de reconhecimento (recomendado antes do mapa)

Colete as categorias reais e revise o dicionário de famílias (`config.py`) antes de comprometer o mapa:

```bash
cd docuparse-project/scripts/SELECT/downloads/fases      # diretório de trabalho
python -m superlogica_download_map --recon
# 1º uso: abre o navegador para login OAuth → gera token.json
# saída: ./categorias_encontradas.csv  (revise as pasta_destino_propostas)
```

Ajuste `FAMILY_RULES` em `config.py` se alguma categoria caiu em pasta errada ou em `_A_Revisar`.

## 5. Gerar o mapa

```bash
python -m superlogica_download_map
# saídas em ./ :
#   mapa_download.csv          (ENTREGÁVEL — consumido pela Fase B)
#   fase_a_relatorio.csv       (exceções para revisão humana)
#   downloads/<pasta>/         (estrutura de pastas; vazia nesta fase)
```

Resumo impresso ao final: nº de PDFs lidos, hyperlinks resolvidos, arquivos mapeados e exceções por tipo.

## 6. Retomar / re-executar

A escrita é incremental e **idempotente** (dedup por `url_download`). Se a execução for interrompida, rode de novo o mesmo comando: o mapa já tem o progresso e nada é duplicado.

## 7. Login expirou? (E-01)

Se aparecer erro fatal de autenticação (exit code 2):

```bash
rm token.json           # no diretório de trabalho
python -m superlogica_download_map   # refaz o login
```

## 8. Verificação (aceitação)

- Cada página do Superlógica com N âncoras gerou N linhas no mapa.
- Toda linha tem `url_download`, `nome_arquivo`, `fornecedor`, `categoria_bruta`, `pasta_destino`, `hyperlink_origem`, `pdf_origem`, `status=pendente`.
- Variantes (`AGUA`/`Água`) na mesma pasta; indeterminadas em `_A_Revisar` + no relatório.
- Nenhum arquivo-alvo baixado.

## 9. Testes

```bash
uv run pytest docuparse-project/scripts/SELECT/superlogica_download_map/tests -q
```
Unit tests não tocam rede/disco; Drive/Superlógica são mockados e a extração de PDF usa fixtures.
