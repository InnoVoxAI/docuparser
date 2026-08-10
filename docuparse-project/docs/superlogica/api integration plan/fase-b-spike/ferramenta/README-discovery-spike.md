# `discovery_spike.py` — Spike de descoberta (READ-ONLY) da API Condomínios

Ferramenta da **Fase B** do estudo DocuParse × Superlógica. Único trabalho: **converter os `[HIP]` do §7 da Fase A em fato** e **testar a regra de associação documento↔condomínio antes de firmá-la**. Produz um relatório de achados que alimenta o `Specify` da Fase C.

> ⚠️ **Segurança:** o script é **descartável** e **100% READ-ONLY** — o cliente HTTP tem uma guarda rígida que bloqueia qualquer método ≠ `GET` (não existe `post`/`put`/`delete`). Rodar não altera nada no ERP. CPF/CNPJ são **mascarados** nos logs e nas saídas. O que persiste é o relatório, não o script.

---

## 1. Pré-requisitos (§3 da Fase B)

Sem estes três itens o script até *roda*, mas não *resolve* nada — só reformula as hipóteses. São os primeiros bloqueios a destravar.

### 1.1 Credencial de API
Um par **`app_token` + `access_token`**, obtido no próprio ERP em **Todos os usuários → API (Integração com outros sistemas) → Aplicativos → Novo App Token**.
- **Crítico:** o token **herda as permissões do usuário que o criou**. Se esse usuário não enxerga toda a carteira, a API filtra os condomínios silenciosamente. Crie o token com um usuário que **veja todos os condomínios**.
- **Ambiente:** idealmente um **trial/sandbox** (plano Enterprise I ou acima). Se for contra produção, tudo bem — o spike só faz `GET`.
- Coloque em variáveis de ambiente (ver §3). **Nunca** versione os tokens.

### 1.2 Amostra rotulada (*ground truth*) — necessária só para a Fase 4
Um conjunto de documentos **cujo condomínio correto já é conhecido**. Sem rótulo, a Fase 4 mede "casou/não casou", mas **não** "acertou/errou" — e é o "errou" que importa.
- **Caminho limpo para obter o gabarito:** pegue documentos **já corretamente arquivados manualmente** no ERP (a associação existente é o gabarito), rode o DocuParse neles e monte o arquivo de amostra (formato no §5).
- Comece pelos tipos já confirmados `[PROD]`: **NF, boleto, conta de consumo** (H7).

### 1.3 Saída do DocuParse
Os campos extraídos desses documentos, **com o papel do CNPJ** (`cnpj_tomador`, `cnpj_fornecedor`, pagador, titular…). É daqui que sai o campo `cnpj_papel_condominio` de cada linha da amostra.

---

## 2. Instalação

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Requer Python 3.9+ e `httpx`. (Para rodar apenas o `--self-test`, nem precisa do `httpx`.)

---

## 3. Configuração

Copie `.env.example` para `.env`, preencha, e exporte (ou use seu carregador de env preferido):

```bash
export SL_APP_TOKEN=...          # obrigatório
export SL_ACCESS_TOKEN=...       # obrigatório
export SL_BASE_URL=https://api.superlogica.net/v2   # opcional (default já é este)
```

| Variável | Obrigatória | Default | Para quê |
|---|---|---|---|
| `SL_APP_TOKEN` | sim | — | autenticação |
| `SL_ACCESS_TOKEN` | sim | — | autenticação |
| `SL_BASE_URL` | não | `https://api.superlogica.net/v2` | base da API |
| `SL_TIMEOUT` | não | `30` | timeout HTTP (s) |
| `SL_MAX_PAGES` | não | `5` | teto de páginas ao montar o índice |
| `SL_FIELD_CNPJ` | não | (heurística) | fixa o nome do campo de CNPJ se a heurística errar |
| `SL_FIELD_ID` | não | (heurística) | fixa o nome do campo de id do condomínio |

---

## 4. Uso

```bash
# 1) Sanidade offline (não bate na API, não precisa de credencial nem httpx)
python discovery_spike.py --self-test

# 2) Smoke check: avalia SOMENTE o endpoint 'condominios' (recomendado como 1ª execução real)
python discovery_spike.py --test-mode -v

# 3) Descoberta completa (fases 0..3, em todos os controllers): auth/erro, endpoints/campos, mecânica, anexos
python discovery_spike.py -v

# 4) Descoberta completa + validação da regra de associação (fase 4)
python discovery_spike.py --sample amostra.json -v

# Rodar só um subconjunto de fases
python discovery_spike.py --phases 0,1

# Diretório de saída customizado
python discovery_spike.py --sample amostra.json --out ./run-2026-01
```

