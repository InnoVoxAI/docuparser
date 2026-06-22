# Feature Specification: Edição e Versionamento de Campos Extraídos

**Feature Branch**: `007-extracted-field-versioning`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Edição e Versionamento de Campos Extraídos — permitir que usuários editem e removam campos extraídos automaticamente durante a validação de documentos, com persistência e versionamento completo das listas de campos, histórico de versões somente leitura e uso da versão ativa (mais recente) em todos os processos subsequentes."

## Clarifications

### Session 2026-06-22

- Q: Quando o usuário tenta salvar edições baseadas numa versão que deixou de ser a ativa (ex.: reprocessamento criou versão nova entretanto), o que o sistema deve fazer? → A: Bloquear o salvamento, avisar do conflito e exigir que o usuário recarregue a versão ativa antes de reaplicar as edições.
- Q: O que acontece com a confiança da extração de um campo quando seu valor é editado manualmente? → A: A confiança do campo passa a ser 100% (o valor inserido pelo humano é tratado como certeza máxima).
- Q: Quais perfis podem editar/remover campos e salvar uma nova versão? → A: Qualquer usuário com acesso à função de validação de documentos (a permissão é vinculada ao acesso de validação, não a um perfil específico).
- Q: Adicionar novos campos (que não vieram da extração automática) está no escopo? → A: Sim — o usuário pode adicionar campos novos (nome + valor) à lista antes de salvar.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Editar e Salvar Campos Extraídos (Priority: P1)

Durante a validação de um documento, o usuário visualiza a lista ativa de campos extraídos automaticamente. Ele corrige o valor de um ou mais campos diretamente na interface. As alterações permanecem em estado não salvo até que o usuário acione "Salvar Alterações" abaixo da lista. O sistema solicita confirmação; ao confirmar, uma nova versão da lista é criada, persistida e tornada a versão ativa. O sistema informa claramente sucesso ou falha do salvamento.

**Why this priority**: É o núcleo da feature e entrega valor imediato — permite corrigir dados extraídos incorretamente, que hoje não podem ser persistidos. Sem isso, nenhuma outra parte da feature tem propósito.

**Independent Test**: Pode ser testado abrindo a lista ativa de um documento, editando o valor de um campo, clicando em "Salvar Alterações", confirmando, e verificando que uma nova versão ativa foi criada com o valor corrigido e que a versão anterior permanece armazenada.

**Acceptance Scenarios**:

1. **Given** a lista ativa de campos extraídos exibida na tela de validação, **When** o usuário altera o valor de um campo, **Then** a alteração é refletida na interface mas marcada/tratada como não salva (não persistida).
2. **Given** existem alterações não salvas na lista, **When** o usuário aciona "Salvar Alterações", **Then** o sistema exibe um diálogo de confirmação solicitando confirmar ou cancelar.
3. **Given** o diálogo de confirmação está aberto, **When** o usuário confirma, **Then** o sistema cria uma nova versão da lista, persiste-a, torna-a a versão ativa e exibe mensagem de sucesso.
4. **Given** o diálogo de confirmação está aberto, **When** o usuário cancela, **Then** nenhuma alteração é persistida e a versão ativa permanece inalterada (as edições continuam visíveis em estado não salvo na interface).
5. **Given** o usuário confirmou o salvamento, **When** ocorre uma falha de persistência, **Then** o sistema exibe mensagem de falha clara e a versão ativa permanece inalterada.
6. **Given** a lista ativa de campos, **When** o usuário adiciona um novo campo (nome + valor) e salva e confirma, **Then** a nova versão ativa contém o campo adicionado com confiança de 100%.

---

### User Story 2 - Remover Campos da Lista (Priority: P1)

Na lista ativa, cada campo possui uma ação de remoção. O usuário remove um ou mais campos; as remoções permanecem em estado não salvo. Ao salvar e confirmar, uma nova versão sem os campos removidos é criada e tornada ativa.

**Why this priority**: Faz parte do mesmo fluxo de edição/salvamento e é igualmente essencial — listas extraídas frequentemente contêm campos espúrios que precisam ser eliminados antes da validação final.

