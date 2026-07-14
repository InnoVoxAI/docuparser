# Contract: `relatorio_final.csv` (entregável central da Fase B)

O **CSV final** é o produto de consumo humano/contábil do projeto. A Fase B o escreve **incrementalmente** (uma linha por download bem-sucedido). Este é um contrato **de saída** — quem consome é o operador/contabilidade, não outra fase.

## Formato

- Arquivo: `relatorio_final.csv` no diretório de trabalho (default; caminho configurável via `--final-csv`).
- Codificação: **UTF-8**. Separador: `,`. Cabeçalho na 1ª linha. Aspas conforme CSV padrão.
- Escrita **incremental** (append por linha + flush; header escrito uma vez). Sobrevive a interrupção (RN-5).
- **Idempotência**: `url_download` é a chave lógica de dedup — uma reexecução **não** regrava uma linha já concluída (RN-6). (A `url_download` não precisa aparecer como coluna, mas é a chave usada internamente para dedup a partir do mapa/estado.)

## Colunas (ordem e semântica)

| # | Coluna | Obrigatório | Semântica |
|---|---|---|---|
| 1 | `nome_arquivo` | sim | Nome **efetivamente salvo** em disco (inclui o discriminador anti-colisão `{id}_...` se houve colisão) |
| 2 | `hyperlink_origem` | sim | Página `publico/arquivos?...` de origem (rastreabilidade) |
| 3 | `categoria` | sim | A `categoria_bruta` do mapa |
| 4 | `caminho_local` | sim | Caminho **relativo** onde o arquivo foi salvo (ex.: `downloads/Construção-Reformas/112235_img20260602.pdf`) |
| 5 | `pasta_destino` | recomendado | Pasta de destino (ex.: `Construção-Reformas`, `_A_Revisar`) |
| 6 | `fornecedor` | recomendado | Fornecedor da despesa de origem |

## Exemplo (ilustrativo)

```csv
nome_arquivo,hyperlink_origem,categoria,caminho_local,pasta_destino,fornecedor
img20260602_08372180.pdf,https://admin345902.superlogica.net/clients/areadocondomino/publico/arquivos?accesskey=634bbf...,Construção-Reformas,downloads/Construção-Reformas/img20260602_08372180.pdf,Construção-Reformas,SINGULAR ENGENHARIA E CONSTRUCAO LTDA
112235_img20260602_08372180.pdf,https://admin345902.superlogica.net/clients/areadocondomino/publico/arquivos?accesskey=99aa...,Manutenções,downloads/Manutenções/112235_img20260602_08372180.pdf,Manutenções,BOMBAS LTDA
```

> A 2ª linha ilustra o caso de **colisão**: o mesmo `nome_arquivo` de scanner já existia na pasta, então o nome final recebeu o prefixo determinístico `{id}_` (D1). O `nome_arquivo` no CSV final reflete o nome efetivamente salvo.

## Garantias

- Toda linha corresponde a um arquivo **de fato presente** em `caminho_local` (gravação atômica — só entra no CSV após o rename final).
- Nenhuma `url_download` aparece duas vezes (dedup — RN-6).
- 100% das linhas com `status = baixado` no mapa têm exatamente uma linha aqui (SC-006).
- `caminho_local` é sempre **relativo** ao diretório de execução (FR-015).
