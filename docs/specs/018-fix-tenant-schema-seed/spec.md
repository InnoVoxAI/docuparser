# Feature Specification: Catálogo global de tipos de documento (schemas/layouts) compartilhado entre tenants

**Feature Branch**: `018-fix-tenant-schema-seed`

**Created**: 2026-07-29 · **Replanejado**: 2026-09-07

**Status**: Draft

**Input (pedido original, 2026-07-29)**: "Corrigir bug conhecido: tenants criados via fluxo de convite (US1 da feature 017-tenant-admin-onboarding) não recebem SchemaConfig/LayoutConfig padrão (nota fiscal, fatura de água/condomínio, fatura de energia). Hoje esses defaults só são populados para o tenant seedado no primeiro boot. (...) Existe também código morto/quebrado (ensure_default_schemas) que tentava resolver isso e nunca funcionou, silenciosamente engolido por um except genérico."

**Replanejamento (pedido atual, 2026-09-07)**: em vez de provisionar uma cópia dos tipos de documento padrão dentro de cada tenant, mudar a arquitetura para que os **tipos de documento (schema de extração + layout) não pertençam a nenhum tenant**. Eles passam a viver num **catálogo global compartilhado**: quando um operador da plataforma cria/edita um tipo de documento, ele fica imediatamente disponível para todos os tenants, sem nada exclusivo criado por tenant. Isso elimina a causa raiz do bug original (acoplamento entre provisionamento de tenant e catálogo de tipos de documento) em vez de remediá-lo.

## Contexto e relação com specs anteriores

- **010-multi-tenancy-schemas — US4 ("Tenant-Scoped Settings")** definiu deliberadamente que cada tenant tem sua própria cópia de "schema configs" e "layout configs", para permitir independência operacional futura. **Este spec reverte essa decisão especificamente para o catálogo de tipos de documento** (schema de extração + layout). As demais configurações por tenant citadas na 010 US4 (OCR settings, integration settings, email settings) **permanecem por tenant** e estão fora do escopo aqui.
- **017-tenant-admin-onboarding** e **019-generalize-tenant-invite**: o fluxo de convite/ativação, papéis e permissões de tenant **não** são alterados por este spec. A única interseção é que o provisionamento de tenant deixa de ter (ou de precisar ter) qualquer passo relacionado a tipos de documento padrão.
- **Bug conhecido documentado**: "tenants criados via convite não recebem SchemaConfig/LayoutConfig padrão" — este spec o resolve por eliminação da causa (catálogo global), tornando obsoletas a correção sugerida naquela nota e a tarefa T040 da 017.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tenant novo já enxerga o catálogo de tipos de documento (Priority: P1)

Um operador da plataforma provisiona um novo tenant pelo fluxo de convite de admin. Sem nenhum passo adicional de provisionamento relacionado a tipos de documento, o novo tenant já tem disponível exatamente o mesmo catálogo de tipos de documento que todos os outros tenants (hoje: nota fiscal, fatura de água/condomínio, fatura de energia).

**Why this priority**: É a razão de ser do replanejamento. Enquanto o catálogo for uma cópia por tenant, sempre existe o risco de um caminho de criação de tenant esquecer de populá-lo — que é exatamente o bug que originou esta feature. Com catálogo global, "tenant novo sem tipos de documento" deixa de ser um estado possível.

**Independent Test**: Provisionar um tenant novo via fluxo de convite (US1 de 017) e, sem qualquer ação manual adicional, confirmar via a área de envio/validação de documentos do tenant que os tipos de documento padrão aparecem disponíveis para seleção e que o pipeline de extração os resolve normalmente.

**Acceptance Scenarios**:

1. **Given** um operador com permissão para gerenciar tenants, **When** ele cria um novo tenant informando nome/slug e dados do admin, **Then** o tenant criado já tem disponível o catálogo global de tipos de documento, sem nenhum registro de tipo de documento criado especificamente para esse tenant.
2. **Given** um administrador que acabou de ativar a conta via convite, **When** ele acessa a área de envio/validação de documentos do seu tenant, **Then** vê exatamente os mesmos tipos de documento que qualquer outro tenant vê, com os mesmos nomes/identificadores.
3. **Given** um documento enviado num tenant recém-criado que corresponde a um tipo de documento do catálogo, **When** o pipeline de extração roda, **Then** ele resolve o tipo de documento e o schema de extração a partir do catálogo global, sem depender de nenhuma configuração local do tenant.

---

### User Story 2 - Operador da plataforma gerencia o catálogo em um único lugar (Priority: P1)

Um operador da plataforma cria, edita, ativa/desativa ou remove um tipo de documento no catálogo global. A mudança passa a valer para todos os tenants imediatamente, sem precisar replicar a alteração tenant a tenant.

