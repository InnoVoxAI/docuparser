# Feature Specification: Convite Direto de Usuários por Tenant Admin

**Feature Branch**: `019-generalize-tenant-invite`

**Created**: 2026-07-29

**Status**: Draft

**Input**: User description: "Generalizar o mecanismo de convite por email criado na feature 017 (tenant-admin-onboarding) para permitir que o tenant admin convide usuários comuns (não apenas administradores) para seu tenant via email, reaproveitando a mesma infraestrutura de token de ativação/expiração/reenvio já existente em vez de duplicar em um modelo paralelo. O fluxo de auto-cadastro existente (novo usuário escolhe o tenant e o tenant admin aprova depois) deve ser mantido como está, funcionando em paralelo à nova opção de convite direto."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tenant admin convida um usuário diretamente (Priority: P1)

Um administrador de tenant, a partir da tela de gestão de usuários do seu tenant, informa nome, email e o papel (role) de um novo usuário e dispara um convite. O sistema envia um email de convite para essa pessoa.

**Why this priority**: É o núcleo do pedido — hoje o único caminho de entrada de um usuário comum é ele mesmo se cadastrar e escolher o tenant, o que exige aprovação manual posterior. O convite direto elimina essa fricção quando é o próprio tenant quem sabe quem deve entrar.

**Independent Test**: Pode ser testado logando como tenant admin, convidando um email de teste com um papel específico, e verificando que (a) um convite é gerado associado àquele tenant e papel, e (b) um email é enviado/capturado com um link de ativação.

**Acceptance Scenarios**:

1. **Given** o tenant admin está na tela de gestão de usuários do seu tenant, **When** ele informa nome, email válido e papel de um novo usuário e confirma, **Then** um convite é criado e um email é enviado ao endereço informado, sem exibir nem atribuir nenhuma senha.
2. **Given** o tenant admin tenta convidar um usuário, **When** o email é inválido, vazio, ou já pertence a um usuário existente naquele tenant, **Then** o sistema impede o envio e exibe uma mensagem de erro clara.
3. **Given** o tenant admin está convidando um usuário, **When** ele seleciona o papel a atribuir, **Then** apenas papéis válidos para uso dentro do próprio tenant (não papéis de plataforma) podem ser escolhidos.

---

### User Story 2 - Usuário convidado ativa sua conta (Priority: P1)

A pessoa convidada recebe um email com um link de convite. Ao clicar, ela define sua própria senha e sua conta é ativada imediatamente, já associada e aprovada naquele tenant com o papel definido no convite — sem exigir nenhuma aprovação manual adicional do tenant admin.

**Why this priority**: Sem esta etapa o convite da História 1 é inútil. É tão crítica quanto disparar o convite.

**Independent Test**: Pode ser testado gerando um convite (via História 1) e percorrendo o link recebido até definir senha e autenticar-se com sucesso, confirmando que a conta já está aprovada e vinculada ao tenant/papel corretos.

**Acceptance Scenarios**:

1. **Given** um convite de usuário válido e não utilizado, **When** a pessoa acessa o link e define uma senha que atende aos critérios mínimos de segurança, **Then** sua conta é ativada, já aprovada e vinculada ao tenant e papel do convite, e ela consegue autenticar-se imediatamente.
2. **Given** um convite já utilizado, **When** alguém tenta acessar o mesmo link novamente, **Then** o sistema recusa a operação sem revelar se a conta existe.
3. **Given** um convite expirado, **When** a pessoa tenta usá-lo, **Then** o sistema informa que expirou e orienta a solicitar um novo convite, sem permitir definir senha.

---

### User Story 3 - Reenvio de convite de usuário expirado ou perdido (Priority: P2)

Quando um convite de usuário expira, é perdido, ou o email não chega, o tenant admin precisa poder solicitar um novo convite para a mesma pessoa, sem recriar nada manualmente.

**Why this priority**: Importante para operação do dia a dia, mas o sistema continua funcional sem isso na primeira entrega (o tenant admin poderia recriar o convite do zero como contorno).

