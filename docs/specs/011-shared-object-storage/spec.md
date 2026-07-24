# Feature Specification: Armazenamento de objetos compartilhado entre backends

**Feature Branch**: `011-shared-object-storage`

**Created**: 2026-07-06

**Status**: Draft

**Input**: User description: "Recurso: armazenamento de objetos compartilhado entre os backends. Substituir o armazenamento local não compartilhado por um storage de objetos compartilhado (compatível com S3/MinIO), de forma que qualquer artefato gravado por um serviço seja legível por todos os outros, sem regressão do comportamento atual."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Artefato gravado por um serviço é legível por outro (Priority: P1)

Um artefato (o arquivo original enviado, ou o `raw_text.json` produzido pelo OCR) gravado por qualquer serviço deve poder ser lido por qualquer outro serviço, independentemente de em qual pod/instância ele foi gerado. Hoje, com cada serviço gravando no disco local do próprio pod, um arquivo escrito pelo serviço de ingestão simplesmente não existe no disco do serviço que serve o arquivo nem do serviço de OCR.

**Why this priority**: É a razão de existir do recurso. Sem isso, o endpoint que serve o arquivo original retorna 404 e o OCR falha, quebrando o fluxo em ambientes com pods isolados (staging/produção). É o requisito de menor granularidade que já entrega valor: torna o sistema funcional entre pods.

**Independent Test**: Gravar um artefato por um serviço e recuperá-lo por outro serviço rodando em pod distinto, verificando que o conteúdo (bytes) é idêntico ao gravado.

**Acceptance Scenarios**:

1. **Given** o storage compartilhado ativado, **When** o serviço de ingestão grava o arquivo original de um documento, **Then** o serviço que serve o arquivo (rodando em outro pod) consegue recuperá-lo com os mesmos bytes.
2. **Given** o storage compartilhado ativado, **When** o serviço de OCR precisa ler o arquivo original gravado pela ingestão, **Then** a leitura é bem-sucedida sem `arquivo não encontrado`.
3. **Given** o storage compartilhado ativado, **When** o serviço de OCR grava o `raw_text.json`, **Then** os serviços de layout e de extração (em pods distintos) conseguem lê-lo.

---

### User Story 2 - Seleção do backend de storage por ambiente, sem regressão (Priority: P1)

O backend de armazenamento deve ser selecionável por configuração de ambiente. O comportamento padrão (sem configuração adicional) deve preservar exatamente o comportamento atual; o storage compartilhado é ativado explicitamente por ambiente. Isso permite habilitar o recurso apenas onde é necessário (staging/produção) sem alterar o comportamento em desenvolvimento local nem forçar um big-bang.

**Why this priority**: Segurança de entrega. Sem um interruptor por ambiente e um padrão idêntico ao atual, a mudança arriscaria regressão em todos os ambientes de uma vez. É pré-requisito para um rollout controlado e reversível.

**Independent Test**: Com a configuração padrão (nenhuma alteração de ambiente), rodar o fluxo atual e confirmar comportamento idêntico ao de hoje; então ativar o storage compartilhado por ambiente e confirmar que o fluxo cross-pod passa a funcionar — tudo sem alteração de código entre os dois modos.

**Acceptance Scenarios**:

1. **Given** nenhuma configuração de storage definida no ambiente, **When** o sistema opera, **Then** o comportamento de leitura/escrita de artefatos é idêntico ao atual (armazenamento local).
2. **Given** o storage compartilhado configurado por variáveis de ambiente, **When** o sistema opera, **Then** todos os serviços passam a ler/gravar no storage compartilhado.
3. **Given** o storage compartilhado ativo, **When** a configuração é revertida para o padrão, **Then** o sistema volta ao comportamento anterior sem alteração de código.

---

### User Story 3 - Coexistência de referências legadas e migração sem downtime (Priority: P2)

Referências de arquivos já gravadas antes da ativação do storage compartilhado devem continuar legíveis mesmo depois que o novo storage for ativado, permitindo migração gradual dos dados existentes e rollback sem perda de acesso. A migração dos dados já existentes deve ocorrer sem interrupção do serviço.

**Why this priority**: Torna a adoção segura em um sistema já em uso. Sem coexistência, ativar o novo storage tornaria todo o histórico inacessível e impediria rollback. É P2 porque depende de US1/US2 estarem no lugar, mas é essencial antes de considerar o recurso concluído em produção.

**Independent Test**: Com o novo storage ativado, abrir um documento cuja referência foi gravada no formato legado (antes da migração) e confirmar que ele abre normalmente; migrar esse artefato e confirmar que continua acessível, sem que o serviço fique indisponível durante o processo.