**Why this priority**: É a contrapartida da US1 e a fonte de verdade única exigida desde o pedido original (evitar duas implementações divergentes de "defaults"). Sem um ponto único de gestão, o catálogo global não entrega valor operacional.

**Independent Test**: Autenticado como operador da plataforma, criar um novo tipo de documento no catálogo; confirmar, a partir de dois tenants diferentes, que o novo tipo aparece para ambos sem nenhuma ação por tenant. Editar/desativar o tipo e confirmar que a mudança reflete nos dois tenants.

**Acceptance Scenarios**:

1. **Given** um operador da plataforma, **When** ele cria um tipo de documento no catálogo global, **Then** o tipo fica disponível para todos os tenants (existentes e futuros) sem passo adicional por tenant.
2. **Given** um operador da plataforma, **When** ele edita a definição de extração ou desativa um tipo de documento do catálogo, **Then** todos os tenants passam a ver a versão atualizada / deixam de ver o tipo desativado.
3. **Given** um usuário de um tenant sem permissão de plataforma (mesmo que seja administrador do próprio tenant), **When** ele tenta criar, editar ou remover um tipo de documento do catálogo, **Then** a operação é recusada e o catálogo permanece inalterado.
4. **Given** um usuário de qualquer tenant, **When** ele consulta a lista de tipos de documento, **Then** consegue lê-la (acesso somente-leitura ao catálogo) para usar no envio/validação de documentos.

---

### User Story 3 - Transição do ambiente atual sem perda nem duplicação (Priority: P1)

A plataforma hoje tem o catálogo replicado dentro de cada tenant (uma cópia por schema). Ao aplicar esta mudança, essas cópias por tenant são consolidadas em um único catálogo global equivalente, sem que nenhum tenant perca acesso aos tipos de documento que já usava e sem criar duplicatas.

**Why this priority**: A mudança de arquitetura só é segura de liberar se a transição do estado atual (N cópias) para o estado novo (1 catálogo) for feita de forma controlada e verificável. É pré-requisito de release, não um item opcional.

**Independent Test**: Rodar a operação de transição contra um ambiente que tem tenants com o catálogo replicado; depois confirmar que existe exatamente um catálogo global com o conjunto esperado de tipos de documento, que todos os tenants continuam conseguindo enviar/validar documentos dos tipos padrão, e que não há cópias remanescentes por tenant.

**Acceptance Scenarios**:

1. **Given** um ambiente com o catálogo replicado em vários tenants (todos com o mesmo conjunto padrão), **When** a transição é executada, **Then** passa a existir um único catálogo global com exatamente esse conjunto de tipos de documento, e nenhuma cópia por tenant permanece.
2. **Given** a transição já executada, **When** ela é executada novamente (idempotência), **Then** o catálogo global permanece com exatamente um conjunto de tipos de documento, sem duplicatas nem erro.
3. **Given** um tenant que, antes da transição, estava sem o catálogo (por causa do bug original), **When** a transição é executada, **Then** esse tenant passa a enxergar o catálogo global completo, igual a todos os outros.
4. **Given** documentos já processados antes da transição que referenciam um tipo de documento pelo identificador, **When** consultados após a transição, **Then** continuam associados ao mesmo tipo de documento (o identificador do tipo é preservado no catálogo global).

---

### User Story 4 - Remoção do provisionamento por tenant e do código morto (Priority: P2)

O mecanismo que hoje tenta popular tipos de documento padrão por tenant — tanto o bloco de seed que roda no primeiro boot quanto a rotina de startup quebrada que era silenciosamente engolida por um `except` genérico — é removido, já que deixa de fazer sentido com o catálogo global.

**Why this priority**: Fecha o débito técnico original (código morto que mascara falhas) e evita que dois modelos mentais conflitantes coexistam no código. Depende da US1–US3 estarem no lugar, por isso P2.

**Independent Test**: Após a mudança, inspecionar os caminhos de provisionamento de tenant e de bootstrap da plataforma e confirmar que nenhum deles cria, copia ou tenta criar tipos de documento por tenant, e que não há mais nenhum ponto de falha silenciosa relacionado a isso.

**Acceptance Scenarios**:

1. **Given** a mudança aplicada, **When** um novo tenant é provisionado, **Then** o fluxo de provisionamento não executa nenhuma etapa relacionada a tipos de documento padrão (nem sucesso, nem falha, nem tentativa).
2. **Given** a plataforma sobe do zero (primeiro boot), **When** o bootstrap roda, **Then** o catálogo global é populado uma única vez a partir da fonte canônica, e não há rotina por tenant tentando fazer isso.
3. **Given** a base de código após a mudança, **When** se busca pela rotina de startup quebrada e pelo laço de seed por tenant, **Then** eles não existem mais (removidos, não apenas desativados).

---

### Edge Cases

