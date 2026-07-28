# Contract: `mapa_download.csv` (interface Fase A → Fase B)

Este é o **contrato central** da Fase A: o artefato que a Fase B (spec futura 013) consome. A Fase A **produz** este arquivo; a Fase B **lê** as colunas de conteúdo e **atualiza apenas** a coluna `status`. Mudanças aqui são breaking para a Fase B.

## Formato

- Arquivo: `mapa_download.csv` no diretório de trabalho (default; caminho configurável).
- Codificação: **UTF-8**. Separador: `,`. Cabeçalho na 1ª linha. Aspas conforme CSV padrão (campos com vírgula/aspas/quebra são escapados).
- Escrita **incremental** (append por linha, com header escrito uma vez). Alternativa aceitável: JSON array equivalente (`--map-format json`).
- **Idempotência**: `url_download` é única. Re-execução não duplica linhas existentes.

## Colunas (ordem e semântica)

| # | Coluna | Obrigatório | Semântica | Uso na Fase B |
|---|---|---|---|---|
| 1 | `url_download` | sim | Endpoint `.../publico/downloadarquivo?id=...&hash=...` | GET (Salto 3) + **chave de idempotência** |
| 2 | `nome_arquivo` | sim | Nome real do arquivo (ou fallback) já sanitizado | Nome com que salvar em disco |
| 3 | `fornecedor` | sim | Fornecedor da despesa de origem | Metadado / nomeação anti-colisão / CSV final |
| 4 | `categoria_bruta` | sim | Categoria isolada (antes do 1º ` - `) | Vai para o CSV final |
| 5 | `complemento` | não (pode ser vazio) | Descrição após o 1º ` - ` | Metadado opcional / nomeação anti-colisão |
| 6 | `pasta_destino` | sim | Pasta derivada da categoria (ou `_A_Revisar`) | Pasta onde salvar (`downloads/<pasta_destino>/`) |
| 7 | `hyperlink_origem` | sim | Página `publico/arquivos?...` de origem | Rastreabilidade / CSV final |
| 8 | `pdf_origem` | sim | Nome do PDF-lista de origem | Rastreabilidade |
| 9 | `status` | sim | `pendente` na Fase A | Base de retomada; Fase B → `baixado`/`erro` |

## Valores de `status`

| Valor | Escrito por | Significado |
|---|---|---|
| `pendente` | Fase A | Descoberto, ainda não baixado (**único valor produzido pela Fase A**) |
| `baixado` | Fase B | Baixado com sucesso |
| `erro` | Fase B | Falha ao baixar (ver relatório de erros da Fase B) |

## Exemplo (ilustrativo)

```csv
url_download,nome_arquivo,fornecedor,categoria_bruta,complemento,pasta_destino,hyperlink_origem,pdf_origem,status
https://admin345902.superlogica.net/clients/areadocondomino/publico/downloadarquivo?id=112235&hash=963b9dee...,img20260602_08372180.pdf,SINGULAR ENGENHARIA E CONSTRUCAO LTDA,Construção-Reformas,IMPERMEABILIZAÇÃO DE RESERVATÓRIOS PARC 10/10,Construção-Reformas,https://admin345902.superlogica.net/clients/areadocondomino/publico/arquivos?accesskey=634bbf...,despesas_06_2026.pdf,pendente
```

## Garantias que a Fase A oferece à Fase B

- Toda linha tem `url_download`, `nome_arquivo`, `pasta_destino` não-vazios.
- `pasta_destino` já resolvida (a Fase B **não** re-executa a heurística de categoria — só cria o diretório).
- Uma página com N âncoras → N linhas (nenhuma perdida).
- `url_download` única no arquivo.
