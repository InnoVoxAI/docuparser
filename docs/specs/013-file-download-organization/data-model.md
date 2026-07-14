# Phase 1 — Data Model: Fase B

Entidades da Fase B e seus estados. A Fase B **consome** a linha do mapa (contrato 012) e **produz** a linha do CSV final e o registro de erro. Nenhum banco de dados: tudo é arquivo local (CSV/JSON) ou objeto em memória durante a execução.

---

## 1. `MapRow` — linha do mapa (entrada, consumida)

Espelha o contrato [`mapa-download.md`](../012-download-map-extraction/contracts/mapa-download.md). A Fase B lê **todas** as colunas e escreve **apenas** `status` (FR-004).

| Campo | Tipo | Origem | Uso na Fase B |
|---|---|---|---|
| `url_download` | str (não vazio) | Fase A | GET (Salto 3) + **chave de idempotência** (dedup/retomada) |
| `nome_arquivo` | str (não vazio) | Fase A | Nome base com que salvar; se vazio → fallback determinístico |
| `fornecedor` | str | Fase A | Metadado; fallback de nome; CSV final |
| `categoria_bruta` | str | Fase A | Vai ao CSV final como `categoria` |
| `complemento` | str (pode vazio) | Fase A | Metadado opcional |
| `pasta_destino` | str (não vazio) | Fase A | Diretório de destino (`downloads/<pasta_destino>/`); **não reclassificar** |
| `hyperlink_origem` | str | Fase A | Rastreabilidade; CSV final |
| `pdf_origem` | str | Fase A | Rastreabilidade |
| `status` | enum | Fase A=`pendente` | **Único campo que a Fase B escreve** (`baixado`/`erro`) |

**Validação na carga (E-01/E-02)**:
- Mapa ausente/ilegível → **fatal** (aborta com mensagem: rode a Fase A).
- Colunas essenciais ausentes (`url_download`, `nome_arquivo`, `pasta_destino`, `status`) → **fatal**.
- `url_download` vazia/malformada numa linha → linha vira `erro` (E-02), não fatal.

## 2. `LineStatus` — estado da unidade de trabalho (base da retomada)

Máquina de estados por linha (coluna `status` do mapa):

```text
pendente ──(download OK + validação OK + salvo)──▶ baixado
   │
   └────────(falha definitiva após retries)──────▶ erro
                                                     │
erro ──(reexecução: re-tentar)──────────────────────┘  (erro NÃO é pulado)
baixado ──(reexecução: pular SOMENTE se arquivo existe no destino)──▶ (skip)
```

- **Regra de retomada (D6)**: pular ⇔ `status == baixado` **E** arquivo presente no caminho final determinístico. Caso contrário, processar. `erro` é sempre re-tentado.
- Transições são **idempotentes**: reprocessar uma linha já `baixado`+presente é um no-op (nem rebaixa, nem duplica no CSV final).

## 3. `DownloadOutcome` — resultado de baixar uma linha (em memória)

Produzido por `downloader` + `content` + `naming`/`atomic`; consumido por `pipeline` para decidir status, CSV final e erro.

| Campo | Tipo | Semântica |
|---|---|---|
| `ok` | bool | `True` se baixou, validou e salvou |
| `caminho_local` | str \| None | Caminho relativo salvo (só quando `ok`) |
| `nome_final` | str \| None | Nome efetivo em disco (com discriminador anti-colisão se houve) |
| `motivo` | str \| None | Motivo do erro (quando `not ok`) — texto humano |
| `tentativas` | int | Nº de tentativas HTTP realizadas |
| `possivel_expiracao` | bool | `True` se o padrão E-04 foi detectado (D3) |

**Regras**:
- `ok=True` ⇒ `caminho_local` e `nome_final` preenchidos; `motivo=None`.
- `ok=False` ⇒ `motivo` preenchido; nada foi salvo (o `.part` foi removido).
- `possivel_expiracao=True` só quando `ok=False` e o padrão de expiração casou.

## 4. `FinalRow` — linha do CSV final (entregável, produzida)

Registro appendado **imediatamente** após sucesso (RN-5). Contrato completo em [`contracts/relatorio-final.md`](./contracts/relatorio-final.md).

| Campo | Obrigatório | Origem |
|---|---|---|
| `nome_arquivo` | sim | `DownloadOutcome.nome_final` (nome efetivamente salvo) |
| `hyperlink_origem` | sim | `MapRow.hyperlink_origem` |
| `categoria` | sim | `MapRow.categoria_bruta` |
| `caminho_local` | sim | `DownloadOutcome.caminho_local` |
| `pasta_destino` | recomendado | `MapRow.pasta_destino` |
| `fornecedor` | recomendado | `MapRow.fornecedor` |

- **Chave de dedup**: `url_download` (não é coluna obrigatória do CSV final, mas é a chave lógica que impede regravação na reexecução — RN-6).

## 5. `ErrorRecord` — registro de erro (produzido)

Uma linha em `fase_b_erros.csv` por falha definitiva. Contrato em [`contracts/fase-b-erros.md`](./contracts/fase-b-erros.md).

| Campo | Obrigatório | Semântica |
|---|---|---|
| `url_download` | sim | A URL que falhou |
| `motivo` | sim | Causa (HTTP 404, conteúdo inválido, url malformada, escrita, …) |
| `tentativas` | sim | Nº de tentativas antes de desistir |
| `possivel_expiracao` | sim | `sim`/`não` — sinal E-04 (recomenda re-rodar a Fase A) |
| `nome_arquivo` | recomendado | Nome esperado (rastreabilidade) |
| `pdf_origem` | recomendado | PDF-lista de origem (rastreabilidade) |

## 6. `Config` — configuração resolvida (parametrização, FR-024)

Frozen dataclass, caminhos relativos ao `work_dir` (cwd). Mesma filosofia do `Config` da Fase A.

| Campo | Default | Semântica |
|---|---|---|
| `work_dir` | cwd | Raiz de entrada/saídas |
| `map_path` | `work_dir/mapa_download.csv` | Mapa de entrada (Fase A) |
| `downloads_root` | `work_dir/downloads` | Raiz das pastas de destino |
| `final_csv_path` | `work_dir/relatorio_final.csv` | **Entregável** |
| `errors_path` | `work_dir/fase_b_erros.csv` | Relatório de erros |
| `map_format` | `csv` | `csv` ou `json` (espelha a Fase A) |
| `http_pause_s` | `1.0` | Pausa entre requisições (E-09) |
| `http_timeout_s` | `30.0` | Timeout por requisição |
| `http_retries` | `3` | Tentativas antes de erro (E-10) |
| `http_backoff_base_s` | `2.0` | Base do backoff progressivo |
| `pdf_signature` | `b"%PDF"` | Assinatura de validação (D2) |

---

## Relações

```text
mapa_download.csv ──(1 linha)──▶ MapRow ──processa──▶ DownloadOutcome
                                    │                      │
                              (escreve status)         ok? │
                                    ▼                      ├─ sim ▶ arquivo salvo (atômico) + FinalRow (append) 
                              mapa (status atualizado)     └─ não ▶ ErrorRecord (append) 
```

- 1 `MapRow` → no máximo 1 arquivo salvo, 1 `FinalRow` **ou** 1 `ErrorRecord` (nunca ambos), e exatamente 1 atualização de `status`.
- `url_download` é a chave que amarra retomada (mapa), dedup (CSV final) e rastreio (erro).
