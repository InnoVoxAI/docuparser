# Feature Specification: Migração do Frontend DocuParse de JavaScript/JSX para TypeScript/TSX

**Feature Branch**: `008-frontend-ts-migration`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Migrar o frontend (React 18 + Vite 5, hoje em JS/JSX, concentrado no monólito `src/main.jsx` + arquivos de dados em `src/models/**`) para TypeScript/TSX, introduzindo tipagem estática de forma incremental e preservando integralmente o comportamento, o visual e as integrações atuais — sem refatoração estrutural."

## Clarifications

### Session 2026-06-22

- Q: A validação de regressão será manual ou exigirá automação de testes (hoje inexistente no frontend)? → A: Exigir uma suíte de testes automatizada que cubra os fluxos principais (telas, integrações e permissões). Isso adiciona uma ferramenta de testes ao frontend, ampliando o escopo além da migração de tipos pura.
- Q: "Modo estrito" é um gate de aceite rígido? → A: O modo estrito deve estar ativado com zero erros bloqueantes; o uso de `any` pontual é permitido, desde que documentado/justificado onde a tipagem completa for custosa (não há proibição de `any`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preservação total do comportamento após a migração (Priority: P1)

Após o frontend ser migrado para TypeScript, qualquer usuário (operador, validador, administrador) abre a aplicação e a utiliza exatamente como antes: as mesmas telas, o mesmo layout, os mesmos fluxos, a mesma navegação, as mesmas permissões e as mesmas integrações com o backend. Nenhuma diferença perceptível de funcionamento ou aparência.

**Why this priority**: É o objetivo central e a maior fonte de risco. Uma migração de tipagem que altere comportamento, visual ou integrações fracassa em sua premissa. Sem esta garantia, nada mais importa.

**Independent Test**: Executar o roteiro de regressão completo (todas as telas e fluxos) na versão migrada e comparar com a versão atual; confirmar que comportamento, aparência e chamadas de rede são idênticos.

**Acceptance Scenarios**:

1. **Given** a aplicação migrada para TypeScript em execução, **When** o usuário percorre todas as telas (Login, Dashboard, Inbox, Validação, Aprovados, Rejeitados, Operações, Configurações, Usuários, Roles), **Then** o layout, os estilos e o posicionamento dos elementos são idênticos ao estado anterior.
2. **Given** a aplicação migrada, **When** o usuário executa os fluxos de negócio (upload, extração, edição/salvamento de campos, histórico de versões, aprovação/rejeição, reprocessamento, configurações), **Then** todos os fluxos produzem o mesmo resultado de antes.
3. **Given** a aplicação migrada, **When** o usuário realiza ações que chamam o backend, **Then** as mesmas requisições (endpoints, parâmetros e payloads) são enviadas e as respostas são tratadas como antes — nenhum contrato de API muda.
4. **Given** usuários com diferentes perfis/permissões, **When** acessam a aplicação migrada, **Then** a visibilidade de menus e telas respeita exatamente as mesmas regras de permissão de antes.

---

### User Story 2 - Validação estática de tipos disponível e build funcional (Priority: P1)

A equipe de desenvolvimento passa a contar com verificação estática de tipos: é possível rodar uma checagem de tipos que reporta erros antes da execução, e o build de produção e o ambiente de desenvolvimento continuam funcionando pelos scripts atuais.

**Why this priority**: É o valor de negócio da iniciativa (segurança de desenvolvimento e manutenibilidade). Sem uma checagem de tipos operável e um build funcional, a migração não entrega benefício.

**Independent Test**: Rodar o comando de checagem de tipos e o build de produção; confirmar que ambos concluem com sucesso e que a checagem de tipos efetivamente detecta um erro de tipo introduzido propositalmente.

**Acceptance Scenarios**:

1. **Given** o projeto migrado, **When** a checagem estática de tipos é executada, **Then** ela conclui sem erros bloqueantes.
2. **Given** o projeto migrado, **When** o build de produção é executado, **Then** ele é gerado com sucesso.
3. **Given** o projeto migrado, **When** o ambiente de desenvolvimento local é iniciado pelos scripts atuais, **Then** a aplicação sobe e serve normalmente.
4. **Given** um erro de tipo deliberado introduzido no código, **When** a checagem de tipos é executada, **Then** o erro é reportado (a validação estática é efetiva, não apenas decorativa).

---

### User Story 3 - Base tipada do domínio e dos componentes (Priority: P2)

Os desenvolvedores passam a ter tipos explícitos para as entidades centrais (documento, campos extraídos, versões de campos, resultado de extração, status documental, usuário/permissões), para os contextos, para as props de componentes e para os dados trocados com o backend (DTOs), de modo que futuras alterações sejam guiadas pelo compilador.

**Why this priority**: É o que sustenta o ganho de manutenibilidade a longo prazo. Depende da migração base (US1/US2) já estar concluída, por isso é P2.

**Independent Test**: Inspecionar o código migrado e confirmar que as entidades de domínio, os contextos, as props de componentes e os DTOs de integração possuem tipos explícitos, e que alterar um uso de forma incompatível gera erro de tipo.

**Acceptance Scenarios**:

1. **Given** o código migrado, **When** um desenvolvedor inspeciona as entidades de domínio, **Then** existem tipos definidos para documento, campos extraídos, versões de campos, resultado de extração e status documental.
2. **Given** o código migrado, **When** um desenvolvedor inspeciona o contexto de autenticação, **Then** o usuário autenticado e suas permissões estão tipados.
3. **Given** o código migrado, **When** um desenvolvedor inspeciona os componentes, **Then** as props (incluindo children, callbacks e eventos) possuem tipagem.
4. **Given** o código migrado, **When** um desenvolvedor altera o uso de um DTO de integração de forma incompatível, **Then** a checagem de tipos acusa o erro.

---

### User Story 4 - Evolução incremental e endurecimento progressivo da tipagem (Priority: P3)

A migração é conduzida de forma incremental, permitindo a coexistência temporária de arquivos JS e TS durante a transição, e o rigor da tipagem é aumentado por etapas até atingir a configuração estrita ao final, sem nunca quebrar a aplicação no caminho.

**Why this priority**: Garante baixo risco operacional e entregas verificáveis a cada passo, mas é uma característica do processo de execução; o resultado final (US1–US3) é o que importa para o negócio.

**Independent Test**: Verificar que, em estados intermediários da migração, a aplicação compila e roda com arquivos JS e TS convivendo; e que, ao final, a configuração estrita está ativa com a aplicação ainda funcional.

**Acceptance Scenarios**:

1. **Given** uma fase intermediária da migração, **When** há arquivos JS e TS no projeto simultaneamente, **Then** a aplicação compila e executa normalmente.
2. **Given** a conclusão da migração, **When** a configuração estrita de tipos está ativa, **Then** o projeto compila sem erros bloqueantes e a aplicação permanece funcional.

---

### Edge Cases

- **Formato duplo de campo extraído**: um campo pode vir do backend como valor escalar ou como objeto `{ value, confidence }`. A tipagem deve contemplar ambos os formatos sem alterar o comportamento de leitura atual.
- **Variáveis de ambiente do frontend**: variáveis de ambiente consumidas pela aplicação (ex.: token interno de serviço) precisam ser tipadas; ausência de uma variável opcional não pode quebrar a build nem o runtime.
- **Aliases de importação**: os aliases de caminho atualmente usados devem continuar resolvendo tanto na checagem de tipos quanto no build/dev.
- **Bibliotecas de terceiros**: todas as bibliotecas em uso devem ter tipos disponíveis; caso alguma não tenha, deve ser tratada sem quebrar a checagem.
- **Campos/respostas opcionais ou nulos**: respostas do backend com campos ausentes/nulos devem ser tipadas de forma a não introduzir erros de runtime nem mudar o tratamento atual.
- **Estado intermediário sem regressão**: a cada etapa incremental, a aplicação não pode ficar em estado quebrado.

## Requirements *(mandatory)*

### Functional Requirements

#### Conversão de Arquivos

- **FR-001**: Os arquivos de interface atualmente em JSX MUST ser convertidos para TSX, incluindo o arquivo principal `src/main.jsx`.
- **FR-002**: Os arquivos JavaScript utilizados pela aplicação em `src/models/**` (schemas, prompts, regras, exemplos) MUST ser convertidos para TypeScript.
- **FR-003**: Arquivos de estilo (CSS), HTML e configurações que possam permanecer em JavaScript sem impacto na tipagem MUST NOT estar no escopo de conversão obrigatória.
- **FR-004**: A estrutura atual de diretórios e a organização do projeto MUST ser preservadas; a migração MUST NOT quebrar o monólito em múltiplos módulos nem reorganizar a arquitetura.

#### Configuração e Validação de Tipos

- **FR-005**: O projeto MUST passar a possuir configuração de TypeScript compatível com o ambiente de build/dev atual.
- **FR-006**: O projeto MUST oferecer um processo executável de validação estática de tipos que reporte erros antes da execução.
- **FR-007**: A configuração MUST suportar os aliases de importação atualmente utilizados, tanto na checagem de tipos quanto no build/dev.
- **FR-008**: As variáveis de ambiente consumidas pelo frontend MUST ser tipadas, tratando variáveis opcionais sem quebrar build ou runtime.
- **FR-009**: A configuração de tipos MUST permitir a coexistência temporária de arquivos JS e TS durante a transição.
- **FR-010**: Ao final da migração, a configuração de tipos MUST estar no modo estrito, com a aplicação compilando sem erros bloqueantes. O uso de `any` pontual é permitido onde a tipagem completa for custosa, desde que documentado/justificado; não há exigência de eliminar todo `any`.

#### Tipagem da Aplicação

- **FR-011**: O contexto de autenticação, o usuário autenticado e as permissões MUST ser tipados.
- **FR-012**: As props dos componentes (incluindo children, callbacks e eventos React) MUST ser tipadas.
- **FR-013**: Os estados (globais e locais) e as estruturas de formulário MUST ser tipados onde a inferência não for suficiente.
- **FR-014**: Os dados de integração com o backend — requests, responses e DTOs — MUST possuir tipagem explícita.
- **FR-015**: As entidades de domínio MUST ser tipadas: documentos, campos extraídos, versões de campos, resultados de extração e status documentais.

#### Preservação de Comportamento

- **FR-016**: A migração MUST NOT alterar fluxos de negócio, comportamento das telas, navegação, permissões, componentes visuais ou UX.
- **FR-017**: A migração MUST NOT alterar nenhum contrato de API (endpoints, parâmetros, payloads de envio ou tratamento de resposta).
- **FR-018**: Nenhuma funcionalidade existente MUST ser removida e nenhum comportamento visual MUST ser alterado.
- **FR-019**: A migração MUST NOT introduzir novas bibliotecas de estado, roteamento ou gerenciamento de dados, nem reescrever componentes.

#### Build, Dev e Compatibilidade

- **FR-020**: O build de produção MUST continuar sendo gerado com sucesso após a migração.
- **FR-021**: O ambiente de desenvolvimento local MUST continuar executando pelos scripts atuais.
- **FR-022**: A aplicação MUST permanecer compatível com as bibliotecas atualmente em uso (camada de UI, cliente HTTP, ícones e utilitários de estilo) nas versões vigentes.
- **FR-023**: A migração MUST NOT introduzir degradação perceptível de performance da aplicação.

#### Validação de Regressão

- **FR-024**: A entrega MUST incluir uma suíte de testes automatizada que cubra os fluxos principais (todas as telas, as integrações com o backend e as regras de permissão), executável por um comando de teste, comprovando que o comportamento permanece inalterado após a migração.
- **FR-025**: A suíte de testes automatizada MUST poder ser executada de forma repetível (localmente e no pipeline de build) e MUST passar integralmente como condição de aceite da migração.

### Key Entities *(include if feature involves data)*

> Entidades a serem representadas por tipos no frontend (espelhando os dados já trocados com o backend; nenhuma estrutura nova de dados é criada).

- **Usuário autenticado**: identidade do usuário logado e seu conjunto de permissões; base do contexto de autenticação.
- **Documento**: item processado pelo sistema, com identificador, status documental, metadados e referência ao resultado de extração e à versão ativa de campos.
- **Status documental**: conjunto de estados possíveis de um documento ao longo do ciclo (recebido, OCR concluído, extração concluída, validação pendente, aprovado, rejeitado, etc.).
- **Resultado de extração**: conjunto atual de campos extraídos de um documento, com confiança associada.
- **Campo extraído**: par nome/valor com confiança; pode aparecer como valor escalar ou como objeto `{ value, confidence }`.
- **Versão de campos extraídos**: snapshot de uma lista de campos em um momento, com número da versão, origem, indicador de versão ativa, autoria e data.
- **DTOs de integração**: estruturas de request/response trocadas com os endpoints existentes (documentos, extração, salvamento/histórico de campos, validação, configurações, usuários e papéis).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das telas e fluxos do roteiro de regressão funcionam de forma idêntica à versão anterior (comportamento e aparência), sem diferenças perceptíveis ao usuário.
- **SC-002**: 100% das integrações com o backend permanecem inalteradas — mesmas chamadas, parâmetros e tratamento de respostas; nenhum contrato de API alterado.
- **SC-003**: A checagem estática de tipos executa e conclui sem erros bloqueantes; um erro de tipo introduzido propositalmente é detectado em 100% das vezes.
- **SC-004**: O build de produção é gerado com sucesso e o ambiente de desenvolvimento local sobe pelos scripts atuais, em 100% das execuções.
- **SC-005**: 100% das entidades de domínio listadas, dos contextos e dos DTOs de integração possuem tipos explícitos definidos.
- **SC-006**: 100% dos componentes possuem tipagem de props.
- **SC-007**: Ao final, a configuração de tipos está no modo estrito com zero erros bloqueantes; ocorrências de `any` são pontuais e acompanhadas de justificativa.
- **SC-008**: Nenhuma regressão de performance perceptível é observada nos fluxos principais em relação ao estado anterior.
- **SC-009**: Em cada etapa intermediária da migração, a aplicação permanece compilando e executável (nenhum estado quebrado entregue).
- **SC-010**: Existe uma suíte de testes automatizada cobrindo os fluxos principais (telas, integrações e permissões), que executa por comando e passa 100% como condição de aceite.

## Assumptions

- O alvo final de rigor de tipagem é o modo estrito; durante a transição admite-se configuração permissiva e coexistência JS/TS.
- A representação dos tipos de domínio e DTOs deve espelhar os dados já produzidos pelos endpoints existentes do backend; nenhuma mudança de contrato é introduzida.
- As bibliotecas atualmente em uso fornecem tipos próprios; não se espera necessidade de criar declarações de tipo de terceiros relevantes.
- Arquivos de configuração de ferramentas de build/estilo podem permanecer em JavaScript quando isso não afetar a tipagem da aplicação.
- O frontend não possui suíte de testes automatizados hoje; esta migração passa a exigir a criação de uma (FR-024/FR-025). A introdução de uma ferramenta de testes é, portanto, parte do escopo — e não conflita com FR-019, que restringe apenas bibliotecas de estado/roteamento/dados, não de teste.
- O uso de "tipagem explícita" não exige eliminar toda inferência: estados e valores triviais podem permanecer inferidos quando isso não reduz a segurança.
- A migração não inclui adoção de linter/formatador novos como requisito; eventuais ajustes de qualidade de código ficam fora do escopo desta entrega.
