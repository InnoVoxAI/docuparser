# Feature Specification: Refatoração Arquitetural do Frontend DocuParse (alinhamento a `frontend_rules.md`)

**Feature Branch**: `016-frontend-architecture-refactor`

**Created**: 2026-07-23

**Status**: Draft

**Input**: User description: "Refatorar a arquitetura do frontend (`docuparse-project/frontend`), hoje um monólito de ~4.630 linhas em `src/main.tsx` sem estrutura modular, roteamento, camada de dados ou formulários padronizados, para migrar incrementalmente (sem big-bang) até a arquitetura-alvo descrita em `docuparse-project/frontend/frontend_rules.md` (React 19, Router v7, TanStack Query, Zustand, React Hook Form + Zod, Tailwind v4, estrutura `app/modules/shared`), preservando 100% do comportamento funcional e visual e mantendo a aplicação sempre operável em produção durante a transição."

## Clarifications

### Session 2026-07-23

- Q: Acessibilidade (WCAG 2.1 AA) — a constituição já exige isso para "novos componentes frontend". Como esta migração deve tratar esse requisito, já que ela reescreve praticamente toda a camada de UI? → A: Dentro do escopo — cada componente migrado/extraído deve atender WCAG 2.1 AA como critério de aceite da própria etapa de migração, aproveitando a reescrita para aplicar o mandato já existente na constituição em vez de adiá-lo para uma iniciativa separada.
- Q: Qual limite numérico de tamanho de arquivo/componente deve ser o alvo mensurável desta migração (para tornar SC-002 verificável)? → A: 150 linhas por componente — mesmo limite já definido em `frontend_rules.md`, mantendo um único número-alvo consistente entre a regra de governança do frontend e o critério de sucesso da spec.
- Q: Qual meta numérica de cobertura de teste deve valer para o código migrado/extraído (FR-010)? → A: ≥80% de cobertura de linha — mesmo piso já exigido pela constituição do projeto para features novas, tratando cada módulo extraído como incremento novo sujeito à mesma régua.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preservação total do comportamento durante toda a transição (Priority: P1)

Em qualquer ponto da migração — antes, durante e depois de cada etapa — qualquer usuário (operador, validador, administrador) usa a aplicação exatamente como usa hoje: mesmas telas, mesmo layout, mesmos fluxos, mesma navegação, mesmas permissões, mesmas integrações com o backend. Nenhuma etapa da refatoração é perceptível para quem usa o sistema.

**Why this priority**: É a premissa inegociável. O frontend está em produção e é usado continuamente; uma refatoração de arquitetura que introduza regressão funcional ou visual, mesmo que temporária, tem custo real para o negócio.

**Independent Test**: A cada etapa entregue, executar o roteiro de regressão completo (todas as telas e fluxos de negócio) e confirmar que o comportamento e a aparência permanecem idênticos aos do estado anterior à etapa.

**Acceptance Scenarios**:

1. **Given** uma etapa da migração concluída, **When** um usuário percorre todas as telas (Login, Dashboard, Inbox, Validação, Aprovados, Rejeitados, Operações, Configurações, Usuários, Roles), **Then** layout, estilos e posicionamento são idênticos ao estado anterior à etapa.
2. **Given** uma etapa concluída, **When** um usuário executa os fluxos de negócio existentes (upload, extração, edição/salvamento de campos, histórico de versões, aprovação/rejeição, reprocessamento, exclusão, configurações, gestão de usuários/roles, operações de DLQ), **Then** todos produzem o mesmo resultado de antes.
3. **Given** uma etapa concluída, **When** a aplicação se comunica com o backend, **Then** os mesmos endpoints, parâmetros e payloads são usados — nenhum contrato de API muda.
4. **Given** usuários com diferentes perfis/permissões, **When** acessam a aplicação após qualquer etapa, **Then** a visibilidade de menus/telas continua respeitando exatamente as mesmas regras de permissão de hoje.

---

### User Story 2 - Arquitetura-alvo disponível e verificável (Priority: P1)

