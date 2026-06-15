# Feature Specification: Ajustes de Interface e Gerenciamento de Modelos de Extração

**Feature Branch**: `006-ui-model-management`

**Created**: 2026-06-15

**Status**: Draft

**Input**: Simplificação da interface nos fluxos de validação e configuração de modelos de extração, incluindo remoção de seções desnecessárias, ajustes de nomenclatura, e nova funcionalidade de exclusão de modelos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tela de Validação Simplificada (Priority: P1)

Como operador revisando um documento, quero visualizar apenas as informações essenciais sobre o modelo de extração ativo, sem dados técnicos desnecessários (como revisão de OCR e detalhes do schema), para que eu possa focar na validação do conteúdo extraído.

**Why this priority**: Redução de ruído visual na tela mais utilizada do sistema — diretamente impacta a produtividade diária do operador.

**Independent Test**: Pode ser testado abrindo qualquer documento na tela de Validação → Extração → Documento e verificando que a seção "Revisão da qualidade do OCR" não aparece, e que "Modelo Ativo" exibe apenas o campo Tipo.

**Acceptance Scenarios**:

1. **Given** um documento em validação, **When** o usuário acessa a aba Documento na tela de Extração, **Then** a subsection "Revisão da qualidade do OCR" não é exibida.
2. **Given** um documento com modelo de extração ativo, **When** o usuário visualiza a subsection "Modelo Ativo", **Then** apenas o campo "Tipo" é exibido — Layout, Status e Schema não aparecem.
3. **Given** qualquer estado do sistema, **When** o processo de extração é executado internamente, **Then** os dados de OCR continuam sendo utilizados pelo sistema sem interrupção.

---

### User Story 2 - Tela de Configurações de Modelo Simplificada (Priority: P2)

Como administrador configurando um modelo de extração, quero ver apenas as informações relevantes do modelo (sem campos técnicos internos como Tenant, Versão e Status), com nomenclatura clara e consistente, para que eu possa configurar modelos de forma mais rápida e intuitiva.

**Why this priority**: Impacta a experiência de configuração de modelos — menos crítico que a tela de validação (que é usada diariamente), mas importante para reduzir confusão nos fluxos de administração.

**Independent Test**: Pode ser testado acessando Configurações → Extração → Modelo e verificando que os campos Tenant, Versão e Status não aparecem, que os rótulos estão corretos ("Schema (Campos)", "Modelos existentes", "Exemplos (Few-shots anotados)"), que a versão não aparece na listagem de modelos, e que a seção "Layouts existentes" e a subsection "Checklist LangExtract" não são exibidas.

**Acceptance Scenarios**:

1. **Given** a tela de configuração de modelo aberta, **When** o usuário visualiza as informações do modelo, **Then** os campos Tenant, Versão e Status não são exibidos em nenhuma parte da interface.
2. **Given** a tela de configuração, **When** o usuário acessa a seção de campos, **Then** o rótulo "Schema" está renomeado para "Schema (Campos)".
3. **Given** a listagem de modelos existentes, **When** exibida ao usuário, **Then** o rótulo da seção é "Modelos existentes" (não "Schemas existentes") e apenas o nome do modelo aparece — sem a versão abaixo.
4. **Given** a tela de configuração, **When** o usuário navega pelos elementos, **Then** a subsection "Checklist LangExtract" não é visível e a seção "Layouts existentes" não é exibida.
5. **Given** a aba de exemplos, **When** o usuário a visualiza, **Then** o título exibe "Exemplos (Few-shots anotados)" em vez de "Few-shot anotados".

---

### User Story 3 - Exclusão de Modelos de Extração (Priority: P3)

Como administrador, quero poder excluir modelos de extração que não são mais necessários, com confirmação antes da ação e proteção dos modelos padrão do sistema, para manter a listagem organizada.

**Why this priority**: Nova funcionalidade; os casos de uso de exclusão são menos frequentes que as telas de validação e configuração. A proteção dos modelos padrão garante que o sistema não fique sem modelos operacionais.

**Independent Test**: Pode ser testado criando um modelo de teste, clicando em Excluir, confirmando, e verificando que o modelo desaparece da listagem e das seleções do sistema. Paralelamente, tentar excluir um modelo padrão e verificar que a ação é bloqueada com mensagem explicativa.

**Acceptance Scenarios**:

1. **Given** a listagem "Modelos existentes", **When** o usuário a visualiza, **Then** cada modelo exibe um botão "Excluir" ao lado do seu nome.
2. **Given** o usuário clica em "Excluir" em um modelo elegível, **When** o diálogo de confirmação aparece, **Then** o usuário pode confirmar ou cancelar a ação.
3. **Given** o usuário confirmou a exclusão, **When** a ação é processada, **Then** o modelo é removido e a listagem é atualizada automaticamente sem recarregamento manual.
4. **Given** o modelo foi excluído, **When** o usuário acessa qualquer seleção de modelo no sistema, **Then** o modelo excluído não aparece mais nas opções disponíveis.
5. **Given** o usuário clica em "Excluir" em `nota_fiscal_default` ou `conta_agua_default`, **When** a ação é solicitada, **Then** o sistema exibe uma mensagem informando que modelos padrão não podem ser excluídos e a ação é bloqueada.