**Acceptance Scenarios**:

1. **Given** um documento com referência de arquivo em formato legado e o novo storage ativado, **When** o usuário/serviço solicita o arquivo, **Then** ele é servido normalmente.
2. **Given** a migração dos dados existentes em andamento, **When** um usuário usa o sistema, **Then** não há janela de indisponibilidade percebida (sem downtime).
3. **Given** a necessidade de rollback após ativar o novo storage, **When** a configuração é revertida, **Then** os artefatos já migrados continuam acessíveis e nenhum acesso é perdido.

---

### User Story 4 - Falha de storage é sempre explícita (Priority: P1)

Qualquer falha de acesso ao storage (indisponibilidade, credencial inválida, objeto inexistente) deve produzir um erro explícito e propagado. O sistema NUNCA deve registrar um "sucesso silencioso" que resulte em um documento persistido sem o arquivo correspondente.

**Why this priority**: Integridade de dados e observabilidade. Um sucesso silencioso cria documentos órfãos (sem arquivo) que corrompem o pipeline e são difíceis de diagnosticar — exatamente a classe de falha que motivou este trabalho. É P1 porque protege a correção do fluxo inteiro.

**Independent Test**: Simular indisponibilidade/credencial inválida do storage no momento da gravação e confirmar que a operação falha de forma observável, sem criar um documento sem arquivo associado.

**Acceptance Scenarios**:

1. **Given** o storage indisponível, **When** um serviço tenta gravar um artefato, **Then** a operação falha com erro explícito e nenhum documento é registrado sem o arquivo correspondente.
2. **Given** uma credencial inválida, **When** um serviço tenta acessar o storage, **Then** o erro é propagado de forma observável (não é engolido).
3. **Given** um objeto inexistente, **When** um serviço tenta lê-lo, **Then** o resultado é um erro claro de "não encontrado", distinguível de outras falhas.

---

### Edge Cases

- **Documento grande (até 20 MB)**: gravação e leitura/serviço devem ocorrer sem estouro de memória nem timeout.
- **Leitura imediatamente após escrita cross-serviço**: um serviço que lê um artefato logo após outro tê-lo gravado deve obtê-lo de forma consistente.
- **Referência com formato legado após ativação do novo storage**: deve resolver para a origem correta e continuar acessível.
- **Falha parcial durante migração**: um artefato ainda não migrado permanece legível pela referência legada; a migração é retomável/idempotente.
- **Objeto ausente vs. storage indisponível**: os dois casos devem ser distinguíveis (não encontrado ≠ falha de conexão/credencial).
- **Tipo de conteúdo apresentado ao navegador**: ao servir o arquivo original ao usuário final, o tipo de conteúdo deve permanecer idêntico ao atual.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir que qualquer artefato (arquivo original e `raw_text.json`) gravado por um serviço seja recuperável por qualquer outro serviço, independentemente do pod/instância que o gerou.
- **FR-002**: O sistema MUST permitir selecionar o backend de armazenamento por configuração de ambiente.
- **FR-003**: O comportamento padrão (sem configuração adicional) MUST preservar exatamente o comportamento atual de armazenamento local; o storage compartilhado MUST ser ativado explicitamente por configuração de ambiente.
- **FR-004**: O sistema MUST manter legíveis as referências de arquivos já existentes (formato legado) mesmo após a ativação do novo storage, permitindo coexistência, migração gradual e rollback sem perda de acesso.
- **FR-005**: A migração dos dados já existentes MUST ocorrer sem downtime perceptível do serviço.
- **FR-006**: O sistema MUST produzir erro explícito e propagado em qualquer falha de acesso ao storage (indisponibilidade, credencial inválida, objeto inexistente), e MUST NOT registrar um documento sem o arquivo correspondente ("sucesso silencioso").
- **FR-007**: O sistema MUST distinguir a condição "objeto não encontrado" das demais falhas de acesso ao storage (conexão/credencial).
- **FR-008**: Endpoint e credenciais do storage MUST vir sempre de configuração/segredos de ambiente, nunca embutidos no código.
- **FR-009**: O comportamento de servir o arquivo original ao usuário final MUST permanecer idêntico ao atual, incluindo o tipo de conteúdo apresentado ao navegador.
- **FR-010**: O sistema MUST gravar e servir documentos de até 20 MB sem estouro de memória nem timeout.
- **FR-011**: O sistema MUST garantir que, após um artefato ser gravado por um serviço, uma leitura subsequente por outro serviço obtenha o conteúdo gravado (consistência de leitura pós-escrita entre serviços).

