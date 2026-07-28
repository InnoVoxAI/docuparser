# Contract: `fase_b_erros.csv` (relatório de erros da Fase B)

Lista as linhas que **falharam em definitivo** (após esgotar retries) para reprocessamento manual. Fail-soft: cada erro aqui **não** interrompeu a execução (FR-018). Este é um contrato **de saída**.

## Formato

- Arquivo: `fase_b_erros.csv` no diretório de trabalho (default; configurável via `--errors`).
- Codificação: **UTF-8**. Separador: `,`. Cabeçalho na 1ª linha. Escrita **incremental** (append por linha).
- Uma linha por `url_download` que falhou.

## Colunas (ordem e semântica)

| # | Coluna | Obrigatório | Semântica |
|---|---|---|---|
| 1 | `url_download` | sim | A URL que falhou (chave de rastreio) |
| 2 | `motivo` | sim | Causa humana: `HTTP 404`, `HTTP 403`, `conteúdo inválido (não-PDF)`, `url malformada`, `falha de escrita`, `timeout`, … |
| 3 | `tentativas` | sim | Nº de tentativas HTTP antes de desistir |
| 4 | `possivel_expiracao` | sim | `sim`/`não` — quando `sim`, recomenda-se **re-rodar a Fase A** para renovar `accesskey`/`hash` (E-04) |
| 5 | `nome_arquivo` | recomendado | Nome esperado do arquivo (rastreabilidade) |
| 6 | `pdf_origem` | recomendado | PDF-lista de origem (rastreabilidade) |

## Exemplo (ilustrativo)

```csv
url_download,motivo,tentativas,possivel_expiracao,nome_arquivo,pdf_origem
https://admin345902.superlogica.net/clients/areadocondomino/publico/downloadarquivo?id=112240&hash=abc...,HTTP 403,3,sim,img20260415_11002233.pdf,despesas_04_2026.pdf
https://admin345902.superlogica.net/clients/areadocondomino/publico/downloadarquivo?id=112250&hash=def...,conteúdo inválido (não-PDF),1,não,recibo_maio.pdf,despesas_05_2026.pdf
```

## Garantias / semântica

- Uma linha `erro` no mapa (`status = erro`) ⇔ uma linha aqui (SC-008).
- `possivel_expiracao = sim` sinaliza o padrão E-04 (HTTP 401/403/410 ou 200-HTML com marcadores de sessão) — o resumo final destaca a recomendação de re-rodar a Fase A e depois a Fase B (que retomará só o que falta).
- Numa reexecução, as linhas `erro` são **re-tentadas**; se passarem, saem do fluxo de erro e entram no CSV final (o operador deve tratar este arquivo como o estado da **última** execução).