---

### Edge Cases

- O que acontece se o usuário tentar excluir um modelo que está sendo utilizado em um documento em processamento? → A exclusão é bem-sucedida; documentos já em processamento continuam com a definição do modelo no momento da extração.
- O que acontece se a listagem de modelos estiver vazia após exclusões? → A listagem exibe estado vazio com mensagem informativa.
- O que acontece se a conexão for perdida durante a exclusão? → O sistema exibe mensagem de erro e o estado da listagem permanece consistente com o banco de dados.
- O que acontece se novos modelos padrão forem adicionados no futuro? → A lista de IDs protegidos (`nota_fiscal_default`, `conta_agua_default`) deve ser expansível via configuração, não hardcoded na interface.

## Requirements *(mandatory)*

### Functional Requirements

**Tela de Validação — Simplificação Visual**

- **FR-001**: O sistema NÃO DEVE exibir a subsection "Revisão da qualidade do OCR" na tela Validação → Extração → Documento.
- **FR-002**: A subsection "Modelo Ativo" DEVE exibir apenas o campo "Tipo"; os campos Layout, Status e Schema NÃO DEVEM ser exibidos.
- **FR-003**: Os dados de qualidade de OCR e do schema DEVEM continuar sendo armazenados e utilizados internamente pelo sistema.

**Tela de Configurações → Extração → Modelo — Simplificação Visual**

- **FR-004**: Os campos Tenant, Versão e Status NÃO DEVEM ser exibidos na tela de configuração do modelo.
- **FR-005**: O rótulo "Schema" DEVE ser renomeado para "Schema (Campos)" na interface.
- **FR-006**: A subsection "Checklist LangExtract" NÃO DEVE ser exibida; nenhuma lógica interna associada deve ser removida.
- **FR-007**: O rótulo da seção de listagem "Schemas existentes" DEVE ser renomeado para "Modelos existentes".
- **FR-008**: Na listagem "Modelos existentes", apenas o nome do modelo DEVE ser exibido; a versão NÃO DEVE ser exibida.
- **FR-009**: A seção "Layouts existentes" NÃO DEVE ser exibida; as funcionalidades de layout subjacentes DEVEM permanecer no sistema.
- **FR-010**: O rótulo "Few-shot anotados" DEVE ser renomeado para "Exemplos (Few-shots anotados)".

**Exclusão de Modelos de Extração**

- **FR-011**: O sistema DEVE exibir um botão "Excluir" ao lado de cada modelo na listagem "Modelos existentes".
- **FR-012**: Ao clicar em "Excluir", o sistema DEVE exibir um diálogo de confirmação antes de prosseguir.
- **FR-013**: Após confirmação, o sistema DEVE remover o modelo e atualizar a listagem automaticamente.
- **FR-014**: O modelo excluído NÃO DEVE mais aparecer em nenhuma lista de seleção do sistema.
- **FR-015**: Os modelos padrão (`nota_fiscal_default`, `conta_agua_default`) NÃO DEVEM poder ser excluídos; o sistema DEVE exibir mensagem explicativa ao tentá-lo.
- **FR-016**: A exclusão de um modelo NÃO DEVE impactar documentos já processados ou em processamento.

### Key Entities

- **Modelo de Extração (SchemaConfig)**: Entidade que define as regras e campos para extração de dados de um tipo de documento. Possui identificador único, tipo/nome e definição completa. Modelos padrão do sistema são protegidos contra exclusão.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Todas as 14 alterações visuais e comportamentais descritas nos critérios de aceitação são verificáveis em uma única sessão de teste sem falhas.
- **SC-002**: O tempo para um operador localizar o tipo do modelo ativo na tela de validação é reduzido — a informação é imediata, sem rolagem ou busca entre múltiplos campos.
- **SC-003**: Ao clicar em "Excluir" e confirmar, o modelo desaparece da listagem em menos de 3 segundos e não reaparece em nenhuma seleção do sistema.
- **SC-004**: Tentativas de excluir modelos padrão são 100% bloqueadas com mensagem explicativa, sem exceções.
- **SC-005**: Nenhum dado de extração existente é perdido ou corrompido após a implementação — documentos previamente processados continuam com seus campos extraídos intactos.

## Assumptions

- As remoções visuais são implementadas no frontend; os dados correspondentes continuam sendo armazenados e processados no backend.
- Apenas os modelos `nota_fiscal_default` e `conta_agua_default` são considerados padrão do sistema para proteção contra exclusão (Opção A conforme especificado).
- Usuários com permissão `roles.manage` têm acesso à tela de Configurações → Extração → Modelo e, portanto, à funcionalidade de exclusão.
- A exclusão é permanente (sem lixeira ou soft delete); a recuperação é possível via recriação manual ou reinicialização do sistema para modelos padrão.
- A tela de Validação é acessível a usuários com permissão `documents.validate`.
