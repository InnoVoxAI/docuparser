# Feature Specification: Disponibilizar Transcrição Formatada para Todos os Engines de Processamento

**Feature Branch**: `010-transcricao-formatada-todos-engines`

**Created**: 2026-06-26

**Status**: Draft

**Input**: User description: "Garantir que todo documento processado possua uma Transcrição Formatada disponível na tela de Validação, independentemente do engine de OCR/extração utilizado, desde que o processamento tenha produzido conteúdo textual."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver a transcrição de um PDF escaneado / imagem (Priority: P1)

Um operador de validação abre a aba **Validação** de uma nota fiscal recebida como
PDF escaneado (imagem) ou como imagem direta. O documento foi processado por um
engine de OCR baseado em visão (não-Docling), que extraiu o texto e os campos. O
operador precisa ler o texto que originou os campos extraídos, na seção
**Transcrição Formatada**, em vez de ver apenas a mensagem de restrição por engine.

**Why this priority**: É o caso central do problema relatado. Hoje esses documentos
nunca exibem transcrição, apesar de o conteúdo textual já existir, impedindo a
conferência humana — exatamente a função da etapa de validação.

**Independent Test**: Processar um PDF escaneado/imagem por um engine não-Docling,
abrir a aba Validação e confirmar que a seção Transcrição Formatada exibe o texto
produzido pelo processamento (e não a mensagem de indisponibilidade).

**Acceptance Scenarios**:

1. **Given** um documento processado por engine não-Docling cujo processamento
   produziu conteúdo textual, **When** o operador abre a aba Validação, **Then** a
   seção Transcrição Formatada exibe esse conteúdo textual.
2. **Given** o mesmo documento, **When** o operador compara a lista de campos
   extraídos com a transcrição exibida, **Then** a transcrição corresponde ao texto
   que serviu de base para os campos apresentados.
3. **Given** um documento processado por engine não-Docling, **When** o operador
   abre a Validação, **Then** a mensagem "Disponível apenas para PDFs digitais
   processados pelo engine Docling." não é exibida.

---

### User Story 2 - Continuar vendo a transcrição de PDFs digitais (Docling) (Priority: P2)

Um operador abre a aba Validação de um PDF digital (com camada de texto)
processado pelo engine que preserva layout. A transcrição com layout preservado
continua sendo exibida exatamente como antes, sem regressão.

**Why this priority**: Garante que a generalização não degrade o caso já suportado,
que oferece a melhor representação (layout preservado).

**Independent Test**: Processar um PDF digital, abrir a Validação e confirmar que a
transcrição com layout preservado aparece como hoje.

**Acceptance Scenarios**:

1. **Given** um PDF digital processado com transcrição formatada (layout
   preservado) disponível, **When** o operador abre a Validação, **Then** a
   transcrição com layout preservado é exibida como antes.
2. **Given** documentos já processados anteriormente, **When** visualizados após a
   mudança, **Then** não há regressão na exibição da transcrição.

---

### User Story 3 - Mensagem clara quando não há transcrição (Priority: P3)

Um operador abre a aba Validação de um documento cujo processamento não produziu
nenhum conteúdo textual (ex.: imagem ilegível, OCR sem retorno). A seção deve
informar de forma neutra que a transcrição não está disponível, sem atribuir a
indisponibilidade a um engine específico.

**Why this priority**: Mantém a interface honesta no caso de borda em que não há o
que exibir, removendo a justificativa enganosa baseada em engine.

**Independent Test**: Processar um documento que não gere texto e confirmar que a
seção mostra uma indisponibilidade neutra (sem citar Docling/engine).

**Acceptance Scenarios**:

1. **Given** um documento cujo processamento não produziu conteúdo textual,
   **When** o operador abre a Validação, **Then** a seção informa que a transcrição
   não está disponível, sem referência ao engine utilizado.

---

### Edge Cases

- **Sem nenhum conteúdo textual**: o sistema exibe indisponibilidade neutra
  (US3), sem atribuir a um engine.
- **Documentos legados** processados antes desta mudança: se possuírem conteúdo
  textual armazenado, a transcrição passa a ser exibida; caso só exista texto
  simples (sem versão com layout), exibe-se o texto disponível.
- **Apenas texto simples, sem versão com layout preservado**: exibe-se o texto
  simples (a indisponibilidade ocorre só quando não há texto algum).
