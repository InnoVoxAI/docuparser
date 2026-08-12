# Feature Specification: Onboarding do Administrador de Tenant via Convite por Email

**Feature Branch**: `017-tenant-admin-onboarding`

**Created**: 2026-07-29

**Status**: Draft

**Input**: User description: "Fluxo completo de onboarding de admin de tenant com convite por email, substituindo geração de email fake e senha global compartilhada por convite real com token de ativação"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operador cria tenant com administrador real (Priority: P1)

Um operador da plataforma (equipe interna que provisiona clientes) cria um novo tenant informando o nome e slug da empresa, e também o nome e o email do responsável administrativo daquele tenant. Ao concluir, o sistema envia um convite por email para essa pessoa, que poderá definir sua própria senha e acessar o sistema como administrador do tenant.

**Why this priority**: É o núcleo da mudança solicitada — sem isso, o problema original (emails fake, senha compartilhada entre clientes) continua existindo. Sem esta história, nenhuma das demais faz sentido.

**Independent Test**: Pode ser testado criando um tenant novo com um email real de teste e verificando que (a) o tenant é criado normalmente, (b) nenhuma senha é atribuída automaticamente, e (c) um convite é enviado ao endereço informado.

**Acceptance Scenarios**:

1. **Given** o operador está na tela de criação de tenant, **When** ele preenche nome do tenant, slug, nome do administrador e email do administrador e confirma, **Then** o tenant é criado e um convite é enviado para o email informado, sem exibir ou compartilhar nenhuma senha.
2. **Given** o operador tenta criar um tenant, **When** o campo de email do administrador é inválido ou vazio, **Then** o sistema impede a criação e exibe uma mensagem de erro clara antes de provisionar qualquer coisa.
3. **Given** um tenant já existe, **When** o operador tenta criar outro tenant reutilizando o mesmo slug, **Then** o sistema mantém o comportamento atual de rejeição (sem regressão), independentemente do novo fluxo de admin.

---

### User Story 2 - Administrador convidado ativa sua conta (Priority: P1)

A pessoa indicada como administradora do tenant recebe um email com um link de convite. Ao clicar no link, ela define sua própria senha e sua conta é ativada, podendo em seguida acessar o sistema normalmente como administradora daquele tenant.

**Why this priority**: Sem esta etapa, o convite enviado na História 1 é inútil — o administrador nunca consegue efetivamente entrar no sistema. É tão crítica quanto a criação do convite.

**Independent Test**: Pode ser testado gerando um convite (via História 1 ou diretamente) e percorrendo o link recebido até definir uma senha e conseguir autenticar-se com sucesso.

**Acceptance Scenarios**:

1. **Given** um convite válido e não utilizado, **When** o administrador acessa o link e define uma senha que atende aos critérios mínimos de segurança, **Then** sua conta é ativada e ele consegue autenticar-se imediatamente com a nova senha.
2. **Given** um convite já utilizado anteriormente, **When** alguém tenta acessar o mesmo link novamente, **Then** o sistema recusa a operação e informa que o convite não é mais válido, sem revelar se a conta existe ou não.
3. **Given** um convite expirado, **When** o administrador tenta usá-lo, **Then** o sistema informa que o convite expirou e orienta a solicitar um novo, sem permitir a definição de senha.

---

### User Story 3 - Reenvio de convite expirado ou perdido (Priority: P2)

Quando um convite expira, é perdido, ou o email não chegou ao destinatário, o operador (ou o próprio administrador, se houver um ponto de entrada apropriado) precisa poder solicitar um novo convite para o mesmo administrador, sem precisar recriar o tenant.

**Why this priority**: É importante para a operação do dia a dia (emails caem em spam, convites expiram), mas o sistema continua minimamente funcional sem isso na primeira entrega — o operador poderia, na pior hipótese, orientar suporte manual. Por isso fica em P2, não P1.

**Independent Test**: Pode ser testado deixando um convite expirar (ou marcando-o como expirado) e então acionando a ação de reenvio, confirmando que um novo convite válido é gerado e o anterior deixa de funcionar.

**Acceptance Scenarios**:

1. **Given** um convite expirado para um administrador de tenant, **When** o operador aciona o reenvio, **Then** um novo convite com novo prazo de validade é gerado e enviado, e o convite anterior é invalidado.
2. **Given** um convite ainda válido, **When** o operador aciona o reenvio mesmo assim, **Then** o sistema invalida o convite anterior e emite um novo, evitando que dois links diferentes fiquem simultaneamente válidos para a mesma conta.

---

### Edge Cases

