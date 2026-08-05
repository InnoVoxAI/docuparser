# Feature Specification: Rastreamento Distribuído (OpenTelemetry) entre Serviços

**Feature Branch**: `016-opentelemetry-tracing`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "Adicionar OpenTelemetry (tracing distribuído) em todos os backends da aplicação (backend-com, backend-core, backend-ocr, langextract-service) e no frontend, cobrindo traces ponta-a-ponta entre os serviços, para identificar gargalos de performance, falhas de comunicação entre os apps, e tracing de erros ao longo de uma requisição que atravessa múltiplos serviços."

## User Scenarios & Testing _(mandatory)_

### User Story 1 - Acompanhar uma requisição de ponta a ponta entre serviços (Priority: P1)

Uma pessoa responsável por operação ou desenvolvimento, ao investigar um problema relatado (ex.: um documento que demorou muito ou falhou ao ser processado), consegue localizar o registro completo do caminho que aquela requisição percorreu — desde o frontend, passando por backend-com, backend-core, backend-ocr e/ou langextract-service — usando um único identificador, e ver a ordem cronológica das etapas.

**Why this priority**: É o núcleo da rastreabilidade pedida. Sem um trace correlacionado entre serviços, não é possível responder "por onde essa requisição passou" nem investigar nada além do que os logs isolados de cada serviço já mostram hoje.

**Independent Test**: Pode ser testado disparando uma operação que atravesse pelo menos dois serviços (ex.: envio de um documento para processamento) e verificando que existe um identificador único que aparece nos registros de cada serviço envolvido, permitindo reconstruir a sequência completa.

**Acceptance Scenarios**:

1. **Given** uma requisição que atravessa o frontend e dois ou mais backends, **When** a operação é concluída (com sucesso ou falha), **Then** existe um registro correlacionado por um identificador único que mostra todas as etapas, em ordem, com o serviço responsável por cada uma.
2. **Given** um identificador de trace conhecido (ex.: obtido de um log de erro), **When** alguém busca por esse identificador, **Then** o sistema permite localizar o registro completo daquela requisição específica.

---

### User Story 2 - Identificar gargalos de performance (Priority: P1)

A pessoa investigando uma lentidão consegue ver quanto tempo cada etapa de uma requisição levou em cada serviço, permitindo apontar exatamente qual etapa (e qual serviço) é responsável pela demora.

**Why this priority**: É um dos dois objetivos centrais citados junto com a rastreabilidade básica — sem tempos por etapa, o trace mostra o caminho mas não onde está o gargalo.

**Independent Test**: Pode ser testado executando uma operação de ponta a ponta e verificando que o tempo total e o tempo de cada etapa individual (por serviço) ficam visíveis e são comparáveis entre si.

**Acceptance Scenarios**:

1. **Given** uma requisição concluída que atravessou múltiplos serviços, **When** alguém consulta seu registro, **Then** o tempo gasto em cada etapa/serviço aparece de forma individualizada, permitindo somar e comparar.
2. **Given** uma etapa específica (ex.: uma chamada do backend-core ao langextract-service) que é consistentemente mais lenta que as demais, **When** vários registros dessa mesma etapa são observados, **Then** é possível identificar esse padrão de lentidão recorrente.

---

### User Story 3 - Diagnosticar falhas de comunicação entre serviços (Priority: P2)

Quando uma chamada de um serviço para outro falha (timeout, serviço indisponível, resposta de erro inesperada), a pessoa investigando consegue ver, no registro da requisição, quais dois serviços estavam se comunicando e qual foi a natureza da falha.

**Why this priority**: Complementa a rastreabilidade básica com o cenário de falha entre apps citado explicitamente, mas depende do rastreamento de ponta a ponta (História 1) já estar em vigor.

**Independent Test**: Pode ser testado forçando uma falha de comunicação entre dois serviços (ex.: indisponibilidade temporária de um deles) e verificando que o registro da requisição indica claramente origem, destino e tipo da falha.

**Acceptance Scenarios**:

1. **Given** uma chamada entre dois serviços que falha por timeout ou indisponibilidade, **When** o registro da requisição é consultado, **Then** a falha aparece associada à etapa exata, indicando os serviços de origem e destino envolvidos.
2. **Given** uma chamada entre serviços que recebe uma resposta de erro inesperada, **When** o registro é consultado, **Then** o tipo/natureza do erro de resposta fica visível junto à etapa correspondente.

---

