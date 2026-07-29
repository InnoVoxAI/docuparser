# Feature Specification: Provisionamento automático de schemas/layouts padrão para novos tenants

**Feature Branch**: `018-fix-tenant-schema-seed`

**Created**: 2026-07-29

**Status**: Draft

**Input**: User description: "Corrigir bug conhecido: tenants criados via fluxo de convite (US1 da feature 017-tenant-admin-onboarding) não recebem SchemaConfig/LayoutConfig padrão (nota fiscal, fatura de água/condomínio, fatura de energia). Hoje esses defaults só são populados para o tenant seedado no primeiro boot. O fluxo real de provisionamento de tenant cria o Tenant, o schema Postgres e o convite de admin, mas nunca seeda schemas/layouts — então tenants novos ficam sem SchemaConfig/LayoutConfig, o que provavelmente quebra o pipeline de extração de documentos para eles. Existe também código morto/quebrado (ensure_default_schemas) que tentava resolver isso e nunca funcionou, silenciosamente engolido por um except genérico."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tenant novo pronto para extrair documentos desde o primeiro dia (Priority: P1)

Um operador cria um novo tenant através do fluxo de onboarding (convite de admin). Assim que o tenant é provisionado, ele já deve ter disponíveis os tipos de documento padrão da plataforma (nota fiscal, fatura de água/condomínio, fatura de energia), sem qualquer passo manual adicional do operador ou do administrador convidado.

**Why this priority**: Sem isso, todo tenant novo nasce quebrado — o admin convidado ativa a conta, mas não consegue extrair nenhum documento até que alguém rode manualmente um seed. Isso é a funcionalidade central da plataforma (extração de documentos) ficando indisponível por um bug de provisionamento invisível.

**Independent Test**: Provisionar um novo tenant via fluxo de convite (US1 de 017) e, sem nenhuma ação manual adicional, confirmar que o tenant tem os tipos de documento padrão disponíveis para envio/extração.

**Acceptance Scenarios**:

1. **Given** um operador com permissão para gerenciar tenants, **When** ele cria um novo tenant informando nome/slug e dados do admin, **Then** o tenant criado já possui os tipos de documento padrão (nota fiscal, fatura de água/condomínio, fatura de energia) disponíveis para uso, sem intervenção manual.
2. **Given** um administrador que acabou de ativar a conta via convite, **When** ele acessa a área de envio/validação de documentos do seu tenant, **Then** os tipos de documento padrão aparecem disponíveis para seleção, igual a qualquer outro tenant da plataforma.

---

### User Story 2 - Ambiente existente não perde nem duplica configuração ao aplicar a correção (Priority: P2)

Um operador da plataforma já tem tenants em produção — alguns criados no primeiro boot (com os defaults) e outros criados via convite (sem os defaults, por causa do bug). Ao aplicar a correção, os tenants que já têm os defaults não devem ser afetados (nem duplicados, nem sobrescritos de forma destrutiva), e os tenants que estão sem devem passar a ter.

**Why this priority**: Sem uma forma de sanar tenants já existentes que nasceram sem os defaults, a correção só previne o problema para o futuro — os tenants atualmente quebrados continuam quebrados. Isso é secundário ao fluxo de criação (P1), mas necessário para resolver o débito técnico já acumulado.

**Independent Test**: Rodar a operação de correção/backfill contra um ambiente com tenants mistos (com e sem defaults) e confirmar que todos passam a ter exatamente um conjunto de tipos de documento padrão, sem duplicação nem erro nos que já tinham.

**Acceptance Scenarios**:

1. **Given** um tenant que já possui os tipos de documento padrão, **When** a operação de correção é executada, **Then** o tenant continua com exatamente um conjunto de tipos de documento padrão (nenhuma duplicata é criada).
2. **Given** um tenant criado via convite antes da correção (sem tipos de documento padrão), **When** a operação de correção é executada, **Then** o tenant passa a ter os mesmos tipos de documento padrão que qualquer tenant novo.

---

### Edge Cases