**Independent Test**: Pode ser testado deixando um convite de usuário expirar e então acionando o reenvio pelo tenant admin, confirmando que um novo convite válido é gerado e o anterior deixa de funcionar.

**Acceptance Scenarios**:

1. **Given** um convite de usuário expirado, **When** o tenant admin aciona o reenvio, **Then** um novo convite com novo prazo de validade é gerado e enviado, e o anterior é invalidado.
2. **Given** um convite de usuário ainda válido, **When** o tenant admin aciona o reenvio mesmo assim, **Then** o convite anterior é invalidado e um novo é emitido, evitando dois links simultaneamente válidos.

---

### Edge Cases

- O que acontece com o fluxo de auto-cadastro existente (usuário escolhe o tenant e aguarda aprovação do tenant admin)? Ele DEVE continuar funcionando sem nenhuma alteração de comportamento, coexistindo com a nova opção de convite direto — as duas formas de entrada de usuário permanecem disponíveis simultaneamente.
- O que acontece se alguém se auto-cadastrar com o mesmo email de um convite de usuário pendente para o mesmo tenant? O sistema deve tratar isso como conflito e impedir duplicidade de conta, orientando qual caminho seguir.
- O que acontece se o tenant admin tentar convidar um email que já é usuário ativo em outro tenant? O sistema deve rejeitar ou tratar de forma explícita, sem misturar identidades entre tenants (mesma regra que já vale para o convite de administrador da feature 017).
- O que acontece se o email de convite não puder ser entregue? O sistema deve registrar a falha de forma visível ao tenant admin, mantendo o convite disponível para reenvio.
- O que acontece se dois convites forem gerados para a mesma pessoa ao mesmo tempo (clique duplo)? Apenas o mais recente permanece válido.
- O que acontece se o tenant admin tentar convidar alguém para um papel de plataforma (não específico do tenant)? O sistema deve impedir, pois convite direto de tenant admin só pode atribuir papéis internos ao próprio tenant.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que um tenant admin, a partir de uma tela de gestão de usuários do seu próprio tenant, informe nome, email e papel de um novo usuário e dispare um convite de ativação.
- **FR-002**: O sistema DEVE validar o formato do email e a existência de conflito (email já usado no tenant) antes de gerar o convite, rejeitando a operação com mensagem clara em caso de erro.
- **FR-003**: O sistema DEVE restringir os papéis selecionáveis num convite de usuário aos papéis válidos dentro do tenant do convite (excluindo papéis de plataforma).
- **FR-004**: O sistema DEVE gerar, para cada convite de usuário, um token de ativação de uso único com prazo de validade, seguindo o mesmo padrão de segurança já usado para convites de administrador (token não recuperável em texto claro, apenas hash persistido).
- **FR-005**: O sistema DEVE enviar o convite de usuário por email com um link de ativação, reaproveitando o mesmo mecanismo de envio (e capturável em dev/teste) já existente para convites de administrador.
- **FR-006**: O sistema DEVE oferecer um ponto de acesso público de ativação onde o convidado define sua senha, análogo ao já existente para convites de administrador.
- **FR-007**: Ao ativar a conta por convite de usuário, o sistema DEVE criar a conta já aprovada e vinculada ao tenant e papel definidos no convite, sem exigir a aprovação manual usada no fluxo de auto-cadastro.
- **FR-008**: O sistema DEVE invalidar um convite de usuário imediatamente após seu uso, impedindo reutilização do link.
- **FR-009**: O sistema DEVE recusar convites de usuário expirados, informando claramente a expiração, sem permitir definição de senha através deles.
- **FR-010**: O sistema DEVE permitir ao tenant admin reenviar um convite de usuário expirado ou perdido, invalidando qualquer convite anterior ainda pendente para a mesma pessoa.
- **FR-011**: O sistema DEVE manter o fluxo de auto-cadastro existente (usuário escolhe tenant, tenant admin aprova) funcionando sem regressão, disponível em paralelo à nova opção de convite direto.
- **FR-012**: O sistema DEVE impedir que uma pessoa não autenticada, de posse de um link de convite de usuário de outro tenant, ative ou altere contas que não sejam a associada àquele token específico.
- **FR-013**: O sistema DEVE registrar (log) envio, sucesso ou falha de entrega de convites de usuário, sem expor senha ou dados sensíveis do convite em texto claro.
- **FR-014**: A infraestrutura de convite (modelo de dados, geração/validação de token, expiração, endpoint de ativação, envio de email) introduzida na feature 017 para convite de administrador DEVE ser reaproveitada/generalizada para servir também o convite de usuário comum, evitando um segundo mecanismo paralelo e duplicado — a forma exata da generalização é uma decisão técnica a ser detalhada na fase de planejamento.
- **FR-015**: O sistema DEVE corrigir o defeito pré-existente em que a criação direta de usuário pela tela de gestão do tenant admin associava o novo usuário sempre ao primeiro tenant cadastrado no sistema em vez de ao tenant de quem está criando — o novo usuário DEVE sempre ser vinculado ao tenant de quem o convida.
- **FR-016**: O ponto de criação de usuário usado pelo operador de plataforma na tela de administração de tenants (hoje já rotulado como "convite" na interface, mas que na prática cria a conta com senha em texto informada pelo operador, sem enviar nenhum convite) DEVE passar a usar o mesmo mecanismo de convite por email desta feature, eliminando a divergência entre o rótulo exibido e o comportamento real.