### User Story 4 - Rastrear erros de aplicação ao longo de uma requisição (Priority: P2)

Quando ocorre um erro de aplicação (exceção, falha de validação) durante o processamento de uma requisição em qualquer serviço, esse erro fica associado ao trace completo daquela requisição, permitindo saber em qual serviço e etapa ele ocorreu, sem expor dados sensíveis do documento ou do usuário.

**Why this priority**: Fecha o terceiro objetivo citado (tracing de erros). É P2 porque, na ausência dela, as Histórias 1-3 já entregam valor de rastreabilidade e diagnóstico de comunicação; erros de aplicação isolados já aparecem hoje em logs de cada serviço, ainda que sem a correlação entre etapas.

**Independent Test**: Pode ser testado forçando um erro de aplicação numa etapa intermediária de uma requisição de ponta a ponta e verificando que o erro aparece associado ao identificador daquele trace específico, com contexto suficiente para localizar a etapa, mas sem conteúdo sensível do documento.

**Acceptance Scenarios**:

1. **Given** uma requisição que sofre um erro de aplicação numa etapa intermediária, **When** o registro daquela requisição é consultado, **Then** o erro aparece associado ao trace, indicando serviço e etapa, sem expor conteúdo do documento ou dados pessoais extraídos.
2. **Given** um erro de aplicação registrado, **When** alguém consulta o restante do trace, **Then** ainda é possível ver as etapas anteriores e posteriores ao erro (o que já havia sido concluído e o que foi impactado).

---

### Edge Cases

- O que acontece quando uma etapa não propaga o identificador de rastreamento adiante (ex.: uma chamada mal instrumentada ou a um serviço de terceiros)? A quebra na cadeia não deve derrubar a requisição; a etapa seguinte deve, na pior hipótese, iniciar um novo trace desconectado em vez de falhar.
- O que acontece quando o volume de requisições é muito alto (produção sob carga)? O sistema deve poder reduzir a quantidade de traces completos capturados (amostragem), mas sem perder o registro de nenhuma requisição que resulte em erro.
- O que acontece quando uma etapa envolve um serviço de terceiros (ex.: um provedor de LLM usado pelo langextract-service)? Essa chamada deve aparecer como uma etapa do trace, identificada como dependência externa, sem exigir que o terceiro colabore com o rastreamento.
- O que acontece se a infraestrutura de coleta/armazenamento de rastreamento ficar indisponível? As requisições da aplicação devem continuar funcionando normalmente, sem falhar nem sofrer lentidão perceptível por causa disso.
- O que acontece com processamento assíncrono (filas, etapas de workflow) que continua depois que a requisição original já respondeu? O identificador de rastreamento deve seguir junto, permitindo religar essas etapas posteriores ao trace de origem.
- O que acontece se dados sensíveis (conteúdo de documento, dados pessoais extraídos, credenciais/tokens) forem, por engano, incluídos em uma etapa? Isso é tratado como falha de conformidade da instrumentação e deve ser evitado por padrão, não apenas corrigido reativamente.

## Requirements _(mandatory)_

### Functional Requirements

- **FR-001**: O sistema DEVE atribuir a cada requisição que entra por qualquer um dos serviços (frontend, backend-com, backend-core, backend-ocr, langextract-service) um identificador único de rastreamento que se mantém ao longo de toda a cadeia de chamadas subsequentes entre serviços.
- **FR-002**: O sistema DEVE registrar, para cada requisição rastreada, a sequência de etapas executadas entre serviços, incluindo qual serviço executou cada etapa, quando começou e quanto tempo levou.
- **FR-003**: O sistema DEVE permitir localizar o registro completo de uma requisição específica a partir do seu identificador único de rastreamento.
- **FR-004**: O sistema DEVE registrar falhas de comunicação entre serviços (timeout, indisponibilidade, resposta de erro inesperada) associadas à etapa exata do trace, indicando os serviços de origem e destino e a natureza da falha.
- **FR-005**: O sistema DEVE registrar erros de aplicação ocorridos durante o processamento de uma requisição, associados ao trace e à etapa/serviço correspondente.
- **FR-006**: O sistema NÃO DEVE incluir, em nenhuma etapa de rastreamento, conteúdo de documentos, dados pessoais extraídos, credenciais ou tokens — apenas metadados técnicos/operacionais (ex.: identificadores, status, duração, tipo de operação, tipo de erro).
- **FR-007**: O sistema DEVE manter a continuidade do rastreamento através de fronteiras de processamento assíncrono (filas, etapas de workflow/orquestração), de modo que etapas posteriores continuem associadas ao trace de origem.
- **FR-008**: O sistema DEVE continuar operando normalmente, sem falhas nem degradação perceptível de desempenho nas requisições do usuário, caso a infraestrutura de coleta de rastreamento esteja indisponível.
- **FR-009**: O sistema DEVE permitir reduzir o volume de traces completos capturados (amostragem) em ambientes de alto tráfego, preservando a captura de 100% das requisições que resultem em erro.
- **FR-010**: O sistema DEVE identificar, em cada etapa registrada, o serviço de origem e o ambiente de execução (ex.: desenvolvimento, staging, produção), permitindo filtrar a investigação por ambiente.
- **FR-011**: O sistema DEVE representar chamadas a serviços de terceiros (ex.: provedores de LLM) como uma etapa identificável do trace, mesmo quando o terceiro não participa do rastreamento.

