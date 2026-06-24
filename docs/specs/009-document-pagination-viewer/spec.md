# Feature Specification: Otimização da Consulta e Navegação de Documentos

**Feature Branch**: `009-document-pagination-viewer`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "Otimização da Consulta e Navegação de Documentos — paginação das listagens de documentos (máx. 25 por página, navegação, info de posição, compatível com filtros/busca, sem carregar a base inteira no frontend) e visualização do documento original diretamente na interface pela ação de visualização (olho) das listagens, sem download, respeitando permissões, adicionando a pré-visualização ao lado das informações já existentes sem removê-las."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Paginação das listagens de documentos (Priority: P1)

Como usuário que acompanha documentos no DocuParse, quero que as listas de
documentos sejam exibidas em páginas de tamanho limitado, com navegação entre
páginas e indicação da minha posição, para que a consulta seja rápida mesmo
quando a base tem muitos documentos.

**Why this priority**: É a base de performance e escalabilidade da consulta
documental. Hoje as listas carregam todos os registros de uma vez, degradando o
carregamento e a navegação conforme a base cresce. Entrega valor imediato e é
pré-requisito para uma experiência saudável em todas as telas de listagem.

**Independent Test**: Com uma base contendo mais de 25 documentos, abrir cada
tela de listagem e confirmar que somente uma página (≤ 25 registros) é exibida e
trafegada por vez, que é possível navegar entre páginas, que a posição (página
atual / total) é exibida, e que busca/filtros continuam retornando resultados
corretos ao longo de todo o conjunto — não apenas dentro da página atual.

**Acceptance Scenarios**:

1. **Given** uma base com 60 documentos pendentes, **When** o usuário abre a tela
   Inbox, **Then** no máximo 25 documentos são exibidos e apenas esses são
   trafegados/renderizados na primeira operação.
2. **Given** o usuário na página 1 de uma listagem com várias páginas, **When**
   ele avança para a próxima página, **Then** os 25 registros seguintes são
   exibidos e a indicação de posição (ex.: "Página 2 de 3") é atualizada.
3. **Given** o usuário aplica uma busca/filtro em uma listagem, **When** o
   resultado tem mais de 25 itens, **Then** a busca considera todo o conjunto
   (não apenas a página corrente) e os resultados são paginados em blocos de até
   25, reiniciando na página 1.
4. **Given** o usuário está em uma página > 1, **When** ele altera a
   busca/filtro, **Then** a navegação retorna à página 1 do novo conjunto de
   resultados.
5. **Given** uma listagem com exatamente 25 ou menos documentos, **When** o
   usuário a abre, **Then** os controles de navegação não permitem avançar além
   da única página existente.

---

### User Story 2 - Visualização do documento original na ação de visualização (Priority: P2)

Como usuário com acesso a um documento, quero, ao acionar a visualização (ícone
de olho) em uma listagem, ver o documento original embutido na própria interface,
ao lado das informações que já são exibidas hoje, para conferir o conteúdo sem
precisar baixar o arquivo nem perder o contexto da navegação.

**Why this priority**: Melhora significativamente a conferência documental, mas
depende de um fluxo já existente (a ação de visualização) e agrega valor mesmo
após a paginação. É incremental e não bloqueia a US1.

**Independent Test**: Acionar a visualização de um registro e confirmar que o
documento original associado é exibido embutido na interface (sem download),
junto às informações já existentes (que permanecem inalteradas), respeitando as
permissões de acesso, e que fechar a visualização retorna ao estado anterior sem
prejudicar a navegação.

**Acceptance Scenarios**:

1. **Given** um registro de documento em uma listagem, **When** o usuário aciona
   a visualização (olho), **Then** as informações já existentes continuam sendo
   exibidas e, ao lado/junto delas, surge uma área com a pré-visualização do
   documento original correspondente àquele registro.
2. **Given** a visualização aberta, **When** o usuário consulta o documento,
   **Then** ele consegue ver o conteúdo sem realizar download do arquivo.
3. **Given** documentos em diferentes formatos suportados pelo sistema, **When** a
   visualização é acionada, **Then** o documento é exibido para todos os formatos
   atualmente processados.
4. **Given** um usuário sem permissão de acesso ao documento, **When** a
   visualização é acionada, **Then** o documento original não é exibido e o
   controle de acesso vigente é respeitado.
