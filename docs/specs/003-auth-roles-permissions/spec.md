# Feature Specification: Authentication, Roles and Permissions

**Feature Branch**: `003-auth-roles-permissions`

**Created**: 2026-06-08

**Status**: Draft

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Login e Logout (Priority: P1)

Um usuário com credenciais válidas acessa o sistema mediante autenticação. Ao encerrar a sessão, o acesso é revogado imediatamente.

**Why this priority**: Toda a feature depende de identidade autenticada. Sem login funcional, nenhuma outra história pode ser exercitada.

**Independent Test**: Pode ser testado criando um usuário manualmente no banco, realizando login via formulário e verificando que o acesso a uma tela protegida é concedido; após logout, o mesmo acesso deve ser bloqueado.

**Acceptance Scenarios**:

1. **Given** um usuário cadastrado e ativo, **When** ele informa credenciais corretas, **Then** acessa as telas autorizadas para sua role.
2. **Given** um usuário autenticado, **When** ele encerra a sessão, **Then** tentativas subsequentes de acessar áreas protegidas são redirecionadas para a tela de login.
3. **Given** um usuário sem cadastro ou com credenciais incorretas, **When** tenta realizar login, **Then** recebe mensagem de erro e não obtém acesso.
4. **Given** um usuário com conta desativada, **When** tenta realizar login, **Then** recebe mensagem informando que a conta está inativa.

---

### User Story 2 — Controle de Acesso por Role (Priority: P2)

Cada usuário autenticado só pode acessar funcionalidades permitidas pela sua role. Tentativas de acessar recursos não autorizados são bloqueadas.

**Why this priority**: É o núcleo de autorização. Sem controle de acesso, autenticação não protege nada.

**Independent Test**: Pode ser testado criando dois usuários com roles diferentes (ex.: Operador e Administrador) e verificando que cada um vê e consegue executar apenas as ações autorizadas para sua role.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado com role Operador, **When** tenta acessar "Gerenciar Usuários", **Then** recebe bloqueio de acesso.
2. **Given** um usuário autenticado com role Administrador, **When** acessa qualquer funcionalidade do sistema, **Then** obtém acesso sem restrições.
3. **Given** um administrador que remove uma permissão de uma role, **When** o usuário com essa role tenta acessar o recurso na próxima requisição, **Then** o acesso é bloqueado imediatamente.
4. **Given** um administrador que adiciona uma permissão a uma role, **When** o usuário com essa role faz login novamente, **Then** passa a ter acesso à funcionalidade correspondente.
5. **Given** um usuário não autenticado, **When** tenta acessar qualquer área protegida, **Then** é redirecionado para a tela de login.

---

### User Story 3 — Gestão de Usuários (Priority: P3)

Um administrador pode criar, editar, ativar, desativar e associar roles a usuários do sistema.

**Why this priority**: Sem gestão de usuários o sistema não escala além do usuário inicial.

**Independent Test**: Pode ser testado pelo fluxo: administrador cria um novo usuário, atribui uma role, o novo usuário faz login e acessa apenas as telas permitidas pela role atribuída.

**Acceptance Scenarios**:

1. **Given** um administrador autenticado, **When** cria um usuário com nome, e-mail, senha e role, **Then** o usuário é salvo e pode realizar login.
2. **Given** um administrador autenticado, **When** edita os dados de um usuário existente (nome, e-mail ou role), **Then** as alterações são persistidas.
3. **Given** um administrador autenticado, **When** desativa um usuário, **Then** o usuário não consegue mais realizar login.
4. **Given** um administrador autenticado, **When** reativa um usuário desativado, **Then** o usuário volta a conseguir realizar login.
5. **Given** um administrador autenticado, **When** altera a role de um usuário, **Then** na próxima autenticação o usuário passa a ter as permissões da nova role.

---

### User Story 4 — Gestão de Roles e Permissões (Priority: P4)

Um administrador pode criar, editar e remover roles, e associar permissões a cada role.