- **Documento ainda em processamento / sem resultado**: a seção reflete a
  ausência de conteúdo até que o processamento conclua, sem erro.
- **Conteúdo textual muito extenso**: a seção continua navegável (rolagem) sem
  travar a tela de validação.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST disponibilizar uma Transcrição Formatada na tela de
  Validação sempre que o processamento do documento tiver produzido conteúdo
  textual, independentemente do engine utilizado.
- **FR-002**: A disponibilidade da Transcrição Formatada MUST NOT depender do
  engine responsável pelo processamento do documento.
- **FR-003**: A aba Validação MUST exibir o conteúdo textual produzido pelo
  processamento sempre que esse conteúdo existir.
- **FR-004**: A transcrição exibida MUST corresponder ao conteúdo textual que
  serviu de base para os campos extraídos apresentados ao usuário (mesma versão do
  documento processado).
- **FR-005**: Quando existir uma representação textual com layout preservado, o
  sistema MUST exibi-la preferencialmente; quando não existir, MUST exibir o
  conteúdo textual disponível (texto simples) em vez de declarar indisponibilidade.
- **FR-006**: Quando o processamento não tiver produzido nenhum conteúdo textual, o
  sistema MUST informar de forma neutra que a transcrição não está disponível, sem
  atribuir a indisponibilidade a um engine específico.
- **FR-007**: O sistema MUST deixar de usar a mensagem "Disponível apenas para PDFs
  digitais processados pelo engine Docling." como restrição baseada em engine.
- **FR-008**: O sistema MUST manter, sem regressão, a exibição da transcrição para
  os documentos atualmente suportados (PDFs digitais com layout preservado).
- **FR-009**: Novos engines adicionados futuramente MUST disponibilizar
  automaticamente a Transcrição Formatada na Validação, desde que produzam conteúdo
  textual durante o processamento, sem alteração na tela de Validação.

### Key Entities *(include if feature involves data)*

- **Documento**: item processado pelo sistema (PDF digital, PDF escaneado, imagem
  ou demais formatos suportados). Possui um resultado de processamento associado.
- **Transcrição**: representação textual do documento produzida pelo processamento.
  Pode ter uma forma com layout preservado e/ou uma forma de texto simples; é a
  base textual dos campos extraídos.
- **Resultado de Extração**: conjunto de campos estruturados extraídos do documento,
  apresentados na Validação e que devem ser consistentes com a Transcrição exibida.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos documentos cujo processamento produziu conteúdo textual
  exibem a Transcrição Formatada na aba Validação, qualquer que seja o engine.
- **SC-002**: 0 documentos exibem a mensagem de restrição por engine ("Disponível
  apenas para PDFs digitais processados pelo engine Docling.").
- **SC-003**: Em uma amostra de PDFs escaneados/imagens, 100% passam a apresentar a
  transcrição na Validação quando há conteúdo textual disponível.
- **SC-004**: 0 regressões na exibição da transcrição de documentos previamente
  suportados (PDFs digitais com layout preservado).
- **SC-005**: A inclusão da transcrição não introduz impacto perceptível no tempo
  de carregamento da tela de Validação (sem aumento perceptível pelo usuário em
  relação ao comportamento atual).
- **SC-006**: Para documentos sem qualquer conteúdo textual, 100% das telas exibem
  uma mensagem de indisponibilidade neutra, sem citar engine.

## Assumptions

- O conteúdo textual produzido pelos engines de OCR/extração (texto simples e, quando
  houver, versão com layout preservado) já é capturado durante o processamento; esta
  feature foca em torná-lo disponível/visível de forma uniforme, não em criar nova
  capacidade de OCR.
- "Transcrição Formatada" para engines que não preservam layout significa exibir o
  conteúdo textual disponível; a expectativa de "layout preservado" permanece
  específica de engines que o produzem.
- A representação a ser exibida é a do mesmo processamento que gerou os campos
  extraídos correntes do documento, garantindo consistência (FR-004).
- A tela de Validação já consome o resultado de processamento do documento; nenhuma
  nova origem de dados externa é necessária.
- Documentos legados sem qualquer conteúdo textual armazenado permanecem sem
  transcrição (exibindo indisponibilidade neutra), sem reprocessamento obrigatório
  no escopo desta feature.