5. **Given** a visualização aberta, **When** o usuário a fecha, **Then** ele
   retorna ao ponto anterior da listagem sem perda de contexto (página, filtro,
   busca).

---

### Edge Cases

- **Listagem vazia**: nenhuma página de resultados; a interface indica ausência
  de registros e não oferece navegação.
- **Última página parcial**: a última página exibe menos de 25 registros sem
  erro.
- **Página fora do intervalo**: solicitar uma página inexistente (ex.: após
  exclusões reduzirem o total) recai de forma segura em uma página válida.
- **Atualização automática durante navegação**: a atualização periódica das
  listas (acompanhamento de processamento) preserva a página/filtros atuais sem
  "pular" o usuário de volta ao início.
- **Documento sem arquivo / arquivo indisponível**: a área de visualização exibe
  um estado claro de indisponibilidade, sem quebrar as informações já exibidas.
- **Formato sem pré-visualização nativa**: caso algum formato não permita
  exibição embutida, a área de visualização informa isso de forma amigável, sem
  forçar download e sem remover as informações existentes.
- **Concorrência busca + troca de página**: alternar rapidamente entre busca e
  navegação não deve exibir resultados inconsistentes da página anterior.

## Clarifications

### Session 2026-06-24

- Q: Quais listagens entram no escopo da paginação? → A: As 4 telas principais —
  Dashboard, Inbox, Aprovados e Rejeitados. O seletor de "documento de
  referência" em Configurações permanece como está (não paginado); DLQ, Usuários
  e Roles ficam fora (não são listas de documentos).
- Q: O que fazer com a busca por valor de campo extraído ao mover a busca para o
  backend? → A: Manter — a busca server-side também pesquisa dentro de
  `extraction_result.fields`, preservando o comportamento atual.

## Requirements *(mandatory)*

### Functional Requirements

#### Paginação (US1)

- **FR-001**: As telas de listagem de documentos no escopo — Dashboard
  ("Documentos"), Inbox (pendentes), Aprovados e Rejeitados — MUST exibir os
  registros de forma paginada. O seletor de "documento de referência" em
  Configurações permanece como lista simples (fora do escopo desta feature).
- **FR-002**: Cada página MUST exibir no máximo 25 documentos.
- **FR-003**: O usuário MUST conseguir navegar entre as páginas (avançar,
  retroceder e, quando aplicável, ir para a primeira/última).
- **FR-004**: A interface MUST exibir a posição do usuário no conjunto: página
  atual, total de páginas e quantidade total de registros quando disponível.
- **FR-005**: Busca e filtros existentes MUST continuar funcionando em conjunto
  com a paginação, considerando o conjunto completo de resultados e não apenas a
  página corrente. A busca MUST cobrir nome, status, tipo e canal **e também os
  valores dos campos extraídos** (`extraction_result.fields`), preservando o
  comportamento atual da busca.
- **FR-006**: Ao alterar busca ou filtros, a navegação MUST reiniciar na primeira
  página do novo conjunto de resultados.
- **FR-007**: O sistema MUST retornar apenas os registros necessários à página
  solicitada, sem carregar a base completa para paginar posteriormente no cliente.
- **FR-008**: A paginação MUST ser aplicada de forma consistente (mesma
  semântica de tamanho de página, posição e navegação) em todas as listagens
  documentais.
- **FR-009**: A atualização automática/periódica das listas MUST preservar a
  página e os filtros atuais do usuário.

#### Visualização do documento original (US2)

- **FR-010**: O usuário MUST conseguir abrir a visualização do documento original
  associado a um registro por meio da ação de visualização já existente na
  listagem.
- **FR-011**: A visualização MUST exibir o documento diretamente na interface,
  sem exigir download do arquivo.
- **FR-012**: A visualização MUST adicionar a pré-visualização do documento
  original **junto às informações já exibidas hoje** nessa ação, sem remover nem
  alterar as informações existentes (ex.: uma seção/área adicional ao lado).
- **FR-013**: A visualização MUST suportar todos os formatos de documento
  atualmente processados pelo sistema.
- **FR-014**: A visualização MUST utilizar o arquivo correto associado ao registro
  selecionado.
- **FR-015**: A visualização MUST respeitar as permissões de acesso já existentes;
  documentos aos quais o usuário não tem acesso não MUST ser exibidos.