- O que acontece se a criação do tenant (schema Postgres + registro) for bem-sucedida, mas o provisionamento dos tipos de documento padrão falhar no meio do processo? O tenant não deve ficar em um estado ambíguo (parcialmente configurado) sem sinalização clara para o operador.
- O que acontece se um tenant já tiver tipos de documento customizados com o mesmo nome/identificador de um tipo padrão (conflito de nomenclatura)? O provisionamento não deve sobrescrever configuração já existente do tenant.
- O que acontece se dois tenants forem criados simultaneamente (concorrência)? Cada um deve receber seu próprio conjunto de tipos de documento padrão sem interferência entre si.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE garantir que todo tenant, ao ser criado através do fluxo de provisionamento (convite de admin), receba automaticamente os tipos de documento padrão da plataforma (nota fiscal, fatura de água/condomínio, fatura de energia) — sem exigir nenhuma ação manual de operador ou administrador.
- **FR-002**: O sistema DEVE aplicar essa mesma lógica de provisionamento de defaults tanto para o tenant inicial da plataforma (primeiro ambiente) quanto para qualquer tenant criado posteriormente, usando uma única fonte de verdade para o conjunto de tipos de documento padrão (evitando duas implementações divergentes que podem ficar dessincronizadas).
- **FR-003**: O sistema DEVE fornecer uma forma de aplicar retroativamente os tipos de documento padrão a tenants já existentes que foram criados antes desta correção e que estão sem eles.
- **FR-004**: A aplicação retroativa (FR-003) DEVE ser idempotente — executá-la múltiplas vezes, ou sobre um tenant que já possui os defaults, não deve criar duplicatas nem sobrescrever configuração já existente do tenant.
- **FR-005**: O sistema DEVE remover ou substituir por uma implementação funcional qualquer mecanismo de provisionamento de defaults que hoje está quebrado e falha silenciosamente, para que uma falha real nesse processo não continue passando despercebida.
- **FR-006**: Se o provisionamento dos tipos de documento padrão falhar durante a criação de um novo tenant, o sistema DEVE tornar essa falha visível (ao invés de mascará-la) para que o problema possa ser corrigido, seguindo o mesmo padrão de tratamento de erro já usado no restante do fluxo de criação de tenant.

### Key Entities

- **Tipo de documento padrão (schema + layout)**: definição de um tipo de documento que a plataforma sabe extrair de forma pronta para uso (ex.: nota fiscal, fatura de água/condomínio, fatura de energia) — inclui o schema de extração e o layout associado. É específico por tenant (cada tenant tem sua própria cópia), mas o conjunto padrão inicial é o mesmo para todos.
- **Tenant**: organização isolada dentro da plataforma, com seu próprio espaço de dados e configuração, incluindo seus próprios tipos de documento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos tenants criados através do fluxo de onboarding têm os tipos de documento padrão disponíveis imediatamente após a criação, sem qualquer passo manual.
- **SC-002**: Um administrador recém-ativado consegue enviar e validar um documento de um dos tipos padrão no seu tenant, no mesmo dia em que ativa a conta, sem depender de suporte técnico ou de um script rodado manualmente por alguém da equipe de plataforma.
- **SC-003**: Após a correção retroativa ser aplicada, 100% dos tenants existentes na plataforma (independente de quando/como foram criados) têm exatamente um conjunto de tipos de documento padrão — nenhum tenant sem defaults, nenhum com duplicatas.
- **SC-004**: Não há mais nenhum ponto de falha silenciosa relacionado a provisionamento de tipos de documento padrão — uma falha nesse processo é visível/detectável, não engolida sem rastro.

## Assumptions

- O conjunto de tipos de documento considerados "padrão" continua sendo os três já existentes hoje (nota fiscal, fatura de água/condomínio, fatura de energia); adicionar novos tipos padrão está fora do escopo desta correção.
- Tenants que já customizaram algum tipo de documento com conflito de nome em relação a um tipo padrão são um caso raro/inexistente no ambiente atual; o comportamento exato de resolução de conflito pode ser refinado durante o planejamento técnico, mas não deve resultar em perda de dados do tenant.
- A aplicação retroativa (FR-003) é uma operação executada sob demanda por quem opera a plataforma (não precisa ser automática/contínua), já que o volume de tenants afetados hoje é conhecido e limitado.
- Esta correção não altera o conjunto de permissões, papéis (roles) ou o fluxo de convite/ativação de administrador já implementado em 017-tenant-admin-onboarding — o escopo é estritamente o provisionamento dos tipos de documento padrão.