**Independent Test**: Pode ser testado removendo um campo da lista ativa, salvando e confirmando, e verificando que a nova versão ativa não contém o campo removido enquanto a versão anterior (com o campo) permanece no histórico.

**Acceptance Scenarios**:

1. **Given** a lista ativa de campos, **When** o usuário aciona a remoção de um campo, **Then** o campo deixa de aparecer na lista exibida, em estado não salvo.
2. **Given** há um ou mais campos removidos não salvos, **When** o usuário salva e confirma, **Then** uma nova versão ativa é criada sem os campos removidos.
3. **Given** uma nova versão foi criada após remoção, **When** o histórico é consultado, **Then** a versão anterior ainda contém os campos removidos.

---

### User Story 3 - Consultar Histórico de Versões (Priority: P2)

A partir da lista ativa, o usuário aciona "Visualizar Histórico" e o sistema exibe as versões anteriores da lista de campos do documento. Cada versão é claramente identificável e exibe os campos e valores armazenados naquele momento. O histórico é somente leitura.

**Why this priority**: Entrega rastreabilidade e auditoria, mas depende da existência do versionamento (US1/US2). É valioso, porém secundário ao fluxo de correção em si.

**Independent Test**: Pode ser testado em um documento com múltiplas versões, acionando "Visualizar Histórico" e verificando que todas as versões são listadas, identificáveis, com seus campos/valores correspondentes, e sem qualquer ação de edição disponível.

**Acceptance Scenarios**:

1. **Given** um documento com mais de uma versão de campos, **When** o usuário aciona "Visualizar Histórico", **Then** o sistema exibe a lista de versões anteriores, cada uma claramente identificada (identificador, data/hora e tipo de geração).
2. **Given** o histórico está aberto, **When** o usuário seleciona/expande uma versão, **Then** o sistema exibe os campos e respectivos valores armazenados naquela versão.
3. **Given** o histórico está aberto, **When** o usuário interage com qualquer versão, **Then** nenhuma ação de edição ou remoção está disponível (somente leitura).

---

### User Story 4 - Versionamento Automático por Processamento (Priority: P2)

Sempre que o documento passa por primeira extração, novo processamento ou reprocessamento, o sistema cria automaticamente uma nova versão da lista de campos extraídos, registrando seu tipo de geração, e a torna a versão ativa, preservando as versões anteriores.

**Why this priority**: Garante que o versionamento seja consistente independentemente da origem (automática ou manual) e que a versão ativa reflita sempre o estado mais recente. É fundamental para a consistência, mas é uma extensão das regras estabelecidas em US1/US2.

**Independent Test**: Pode ser testado reprocessando um documento que já possui versões e verificando que uma nova versão do tipo "reprocessamento" foi criada e tornada ativa, com as versões anteriores intactas no histórico.

**Acceptance Scenarios**:

1. **Given** um documento sem versões de campos, **When** a primeira extração é concluída, **Then** o sistema registra a versão inicial e a marca como ativa.
2. **Given** um documento com versões existentes, **When** o documento é reprocessado, **Then** uma nova versão do tipo "reprocessamento" é criada, tornada ativa, e nenhuma versão anterior é sobrescrita ou excluída.
3. **Given** qualquer evento gerador de versão (extração inicial, processamento, reprocessamento ou edição manual), **When** a versão é criada, **Then** ela registra seu tipo de geração e a referência à versão anterior quando aplicável.

---

### Edge Cases

- **Salvar sem alterações**: O que acontece quando o usuário aciona "Salvar Alterações" sem ter feito nenhuma modificação? (Assunção: o sistema não cria nova versão; informa que não há alterações a salvar.)
- **Remover todos os campos**: O que acontece quando o usuário remove todos os campos e salva? (Assunção: Não é permitido criar uma versão ativa com lista vazia, aviso em tela deve ser disparado.)
- **Edições concorrentes**: Se um reprocessamento automático criar uma nova versão ativa enquanto o usuário tem edições não salvas baseadas em uma versão que deixou de ser a ativa, ao salvar o sistema bloqueia a operação, avisa do conflito e exige que o usuário recarregue a versão ativa antes de reaplicar as edições (ver FR-024).
- **Falha parcial de persistência**: Se a persistência falhar após a confirmação, a versão ativa anterior deve permanecer intacta e nenhuma versão parcial deve ficar armazenada.
- **Documento sem extração**: Acionar "Visualizar Histórico" em um documento que ainda não possui nenhuma versão deve exibir um estado vazio claro, não um erro.
- **Valor inválido em campo**: O que acontece se o usuário inserir um valor vazio ou claramente inválido em um campo editável? (Assunção: valores livres são aceitos; validação de formato está fora do escopo desta feature.)