Uma pessoa desenvolvedora abre o repositório e encontra o frontend organizado segundo `frontend_rules.md`: estrutura de pastas por módulo de domínio com API pública única (barrel), navegação por rotas reais, dados de servidor geridos por uma camada de cache/consulta dedicada, estado de cliente isolado do estado de servidor, formulários com validação declarativa, e cada tela/componente pequeno o suficiente para ser entendido isoladamente.

**Why this priority**: É o valor de negócio central da iniciativa — sem isso, a migração não resolve o problema relatado ("desenvolvimento sem critério"), que é a causa da dificuldade de manter e evoluir o frontend com segurança.

**Independent Test**: Inspecionar a árvore de `src/` e confirmar a existência da estrutura modular, ausência de um arquivo concentrando todas as telas, presença de rotas reais, de uma camada de consulta de dados e de validação de formulários declarativa.

**Acceptance Scenarios**:

1. **Given** o frontend após a migração, **When** um desenvolvedor procura o código de uma tela específica, **Then** encontra um módulo próprio com seus próprios componentes, hooks, serviços e tipos — não um único arquivo com todas as telas.
2. **Given** o frontend após a migração, **When** a navegação entre telas ocorre, **Then** ela é feita por rotas reais (URLs distintas por tela), não por alternância de estado interno de um único componente.
3. **Given** o frontend após a migração, **When** uma tela busca dados do backend, **Then** a busca é feita por uma camada de consulta centralizada (com cache e chaves nomeadas), não por `useEffect` + `useState` ad hoc repetido em cada tela.
4. **Given** o frontend após a migração, **When** um desenvolvedor tenta importar um arquivo interno de outro módulo diretamente (fora da API pública do módulo), **Then** essa importação é sinalizada automaticamente como inválida.

---

### User Story 3 - Rede de segurança que impede reintrodução de anti-padrões (Priority: P2)

A equipe passa a contar com verificação automática (lint) e uma suíte de testes que reprovam mudanças que reintroduzam os problemas atuais (tipos `any`, chamadas de API direto em componentes, ausência de tratamento de erro, imports cruzados entre módulos, componentes gigantes).

**Why this priority**: É o que garante que o esforço de migração não se degrade novamente com o tempo — mas depende da arquitetura-alvo (US2) já existir para fazer sentido em toda sua extensão, por isso é P2.

**Independent Test**: Introduzir deliberadamente uma violação de cada regra-chave (um `any`, uma chamada axios direta em um componente de tela, um import direto de arquivo interno de outro módulo) e confirmar que a verificação automática (lint) reporta erro.

**Acceptance Scenarios**:

1. **Given** o projeto migrado, **When** a checagem de tipos é executada, **Then** conclui sem erros bloqueantes.
2. **Given** o projeto migrado, **When** a verificação de lint é executada, **Then** conclui sem violações nas regras configuradas.
3. **Given** um `any` introduzido deliberadamente, **When** a verificação de lint roda, **Then** o erro é reportado.
4. **Given** um import direto de um arquivo interno de outro módulo (fora do barrel), **When** a verificação de lint roda, **Then** o erro é reportado.
5. **Given** a suíte de testes automatizados, **When** ela é executada após qualquer etapa da migração, **Then** conclui com sucesso (mesmo padrão de cobertura de hoje ou superior).

---

### User Story 4 - Evolução incremental, sempre entregável (Priority: P3)

A migração é conduzida em etapas pequenas e independentes (por dependência de upgrade, depois por módulo de domínio), cada uma entregável isoladamente, sem exigir que toda a refatoração esteja pronta para gerar valor ou ser integrada.

**Why this priority**: Reduz risco operacional e permite pausar/retomar o trabalho a qualquer momento sem deixar o frontend em estado quebrado — mas é uma característica do processo de execução, não o resultado de negócio em si (esse é US1–US3), por isso P3.

**Independent Test**: Verificar que, em qualquer estado intermediário da migração, a aplicação compila, os testes passam e o app roda normalmente — inclusive com o arquivo monolítico original e os módulos já extraídos coexistindo temporariamente.

**Acceptance Scenarios**:

1. **Given** um módulo de domínio já extraído e outros ainda no arquivo monolítico original, **When** a aplicação é executada, **Then** todas as telas funcionam normalmente, independentemente de já terem sido migradas ou não.
2. **Given** uma etapa de upgrade de dependência (ex.: versão de biblioteca de UI) concluída isoladamente, **When** a suíte de testes roda, **Then** conclui com sucesso antes de qualquer extração estrutural começar.
3. **Given** o trabalho pausado em qualquer etapa, **When** for retomado posteriormente (mesma sessão ou outra), **Then** não é necessário refazer trabalho já concluído nem há estado quebrado para reverter.

### Edge Cases

- O que acontece se uma etapa de extração de um módulo quebrar um teste existente? A etapa não é considerada concluída até o teste voltar a passar — não avança para a próxima etapa com testes quebrados.
- Como o sistema se comporta durante a transição de navegação (de alternância de estado interno para rotas reais) para usuários com sessão ativa? A URL/rota não pode quebrar o controle de permissões existente — cada rota deve respeitar a mesma checagem de permissão que hoje é feita antes de renderizar cada tela.
- O que acontece com formulários que ainda não foram migrados para a validação declarativa enquanto outros já foram? Ambos os padrões podem coexistir temporariamente sem conflito, desde que cada formulário migrado preserve as mesmas regras de validação e mensagens que tinha antes.
- Como tratar dados de API cujo formato é heterogêneo/dinâmico (ex.: eventos de fila de erro no módulo de operações)? A tipagem permissiva já usada hoje para esses casos pode ser preservada — a regra de "nenhum `any`" não exige modelar exaustivamente payloads legitimamente variáveis, apenas evitar `any` onde a forma dos dados é conhecida.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O frontend DEVE ser organizado em módulos de domínio (ex.: autenticação, documentos, operações, configurações, administração, upload), cada um com sua própria API pública, sem que um módulo importe arquivos internos de outro.
- **FR-002**: A navegação entre telas DEVE ser feita por rotas reais e endereçáveis, substituindo a alternância de estado interno usada hoje, preservando as mesmas regras de controle de acesso por permissão já existentes.
- **FR-003**: Toda busca e mutação de dados vindos do backend DEVE passar por uma camada de consulta/cache centralizada com chaves de consulta nomeadas por módulo, eliminando a busca ad hoc via `useEffect`/`useState` direto em componentes de tela.
- **FR-004**: Estado de cliente (UI) e estado de servidor (dados do backend) DEVEM ser mantidos em mecanismos distintos — o estado de servidor nunca deve ser duplicado em um armazenamento de estado de cliente.
- **FR-005**: Formulários DEVEM usar validação declarativa centralizada em esquema, com mensagens de erro por campo, preservando as mesmas regras de validação e textos já existentes.
- **FR-006**: Todo componente de tela com dados assíncronos DEVE tratar explicitamente os três estados (carregando, erro, sucesso), como já é feito hoje, mantido de forma consistente em toda a aplicação.
- **FR-007**: Erros DEVEM ser capturados por limites de erro (error boundaries) por módulo/rota, com uma mensagem amigável ao usuário final e nunca expor detalhes técnicos crus (stack trace, código bruto de erro de API).
- **FR-008**: O código DEVE ser submetido a verificação automática de lint que bloqueie os anti-padrões identificados hoje (tipo `any` não justificado, chamada de API direta em componente de tela, import cruzado entre módulos fora da API pública, componente excessivamente grande).
- **FR-009**: A migração DEVE ser executada em etapas entregáveis de forma independente (upgrades de dependência isolados da extração estrutural; extração módulo a módulo), sem exigir uma janela de indisponibilidade da aplicação.
- **FR-010**: A cada etapa entregue, a suíte de testes automatizados existente DEVE continuar passando integralmente, e novas partes extraídas/migradas DEVEM atingir cobertura de linha ≥80% (mesmo piso já exigido pela constituição do projeto para features novas), combinando teste de fumaça por tela/componente crítico, teste de integração para lógica assíncrona e teste unitário para funções de acesso a dados.
- **FR-011**: Nenhuma mudança de contrato com o backend (endpoints, parâmetros, formatos de payload) é permitida como parte desta migração.
- **FR-012**: Ao final da migração, não deve restar um único arquivo concentrando múltiplas telas/domínios não relacionados — cada tela/domínio deve residir em seu módulo correspondente, e nenhum arquivo de componente deve exceder 150 linhas, exceto exceções pontuais justificadas explicitamente no código.
- **FR-013**: Cada componente migrado/extraído para a nova estrutura DEVE atender ao nível WCAG 2.1 AA (conforme já exigido pela constituição do projeto para novos componentes frontend), validado como critério de aceite da própria etapa de extração em que o componente é migrado — não adiado para uma iniciativa futura separada.

