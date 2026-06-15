# Feature Specification: Front-end e Ajustes de Plataforma

**Feature Branch**: `005-frontend-platform-adjustments`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "Front-end e Ajustes de Plataforma — remoção de funcionalidades visuais, ajustes de nomenclatura e ordenação de abas, persistência de sessão de 12h, criação automática de modelos padrão de extração na inicialização, e remoção visual da seção Transcrição Completa na tela de validação."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Sessão Persistente (Priority: P1)

Um usuário autenticado continua trabalhando na plataforma por horas seguidas sem ser deslogado inesperadamente, evitando perda de contexto e retrabalho.

**Why this priority**: A expiração em 10 minutos interrompe o fluxo de trabalho e é a principal queixa de usabilidade relatada. Resolve o maior ponto de atrito de imediato.

**Independent Test**: Pode ser testado de forma autônoma fazendo login e aguardando 15–20 minutos sem interação, verificando que a sessão permanece ativa; entrega valor imediato sem dependência de outras histórias.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado, **When** ele permanece na plataforma por até 12 horas, **Then** a sessão continua ativa sem ser encerrada automaticamente.
2. **Given** um usuário autenticado que ficou inativo por 10 minutos, **When** ele realiza qualquer ação na plataforma, **Then** a ação é executada normalmente sem redirecionamento para login.
3. **Given** um usuário autenticado há mais de 12 horas, **When** o token expira, **Then** o usuário é redirecionado para a tela de login de forma adequada.

---

### User Story 2 — Modelos Padrão Disponíveis ao Iniciar (Priority: P2)

Um usuário acessa a plataforma recém-instalada e já encontra os modelos de extração `nota_fiscal_default` e `conta_agua_default` disponíveis para uso, sem precisar criá-los manualmente.

**Why this priority**: Elimina barreira de onboarding que exige que o usuário execute uma sequência manual de etapas antes de poder usar a funcionalidade principal de extração.

**Independent Test**: Pode ser testado instalando a aplicação do zero (ou limpando o banco) e verificando que os modelos padrão aparecem listados sem nenhuma configuração manual.

**Acceptance Scenarios**:

1. **Given** uma instalação sem modelos cadastrados, **When** a aplicação é inicializada, **Then** os modelos `nota_fiscal_default` e `conta_agua_default` são criados automaticamente no banco de dados.
2. **Given** os modelos padrão já existem no banco, **When** a aplicação é reinicializada, **Then** nenhum registro duplicado é criado.
3. **Given** os modelos foram criados na inicialização, **When** o usuário acessa a tela de extração, **Then** os modelos estão imediatamente disponíveis para seleção.

---

### User Story 3 — Abas de Configuração Reorganizadas (Priority: P3)

Um usuário navega para Configurações → Extração e encontra a aba "Documento" como primeira opção (antes denominada "OCR Referência"), seguida da aba "Modelo", refletindo o fluxo natural de uso.

**Why this priority**: Melhoria de usabilidade e nomenclatura; impacto direto na clareza da interface, mas não bloqueia nenhuma funcionalidade existente.

**Independent Test**: Pode ser testado abrindo a tela de Configurações → Extração e verificando a ordem e os nomes das abas, sem dependência de outras histórias.

**Acceptance Scenarios**:

1. **Given** o usuário está em Configurações → Extração, **When** a tela é carregada, **Then** a primeira aba exibida se chama "Documento".
2. **Given** o usuário está em Configurações → Extração, **When** a tela é carregada, **Then** a aba "Modelo" aparece após a aba "Documento".
3. **Given** o usuário clica na aba "Documento", **When** o conteúdo é exibido, **Then** o conteúdo anteriormente exibido em "OCR Referência" é apresentado normalmente.

---

### User Story 4 — Interface de Publicação Simplificada (Priority: P4)

Um usuário em Configurações → Extração → Publicação não vê mais o trecho "Vincular layout ao schema", reduzindo a poluição visual e possíveis confusões na interface.

**Why this priority**: Remoção de elemento não utilizado ou prematuro; baixo risco e melhora a clareza, mas não bloqueia outras funcionalidades.

**Independent Test**: Pode ser testado navegando para Configurações → Extração → Publicação e verificando que o trecho "Vincular layout ao schema" não aparece em nenhuma parte da tela.

**Acceptance Scenarios**:

1. **Given** o usuário está em Configurações → Extração → Publicação, **When** a tela é carregada, **Then** o trecho "Vincular layout ao schema" não é exibido.
2. **Given** a remoção do trecho, **When** o usuário interage com as demais funcionalidades de publicação, **Then** todas funcionam normalmente sem erros.

---

### User Story 5 — Tela de Validação Mais Limpa (Priority: P5)

Um usuário na tela de validação encontra apenas a seção "Transcrição Formatada", sem a seção "Transcrição Completa", tornando a visualização mais objetiva sem perder dados processados.

**Why this priority**: Melhoria visual; a seção "Transcrição Formatada" permanece intacta e os dados da "Transcrição Completa" continuam armazenados internamente.