- **Tipo de documento em uso ao ser removido**: se um operador tenta remover do catálogo um tipo de documento que ainda é referenciado por documentos já processados ou por layouts, a operação deve ser bloqueada com mensagem clara (mesma proteção que já existe hoje para modelos "padrão do sistema" e para schemas com layouts vinculados), preservando o histórico.
- **Divergência entre cópias na transição**: assume-se que hoje todas as cópias por tenant têm o mesmo conjunto padrão. Se a transição encontrar uma cópia de tenant com um tipo de documento que não existe na fonte canônica (customização inesperada), ela deve **parar e sinalizar** em vez de descartar silenciosamente — a decisão de mesclar/descartar é do operador, e nenhum dado de tenant pode ser perdido sem sinalização.
- **Colisão de identificador**: se dois tipos de documento diferentes (em tenants diferentes) tiverem o mesmo identificador com definições diferentes, a transição não pode simplesmente escolher um — deve sinalizar o conflito para resolução manual.
- **Falha no meio da transição**: a transição deve ser reexecutável (idempotente); uma interrupção não pode deixar o ambiente num estado onde parte dos tenants enxerga o catálogo global e parte ainda depende de cópias locais de forma ambígua.
- **Leitura concorrente durante a transição**: enquanto a transição roda, tenants podem estar enviando documentos. O resultado final deve ser consistente (todo tenant resolve tipos de documento pelo catálogo global) e nenhuma extração deve falhar de forma permanente por causa da janela de transição.
- **Permissão de plataforma ausente no ambiente**: se nenhum papel com permissão de plataforma estiver configurado, a gestão do catálogo fica indisponível (somente-leitura para todos) em vez de cair para "qualquer admin de tenant pode editar".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE manter os tipos de documento (schema de extração + layout) em um **catálogo único, compartilhado por todos os tenants**, não pertencente a nenhum tenant específico.
- **FR-002**: Todo tenant DEVE enxergar automaticamente o catálogo global completo (tipos ativos), sem qualquer registro de tipo de documento criado especificamente para ele e sem nenhum passo de provisionamento por tenant.
- **FR-003**: O pipeline de extração de documentos DEVE resolver o tipo de documento e o schema de extração de qualquer documento a partir do catálogo global, independentemente do tenant em que o documento foi recebido, preservando o comportamento de classificação atual (layout explícito → classificador por texto → tipo de documento).
- **FR-004**: Somente usuários com **permissão de operador da plataforma** DEVEM poder criar, editar, ativar/desativar ou remover tipos de documento no catálogo global.
- **FR-005**: Usuários de qualquer tenant DEVEM ter acesso **somente-leitura** ao catálogo global (listar/consultar tipos de documento para uso no envio e na validação).
- **FR-006**: Uma alteração no catálogo global (criação, edição, ativação/desativação) DEVE passar a valer para todos os tenants imediatamente, sem necessidade de replicar a alteração por tenant.
- **FR-007**: O sistema DEVE popular o catálogo global uma única vez, a partir de uma **fonte de verdade canônica** dos tipos de documento padrão (nota fiscal, fatura de água/condomínio, fatura de energia), tanto no primeiro boot de um ambiente novo quanto na transição de um ambiente existente.
- **FR-008**: O sistema DEVE fornecer uma operação de **transição** que consolide as cópias do catálogo hoje replicadas por tenant em um único catálogo global equivalente, preservando os identificadores dos tipos de documento e sem criar duplicatas.
- **FR-009**: A operação de transição (FR-008) DEVE ser **idempotente**: executá-la mais de uma vez, ou sobre um ambiente já migrado, não pode criar duplicatas, sobrescrever indevidamente nem gerar erro.
- **FR-010**: Se a transição encontrar, em alguma cópia por tenant, um tipo de documento divergente da fonte canônica (customização inesperada) ou um conflito de identificador entre tenants, ela DEVE **interromper e sinalizar** o caso para decisão do operador, sem descartar nem sobrescrever dados de tenant silenciosamente.
- **FR-011**: Após a transição, o sistema NÃO DEVE manter cópias do catálogo por tenant, e nenhum caminho de código DEVE voltar a criá-las.
- **FR-012**: O fluxo de provisionamento de tenant NÃO DEVE conter nenhuma etapa relacionada a tipos de documento padrão (nem criação, nem cópia, nem tentativa protegida por captura de erro).
- **FR-013**: O sistema DEVE **remover** (não apenas desativar) o mecanismo de provisionamento por tenant hoje existente: o laço de seed por tenant no bootstrap e a rotina de startup quebrada cuja falha era engolida por um tratamento de erro genérico.
- **FR-014**: A remoção de um tipo de documento do catálogo global DEVE ser bloqueada, com mensagem clara, quando o tipo ainda for referenciado (por layouts vinculados ou por documentos já processados) ou quando for um tipo protegido "padrão do sistema", preservando o histórico.
- **FR-015**: O identificador de tipo de documento gravado em documentos já processados DEVE continuar resolvendo para o mesmo tipo de documento após a transição.
- **FR-016**: A documentação normativa afetada (referência de modelo de dados e a decisão da 010-multi-tenancy-schemas US4) DEVE ser atualizada para registrar que o catálogo de tipos de documento passou a ser global, e a nota de bug conhecido correspondente DEVE ser marcada como resolvida.