### Key Entities _(include if feature involves data)_

- **Trace**: Representa uma requisição de ponta a ponta que pode atravessar um ou mais serviços; possui identificador único, duração total e status geral (sucesso, erro, falha de comunicação parcial).
- **Etapa (Span)**: Unidade de trabalho dentro de um trace, associada a um serviço e a uma operação específica; possui início, duração, status, e relação de hierarquia com outras etapas do mesmo trace.
- **Falha de comunicação**: Evento registrado quando uma chamada entre serviços não se completa como esperado; associado ao trace e às etapas de origem/destino envolvidas, com a natureza da falha (timeout, indisponibilidade, erro de resposta).
- **Erro de aplicação**: Evento registrado quando ocorre uma exceção ou falha de validação durante o processamento de uma etapa; associado ao trace e à etapa correspondente, sem conter dados sensíveis do documento ou do usuário.

## Success Criteria _(mandatory)_

### Measurable Outcomes

- **SC-001**: Para qualquer requisição de ponta a ponta que atravesse dois ou mais serviços, é possível localizar o registro completo do fluxo (todas as etapas, em ordem, com tempos individuais) em menos de 2 minutos a partir de um único identificador.
- **SC-002**: Em 100% dos casos de falha de comunicação entre serviços, o registro correspondente indica claramente os serviços de origem e destino e a natureza da falha.
- **SC-003**: Em 100% dos casos de erro de aplicação durante uma requisição rastreada, o erro aparece associado ao trace correspondente, permitindo identificar em qual serviço e etapa ele ocorreu.
- **SC-004**: A instrumentação de rastreamento adiciona no máximo um overhead de desempenho imperceptível às operações monitoradas (até 5% de latência adicional).
- **SC-005**: Nenhum dado sensível (conteúdo de documentos, dados pessoais extraídos, credenciais) aparece nos registros de rastreamento, verificado por auditoria por amostragem.
- **SC-006**: 100% das requisições que resultam em erro são preservadas nos registros de rastreamento, mesmo em cenários de amostragem reduzida.

## Assumptions

- O escopo cobre os quatro backends (backend-com, backend-core, backend-ocr, langextract-service) e o frontend, incluindo o código compartilhado usado por eles (contracts, layout-service, shared) quando executado no contexto desses serviços.
- Processamento assíncrono (filas, motor de workflow) faz parte do escopo de propagação do identificador de rastreamento, já que falhas de comunicação e erros ao longo dessas etapas também são um objetivo citado.
- Amostragem (sampling) é aceitável em ambientes de produção para controlar volume/custo de dados de rastreamento, desde que requisições com erro sejam sempre preservadas integralmente.
- A ferramenta específica de coleta, armazenamento e visualização dos dados de rastreamento é uma decisão técnica a ser definida na fase de planejamento, não uma decisão de negócio desta especificação.
- O período de retenção dos dados de rastreamento segue prática padrão de mercado para observabilidade, podendo ser ajustado tecnicamente sem impacto no valor de negócio desta feature.
- Esta feature cobre rastreabilidade e diagnóstico (visualização e localização de causas); não inclui alertas automáticos proativos ou dashboards de métricas de negócio, que podem ser trabalho futuro.
- Ambientes de desenvolvimento e teste também recebem instrumentação, permitindo validar o rastreamento antes de produção, mas os requisitos de conformidade de dados sensíveis (FR-006) valem em todos os ambientes igualmente.
