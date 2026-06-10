# Feature Specification: Workflow Redesign – Ajustes Pós Implementação (v2)

**Feature Branch**: `001-workflow-redesign`

**Created**: 2026-06-03

**Status**: Draft

**Input**: Ajustes de experiência do operador identificados após a implementação da feature Workflow Redesign.

## Contexto

Após a entrega da fase 1 do redesign do fluxo de validação, cinco melhorias foram identificadas pelo time operacional. O objetivo é simplificar a interface, exibir informações mais relevantes ao operador e reduzir o esforço cognitivo durante o processo de validação de documentos.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 – Metadados do Documento na Tela de Validação (Priority: P1)

Durante a validação, o operador precisa entender o contexto do documento sem buscar informações em outros sistemas. Atualmente, a tela exibe dados técnicos de OCR que não auxiliam a decisão de aprovar ou rejeitar. Substituindo esses dados por metadados do documento (remetente, assunto, data), o operador toma decisões mais rápidas e com mais contexto.

**Why this priority**: É a mudança de maior impacto para a eficiência operacional. Reduz o tempo de validação ao eliminar o acesso manual a sistemas externos para identificar a origem e o contexto do documento.

**Independent Test**: Abrir a tela de Validação com um documento selecionado e verificar que a seção "Metadados do Documento" é exibida no lugar das informações técnicas de OCR, mostrando apenas campos com valor preenchido.

**Acceptance Scenarios**:

1. **Given** um documento com metadados de canal (ex: remetente, assunto, data de envio), **When** o operador abre a tela de Validação com esse documento selecionado, **Then** a seção "Metadados do Documento" exibe apenas os campos com valor disponível (nome do documento, remetente, assunto, data de envio, etc.)
2. **Given** um documento sem metadados de canal, **When** o operador abre a tela de Validação, **Then** a seção "Metadados do Documento" não exibe nenhum campo (seção pode exibir estado vazio)
3. **Given** a tela de Validação, **When** o operador observa o painel lateral, **Then** nenhuma informação técnica de OCR (nome do motor, hint, schema ID, confidence, layout) é visível nessa seção

---

### User Story 2 – Campos Extraídos Sem Valor São Omitidos (Priority: P2)

Ao executar a extração de campos de um documento, a listagem exibe itens com "Valor não Encontrado" e confiança 0%. Esses itens poluem a lista e obrigam o operador a ignorá-los manualmente. Omiti-los automaticamente foca a atenção nos campos efetivamente extraídos.

**Why this priority**: Impacta diretamente a qualidade da informação apresentada durante a extração, que é uma etapa crítica do fluxo de validação. Complementa o CR-01 ao garantir que apenas dados relevantes sejam exibidos.

**Independent Test**: Executar a extração de campos em um documento onde nem todos os campos do modelo são encontrados e verificar que apenas os campos com valor aparecem na listagem.

**Acceptance Scenarios**:

1. **Given** uma extração concluída com campos parcialmente preenchidos, **When** o operador visualiza a lista de campos extraídos, **Then** apenas campos com valor não vazio são exibidos; campos sem valor não aparecem na lista
2. **Given** uma extração onde todos os campos foram encontrados, **When** o operador visualiza a lista, **Then** todos os campos são exibidos normalmente
3. **Given** uma extração onde nenhum campo foi encontrado, **When** o operador visualiza a lista, **Then** a lista exibe estado vazio (sem linhas com "Valor não Encontrado")

---

### User Story 3 – Nome Real do Documento no Visualizador (Priority: P2)

O visualizador de documentos exibe o título genérico "Documento". O operador precisa identificar visualmente qual arquivo está sendo visualizado, especialmente quando valida múltiplos documentos em sequência.

**Why this priority**: Melhoria simples de alta utilidade. Elimina ambiguidade e reduz erros de validação ao confirmar visualmente que o documento correto está sendo analisado.

**Independent Test**: Abrir a tela de Validação com um documento selecionado e verificar que o título do visualizador exibe o nome real do arquivo (ex: "NF_Maria.pdf") em vez de "Documento".

**Acceptance Scenarios**:

1. **Given** um documento com nome de arquivo definido, **When** o operador visualiza a tela de Validação, **Then** o cabeçalho do visualizador exibe o nome real do arquivo (ex: "N.F VANDA MOTA.pdf")
2. **Given** um documento sem nome de arquivo, **When** o operador visualiza a tela de Validação, **Then** o cabeçalho exibe o identificador único do documento como fallback

---

### User Story 4 – Transcrições Colapsáveis (Priority: P3)

A tela de Validação exibe as seções "Transcrição Completa" e "Transcrição Formatada" sempre expandidas e ocupando grande espaço vertical. Operadores que não precisam revisar a transcrição textual são obrigados a rolar a página para acessar os controles de validação.

**Why this priority**: Melhora o fluxo de trabalho sem alterar funcionalidades existentes. Operadores que usam a transcrição mantêm acesso; os que não usam ganham mais espaço útil na tela.

**Independent Test**: Abrir a tela de Validação com um documento selecionado, clicar em "Recolher" em uma seção de transcrição e verificar que apenas essa seção é recolhida, enquanto a outra permanece no estado anterior.

**Acceptance Scenarios**:

