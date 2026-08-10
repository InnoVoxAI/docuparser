# `notafiscal`

**Status:** ⚠️ Erro do servidor · **Papel no projeto:** —

## O que é

Esperava-se o cadastro de notas fiscais. Responde `500` com um erro de SQL vazando para o cliente — não é 'não existe', é endpoint quebrado ou não provisionado.

## Chamada

| | |
|---|---|
| **Path** | `GET /v2/condor/notafiscal` |
| **Métodos sondados** | `GET` apenas — o spike é read-only por construção (RI-001). Escrita não foi testada e está fora do escopo da Fase B |
| **Parâmetro obrigatório** | nenhum identificado |
| **HTTP observado** | `500` |
| **Registros na sonda** | 0 |
| **Campos descobertos** | 0 |
| **Erro no corpo** | `SQLSTATE[42S02]: Base table or view not found: 1146 Table 'admin345902.EMPRESA_CONF' doesn't exist` |

## Campos descobertos

Nenhum — o endpoint não retornou dados.

## Encaminhamento

- O erro de SQL vazando indica problema do lado do ERP. **Reportar ao Superlógica** e confirmar se o módulo está provisionado para esta licença.


---

_Gerado a partir de `fase-b-spike/achados/execucoes/2026-08-07/achados.json`. Ver [RELATORIO-ACHADOS.md](../fase-b-spike/achados/RELATORIO-ACHADOS.md)._
