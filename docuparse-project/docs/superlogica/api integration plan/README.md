# DocuParse × API Condomínios (Superlógica)

_Integração para associar cada documento processado pelo DocuParse ao condomínio correto no ERP._

> **Começando agora ou voltando depois de um tempo?**
> Leia [`00-visao-geral/estado atual discovery superlogica.md`](00-visao-geral/estado%20atual%20discovery%20superlogica.md).
> Ele diz em que pé está cada fase, o que falta e como interpretar os resultados.
>
> **Vai escrever código da Fase C?**
> Leia antes [`00-visao-geral/restricoes-criticas.md`](00-visao-geral/restricoes-criticas.md).
> São 14 restrições que condicionam o desenho — quatro delas corrompem dado ou vazam segredo
> **sem sintoma visível**.

---

## O problema

O DocuParse extrai dados de documentos (nota fiscal, boleto, conta de consumo). O Superlógica
organiza tudo **por condomínio**. A ponte entre os dois é uma hipótese: *o CNPJ extraído do
documento identifica o condomínio certo*. Errar associa uma despesa ao condomínio errado num
sistema financeiro. **Todo o trabalho aqui existe para testar essa hipótese antes de construir
em cima dela.**

## As três fases

```
FASE A ✅ concluída        FASE B 🟡 em andamento        FASE C ⬜ não iniciada
Entendimento               Spike de descoberta            Specify da integração
e estudo da API            (mede e reporta)               (construir de verdade)
```

## Mapa das pastas

| Pasta | O que tem | Quando abrir |
|---|---|---|
| [`00-visao-geral/`](00-visao-geral/) | Estado atual, **restrições críticas** e roadmap | **Comece aqui** |
| [`fase-a-estudo/`](fase-a-estudo/) | Estudo da API (§7 = as perguntas) e H1–H8 (decisões humanas) | Para entender de onde vieram as perguntas |
| [`fase-b-spike/`](fase-b-spike/) | Plano do spike, a ferramenta e **os achados** | Para ver o que foi medido |
| [`endpoints/`](endpoints/) | Um documento por endpoint: o que é, campos, status | Para consultar um endpoint específico |

### Detalhe por fase

**[`fase-a-estudo/`](fase-a-estudo/)** — o entendimento inicial
- [`estudo-api-superlogica-condominios-docuparse.md`](fase-a-estudo/estudo-api-superlogica-condominios-docuparse.md) — o estudo. O **§7** lista as 9 perguntas que só a API responde
- [`pontos-a-esclarecer-validacao-humana.md`](fase-a-estudo/pontos-a-esclarecer-validacao-humana.md) — **H1–H8**, decisões de produto/negócio

> ⚠️ O estudo ainda traz suas 21 tags `[HIP]` originais e **não foi atualizado** com o que a
> Fase B mediu. Alguns pontos dele estão hoje desatualizados — ver a seção §0 do relatório.

**[`fase-b-spike/`](fase-b-spike/)** — a descoberta read-only
- [`plano-fase-b-spike-descoberta.md`](fase-b-spike/plano-fase-b-spike-descoberta.md) — o plano: sub-fases 0–5 e o DoD
- [`ferramenta/`](fase-b-spike/ferramenta/) — o `discovery_spike.py`, seu README e o molde de amostra
- [`achados/RELATORIO-ACHADOS.md`](fase-b-spike/achados/RELATORIO-ACHADOS.md) — **o entregável da fase**
- `achados/execucoes/` — artefatos crus por execução (**fora do git**: contêm PII do ERP)

**[`endpoints/`](endpoints/)** — referência por endpoint
- [`README.md`](endpoints/README.md) — índice com o status de todos
- 4 disponíveis (`condominios`, `despesas`, `fornecedores`, `unidades`), 4 não encontrados, 1 com erro

## Rodar a ferramenta

```bash
# Da raiz do repositório. Sanidade offline — sem rede, sem credencial:
python3 "docuparse-project/docs/superlogica/api integration plan/fase-b-spike/ferramenta/discovery_spike.py" --self-test

# Descoberta completa (precisa de SL_APP_TOKEN e SL_ACCESS_TOKEN no .env):
./run_script.sh python3 "docuparse-project/docs/superlogica/api integration plan/fase-b-spike/ferramenta/discovery_spike.py" -v
```

As saídas caem em `fase-b-spike/achados/execucoes/<AAAA-MM-DD>/`. Detalhes de uso, modos e
variáveis no [README da ferramenta](fase-b-spike/ferramenta/README-discovery-spike.md).

## Estado em uma tabela

| Item | Estado |
|---|---|
| Autenticação e modelo de erro (§7.4) | ✅ Resolvido |
| Endpoints e nomes de campo (§7.1, §7.2-campo, §7.8) | ✅ Resolvido |
| Formato de data, rate limit (§7.6, §7.7) | ✅ Resolvido |
| Anexos na leitura (§7.3) | ⚠️ Campo achado, formato não classificado |
| **Filtro server-side por CNPJ (§7.2)** | ⛔ **Não conclusivo** — a maior decisão de arquitetura da Fase C |
| Paginação (§7.5) | ⛔ Não conclusivo |
| Lote (§7.6) | ⬜ Deferido (depende de escrita) |
| **⭐ Regra de associação (Fase 4)** | ⬜ **Não executada** — falta amostra rotulada |
| H1–H8 (decisões humanas) | ⬜ Todas abertas |

**Bloqueio principal:** a credencial enxerga **1 condomínio**, o que impede o go/no-go da regra
de associação e as conclusões que dependem de volume de carteira.

## Invariantes

- **READ-ONLY absoluto** — só `GET`, por guarda no cliente HTTP. Nenhuma execução altera o ERP.
- **PII e credenciais mascaradas** em toda saída persistida.
- **Nenhum limiar de auto-confirmação embutido** — a ferramenta mede; a política é humana (H5).
- **Fase não executada é declarada**, nunca preenchida com dado inventado.

---

_Spec formal: [`docs/specs/015-superlogica-discovery-spike/spec.md`](../../../../docs/specs/015-superlogica-discovery-spike/spec.md)_