- **FR-016**: O mecanismo de visualização MUST funcionar para documentos
  armazenados localmente ou em serviços externos de armazenamento.
- **FR-017**: Abrir e fechar a visualização MUST preservar o contexto de
  navegação (página, busca e filtros) da listagem de origem.

#### Compatibilidade (US1 + US2)

- **FR-018**: A solução MUST funcionar com os mecanismos atuais de autenticação,
  autorização, busca e filtragem, sem regressão de comportamento.
- **FR-019**: A solução MUST preservar as informações e ações já disponíveis nas
  listagens (nenhuma informação existente é removida pela mudança).

### Key Entities *(include if feature involves data)*

- **Documento**: registro processado pelo sistema, com metadados (ex.: nome,
  status, canal, tipo, datas) e um arquivo original associado. É o item listado e
  o alvo da visualização.
- **Página de resultados**: recorte do conjunto de documentos correspondente a
  uma posição (página atual) e a um tamanho fixo (até 25), derivado dos filtros/
  busca vigentes; expõe a quantidade total de registros e de páginas.
- **Arquivo original**: conteúdo binário do documento (em armazenamento local ou
  externo) exibido na visualização, sujeito às permissões de acesso.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em qualquer tela de listagem, no máximo 25 documentos são exibidos
  e trafegados por operação de carregamento, independentemente do tamanho total
  da base.
- **SC-002**: O tempo de carregamento inicial de uma listagem com base grande
  (ex.: ≥ 1.000 documentos) é perceptivelmente menor que o comportamento atual
  (meta: redução de pelo menos 50% no tempo até a lista ficar utilizável).
- **SC-003**: O usuário consegue localizar e abrir qualquer documento navegando
  por páginas e/ou usando busca/filtros, com a posição (página atual/total)
  sempre visível e correta.
- **SC-004**: Busca e filtros retornam os mesmos resultados de antes, agora
  paginados, considerando todo o conjunto (verificável comparando a contagem
  total de resultados com o esperado).
- **SC-005**: 100% dos formatos de documento atualmente suportados podem ser
  visualizados embutidos na interface, sem download.
- **SC-006**: Ao acionar a visualização, todas as informações exibidas antes da
  mudança continuam presentes, com a pré-visualização adicionada ao lado delas.
- **SC-007**: Nenhum usuário consegue visualizar documento ao qual não tem
  acesso (0 casos de acesso indevido em teste de permissões).
- **SC-008**: Abrir/fechar a visualização não reinicia nem perde a página, busca
  ou filtros ativos da listagem.

## Assumptions

- **Telas no escopo** (definido em Clarifications): Dashboard ("Documentos"),
  Inbox (pendentes), Aprovados e Rejeitados. O seletor de "documento de
  referência" em Configurações permanece como lista simples (fora do escopo).
  Listagens que não são de documentos (eventos de fila/DLQ em Operações,
  usuários, roles) também estão fora do escopo.
- **Tamanho de página fixo**: 25 registros por página, não configurável pelo
  usuário nesta versão (limite definido por RF-02).
- **Busca/filtros server-side**: para atender "apenas os registros necessários" e
  manter busca/filtros corretos sobre todo o conjunto, a filtragem/busca passa a
  ser resolvida no backend em conjunto com a paginação (o frontend deixa de
  carregar a base inteira para filtrar localmente). A busca inclui os valores dos
  campos extraídos (`extraction_result.fields`), conforme Clarifications —
  preservando o comportamento atual; a implementação trata o custo da varredura
  desses campos (ver plano/research).
- **Formatos suportados**: os mesmos já processados hoje pelo sistema (ex.: PDF e
  imagens como PNG/JPG/TIFF/WebP); nenhum novo formato é introduzido por esta
  feature.
- **Reuso de acesso ao arquivo**: a visualização reutiliza o mecanismo existente
  de acesso ao arquivo original do documento, respeitando o controle de acesso já
  vigente; nenhum novo modelo de permissão é criado.
- **Ação de visualização existente**: a feature evolui a ação de visualização já
  presente nas listagens (ícone de olho), preservando seu conteúdo atual e
  apenas acrescentando a pré-visualização.
- **Evolução futura (fora do escopo)**: comparação lado a lado entre documento
  original e dados extraídos pode ser construída sobre esta base, mas não faz
  parte desta entrega.