**`--test-mode`** avalia **somente o endpoint `condominios`** (a entidade central da associação): roda auth/erro + descoberta de campos + mecânica só sobre ele, pula a Fase 3 (que ataca `despesas`), e gera achados apenas dele. É o smoke check ideal — confirma conectividade, autenticação e descobre o nome do campo de CNPJ antes de você se comprometer com a varredura completa.

Fluxo recomendado na 1ª vez: **(a)** `--self-test` (offline); **(b)** `--test-mode` para confirmar conectividade/auth e descobrir o `campo_cnpj_condominio` só com `condominios`; se a heurística errar o nome, fixe `SL_FIELD_CNPJ`; **(c)** rode o modo completo; **(d)** por fim, a Fase 4 com `--sample`.

---

## 5. Formato da amostra rotulada (Fase 4)

JSON: uma lista de objetos, um por documento.

```json
[
  {"doc_id": "nf-0001", "tipo": "nota_fiscal", "cnpj_papel_condominio": "11.222.333/0001-81", "condominio_esperado_id": "42"},
  {"doc_id": "agua-0003", "tipo": "conta_consumo", "cnpj_papel_condominio": "", "condominio_esperado_id": "57"}
]
```

| Campo | Obrigatório | O que é |
|---|---|---|
| `doc_id` | sim | identificador do documento (livre) |
| `tipo` | recomendado | tipo do documento (aparece no CSV para segmentar por tipo) |
| `cnpj_papel_condominio` | sim | o CNPJ do **lado condomínio** já extraído pelo DocuParse (com ou sem máscara; vazio se ausente) |
| `condominio_esperado_id` | **para medir precisão** | o `id_condominio` correto (o **gabarito**). Sem ele, mede-se só cobertura |

Veja `amostra.exemplo.json`.

---

## 6. Saídas (o que persiste)

Gravadas em `--out` (default `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/`):

| Arquivo | Conteúdo |
|---|---|
| `RELATORIO-ACHADOS.md` | **Leia primeiro.** Mapeia cada item do §7 da Fase A ao status resolvido + go/no-go da regra |
| `achados.json` | Achados completos e estruturados (todas as fases) |
| `achados.csv` | Por endpoint: existe / HTTP / nº registros / nº campos / erro |
| `associacao.csv` | Por documento: cnpj (mascarado), condomínio casado, esperado, resultado |

Alinhado ao seu padrão CSV-intermediário: os CSVs são auditáveis e servem de insumo direto para as próximas fases.

---

## 7. Rastreabilidade — fases → §7 da Fase A

| Fase do spike | Resolve (§7 da Fase A) |
|---|---|
| 0 — auth & modelo de erro | §7.4 |
| 1 — endpoints & campos (inclui achar o **nome** do campo de CNPJ) | §7.1, §7.2 (campo), §7.8 |
| 2 — filtro, paginação, lote, data | §7.2 (filtro), §7.5, §7.6, §7.7 |
| 3 — anexos (leitura) | §7.3 |
| 4 — ⭐ regra de associação | §7 (⭐) e o risco do §5 |
| 5 — consolidação | gera o relatório |

---

## 8. Limitações (honestas)

- **Escrita não é testada.** Confirmar se a despesa **aceita anexo** e o formato de **lançamento** só se resolve escrevendo — fica para um passo autorizado, fora do spike (H1).
- **Expiração de token** não é verificável numa execução única (precisa observação ao longo do tempo).
- **Formato de data com barra** não distingue `DD/MM` de `MM/DD` só na leitura; o teste ativo depende de existir um filtro de data.
- **Nomes de campo/controller são descobertos por heurística.** Confirme via **inspeção do tráfego do ERP** (a interface usa a mesma API — aba *Network* do navegador revela path e nomes de campo exatos). É a conferência cruzada recomendada.
- **CNPJ alfanumérico** (rollout brasileiro em andamento): a validação/normalização aqui é numérica; se surgir CNPJ alfanumérico no cadastro, ajustar `normalize_cnpj`/`is_valid_cnpj`.
- **Rate limit** não é público; o burst da sonda é pequeno de propósito. Na integração, use throttle conservador.

---

## 9. Como isto alimenta a Fase C

O `RELATORIO-ACHADOS.md` reescreve os `[HIP]` da Fase A em fato, e o **go/no-go da regra** + os **endpoints/campos confirmados** viram as entradas do `Specify` real da integração: comportamento observável, critérios de aceite testáveis e o desenho read-only × escrita já sustentado por evidência — não por suposição. Depois disso, o script pode ser descartado.
