---
title: Preferências de trabalho do usuário
type: note
permalink: docuparser/preferencias-de-trabalho-do-usuario
tags:
- preferences
---

- Em fase de desenho, não começar a implementar até o usuário pedir explicitamente
  ("comece a implementação"). Aprovar decisões de desenho ou pedir um diagrama não
  autoriza implementar. **Por quê:** em 2026-09-30 (plano de contas) o usuário
  interrompeu a implementação iniciada junto com o pedido de um diagrama.
- Diagramas de modelo de dados: só o diagrama, no estilo do mapa de banco que o
  usuário usa como referência (SVG com agrupamentos por app, setas ortogonais,
  legenda, clique destaca ligações), e sempre mostrando como as tabelas novas se
  ligam aos modelos existentes. Sem seções extras de texto.
- Não usar os PDFs soltos na raiz do repo (ex. `01_2025_DARF.pdf`) como base de
  análise. Documentos reais de clientes ficam em `docs_por_plano_de_contas/`
  (ver [[docuparser/reference/docs-por-plano-de-contas-dataset-de-documentos-reais]]).
  **Por quê:** em 2026-10-04 o usuário corrigiu uma análise do motor de regras
  feita sobre o DARF da raiz.
- Revisão de arquitetura 2026-11: uma AR-* por sessão. O agente faz o commit na branch e o
  usuário abre o PR. **Deploy em hml só no final de todas as modificações**, não a cada
  AR. **Por quê:** pedido do usuário em 2026-11-27, depois do AR-23. Ao fim de cada
  sessão, entregar um prompt pronto para a próxima tarefa.
