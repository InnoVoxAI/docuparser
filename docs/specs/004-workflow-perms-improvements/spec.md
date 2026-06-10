# Feature Specification: Workflow and Permissions Improvements

**Feature Branch**: `004-workflow-perms-improvements`

**Created**: 2026-06-08

**Status**: Draft

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detalhes e Ações em Documentos Rejeitados (Priority: P1)

Um operador acessa o Dashboard e clica em um documento com status REJEITADO. O sistema exibe um painel dinâmico com o motivo da rejeição, a data em que foi rejeitado e as ações disponíveis: reprocessar o documento (reiniciar o ciclo de processamento) ou excluir o documento.

**Why this priority**: É a funcionalidade com maior impacto operacional imediato — operadores precisam agir sobre documentos rejeitados diariamente e hoje não têm visibilidade do motivo nem como agir diretamente pelo Dashboard.

**Independent Test**: Pode ser testado rejeitando um documento com um motivo, abrindo o Dashboard e verificando que o painel dinâmico exibe o motivo correto, a data e as duas ações disponíveis.

**Acceptance Scenarios**:

1. **Given** um documento com status REJEITADO no Dashboard, **When** o operador clica nesse documento, **Then** um painel dinâmico é exibido na tela com o motivo da rejeição, a data e hora da rejeição, o botão "Reprocessar" e o botão "Excluir".
2. **Given** o painel dinâmico de um documento rejeitado está aberto, **When** o operador clica em "Reprocessar", **Then** o documento retorna ao início do ciclo de processamento e o painel é fechado.
3. **Given** o painel dinâmico de um documento rejeitado está aberto, **When** o operador clica em "Excluir", **Then** o sistema solicita confirmação antes de remover o documento, e após confirmação o documento é removido do Dashboard.
4. **Given** um documento foi rejeitado sem motivo informado, **When** o operador abre o painel, **Then** o sistema exibe "Motivo não informado" no campo correspondente.

---

### User Story 2 - Datas de Aprovação e Rejeição no Dashboard (Priority: P2)

Um operador visualiza o Dashboard e consegue ver, para cada documento, quando ele foi aprovado ou rejeitado sem precisar abrir o documento individualmente.

**Why this priority**: Melhora a rastreabilidade diária do fluxo documental sem alterar nenhum processo existente — é uma adição de informação, não uma mudança de comportamento.

**Independent Test**: Pode ser testado aprovando e rejeitando documentos diferentes e verificando que as colunas "Aprovado em" e "Rejeitado em" exibem os valores corretos no Dashboard.

**Acceptance Scenarios**:

1. **Given** o Dashboard está sendo exibido, **When** um documento tem status APROVADO, **Then** a coluna "Aprovado em" exibe a data e hora da aprovação formatada de forma legível.
2. **Given** o Dashboard está sendo exibido, **When** um documento tem status REJEITADO, **Then** a coluna "Rejeitado em" exibe a data e hora da rejeição formatada de forma legível.
3. **Given** o Dashboard está sendo exibido, **When** um documento ainda não foi aprovado ou rejeitado, **Then** as colunas "Aprovado em" e "Rejeitado em" ficam vazias (sem exibir erro ou valor nulo visível).

---

### User Story 3 - Extração Automática após OCR (Priority: P3)

Após o upload de um documento e a conclusão do processamento OCR, o sistema inicia automaticamente a extração de campos estruturados sem que o operador precise acionar nenhuma ação manual.

**Why this priority**: Elimina uma etapa manual no fluxo de processamento, reduzindo o tempo total do ciclo documental e o risco de documentos ficarem parados aguardando intervenção.

**Independent Test**: Pode ser testado fazendo upload de um documento e aguardando — sem nenhuma ação adicional, o documento deve progredir automaticamente até o status de aguardando validação.

**Acceptance Scenarios**:

1. **Given** um documento foi enviado e o OCR foi concluído com sucesso, **When** o sistema detecta a conclusão do OCR, **Then** a extração de campos inicia automaticamente sem intervenção humana.
2. **Given** a extração automática foi concluída com sucesso, **When** o operador acessa o Dashboard, **Then** o documento aparece com status de aguardando validação.
3. **Given** o OCR falhou para um documento, **When** o sistema processa o evento de falha, **Then** a extração não é tentada e o documento permanece com status de falha no OCR.