1. **Given** a tela de Validação com transcrições carregadas, **When** o operador clica em "Recolher" na seção "Transcrição Completa", **Then** apenas essa seção é recolhida; "Transcrição Formatada" permanece inalterada
2. **Given** uma seção de transcrição recolhida, **When** o operador clica em "Expandir", **Then** o conteúdo é exibido novamente sem recarregar a página
3. **Given** o estado de cada seção alternado individualmente, **When** o operador navega entre documentos, **Then** cada seção mantém seu estado independente (o estado não é compartilhado entre seções)

---

### User Story 5 – Reorganização do Menu Principal (Priority: P3)

A ordem atual do menu coloca Dashboard como primeiro item e Upload como terceiro. O fluxo operacional começa com o envio de documentos (Upload), seguido pela revisão no Inbox. Ajustar a ordem reflete o fluxo real de trabalho.

**Why this priority**: Mudança de baixo custo e alto retorno em usabilidade. Alinha a navegação ao fluxo operacional real: envio → inbox → validação.

**Independent Test**: Abrir o sistema e verificar que o menu exibe os itens na nova ordem: Upload, Inbox, Dashboard, Rejeitados, Validação, Operações, Configurações.

**Acceptance Scenarios**:

1. **Given** o sistema carregado, **When** o operador observa o menu de navegação, **Then** a ordem dos itens é: Upload, Inbox, Dashboard, Rejeitados, Validação, Operações, Configurações
2. **Given** o menu reorganizado, **When** o operador clica em qualquer item de navegação, **Then** a tela correspondente é carregada normalmente

---

### Edge Cases

- O que acontece quando um documento tem metadados parciais (ex: remetente presente, assunto ausente)? → Apenas os campos com valor são exibidos; campos ausentes são omitidos silenciosamente.
- O que acontece quando a extração retorna uma lista vazia de campos (todos sem valor)? → A seção de campos extraídos exibe estado vazio sem nenhuma linha.
- O que acontece quando o operador recolhe uma transcrição e então navega para outro documento? → O estado de colapso é independente por seção, não por documento; o estado persiste na sessão.
- O que acontece quando o nome do arquivo contém caracteres especiais ou é muito longo? → O título do visualizador exibe o nome completo, com truncamento visual se necessário, preservando legibilidade.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A tela de Validação DEVE exibir uma seção "Metadados do Documento" em substituição ao painel técnico de OCR, contendo os metadados de canal disponíveis do documento
- **FR-002**: A seção "Metadados do Documento" DEVE exibir apenas campos com valor disponível; campos vazios, nulos ou ausentes DEVEM ser omitidos
- **FR-003**: Os campos de metadados a exibir, quando disponíveis, são: nome do documento, código do processo, remetente, destinatário, assunto, data de envio, message-ID, provedor, lista de anexos e corpo do email
- **FR-004**: O visualizador de documentos DEVE exibir o nome real do arquivo como título da seção, no lugar do título genérico "Documento"
- **FR-005**: Quando o nome do arquivo não estiver disponível, o visualizador DEVE exibir o identificador único do documento como fallback
- **FR-006**: A lista de campos extraídos pelo modelo de extração DEVE omitir automaticamente campos cujo valor não foi encontrado (valor vazio, nulo ou ausente após extração)
- **FR-007**: Cada seção de transcrição ("Transcrição Completa" e "Transcrição Formatada") DEVE possuir controle independente de expansão e colapso
- **FR-008**: O estado de expansão/colapso de cada seção de transcrição DEVE ser independente (alternar uma não afeta a outra)
- **FR-009**: O conteúdo das seções de transcrição DEVE permanecer carregado em memória ao ser recolhido, sem necessidade de recarregamento ao expandir
- **FR-010**: A ordem dos itens do menu principal DEVE ser: Upload, Inbox, Dashboard, Rejeitados, Validação, Operações, Configurações

### Key Entities

- **Documento**: Entidade central do fluxo, identificado por nome de arquivo e metadados de canal (origin, sender, subject, date, attachments, body)
- **Metadados de Canal**: Informações de contexto do documento derivadas do canal de recebimento (ex: metadados de email como remetente, assunto, data)
- **Campo Extraído**: Par nome/valor resultado da extração automática de um documento; pode ter valor presente ou ausente

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O operador consegue identificar o remetente, assunto e data de envio de um documento diretamente na tela de Validação, sem sair da tela ou consultar outro sistema
- **SC-002**: Após a extração de campos, apenas campos com valor aparecem na listagem — zero linhas com "Valor não Encontrado" são exibidas
- **SC-003**: O título do visualizador de documentos exibe o nome real do arquivo em 100% dos casos em que o nome está disponível
- **SC-004**: O operador consegue recolher e expandir cada seção de transcrição individualmente sem recarregar a página
- **SC-005**: A ordem do menu reflete o fluxo operacional real (Upload → Inbox → Validação), verificável na primeira tela após o login

---

## Assumptions

- Os metadados de canal (remetente, assunto, data, etc.) já estão disponíveis na estrutura de dados do documento atual — nenhuma nova API ou campo de banco de dados é necessário
- Os campos de metadados de canal podem variar por documento dependendo do canal de recebimento (email, upload manual); a exibição deve ser dinâmica e baseada no que está disponível
- O código do processo é um campo presente nos metadados de canal quando o documento é recebido via email
- O estado de colapso das transcrições não precisa ser persistido entre sessões; reiniciar o estado a cada acesso à tela de Validação é aceitável
- As informações técnicas de OCR (motor, schema, confidence, layout) removidas da interface principal ainda estão acessíveis via outras telas de operações se necessário para diagnóstico técnico
- Nenhuma mudança de backend é necessária para esta versão; todas as alterações são no frontend
