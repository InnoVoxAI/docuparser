# Feature Specification: Workflow Redesign – Validação de Documentos

**Feature Branch**: `001-workflow-redesign`

**Created**: 2026-06-02

**Status**: Draft

---

## Cenários de Uso e Testes *(obrigatório)*

### User Story 1 – Inbox e Navegação para Validação (Prioridade: P1)

O usuário acessa o sistema e visualiza o Inbox, que lista apenas os documentos
com status **pendente**. O componente de Upload aparece posicionado acima do
Inbox. Ao clicar em qualquer documento listado, o usuário é redirecionado
automaticamente para a tela de Validação, que exibe exclusivamente aquele
documento.

**Por que esta prioridade**: É o ponto de entrada principal do fluxo; sem ele
as demais histórias não podem ser executadas.

**Teste Independente**: Acessar a tela principal, verificar que somente
documentos pendentes aparecem, que o Upload está acima do Inbox, e que clicar
em um documento exibe a tela de Validação com aquele documento selecionado.

**Acceptance Scenarios**:

1. **Dado** que existem documentos com status pendente, aprovado e rejeitado,
   **Quando** o usuário acessa o Inbox,
   **Então** somente os documentos com status pendente são exibidos.

2. **Dado** que o usuário está no Inbox,
   **Quando** visualiza a tela,
   **Então** o componente de Upload está posicionado acima da lista do Inbox.

3. **Dado** que o usuário está no Inbox e clica em um documento,
   **Quando** o redirecionamento ocorre,
   **Então** a tela de Validação é exibida com o documento selecionado.

4. **Dado** que o usuário tenta acessar a tela de Validação diretamente
   (por URL ou navegação sem clique no Inbox),
   **Quando** a navegação é tentada,
   **Então** o acesso é bloqueado e o usuário é redirecionado para o Inbox.

---

### User Story 2 – Tela de Validação com Metadados (Prioridade: P2)

O usuário, após clicar em um documento no Inbox, visualiza a tela de Validação
que exibe apenas o documento selecionado junto com seus metadados extraídos.
Campos de metadados sem valor não são exibidos, mantendo a interface limpa.

**Por que esta prioridade**: Depende da navegação (US1) e é o núcleo funcional
da validação; os operadores precisam ver os dados para aprovar ou rejeitar.

**Teste Independente**: Selecionar um documento no Inbox, verificar que a tela
de Validação exibe somente aquele documento, que os metadados preenchidos
aparecem e que campos vazios estão ocultos.

**Acceptance Scenarios**:

1. **Dado** que o usuário navegou para a Validação a partir de um documento,
   **Quando** a tela carrega,
   **Então** somente o documento selecionado é exibido (nenhum outro documento
   aparece na mesma tela).

2. **Dado** que o documento possui metadados extraídos (ex.: CNPJ, data,
   valor total),
   **Quando** a tela de Validação é exibida,
   **Então** todos os metadados com valor são apresentados ao usuário.

3. **Dado** que um campo de metadado não possui valor (null ou vazio),
   **Quando** a tela de Validação é exibida,
   **Então** esse campo não é renderizado na interface.

---

### User Story 3 – Lista de Rejeitados (Prioridade: P3)

O usuário rejeita um documento informando o motivo da rejeição. O documento
é movido para uma nova tela dedicada à lista de rejeitados. Nessa tela, o
usuário consegue ver o motivo de cada rejeição e pode decidir entre
reprocessar o documento ou excluí-lo definitivamente.

**Por que esta prioridade**: Complementa o fluxo de validação; documentos
rejeitados precisam de tratamento explícito para não ficarem perdidos no
sistema.

**Teste Independente**: Rejeitar um documento na Validação, acessar a tela de
Rejeitados, verificar que o documento aparece com o motivo da rejeição, e
confirmar que as ações de reprocessar e excluir funcionam.

**Acceptance Scenarios**:

1. **Dado** que o usuário rejeita um documento na tela de Validação,
   **Quando** a rejeição é confirmada,
   **Então** o documento é removido do Inbox e adicionado à lista de
   Rejeitados com o motivo informado.

