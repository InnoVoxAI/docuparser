# Feature Specification: Workflow de Aprovação e Rejeição de Documentos

**Feature Branch**: `002-doc-approval-rejection`

**Created**: 2026-06-03

**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Aprovação de Documento (Priority: P1)

O operador, após revisar um documento com extração de campos concluída, aprova o documento. O documento sai da Inbox e passa a aparecer na tela de Aprovados.

**Why this priority**: Essa é a ação primária do fluxo de validação — sem ela, nenhum documento avança no processo.

**Independent Test**: Selecionar um documento pendente com extração concluída na Inbox e clicar em "Aprovar". Verificar que o documento some da Inbox e aparece na tela "Aprovados" com data de aprovação preenchida.

**Acceptance Scenarios**:

1. **Given** um documento com status PENDENTE e extração concluída está na Inbox, **When** o operador clica em "Aprovar", **Then** o status do documento muda para APROVADO, a data de aprovação é registrada, o documento desaparece da Inbox e aparece na tela "Aprovados".
2. **Given** um documento com status PENDENTE e extração NÃO concluída está na Inbox, **When** o operador tenta clicar em "Aprovar", **Then** o sistema exibe uma mensagem de erro informando que a extração precisa ser concluída antes da aprovação, e o status não é alterado.
3. **Given** um documento já APROVADO, **When** o operador acessa a tela "Aprovados", **Then** o documento é exibido com nome, status e data de aprovação.

---

### User Story 2 — Rejeição de Documento com Motivo (Priority: P1)

O operador rejeita um documento, fornecendo obrigatoriamente um motivo de rejeição. O documento sai da Inbox e aparece na tela de Rejeitados com o motivo persistido.

**Why this priority**: Rejeição é o outro resultado possível do fluxo de validação; o motivo é essencial para rastreabilidade.

**Independent Test**: Selecionar um documento pendente com extração concluída na Inbox, preencher o campo "Motivo da Rejeição" e clicar em "Rejeitar". Verificar que o documento some da Inbox, aparece em "Rejeitados" e que o motivo é recuperável.

**Acceptance Scenarios**:

1. **Given** um documento PENDENTE com extração concluída, **When** o operador preenche o campo "Motivo da Rejeição" e clica em "Rejeitar", **Then** o status muda para REJEITADO, o motivo e a data de rejeição são persistidos, o documento some da Inbox e aparece em "Rejeitados".
2. **Given** um documento PENDENTE com extração concluída, **When** o operador clica em "Rejeitar" sem preencher o "Motivo da Rejeição", **Then** o sistema exibe uma mensagem de erro indicando que o motivo é obrigatório e o status não é alterado.
3. **Given** um documento PENDENTE com extração NÃO concluída, **When** o operador tenta rejeitar, **Then** o sistema bloqueia a ação no backend e exibe mensagem de erro, independentemente da interface.

---

### User Story 3 — Inbox Exibe Apenas Documentos Pendentes (Priority: P2)

A tela Inbox exibe somente documentos com status PENDENTE, removendo da listagem qualquer documento já aprovado ou rejeitado.

**Why this priority**: A Inbox é o ponto de entrada do fluxo; documentos já decididos não devem poluir a fila de trabalho.

**Independent Test**: Com documentos em diferentes estados (PENDENTE, APROVADO, REJEITADO) no sistema, acessar a Inbox e verificar que apenas os PENDENTES são exibidos.

**Acceptance Scenarios**:

1. **Given** o sistema possui documentos nos estados PENDENTE, APROVADO e REJEITADO, **When** o operador acessa a Inbox, **Then** apenas os documentos com status PENDENTE são listados.
2. **Given** um documento é aprovado pelo operador, **When** o operador retorna à Inbox, **Then** o documento aprovado não aparece mais na listagem.
3. **Given** um documento é rejeitado pelo operador, **When** o operador retorna à Inbox, **Then** o documento rejeitado não aparece mais na listagem.

---

### User Story 4 — Tela de Aprovados (Priority: P2)

Uma nova tela "Aprovados" é acessível pelo menu lateral e exibe todos os documentos com status APROVADO.

**Why this priority**: Necessária para que o operador tenha visibilidade sobre o histórico de documentos aprovados.

**Independent Test**: Após aprovar ao menos um documento, navegar para "Aprovados" pelo menu lateral e verificar que o documento aparece com nome, status e data de aprovação.

**Acceptance Scenarios**:

1. **Given** o operador está no sistema, **When** clica em "Aprovados" no menu lateral, **Then** uma tela é exibida listando todos os documentos com status APROVADO, contendo nome do documento, status e data de aprovação.
2. **Given** nenhum documento foi aprovado ainda, **When** o operador acessa "Aprovados", **Then** a tela exibe uma mensagem de estado vazio (ex.: "Nenhum documento aprovado").
3. **Given** vários documentos foram aprovados, **When** o operador acessa "Aprovados", **Then** todos os documentos aprovados são listados.

---

### User Story 5 — Gestão de Documentos Rejeitados (Priority: P2)

A tela "Rejeitados" exibe todos os documentos rejeitados com nome, status e data de rejeição. Para cada documento, o operador pode visualizar o motivo, reprocessar o OCR ou excluir o documento.

**Why this priority**: Permite que erros de rejeição sejam corrigidos e que o ciclo de vida do documento continue.

**Independent Test**: Com ao menos um documento rejeitado, acessar "Rejeitados", verificar exibição dos dados e executar cada uma das três ações individualmente.

**Acceptance Scenarios**:

1. **Given** existem documentos rejeitados, **When** o operador acessa "Rejeitados", **Then** cada documento é listado com nome, status REJEITADO e data de rejeição.
2. **Given** um documento rejeitado está na lista, **When** o operador clica em "Visualizar Motivo", **Then** o motivo de rejeição persistido é exibido.
3. **Given** um documento rejeitado está na lista, **When** o operador clica em "Reprocessar OCR", **Then** o processamento OCR é reiniciado, o documento retorna ao fluxo e seu status passa a PENDENTE ao final do reprocessamento.
4. **Given** um documento rejeitado está na lista, **When** o operador clica em "Excluir" e confirma, **Then** o documento é removido permanentemente do sistema e não aparece mais em nenhuma tela.

---

### Edge Cases

- O que acontece se o operador tenta aprovar ou rejeitar um documento que já foi aprovado ou rejeitado? O sistema deve bloquear a ação e informar que a decisão já foi tomada.
- O que acontece se o motivo de rejeição contiver apenas espaços em branco? O sistema deve tratar como campo vazio e exibir erro de validação.
- O que acontece se o reprocessamento de OCR falhar? O sistema deve exibir uma mensagem de erro e manter o status REJEITADO.
- O que acontece se o operador tentar excluir um documento que está em processamento? O sistema deve bloquear ou avisar sobre o estado ativo.
- O que acontece se múltiplos operadores tentarem aprovar/rejeitar o mesmo documento simultaneamente? O primeiro a confirmar prevalece; o segundo vê uma mensagem informando que o documento já foi decidido.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Documentos que não possuem status APROVADO nem REJEITADO DEVEM ter status PENDENTE.
- **FR-002**: A tela Inbox DEVE exibir exclusivamente documentos com status PENDENTE.
- **FR-003**: O sistema DEVE permitir a aprovação de um documento PENDENTE somente quando a extração de campos estiver concluída.
- **FR-004**: Ao aprovar um documento, o sistema DEVE persistir o novo status (APROVADO) e a data/hora da aprovação.
- **FR-005**: Ao aprovar um documento, este DEVE desaparecer da Inbox e passar a ser exibido na tela "Aprovados".
- **FR-006**: O sistema DEVE permitir a rejeição de um documento PENDENTE somente quando a extração de campos estiver concluída.
- **FR-007**: A rejeição de um documento EXIGE que o campo "Motivo da Rejeição" esteja preenchido com conteúdo não vazio.
- **FR-008**: Ao rejeitar um documento, o sistema DEVE persistir o novo status (REJEITADO), a data/hora da rejeição e o motivo informado.
- **FR-009**: Ao rejeitar um documento, este DEVE desaparecer da Inbox e passar a ser exibido na tela "Rejeitados".
- **FR-010**: A validação que impede aprovação/rejeição sem extração concluída DEVE existir no backend, independentemente da interface.
- **FR-011**: Uma nova tela "Aprovados" DEVE ser criada e acessível pelo menu lateral, exibindo nome do documento, status e data de aprovação para cada documento aprovado.
- **FR-012**: A tela "Rejeitados" DEVE exibir nome do documento, status e data de rejeição para cada documento rejeitado.
- **FR-013**: A tela "Rejeitados" DEVE oferecer a ação "Visualizar Motivo" para cada documento, exibindo o motivo persistido.
- **FR-014**: A tela "Rejeitados" DEVE oferecer a ação "Reprocessar OCR" para cada documento, reiniciando o processamento e retornando o documento ao fluxo com status PENDENTE.
- **FR-015**: A tela "Rejeitados" DEVE oferecer a ação "Excluir" para cada documento, removendo-o permanentemente do sistema após confirmação do operador.

### Key Entities

- **Documento**: Representa o arquivo enviado para processamento. Possui: nome original, status (PENDENTE | APROVADO | REJEITADO), data de aprovação (opcional), data de rejeição (opcional), motivo de rejeição (opcional).
- **Decisão de Aprovação**: Evento associado a um documento que registra a aprovação com data/hora.
- **Decisão de Rejeição**: Evento associado a um documento que registra a rejeição com data/hora e motivo obrigatório.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O operador consegue aprovar ou rejeitar um documento com extração concluída em menos de 60 segundos a partir da abertura da Inbox.
- **SC-002**: 100% dos documentos aprovados ou rejeitados deixam de aparecer na Inbox imediatamente após a decisão, sem necessidade de recarregar a página.
- **SC-003**: 100% das tentativas de aprovação ou rejeição sem extração concluída são bloqueadas pelo sistema com mensagem de erro clara.
- **SC-004**: O motivo de rejeição é sempre recuperável — 100% dos documentos rejeitados exibem corretamente o motivo ao usar "Visualizar Motivo".
- **SC-005**: Um documento rejeitado reprocessado retorna ao fluxo de OCR e, ao final do reprocessamento, aparece na Inbox com status PENDENTE.
- **SC-006**: A tela "Aprovados" é acessível em até 5 cliques a partir de qualquer tela do sistema via menu lateral.

---

## Assumptions

- O sistema já possui um mecanismo para determinar quando a extração de campos de um documento está concluída; esse estado será consultado na validação de aprovação/rejeição.
- "Extração concluída" é definida como: o processo de extração de campos foi executado e retornou resultado (com ou sem valores encontrados) para o documento.
- Apenas um status de decisão é possível por documento: um documento APROVADO não pode ser rejeitado e vice-versa, a menos que seja reprocessado.
- A confirmação de exclusão (passo de confirmação antes de excluir) é assumida como padrão de UX para evitar exclusões acidentais.
- Não há controle de permissões por papel de usuário nesta versão — todos os operadores têm acesso às ações de aprovação, rejeição, reprocessamento e exclusão.
- A tela "Rejeitados" já existe no menu como item de navegação; esta feature expande seu conteúdo e adiciona as ações.
- O reprocessamento de OCR reseta os campos extraídos anteriormente, pois o documento retorna ao início do fluxo de processamento.