---

### User Story 4 - Processamento em Fila para Múltiplos Documentos (Priority: P4)

Um operador envia vários documentos simultaneamente. Todos entram numa fila de processamento controlada: OCR e extração são executados de forma ordenada e falhas em documentos individuais não bloqueiam os demais.

**Why this priority**: Sem processamento em fila, o envio múltiplo pode sobrecarregar o sistema ou resultar em falhas encadeadas — o que afeta a escalabilidade do sistema quando o volume de documentos cresce.

**Independent Test**: Pode ser testado enviando 5 documentos ao mesmo tempo e verificando que todos são processados (ou falham individualmente) sem que um bloqueie os outros.

**Acceptance Scenarios**:

1. **Given** múltiplos documentos são enviados ao mesmo tempo, **When** o sistema os recebe, **Then** todos são adicionados à fila de processamento e passam pelo OCR e extração de forma controlada.
2. **Given** um documento na fila encontra uma falha durante o OCR, **When** o erro ocorre, **Then** os demais documentos da fila continuam sendo processados normalmente.
3. **Given** múltiplos documentos estão sendo processados em fila, **When** o operador acessa o Dashboard, **Then** os documentos exibem seus status individuais de forma precisa e independente.

---

### User Story 5 - Restrição da Tela Operações a Desenvolvedores (Priority: P5)

Usuários comuns acessam o sistema e não visualizam a opção "Operações" no menu lateral. Apenas usuários identificados como desenvolvedores têm acesso a essa funcionalidade.

**Why this priority**: Reduz a exposição de funcionalidades técnicas a usuários operacionais — melhora a clareza da interface e restringe acesso a operações internas potencialmente destrutivas.

**Independent Test**: Pode ser testado logando com um usuário operador e verificando que "Operações" não aparece no menu; depois logando como desenvolvedor e confirmando que a opção está visível.

**Acceptance Scenarios**:

1. **Given** um usuário sem perfil de desenvolvedor está logado, **When** a interface é carregada, **Then** a opção "Operações" não aparece no menu lateral.
2. **Given** um usuário com perfil de desenvolvedor está logado, **When** a interface é carregada, **Then** a opção "Operações" aparece no menu lateral e é acessível.
3. **Given** um usuário sem perfil de desenvolvedor tenta acessar a URL de Operações diretamente, **When** a navegação ocorre, **Then** o sistema nega o acesso e exibe uma mensagem de acesso não autorizado.

---

### User Story 6 - Nomes Legíveis para Permissões (Priority: P6)

Um administrador acessa a tela de gerenciamento de roles e vê os nomes das permissões em linguagem natural em vez de identificadores técnicos como `documents.send`.

**Why this priority**: Melhora a experiência do administrador ao configurar roles sem necessidade de conhecimento técnico dos códigos internos.

**Independent Test**: Pode ser testado acessando a tela de criação/edição de roles como administrador e verificando que as permissões são listadas com nomes como "Upload de documentos" em vez de `documents.send`.

**Acceptance Scenarios**:

1. **Given** um administrador acessa a tela de gerenciamento de roles, **When** a lista de permissões é exibida, **Then** cada permissão aparece com um nome legível em vez do código técnico.
2. **Given** um administrador está criando uma nova role, **When** seleciona permissões, **Then** os nomes exibidos são compreensíveis por um usuário não técnico.

---

### Edge Cases