### Key Entities

- **Catálogo global de tipos de documento**: coleção única, compartilhada por toda a plataforma, dos tipos de documento que o sistema sabe extrair. Cada item reúne um **schema de extração** (definição versionada de quais campos extrair) e um ou mais **layouts** (regras de reconhecimento/classificação que apontam para um schema). Não tem dono por tenant. Identificadores de schema e de layout são únicos no âmbito global.
- **Tipo de documento padrão**: subconjunto do catálogo definido pela fonte canônica da plataforma (hoje: nota fiscal, fatura de água/condomínio, fatura de energia). São os itens usados para popular o catálogo no primeiro boot e como referência na transição; podem ser marcados como "padrão do sistema" para proteção contra remoção acidental.
- **Operador da plataforma**: papel/permissão transversal aos tenants (não é o administrador de um tenant) autorizado a gerenciar o catálogo global.
- **Tenant**: organização isolada dentro da plataforma, com seu próprio espaço de dados (documentos, validações, configurações de OCR/integração/email). Passa a **consumir** o catálogo global de tipos de documento em vez de manter uma cópia própria.
- **Documento**: item enviado dentro de um tenant; referencia um tipo de documento do catálogo global pelo identificador, não por vínculo a uma cópia local.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos tenants (existentes após a transição e criados depois dela) enxergam exatamente o mesmo catálogo de tipos de documento, sem nenhum passo manual ou de provisionamento por tenant.
- **SC-002**: "Tenant novo sem tipos de documento disponíveis" deixa de ser um estado alcançável: em qualquer tenant recém-criado, os tipos de documento padrão estão disponíveis para envio/validação imediatamente após a criação.
- **SC-003**: Um operador da plataforma consegue disponibilizar um novo tipo de documento para todos os tenants com **uma única** operação de criação, sem repetir nada por tenant; a mudança aparece para todos os tenants sem ação adicional.
- **SC-004**: Um administrador de tenant (sem permissão de plataforma) não consegue, por nenhum caminho, alterar o catálogo global; a tentativa é recusada e registrável.
- **SC-005**: Após a transição, existe exatamente um catálogo global com o conjunto esperado de tipos de documento — nenhuma cópia remanescente por tenant, nenhuma duplicata — e todos os tenants continuam conseguindo enviar e validar documentos dos tipos padrão.
- **SC-006**: A transição pode ser reexecutada sem efeito colateral (mesmo resultado, sem erro).
- **SC-007**: Não há mais nenhum ponto de falha silenciosa relacionado a provisionamento de tipos de documento: o laço de seed por tenant e a rotina de startup quebrada não existem mais no código.
- **SC-008**: Nenhum documento previamente processado perde a associação com seu tipo de documento por causa da transição.

## Assumptions

- **Sem customização real hoje**: assume-se que nenhum tenant em produção tem tipos de documento além dos três padrão. Se a transição provar o contrário (FR-010), o release é pausado para decisão do operador — mas o caminho feliz não trata mesclagem automática de customizações.
- **Sem override por tenant no escopo**: a arquitetura escolhida é "100% global". Não há, neste spec, mecanismo para um tenant ter um tipo de documento exclusivo ou sobrescrever um do catálogo. Se essa necessidade surgir, é uma feature futura separada.
- **Fonte canônica já existe**: as definições dos três tipos de documento padrão já vivem em um local canônico versionado no repositório e são reutilizadas para popular o catálogo.
- **Permissão de plataforma já existe**: já há uma permissão/papel transversal (usado hoje para gerenciar tenants) que serve como base para "operador da plataforma"; este spec a reutiliza em vez de criar um novo modelo de permissão.
- **Isolamento entre tenants preservado**: tornar o catálogo global afeta **apenas** tipos de documento (schema de extração + layout). Documentos, resultados de extração, decisões de validação e as demais configurações por tenant (OCR, integração, email) continuam totalmente isolados por tenant.
- **Escopo de release**: a mudança inclui a transição de dados e a atualização da documentação normativa citada em FR-016; não inclui mudanças no fluxo de convite/ativação, papéis de tenant ou UI além do necessário para refletir que a gestão do catálogo é uma operação de plataforma.
- **Operação sob demanda**: a transição (FR-008) é executada uma vez, de forma controlada, por quem opera a plataforma, no momento do deploy desta mudança.
