# `condominos`

**Status:** ❌ Não encontrado · **Papel no projeto:** —

## O que é

Esperava-se o cadastro de condôminos/moradores. Não existe com este nome.

## Chamada

| | |
|---|---|
| **Path** | `GET /v2/condor/condominos` |
| **Métodos sondados** | `GET` apenas — o spike é read-only por construção (RI-001). Escrita não foi testada e está fora do escopo da Fase B |
| **Parâmetro obrigatório** | nenhum identificado |
| **HTTP observado** | `404` |
| **Registros na sonda** | 0 |
| **Campos descobertos** | 0 |
| **Erro no corpo** | `Não encontrado. A página que você tentou acessar não existe.` |

## Campos descobertos

Nenhum — o endpoint não retornou dados.

## Encaminhamento

- Descobrir o path real por **inspeção do tráfego do ERP** (a interface usa a mesma API; a aba *Network* revela o path exato).


---

_Gerado a partir de `fase-b-spike/achados/execucoes/2026-08-07/achados.json`. Ver [RELATORIO-ACHADOS.md](../fase-b-spike/achados/RELATORIO-ACHADOS.md)._