2. **Dado** que existem documentos rejeitados,
   **Quando** o usuário acessa a tela de Rejeitados,
   **Então** cada documento listado exibe o motivo de sua rejeição.

3. **Dado** que o usuário seleciona "Reprocessar" em um documento rejeitado,
   **Quando** a ação é confirmada,
   **Então** o documento retorna ao Inbox com status pendente.

4. **Dado** que o usuário seleciona "Excluir" em um documento rejeitado,
   **Quando** a exclusão é confirmada,
   **Então** o documento é removido permanentemente do sistema.

---

### Edge Cases

- O que acontece se o usuário tentar navegar para a Validação sem ter
  selecionado nenhum documento (ex.: acesso direto por URL)?
- O que acontece se um documento pendente for rejeitado por outro usuário
  enquanto o primeiro ainda está visualizando no Inbox?
- O que acontece se a rejeição ocorrer sem motivo preenchido?

## Requisitos Funcionais *(obrigatório)*

- **RF-01**: O sistema DEVE exibir no Inbox somente documentos com status
  pendente.
- **RF-02**: O sistema DEVE redirecionar o usuário para a tela de Validação
  ao clicar em um documento no Inbox.
- **RF-03**: A tela de Validação DEVE exibir somente o documento selecionado
  a partir do Inbox.
- **RF-04**: A tela de Validação DEVE apresentar os metadados extraídos do
  documento selecionado.
- **RF-05**: Campos de metadados sem valor (null ou vazio) NÃO DEVEM ser
  exibidos na tela de Validação.
- **RF-06**: Documentos rejeitados DEVEM ser movidos para a lista de
  Rejeitados após a rejeição.
- **RF-07**: A lista de Rejeitados DEVE exibir o motivo da rejeição para cada
  documento.
- **RF-08**: O usuário DEVE poder reprocessar ou excluir qualquer documento
  na lista de Rejeitados.
- **RF-09**: A lista de Rejeitados DEVE ser exibida em uma tela separada e
  dedicada.
- **RF-10**: A tela de Validação DEVE ser acessível exclusivamente via seleção
  de documento no Inbox; acesso direto (ex.: URL) DEVE ser bloqueado e
  redirecionar para o Inbox.
- **RF-11**: O componente de Upload DEVE ser posicionado acima da lista do
  Inbox na tela principal.

### Entidades Principais

- **Documento**: Representa um arquivo submetido ao sistema. Atributos-chave:
  identificador, status (pendente / aprovado / rejeitado), metadados extraídos,
  motivo de rejeição (quando aplicável).
- **Metadado**: Par chave-valor extraído do documento e do canal que foi enviado (ex.: Data, Metadados do Email). Pode estar presente ou ausente.

## Critérios de Sucesso *(obrigatório)*

### Resultados Mensuráveis

- **SC-001**: O usuário consegue navegar do Inbox à Validação e concluir a
  revisão de um documento em no máximo 5 cliques sem considerar ajustes referentes a campos e visualizacão de outros dados.
- **SC-002**: 100% dos documentos com status não-pendente são excluídos da
  visualização do Inbox após a mudança de status.
- **SC-003**: Tentativas de acesso direto à tela de Validação (sem seleção
  prévia no Inbox) são bloqueadas em 100% dos casos.
- **SC-004**: Documentos rejeitados aparecem na lista de Rejeitados em menos
  de 2 segundos após a confirmação da rejeição.
- **SC-005**: O usuário consegue reprocessar ou excluir um documento rejeitado
  com no máximo 2 ações (seleção + confirmação).

## Premissas

- Os status possíveis de um documento são: pendente, aprovado e rejeitado.
- O motivo de rejeição é um campo de texto livre preenchido pelo usuário no
  momento da rejeição; o campo é obrigatório para confirmar a rejeição.
- Reprocessar um documento rejeitado significa devolvê-lo ao Inbox com status
  pendente; nenhum reprocessamento de OCR/IA é disparado automaticamente.
- Não há suporte a operações em lote (rejeição/reprocessamento de múltiplos
  documentos simultaneamente) nesta versão.