**Why this priority**: Roles são a unidade de controle de acesso. Sem gerenciá-las dinamicamente o sistema não cobre a evolução dos perfis de acesso.

**Independent Test**: Pode ser testado criando uma role nova, adicionando permissões específicas, atribuindo a um usuário e verificando que apenas as funcionalidades mapeadas ficam acessíveis.

**Acceptance Scenarios**:

1. **Given** um administrador autenticado, **When** cria uma role com nome e ao menos uma permissão, **Then** a role fica disponível para ser atribuída a usuários.
2. **Given** um administrador autenticado, **When** edita as permissões de uma role existente, **Then** as mudanças refletem para todos os usuários com essa role no próximo login.
3. **Given** um administrador autenticado, **When** tenta remover uma role que está atribuída a pelo menos um usuário, **Then** a operação é bloqueada com mensagem explicativa.
4. **Given** um administrador autenticado, **When** remove uma role que não está atribuída a nenhum usuário, **Then** a role é excluída com sucesso.
5. **Given** um administrador autenticado, **When** tenta salvar uma role sem nenhuma permissão associada, **Then** recebe erro de validação.

---

### User Story 5 — Criação de Conta (Priority: P5)

Um novo usuário pode criar sua própria conta no sistema. A conta fica inativa até que um administrador atribua uma role e ative o usuário.

**Why this priority**: Facilita a integração de novos usuários sem depender exclusivamente do administrador para o cadastro inicial. É complementar à US3.

**Independent Test**: Pode ser testado pelo fluxo: usuário preenche formulário de cadastro, tenta fazer login (deve ser bloqueado por conta inativa), administrador ativa e atribui role, usuário realiza login com sucesso.

**Acceptance Scenarios**:

1. **Given** um visitante não autenticado, **When** preenche o formulário de criação de conta com nome, e-mail e senha válidos, **Then** a conta é criada com status inativo e sem role.
2. **Given** uma conta recém-criada sem role, **When** o usuário tenta realizar login, **Then** recebe mensagem informando que a conta aguarda ativação.
3. **Given** um administrador que ativa e atribui role ao novo usuário, **When** o usuário tenta login, **Then** acessa o sistema normalmente.
4. **Given** um visitante, **When** tenta criar conta com e-mail já cadastrado, **Then** recebe mensagem de erro sem exposição de informações sensíveis.

---

### Edge Cases

- O que acontece se o último administrador for desativado? O sistema deve impedir a desativação se não houver outro administrador ativo.
- O que acontece se todas as permissões forem removidas de uma role ativa? A role não pode ficar sem permissões (validação obrigatória).
- O que acontece se um usuário autenticado tiver sua role removida do sistema por um administrador durante uma sessão ativa? O acesso deve ser bloqueado na próxima verificação de permissão.
- O que acontece ao tentar criar dois usuários com o mesmo e-mail? A operação deve ser rejeitada com mensagem clara.
- O que acontece se um usuário tentar acessar uma URL de área protegida diretamente sem estar autenticado? Deve ser redirecionado para o login, sem exibir dados protegidos.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que usuários realizem login com e-mail e senha.
- **FR-002**: O sistema DEVE permitir que usuários encerrem a sessão a qualquer momento.
- **FR-003**: O sistema DEVE bloquear o acesso a qualquer área protegida para usuários não autenticados, redirecionando para o login.
- **FR-004**: O sistema DEVE permitir que visitantes criem uma conta fornecendo nome, e-mail e senha.
- **FR-005**: Contas criadas por auto-cadastro DEVEM iniciar com status inativo e sem role atribuída.
- **FR-006**: Usuários com conta inativa NÃO DEVEM conseguir realizar login.
- **FR-007**: O sistema DEVE permitir que administradores criem usuários com nome, e-mail, senha e role já atribuída.
- **FR-008**: O sistema DEVE permitir que administradores editem dados de usuários existentes.
- **FR-009**: O sistema DEVE permitir que administradores ativem e desativem usuários.
- **FR-010**: O sistema DEVE impedir a desativação do último administrador ativo.
- **FR-011**: Cada usuário DEVE ter exatamente uma role ativa por vez.
- **FR-012**: O sistema DEVE permitir que administradores criem roles com nome único e ao menos uma permissão associada.
- **FR-013**: O sistema DEVE permitir que administradores editem o nome e as permissões de roles existentes.
- **FR-014**: O sistema DEVE impedir a exclusão de roles que estejam atribuídas a pelo menos um usuário.
- **FR-015**: O sistema DEVE impedir a remoção de todas as permissões de uma role (toda role DEVE ter ao menos uma permissão).
- **FR-016**: O sistema DEVE controlar o acesso a cada funcionalidade com base nas permissões da role do usuário autenticado.
- **FR-017**: A remoção de uma permissão de uma role DEVE bloquear imediatamente o acesso ao recurso correspondente para usuários com essa role.
- **FR-018**: A adição de uma permissão a uma role DEVE refletir para o usuário após seu próximo login.
- **FR-019**: As permissões disponíveis no sistema DEVEM cobrir no mínimo: Visualizar Inbox, Enviar Documentos, Validar Documentos, Criar Modelos, Editar Modelos, Acessar Operações, Gerenciar Usuários, Gerenciar Roles.