### Key Entities

- **Módulo de domínio**: unidade de organização do frontend (ex.: autenticação, documentos, operações, configurações, administração, upload) com seus próprios componentes, lógica de dados e tipos, e uma única API pública exposta a outros módulos.
- **Rota**: endereço navegável correspondente a uma tela ou fluxo, associado às mesmas regras de permissão hoje aplicadas por tela.
- **Consulta de dados (query)**: operação nomeada e cacheável de leitura ou escrita de dados do backend, associada a uma chave que identifica univocamente o dado buscado por módulo.
- **Estado de cliente**: dado que existe apenas na interface (não vem do backend e não precisa ser sincronizado com ele), mantido separado do estado de servidor.
- **Limite de erro (error boundary)**: fronteira de captura de falhas de renderização/dados por módulo/rota, responsável por exibir uma mensagem amigável e registrar o erro.
- **Regra de lint**: verificação automática que impede a reintrodução de um anti-padrão específico já observado no código atual.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em nenhuma etapa da migração é registrada regressão funcional ou visual perceptível pelo usuário final — o roteiro de regressão completo passa 100% a cada etapa entregue.
- **SC-002**: O maior arquivo do frontend deixa de concentrar múltiplas telas e domínios não relacionados; ao final da migração, nenhum arquivo de componente excede 150 linhas (mesmo limite de `frontend_rules.md`), exceto exceções pontuais justificadas explicitamente no código.
- **SC-003**: 100% das etapas entregues passam simultaneamente por verificação de tipos, verificação de lint e suíte de testes automatizados antes de serem consideradas concluídas.
- **SC-004**: A aplicação permanece disponível e utilizável em produção durante toda a transição, sem indisponibilidade atribuível à migração.
- **SC-005**: Após a conclusão, tentativas de reintroduzir os anti-padrões identificados hoje (tipo `any` não justificado, chamada de API direta em componente, import cruzado entre módulos, componente sem tratamento de erro) são bloqueadas automaticamente antes da integração do código, sem depender de revisão manual para serem detectadas.
- **SC-006**: 100% dos componentes migrados/extraídos passam em verificação automatizada de acessibilidade sem violações de nível WCAG 2.1 AA.

## Assumptions

- `docuparse-project/frontend/frontend_rules.md` funciona como documento de governança técnica para o frontend (equivalente, neste domínio, à constituição do projeto) — suas escolhas de stack-alvo (React 19, React Router v7, TanStack Query, Zustand, React Hook Form + Zod, Tailwind v4, estrutura `app/modules/shared`) são tratadas como requisito dado nesta feature, não como decisão de implementação em aberto a ser revisitada durante o planejamento.
- A aplicação atual está em uso em produção (deploy via Cloudflare Pages e Docker) e não há janela de manutenção dedicada disponível para esta migração — a transição deve ocorrer com a aplicação sempre operável.
- A suíte de testes automatizados já existente (Vitest + React Testing Library + MSW, cobrindo autenticação, fluxos principais, paginação, permissões, telas e validação) é considerada o piso de regressão válido para começar; sua expansão é parte do trabalho desta feature, não um pré-requisito bloqueante para iniciar.
- Não há mudança de contrato de API ou de comportamento de backend nesta feature — o escopo é exclusivamente a organização e a stack técnica do frontend.
- A ordem de extração dos módulos e o sequenciamento de upgrades de dependência são decisões técnicas de planejamento (`/speckit-plan`), não requisitos de negócio desta especificação.