### Key Entities *(include if feature involves data)*

- **Artefato**: uma unidade de conteúdo binário persistida e compartilhada entre serviços. Nesta feature, os tipos em escopo são o **arquivo original** (enviado no upload) e o **`raw_text.json`** (produzido pelo OCR). Cada artefato possui um conteúdo (bytes) e um identificador/referência estável.
- **Referência de artefato**: o ponteiro persistido (no banco e propagado em eventos) que localiza um artefato. Pode existir em formato **legado** (armazenamento local) ou no formato do **novo storage compartilhado**; ambos devem resolver para o artefato correto durante o período de coexistência.
- **Backend de storage**: a origem/destino físico dos artefatos, selecionável por ambiente — o modo padrão (comportamento atual) e o modo compartilhado (compatível com S3/MinIO).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos artefatos gravados por um serviço são recuperáveis por outro serviço em pod distinto (verificado por bytes idênticos).
- **SC-002**: O endpoint que serve o arquivo original funciona a partir de um pod diferente daquele que gravou o arquivo, em 100% das tentativas para artefatos existentes.
- **SC-003**: O pipeline completo (ingestão → core → OCR → layout → extração) lê todos os artefatos intermediários entre pods sem nenhuma falha de "arquivo não encontrado".
- **SC-004**: Documentos de até 20 MB são gravados e servidos com sucesso, sem estouro de memória do serviço nem timeout, em 100% das tentativas.
- **SC-005**: Em toda falha de conexão/credencial do storage, a operação de gravação resulta em erro observável e em zero documentos registrados sem o arquivo correspondente.
- **SC-006**: 100% das referências legadas (gravadas antes da migração) continuam abrindo normalmente com o novo storage ativado.
- **SC-007**: Com a configuração padrão, o comportamento observável do sistema é idêntico ao atual (nenhuma regressão detectada nos fluxos existentes de upload, serviço de arquivo e pipeline).
- **SC-008**: A migração dos dados existentes é concluída sem nenhuma janela de indisponibilidade percebida pelos usuários.

## Assumptions

- Os únicos artefatos em escopo são o **arquivo original** e o **`raw_text.json`**; outros artefatos (por exemplo, exports para consumo externo) só entram em escopo conforme resolvido nas clarificações abaixo.
- O storage compartilhado alvo é **compatível com S3/MinIO** (conforme o objetivo declarado), mas a spec não prescreve produto, biblioteca ou desenho — isso é responsabilidade da fase de plan.
- O sistema já opera com múltiplos serviços em pods separados em staging/produção, e com diretório físico compartilhado em desenvolvimento local (origem do "funciona local, quebra em staging").
- A correção do bug de rede na sincronização ingestão→core é tratada separadamente e NÃO faz parte desta feature (ver Fora de Escopo).

## Out of Scope

- **Bug de rede na sincronização ingestão→core**: o documento não chega ao banco do core por um problema distinto de HTTP/rede. É o que causa o sintoma atualmente reportado ("documento não aparece na listagem") e **não** é resolvido por esta mudança. Tratado separadamente.
- **Decisões de implementação**: escolha de biblioteca, desenho de classes, estrutura de pacotes e sequência de implementação — responsabilidade da fase de plan.

## Clarifications *(pending — não resolver nesta spec)*

Os itens abaixo foram sinalizados como `[NEEDS CLARIFICATION]` e devem ser resolvidos antes/na fase de plan. Não alteram os requisitos comportamentais acima, mas afetam a extensão real do problema e opções de implementação:

- **[NEEDS CLARIFICATION]**: Já existe um volume compartilhado (PVC ReadWriteMany) montado igualmente em todos os pods? Se sim, a extensão real do problema muda (parte do sintoma poderia já estar mitigada por infraestrutura).
- **[NEEDS CLARIFICATION]**: Endpoint, bucket, região e origem dos segredos do storage (por exemplo, k8s Secret ou Vault)?
- **[NEEDS CLARIFICATION]**: Política de retenção/lifecycle do arquivo original e do `raw_text.json`?
- **[NEEDS CLARIFICATION]**: O export gerado para consumo externo (ERP/integração) é lido por outro backend? Se sim, entra no escopo do storage compartilhado; se não, permanece em volume dedicado.
- **[NEEDS CLARIFICATION]**: Tamanho típico/máximo dos documentos, para decidir entre leitura em memória e streaming / URL pré-assinada (o limite de 20 MB é um teto conhecido; falta o perfil típico).