- O que acontece quando o painel dinâmico de um documento rejeitado está aberto e o documento é reprocessado por outro usuário simultaneamente?
- O que acontece quando a fila de processamento está sobrecarregada e novos documentos chegam?
- O que acontece quando um documento rejeitado é excluído mas ainda há referências a ele em auditorias ou relatórios?
- O que acontece quando a extração automática falha após o OCR ter sido concluído com sucesso?

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE exibir um painel dinâmico (modal/overlay) ao clicar em um documento com status REJEITADO no Dashboard, contendo motivo da rejeição, data e hora da rejeição e as ações "Reprocessar" e "Excluir".
- **FR-002**: O sistema DEVE exibir "Motivo não informado" quando nenhum motivo foi registrado durante a rejeição.
- **FR-003**: A ação "Reprocessar" DEVE reiniciar o ciclo de processamento do documento a partir do início, sem exigir ação adicional do operador.
- **FR-004**: A ação "Excluir" DEVE solicitar confirmação do operador antes de remover o documento permanentemente do sistema.
- **FR-005**: O Dashboard DEVE exibir as colunas "Aprovado em" e "Rejeitado em" para cada documento, com data e hora formatadas de forma legível.
- **FR-006**: Quando as datas de aprovação ou rejeição não existirem, as colunas correspondentes DEVEM ficar vazias sem exibir valor nulo ou mensagem de erro.
- **FR-007**: Após a conclusão bem-sucedida do OCR, o sistema DEVE iniciar automaticamente a extração de campos estruturados sem intervenção humana.
- **FR-008**: Falhas no OCR DEVEM impedir a tentativa de extração automática para o documento em questão.
- **FR-009**: O sistema DEVE suportar processamento em fila para múltiplos documentos recebidos simultaneamente, garantindo que falhas individuais não interrompam os demais.
- **FR-010**: O menu lateral DEVE ocultar a opção "Operações" para usuários sem a permissão `operations.access`. O sistema de permissões existente já possui esta permissão — basta garantir que apenas roles de desenvolvedor/administrador técnico a recebam.
- **FR-011**: O acesso direto à URL de Operações por usuários sem perfil de desenvolvedor DEVE ser bloqueado pelo sistema.
- **FR-012**: As permissões DEVEM ser exibidas com nomes legíveis em linguagem natural nas telas de gerenciamento de roles.

### Key Entities

- **Document**: Entidade central. Passa por estados (RECEIVED → ... → APPROVED / REJECTED). Possui motivo de rejeição, datas de aprovação e rejeição.
- **ValidationDecision**: Registra decisões de aprovação/rejeição com motivo, notas e data.
- **Permission**: Identificador técnico (código) associado a um nome legível para exibição na interface.
- **User/Developer**: Usuário com atributo ou designação que indica perfil de desenvolvedor, concedendo acesso à tela Operações.
- **ProcessingQueue**: Abstração da fila de processamento que garante isolamento entre documentos durante OCR e extração.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operadores conseguem visualizar o motivo e a data de rejeição de qualquer documento rejeitado em menos de 3 cliques a partir do Dashboard.
- **SC-002**: Operadores conseguem reprocessar ou excluir um documento rejeitado sem sair do Dashboard.
- **SC-003**: Documentos percorrem o fluxo Upload → OCR → Extração → Validação sem nenhuma ação manual intermediária.
- **SC-004**: O envio de até 10 documentos simultâneos resulta em todos sendo processados independentemente — falhas individuais não afetam os demais.
- **SC-005**: Administradores conseguem configurar roles sem consultar documentação técnica de códigos de permissão.
- **SC-006**: Usuários sem perfil de desenvolvedor não visualizam nem conseguem acessar a tela Operações por nenhum meio disponível na interface.
- **SC-007**: O Dashboard exibe a data de aprovação ou rejeição de 100% dos documentos que passaram por essas ações.

---

## Assumptions

- A data de aprovação ou rejeição é derivada do registro de `ValidationDecision` já existente no banco — não requer novo campo no modelo `Document`.
- O motivo de rejeição é o campo `notes` ou `corrected_fields` já persistido em `ValidationDecision` durante a rejeição.
- "Reprocessar" significa reiniciar o ciclo do início (status volta para RECEIVED e OCR é acionado novamente) — não apenas re-executar a extração.
- "Excluir" é uma exclusão permanente (hard delete) do documento e seus registros relacionados — não um soft delete com arquivamento.
- A fila de processamento usa o mecanismo de eventos já existente no sistema (Redis) — não requer nova infraestrutura.
- A extração automática é acionada via evento gerado pelo serviço de OCR ao concluir com sucesso — sem polling.
- Os nomes legíveis das permissões são uma propriedade da entidade `Permission` já existente (campo `description`) — apenas a interface precisa exibi-los no lugar dos códigos.
- Múltiplos documentos simultâneos implica envio pelo mesmo usuário ou por usuários diferentes ao mesmo tempo — ambos os casos devem funcionar.