## Requirements *(mandatory)*

### Functional Requirements

#### Edição de Campos

- **FR-001**: O sistema MUST exibir, na tela de validação, exclusivamente a versão ativa da lista de campos extraídos do documento.
- **FR-002**: Cada item da lista ativa MUST apresentar nome do campo, valor editável, confiança da extração e uma ação de remoção.
- **FR-003**: O usuário MUST poder editar o valor de qualquer campo da lista ativa.
- **FR-004**: O usuário MUST poder remover qualquer campo da lista ativa.
- **FR-027**: O usuário MUST poder adicionar um novo campo (nome + valor) à lista antes de salvar. Campos adicionados manualmente seguem a mesma regra de confiança da FR-025 (registrados com confiança de 100%) e permanecem em estado não salvo até a confirmação do salvamento.
- **FR-005**: As edições e remoções MUST permanecer apenas na interface, em estado não salvo, e NÃO devem ser persistidas a cada alteração individual.
- **FR-025**: Quando o valor de um campo é editado manualmente, o sistema MUST definir a confiança da extração desse campo como 100% na versão criada ao salvar (o valor inserido pelo humano é tratado como certeza máxima).
- **FR-026**: Apenas usuários com acesso à função de validação de documentos MUST poder editar valores, remover campos e salvar uma nova versão. A permissão é vinculada ao acesso de validação e não a um perfil específico; usuários sem esse acesso não devem poder alterar os campos.

#### Salvar Alterações

- **FR-006**: O sistema MUST disponibilizar uma ação "Salvar Alterações" posicionada abaixo da lista de campos exibida.
- **FR-007**: Ao acionar "Salvar Alterações", o sistema MUST exibir uma confirmação que permita ao usuário confirmar ou cancelar a operação.
- **FR-008**: Ao confirmar o salvamento, o sistema MUST criar uma nova versão da lista de campos, persisti-la e torná-la a versão ativa.
- **FR-009**: Ao cancelar o salvamento, o sistema MUST NOT persistir nenhuma alteração e MUST manter a versão ativa atual inalterada.
- **FR-010**: Após a conclusão da operação de salvamento, o sistema MUST informar claramente ao usuário se o salvamento foi bem-sucedido ou se ocorreu falha.

#### Versionamento

- **FR-011**: O sistema MUST criar uma nova versão da lista de campos extraídos em cada um dos seguintes eventos: primeira extração, novo processamento, reprocessamento e alteração manual confirmada pelo usuário.
- **FR-012**: O sistema MUST registrar a primeira extração de um documento como versão inicial.
- **FR-013**: O sistema MUST NOT sobrescrever nenhuma versão existente; toda alteração gera uma nova versão.
- **FR-014**: O sistema MUST manter no máximo uma versão ativa por documento, sendo a versão ativa sempre a mais recente.
- **FR-015**: Todas as consultas e processos operacionais subsequentes MUST utilizar exclusivamente a versão ativa.
- **FR-016**: O sistema MUST preservar todas as versões anteriores; nenhuma versão anterior pode ser excluída automaticamente durante a criação de novas versões.
- **FR-017**: Cada versão MUST registrar, no mínimo: identificador da versão, data e hora de criação, tipo de geração (extração inicial, usuário que fez a salvou a alteração, processamento, reprocessamento ou edição manual) e referência à versão anterior quando aplicável.

#### Histórico

