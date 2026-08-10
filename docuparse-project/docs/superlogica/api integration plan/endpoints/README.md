# Endpoints da API Condomínios (Superlógica) — o que foi avaliado

_Base: `https://api.superlogica.net/v2` · sondagem de 2026-08-07 · modo completo_

Um documento por endpoint candidato do §3 da Fase A, com o que ele é, o que responde e o
estado em que a sondagem o encontrou. **Tudo aqui vem de execução real da ferramenta**, não de
documentação de fornecedor.

> ⚠️ **Só `GET` foi sondado.** O spike é read-only por construção (RI-001). Nada se sabe sobre
> `POST`/`PUT`/`DELETE` nestes endpoints — a validação de escrita é um passo separado e
> explicitamente autorizado, fora da Fase B.

## Índice

| Endpoint | Status | HTTP | Campos | Papel no projeto |
|---|---|---|---|---|
| [`condominios`](condominios.md) | ✅ Disponível | `200` | 109 | ⭐ Núcleo da associação |
| [`despesas`](despesas.md) | ✅ Disponível | `200` | 97 | ⭐ Fonte do gabarito |
| [`fornecedores`](fornecedores.md) | ✅ Disponível | `200` | 83 | Contexto |
| [`unidades`](unidades.md) | ✅ Disponível | `200` | 49 | Apoio |
| [`condominos`](condominos.md) | ❌ Não encontrado | `404` | 0 | — |
| [`contatosunidade`](contatosunidade.md) | ❌ Não encontrado | `404` | 0 | — |
| [`cobrancas`](cobrancas.md) | ❌ Não encontrado | `404` | 0 | — |
| [`planodecontas`](planodecontas.md) | ❌ Não encontrado | `404` | 0 | — |
| [`notafiscal`](notafiscal.md) | ⚠️ Erro do servidor | `500` | 0 | — |

**4 de 9 disponíveis.** Os quatro `404` provavelmente existem sob outro nome — o path foi
inferido na Fase A, não confirmado. `notafiscal` é caso à parte: responde `500` com erro de SQL
vazando, o que indica endpoint quebrado ou não provisionado, não inexistente.

## Como ler os status

| | |
|---|---|
| ✅ **Disponível** | Respondeu `200` com dados; campos registrados |
| ❌ **Não encontrado** | `404`. O path chutado na Fase A está errado — descobrir o real por inspeção do tráfego do ERP |
| ⚠️ **Erro do servidor** | `5xx`. Existe, mas falha do lado do ERP |

## Três coisas que valem para todos

**1. O parâmetro obrigatório.** `condominios` exige `id` — sem ele responde
`403 "Id do condomínio não informado"`, o que faz o endpoint *parecer* quebrado. O coringa
`id=todos` devolve a carteira. Os demais endpoints disponíveis não exigem parâmetro.

**2. O envelope é aninhado.** As respostas vêm como `[ { "<entidade>": [ {…campos…} ] } ]`. Sem
desembrulhar, você lê 1 registro com um único "campo" que é o nome da entidade.

**3. Erro pode vir com HTTP 200.** O corpo pode trazer `msg` (padrão v2) ou `status ≥ 100`
(padrão v1). Sempre confira o corpo, não só o status.

## Limites desta avaliação

- **Carteira de 1 condomínio.** A credencial enxerga apenas `id_condominio_cond=7`. Contagens
  de registros refletem isso, não o volume real.
- **Campos são os do primeiro registro** de cada sonda. Registros diferentes podem trazer campos
  adicionais.
- **Nada sobre escrita.** Ver ressalva no topo.

---

_Fonte: `fase-b-spike/achados/execucoes/2026-08-07/achados.json`.
Contexto completo em [RELATORIO-ACHADOS.md](../fase-b-spike/achados/RELATORIO-ACHADOS.md)._