**Independent Test**: Pode ser testado abrindo a tela de validação de qualquer documento e verificando que a seção "Transcrição Completa" não aparece, enquanto a "Transcrição Formatada" permanece visível.

**Acceptance Scenarios**:

1. **Given** o usuário está na tela de validação de um documento, **When** a tela é carregada, **Then** a seção "Transcrição Completa" não é exibida.
2. **Given** a remoção visual da seção "Transcrição Completa", **When** o sistema processa documentos, **Then** os dados de transcrição completa continuam sendo armazenados internamente e acessíveis via API/serviços.
3. **Given** o usuário está na tela de validação, **When** a tela é carregada, **Then** a seção "Transcrição Formatada" permanece exatamente como estava antes da mudança.

---

### Edge Cases

- O que acontece se a criação dos modelos padrão falhar durante a inicialização (ex.: banco indisponível)? O sistema deve logar o erro e continuar inicializando sem travar.
- O que acontece se os modelos padrão forem manualmente deletados do banco e a aplicação for reiniciada? Os modelos devem ser recriados automaticamente.
- O que acontece se um modelo com o mesmo nome mas configuração diferente já existir? O processo idempotente deve preservar o modelo existente sem sobrescrevê-lo.
- O que acontece se o token de sessão for inválido (ex.: alteração de segredo)? O usuário deve ser redirecionado para login normalmente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE manter a sessão do usuário autenticada por pelo menos 12 horas após o login.
- **FR-002**: O sistema DEVE verificar a existência dos modelos `nota_fiscal_default` e `conta_agua_default` durante a inicialização da aplicação.
- **FR-003**: O sistema DEVE criar automaticamente os modelos padrão ausentes durante a inicialização, sem intervenção do usuário.
- **FR-004**: O processo de criação dos modelos padrão DEVE ser idempotente: reinicializações subsequentes NÃO devem criar registros duplicados.
- **FR-005**: A interface DEVE exibir a aba "Documento" (antes "OCR Referência") como primeira aba em Configurações → Extração.
- **FR-006**: A interface DEVE exibir a aba "Modelo" após a aba "Documento" em Configurações → Extração.
- **FR-007**: A interface NÃO DEVE exibir o trecho "Vincular layout ao schema" em Configurações → Extração → Publicação.
- **FR-008**: A interface NÃO DEVE exibir a seção "Transcrição Completa" na tela de validação.
- **FR-009**: Os dados de "Transcrição Completa" DEVEM continuar sendo armazenados internamente e disponíveis via API/serviços após a remoção visual.
- **FR-010**: A seção "Transcrição Formatada" na tela de validação DEVE permanecer inalterada em comportamento e exibição.
- **FR-011**: As demais funcionalidades de publicação DEVEM continuar operando normalmente após a remoção do trecho "Vincular layout ao schema".

### Key Entities

- **Modelo de Extração (ExtractionModel)**: Configuração reutilizável que define como documentos de um tipo específico devem ser processados; possui nome único, tipo de documento e parâmetros de extração.
- **Sessão de Usuário**: Credencial autenticada com tempo de vida configurável; controla o acesso à plataforma.
- **Transcrição Completa**: Dado interno gerado pelo processamento OCR; permanece no banco de dados mesmo sem exibição na interface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuários permanecem autenticados por até 12 horas sem ser deslogados automaticamente, medido por tempo de sessão ativa sem reautenticação.
- **SC-002**: Os modelos `nota_fiscal_default` e `conta_agua_default` estão disponíveis para seleção em menos de 60 segundos após a inicialização da aplicação em ambiente limpo.
- **SC-003**: Nenhum registro duplicado de modelos padrão é criado após 10 reinicializações consecutivas da aplicação.
- **SC-004**: A tela de Configurações → Extração exibe "Documento" como primeira aba em 100% das sessões após a mudança.
- **SC-005**: A seção "Transcrição Completa" está ausente da tela de validação em 100% dos documentos validados após a mudança.
- **SC-006**: A seção "Transcrição Formatada" permanece funcional e visível em 100% dos documentos validados após a mudança.
- **SC-007**: O trecho "Vincular layout ao schema" não é renderizado na interface em nenhuma condição após a remoção.

## Assumptions

- O mecanismo de autenticação atual utiliza tokens com expiração configurável (JWT ou similar); a mudança para 12 horas será feita via ajuste de configuração, não reescrita do sistema de auth.
- Os modelos padrão terão configurações mínimas suficientes para serem funcionais; configurações avançadas poderão ser ajustadas pelo usuário posteriormente.
- A remoção do trecho "Vincular layout ao schema" é estritamente visual — a funcionalidade subjacente (se existir) não é afetada.
- A remoção da seção "Transcrição Completa" da interface não remove os dados do banco nem da lógica de processamento; apenas oculta a exibição.
- O conteúdo da aba "OCR Referência" permanece idêntico após a renomeação para "Documento".
- A ordenação das abas implica apenas reordenação visual, sem mudanças na lógica ou dados associados a cada aba.
