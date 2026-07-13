# Contract: CLI, configuração e formatos de saída (Fase A)

## Invocação

Pacote executável (Typer):

```bash
# a partir do diretório de trabalho (onde está credentials.json), ex.: .../downloads/fases/
python -m superlogica_download_map [OPÇÕES]
```

### Opções

| Flag | Default | Efeito |
|---|---|---|
| `--work-dir PATH` | `.` (cwd) | Raiz de credenciais e saídas. |
| `--recon` | off | Executa **apenas** a passada de reconhecimento (gera `categorias_encontradas.csv` e para, para revisão humana do dicionário). |
| `--recursive / --no-recursive` | `--recursive` | Varredura recursiva das subpastas do Drive (E-11). |
| `--map-format [csv\|json]` | `csv` | Formato do mapa de download. |
| `--credentials PATH` | `<work-dir>/credentials.json` | Caminho da credencial OAuth. |
| `--verbose` | off | Log em nível debug (linhas sem link, fallbacks de nome, etc.). |

### Códigos de saída

| Código | Significado |
|---|---|
| `0` | Execução concluída (mesmo com exceções não-fatais registradas no relatório). |
| `2` | **Fatal** de autenticação (E-01): token inválido/refresh falhou. Mensagem instrui apagar `token.json` e re-logar. |
| `1` | Erro inesperado não tratado. |

## Fluxo de execução (mapeado ao roteiro, Seção 7)

1. **Autenticar** (Drive read-only; cria/reutiliza `token.json`) → falha = exit 2 (E-01). Imprime nomes dos PDFs das duas pastas (marco de validação).
2. **Listar/baixar** PDFs-lista (recursivo) — um por vez.
3. **(`--recon`)** coletar `categoria_bruta` distintas → `categorias_encontradas.csv` → **parar**.
4. Para cada PDF: extrair (hyperlink, categoria, complemento, fornecedor); split categoria/complemento; linhas sem link → ignorar (E-03); cruzamento ambíguo → marcar (E-12).
5. Para cada hyperlink: GET Superlógica (retry/backoff); raspar **todas** as âncoras (`href` + `img title`); E-04/E-05/E-06/E-09 conforme o caso.
6. Determinar `pasta_destino` (normalização → família → fallback → `_A_Revisar`).
7. Sanitizar + idempotência (dedup `url_download`) + **append** ao mapa; `status=pendente`.
8. Consolidar `fase_a_relatorio.csv`.
9. Resumo final: nº PDFs lidos, hyperlinks resolvidos, arquivos mapeados, exceções por tipo. **Nenhum** arquivo-alvo baixado.

## Configuração (`config.py`) — parametrizável, FR-024

Ver `data-model.md#Config`. Pontos que **não** podem ser hardcoded no meio da lógica: IDs das pastas, dicionário de famílias, tolerância de cruzamento, política de pausa/retry, caminhos de saída.

## Saídas secundárias — formatos

### `fase_a_relatorio.csv` (relatório de exceções)
```csv
tipo,origem,detalhe,acao_tomada
E-04,"despesas_06_2026.pdf | FORNECEDOR X | https://...arquivos?accesskey=...",HTTP 404 na página,pulado
E-07,"despesas_05_2026.pdf | FORNECEDOR Y",categoria indeterminada,"→ _A_Revisar"
E-12,"despesas_06_2026.pdf | link @y=412",mais de um candidato de categoria,"revisar cruzamento"
```

### `categorias_encontradas.csv` (passada de reconhecimento)
```csv
categoria_bruta,chave_canonica,pasta_destino_proposta
Construção-Reformas,construcao reformas,Construção-Reformas
Água,agua,Água
Condomínio,condominio,Condomínio
```

### Estrutura de pastas (só estrutura; sem arquivos-alvo na Fase A)
```
downloads/
├── Construção-Reformas/
├── Água/
└── _A_Revisar/
```

## Segurança

`credentials.json` e `token.json` **nunca** versionados. Cobertos pela regra `downloads/` do `.gitignore`; adicionar também regras explícitas `credentials.json` e `token.json` (defesa em profundidade, R10).