### Key Entities

- **Usuário**: identidade no sistema; possui nome, e-mail (único), senha (armazenada de forma segura), status (ativo/inativo), e exatamente uma role ativa.
- **Role**: agrupamento de permissões com nome único; deve ter ao menos uma permissão; pode ser atribuída a múltiplos usuários.
- **Permissão**: unidade atômica de autorização com código único e descrição legível; determina o acesso a uma funcionalidade específica do sistema.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário com credenciais válidas consegue acessar o sistema em menos de 5 segundos a partir do envio do formulário de login.
- **SC-002**: 100% das rotas protegidas bloqueiam acesso não autenticado — nenhuma tela ou dado protegido é acessível sem login.
- **SC-003**: Alterações de permissão (remoção) bloqueiam acesso em no máximo uma requisição após a mudança, sem necessidade de intervenção manual.
- **SC-004**: Um administrador consegue criar um novo usuário com role e ter esse usuário operacional em menos de 2 minutos.
- **SC-005**: 100% das funcionalidades listadas em FR-019 possuem controle de acesso por permissão — nenhuma é acessível sem a permissão correspondente.
- **SC-006**: A tela de gestão de usuários e roles responde a todas as operações (criar, editar, ativar/desativar) em menos de 3 segundos.

---

## Assumptions

- **Escopo inicial no backend-core**: A implementação de autenticação, roles e permissões será feita no módulo `backend-core`. O frontend existente (React/single-page) será atualizado para suportar o fluxo de login e respeitar as permissões retornadas.
- **Sem recuperação de senha na v1**: A funcionalidade de recuperação de acesso (esqueci a senha) está fora do escopo desta entrega. Usuários que perderem acesso devem solicitar redefinição a um administrador.
- **Contas auto-cadastradas ficam inativas**: Usuários que criam conta via formulário público não obtêm acesso até que um administrador ative e atribua uma role. Isso evita acesso não controlado ao sistema.
- **Um usuário = uma role**: O modelo de autorização é simples: um usuário tem exatamente uma role. Múltiplas roles por usuário estão fora do escopo.
- **Permissões pré-definidas**: O conjunto de permissões do sistema é fixo e definido pelo desenvolvimento. Administradores associam permissões existentes às roles, mas não criam novas permissões.
- **Proteção de telas, não de dados individuais**: O controle de acesso é por funcionalidade/tela, não por documento individual (ex.: um Operador vê todos os documentos da Inbox, não apenas os seus).
- **O último administrador não pode ser desativado**: Para evitar bloqueio total do sistema, o sistema impede a desativação do único administrador ativo restante.