### Key Entities *(include if feature involves data)*

- **Convite (Invite)**: Generalização do "Convite de Administrador" da feature 017. Representa a intenção de ativação de uma conta para um tenant específico, com um papel (role) associado. Possui identificador único não-adivinhável (token), destino (nome/email do convidado), prazo de validade, estado (pendente/usado/invalidado) e o papel que a conta ativada deve receber. Relaciona-se com o tenant e, opcionalmente, com o usuário que disparou o convite (tenant admin ou operador de plataforma).
- **Usuário convidado**: Pessoa indicada por nome e email no momento do convite; inicia sem senha definida até ativar a conta através do link recebido, momento em que a conta nasce já aprovada e vinculada ao tenant/papel do convite.
- **Auto-cadastro pendente**: Fluxo já existente (fora do escopo desta feature), mantido sem alterações — usuário se cadastra escolhendo o tenant e aguarda aprovação manual do tenant admin.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um tenant admin consegue convidar um novo usuário para seu tenant em menos de 1 minuto, sem precisar compartilhar senha nenhuma.
- **SC-002**: Um usuário convidado consegue, a partir do recebimento do email, ativar sua conta e autenticar-se em menos de 5 minutos em condições normais de uso, já com acesso aprovado ao tenant.
- **SC-003**: Convites de usuário expirados ou já utilizados são rejeitados em 100% das tentativas de reuso.
- **SC-004**: O tenant admin consegue reenviar um convite de usuário e o novo link funciona, invalidando o anterior, em 100% dos casos testados.
- **SC-005**: O fluxo de auto-cadastro existente continua funcionando sem nenhuma regressão observável após a entrega desta feature (0 casos de quebra em testes de regressão).

## Assumptions

- O convite direto é disparado pelo tenant admin (ou por um operador de plataforma agindo em nome do tenant), não é um recurso self-service público.
- O papel padrão sugerido para convite de usuário comum é o papel operacional já existente no tenant (ex.: `operator`), mas o tenant admin pode escolher outro papel válido dentro do tenant no momento do convite.
- A generalização do modelo `TenantAdminInvite` (ex.: renomear para um `Invite` genérico com campo de papel/tipo) é tratada como decisão de implementação na fase de plano, não uma decisão de negócio desta especificação.
- Critérios de força de senha e prazo de expiração seguem os mesmos padrões já definidos/adotados na feature 017 para convite de administrador, salvo indicação em contrário durante o planejamento.
- Contas de usuários criadas antes desta feature (via auto-cadastro) não são afetadas nem migradas por esta feature.