- O que acontece se o email de convite não puder ser entregue (endereço inexistente, provedor rejeita)? O sistema deve registrar a falha de envio de forma visível ao operador, sem deixar o tenant em estado ambíguo (tenant deve continuar existindo e permitir reenvio).
- O que acontece se dois convites forem gerados para o mesmo administrador ao mesmo tempo (ex.: reenvio duplicado por clique duplo)? Apenas o convite mais recente deve permanecer válido.
- O que acontece se alguém tentar definir uma senha fraca ou reutilizar o token para forjar outra ação? O sistema deve validar critérios mínimos de senha e garantir que o token só sirva para a ativação daquela conta específica, uma única vez.
- O que acontece com tenants já existentes, criados pelo processo antigo (email fake, senha compartilhada)? Precisam continuar funcionando após a mudança — a migração cobre apenas a criação de **novos** tenants; contas antigas não são automaticamente convertidas nesta feature (ver Assumptions).
- O que acontece em ambientes de desenvolvimento/teste automatizado, onde não há serviço de email real disponível? O sistema deve permitir observar/capturar o convite (ex.: log ou caixa de saída local) sem exigir um provedor de email externo configurado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que o operador informe nome e email do administrador do tenant no momento da criação do tenant, além dos campos já existentes (nome do tenant e slug).
- **FR-002**: O sistema DEVE validar que o email do administrador tem formato válido antes de criar o tenant, rejeitando a operação inteira em caso de erro.
- **FR-003**: O sistema NÃO DEVE mais gerar um endereço de email artificial baseado no slug do tenant para o administrador.
- **FR-004**: O sistema NÃO DEVE mais atribuir uma senha padrão compartilhada entre diferentes tenants para a conta administrativa recém-criada.
- **FR-005**: Ao criar um tenant, o sistema DEVE gerar um convite de ativação de conta, de uso único e com prazo de validade, associado ao administrador informado.
- **FR-006**: O sistema DEVE enviar o convite de ativação para o email informado, com um link que permita à pessoa convidada definir sua própria senha.
- **FR-007**: O sistema DEVE oferecer um ponto de acesso público (sem exigir login prévio) onde o convidado, mediante o link recebido, define sua senha e ativa a conta.
- **FR-008**: O sistema DEVE invalidar um convite imediatamente após seu uso, impedindo reutilização do mesmo link.
- **FR-009**: O sistema DEVE recusar convites expirados, informando claramente que expiraram, sem permitir a definição de senha através deles.
- **FR-010**: O sistema DEVE permitir gerar um novo convite para o mesmo administrador quando o anterior expirar ou for perdido, invalidando qualquer convite anterior ainda pendente para essa conta.
- **FR-011**: O sistema DEVE registrar (log) o envio, sucesso ou falha de entrega de convites, de forma que problemas de entrega possam ser diagnosticados sem expor a senha ou dados sensíveis do convite em texto claro nos logs.
- **FR-012**: Em ambientes de desenvolvimento/teste, o sistema DEVE permitir verificar o conteúdo do convite sem depender de um provedor de email externo real.
- **FR-013**: Tenants criados anteriormente ao mecanismo de convite (com o padrão antigo de email fake) DEVEM continuar autenticando normalmente; esta feature não exige migração retroativa dessas contas.
- **FR-014**: O sistema DEVE impedir que uma pessoa não autenticada, de posse de um link de convite de outro tenant, consiga ativar ou alterar contas que não sejam a associada àquele token específico.

### Key Entities *(include if feature involves data)*

- **Convite de Administrador (Admin Invite)**: Representa a intenção de ativação de uma conta administrativa para um tenant específico. Possui um identificador único e não-adivinhável (token), um destino (o administrador/usuário associado), um prazo de validade, e um estado (pendente, usado, expirado/invalidado). Relaciona-se 1:1 com o usuário administrador e com o tenant ao qual pertence.
- **Administrador do Tenant**: A pessoa responsável por um tenant. É identificada por nome e email reais fornecidos no momento da criação do tenant; inicia sem senha definida até que ative sua conta através do convite.
- **Tenant**: Entidade já existente no sistema (nome, slug); passa a ter, no momento de sua criação, um administrador associado com dados reais em vez de um placeholder gerado automaticamente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos tenants criados após a entrega desta feature possuem um administrador com email real e verificável, sem nenhum email no padrão artificial antigo.
- **SC-002**: Nenhuma nova conta administrativa de tenant é criada com uma senha idêntica à de outro tenant (elimina a senha compartilhada entre clientes).
- **SC-003**: Um administrador convidado consegue, a partir do recebimento do email, ativar sua conta e autenticar-se em menos de 5 minutos em condições normais de uso.
- **SC-004**: Convites expirados ou já utilizados são rejeitados em 100% das tentativas de reuso, sem exceções.
- **SC-005**: O operador consegue solicitar reenvio de um convite e o novo link funciona, invalidando o anterior, em 100% dos casos testados.

## Assumptions

- O processo de criação de tenant continua sendo executado por um operador interno da plataforma (não é um fluxo de self-service público de cadastro de clientes) — o formulário afetado é o mesmo hoje restrito à área administrativa.
- Contas administrativas de tenants criados antes desta feature (padrão de email fake) não serão migradas automaticamente; permanecem funcionando como estão até serem tratadas em uma iniciativa separada, se necessário.
- Existe (ou será provisionado como parte da implementação) algum meio de envio de email de saída para o ambiente de produção; em ambientes de desenvolvimento/teste, capturar o convite localmente (sem envio real) é aceitável.
- O prazo de expiração do convite segue práticas padrão de mercado para convites de ativação de conta (tipicamente na ordem de horas a poucos dias) — o valor exato é um detalhe de implementação, não uma decisão de negócio crítica para esta especificação.
- Critérios mínimos de força de senha seguem os mesmos padrões já eventualmente aplicados em outros fluxos de definição de senha do sistema; na ausência de um padrão existente, usam-se práticas comuns de mercado.