- **FR-018**: O sistema MUST disponibilizar uma ação "Visualizar Histórico" a partir da lista ativa.
- **FR-019**: Ao acionar "Visualizar Histórico", o sistema MUST exibir as versões anteriores de forma que cada versão seja claramente identificável.
- **FR-020**: O histórico MUST exibir, para cada versão, os campos e respectivos valores armazenados naquele momento.
- **FR-021**: O histórico MUST ser somente leitura — nenhuma ação de edição ou remoção pode estar disponível na visualização de histórico.
- **FR-022**: O histórico MUST permanecer disponível para consulta e auditoria ao longo do ciclo de vida do documento.

#### Consistência e Concorrência

- **FR-023**: Os dados exibidos na interface MUST refletir a versão ativa armazenada.
- **FR-024**: Quando o usuário tenta salvar edições baseadas em uma versão que deixou de ser a versão ativa (por exemplo, devido a um reprocessamento ocorrido entretanto), o sistema MUST bloquear o salvamento, exibir um aviso de conflito e exigir que o usuário recarregue a versão ativa atual antes de reaplicar as edições. Nesse cenário, nenhuma versão nova é criada a partir das edições baseadas na versão obsoleta.

### Key Entities *(include if feature involves data)*

- **Documento**: Entidade à qual as listas de campos extraídos estão associadas. Possui uma versão ativa corrente e um conjunto de versões históricas.
- **Versão de Campos Extraídos**: Snapshot completo da lista de campos de um documento em um dado momento. Atributos: identificador único, data/hora de criação, tipo de geração (extração inicial, processamento, reprocessamento, edição manual), referência à versão anterior (quando aplicável), indicador de versão ativa.
- **Campo Extraído**: Item pertencente a uma versão. Atributos: nome do campo, valor, confiança da extração. Para campos editados manualmente, a confiança é registrada como 100%. Os campos pertencem a uma versão específica e não são compartilhados entre versões (cada versão preserva seu próprio conjunto).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O usuário consegue editar o valor de um campo e persistir a alteração através do fluxo de salvamento com confirmação, com 100% das alterações confirmadas resultando em uma nova versão ativa.
- **SC-002**: O usuário consegue remover campos e, após salvamento confirmado, a nova versão ativa não contém os campos removidos em 100% dos casos.
- **SC-003**: Nenhuma versão é sobrescrita ou perdida — 100% das versões criadas (manuais ou automáticas) permanecem recuperáveis no histórico.
- **SC-004**: Em 100% dos documentos, existe exatamente uma versão ativa e ela corresponde à versão mais recente.
- **SC-005**: Toda consulta operacional subsequente retorna dados da versão ativa, sem divergência entre o que é exibido na interface e a versão ativa armazenada.
- **SC-006**: O usuário consegue identificar e consultar qualquer versão anterior através do histórico, visualizando os campos e valores corretos daquela versão, em uma visualização somente leitura.
- **SC-007**: Quando o usuário cancela o salvamento, em 100% dos casos nenhuma alteração é persistida.
- **SC-008**: Após cada operação de salvamento, o usuário recebe feedback explícito de sucesso ou falha em 100% das tentativas.

## Assumptions

- A tela de validação de documentos já existe e atualmente exibe a lista de campos com comportamento parcialmente mockado; esta feature substitui o mock por persistência real e versionamento.
- A extração automática de campos (incluindo nome, valor e confiança) já é produzida pelo pipeline de processamento existente; esta feature consome esses dados, não os gera.
- Na interface, apenas o valor do campo é editável diretamente; nome e confiança não são digitados manualmente. Ao salvar, a confiança de um campo cujo valor foi editado é automaticamente registrada como 100%.
- Não há validação de formato/tipo dos valores editados nesta feature; valores livres são aceitos.
- O versionamento adota um modelo de snapshot completo por versão (cada versão guarda a lista inteira de campos), garantindo independência total entre versões.
- A retenção de versões segue práticas padrão de auditoria do domínio; não há expurgo automático no escopo desta feature.
- A identidade do usuário responsável pela edição manual é registrada na versão (conforme FR-017), reaproveitando o mecanismo de autenticação já existente no sistema.
- O controle de acesso à função de validação de documentos já existe no sistema; esta feature reaproveita esse controle para autorizar a edição/salvamento de campos (FR-026), sem introduzir um novo perfil.
