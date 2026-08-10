# Feature Specification: Spike de descoberta READ-ONLY da API Condomínios (Superlógica)

**Feature Branch**: `015-superlogica-discovery-spike`

**Created**: 2026-07-22

**Status**: Draft

**Input**: Especificar a ferramenta de descoberta descartável (Fase B) que sonda a API Condomínios do Superlógica em modo read-only, converte as hipóteses técnicas do §7 da Fase A em fato e valida a regra de associação documento↔condomínio antes de firmá-la.

---

## Natureza e Escopo *(mandatory)*

### O que é

Uma **ferramenta de descoberta descartável** (*spike*), executada manualmente por um
engenheiro, cujo único trabalho é:

1. **Converter hipóteses em fato** — cada `[HIP]` do §7 da Fase A ganha um status resolvido
   (confirmado / não-encontrado / diferente do esperado).
2. **Medir a regra de associação** documento↔condomínio por CNPJ contra uma amostra rotulada,
   produzindo um **go/no-go sustentado por métricas** em vez de achismo.

O que persiste é o **relatório de achados**; a ferramenta em si é descartada depois de cumprir
seu papel.

### O que NÃO é

- **Não é uma feature do DocuParse.** Não roda em produção, não é exposta a usuários finais,
  não integra o pipeline de documentos, não tem interface, não persiste nada em banco.
- **Não é a integração (Fase C).** Nenhum comportamento de produção — cache, fila, retry
  robusto, idempotência, webhooks, sincronização agendada — está no escopo.
- **Não é caminho de escrita.** Lançar despesa, anexar PDF e qualquer confirmação que só se
  resolva escrevendo ficam **fora**, deferidos para um passo separado e explicitamente
  autorizado.
- **Não decide políticas humanas.** Nenhum limiar de auto-confirmação da associação é assumido
  ou embutido: a ferramenta **mede e reporta**; a política é decisão humana (H5).
- **Não resolve H1–H8.** As questões de validação humana permanecem abertas; a ferramenta
  apenas opera sobre *defaults assumidos* e registra isso.

### Referências (apontadas, não reproduzidas aqui)

| Documento | Papel |
|---|---|
| [plano-fase-b-spike-descoberta.md](../../../docuparse-project/docs/superlogica/api%20integration%20plan/fase-b-spike/plano-fase-b-spike-descoberta.md) | Requisito de origem (o quê/porquê + tarefas por fase) |
| [discovery_spike.py](../../../docuparse-project/docs/superlogica/api%20integration%20plan/fase-b-spike/ferramenta/discovery_spike.py) | Comportamento de referência já implementado e testado |
| [README-discovery-spike.md](../../../docuparse-project/docs/superlogica/api%20integration%20plan/fase-b-spike/ferramenta/README-discovery-spike.md) | Contratos operacionais (credenciais, amostra, saídas) |
| [estudo-api-superlogica-condominios-docuparse.md](../../../docuparse-project/docs/superlogica/api%20integration%20plan/fase-a-estudo/estudo-api-superlogica-condominios-docuparse.md) | **§7** — as hipóteses que este spike resolve |
| [pontos-a-esclarecer-validacao-humana.md](../../../docuparse-project/docs/superlogica/api%20integration%20plan/fase-a-estudo/pontos-a-esclarecer-validacao-humana.md) | **H1–H8** — decisões humanas em aberto |

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Verificação offline de sanidade (Priority: P1)

O engenheiro precisa confirmar que a lógica interna da ferramenta (validação de CNPJ,
mascaramento de PII, descoberta de nome de campo, cálculo de métricas) está correta **antes**
de gastar uma chamada de API ou expor credenciais.

**Why this priority**: é a única execução que não depende de credencial, rede ou amostra.
Sem ela, qualquer achado posterior fica sob suspeita de erro de cálculo. Entrega valor sozinha:
prova que as funções que sustentam o go/no-go estão corretas.

**Independent Test**: executar o modo de auto-verificação sem credenciais e sem rede;
verificar que todas as checagens passam e que o código de saída reflete o resultado.

**Acceptance Scenarios**:

1. **Given** nenhuma credencial configurada e sem acesso à rede, **When** o operador roda o modo
   de auto-verificação, **Then** as 28 checagens são impressas individualmente como PASS/FAIL,
   um veredito final é exibido e o processo encerra com código 0.
2. **Given** uma regressão em qualquer função pura, **When** o modo de auto-verificação roda,
   **Then** a checagem correspondente é impressa como FAIL e o processo encerra com código
   diferente de 0.
3. **Given** o modo de auto-verificação, **When** ele roda, **Then** **nenhuma** requisição de
   rede é emitida e nenhum arquivo de saída é gravado.

---

### User Story 2 — Smoke check antes da varredura completa (Priority: P1)

Antes de se comprometer com a varredura de todos os controllers, o engenheiro roda a ferramenta
em **modo de teste**, que avalia **somente o endpoint `condominios`** — a entidade central da
associação. Confirma conectividade, autenticação, que o endpoint-núcleo responde e descobre o
**nome do campo de CNPJ** do lado Superlógica.

**Why this priority**: é pré-condição do DoD global. Sem `condominios` respondendo e sem o nome
do campo de CNPJ identificado, a Fase 4 (a que decide tudo) não tem como rodar. Falhar aqui é
barato; falhar depois de uma varredura completa não é.

**Independent Test**: executar em modo de teste com credenciais válidas e verificar que os
achados gerados contêm apenas `condominios`, que o modo está rotulado como "teste" e que o nome
do campo de CNPJ foi identificado.

**Acceptance Scenarios**:

1. **Given** credenciais válidas, **When** o operador roda em modo de teste, **Then** apenas o
   controller `condominios` é sondado, os achados registram o modo como *teste (somente
   condominios)*, e a sonda de anexos é **pulada**.
2. **Given** o modo de teste concluído, **When** o operador lê o relatório, **Then** o **nome**
   do campo que guarda o CNPJ do condomínio está identificado (ex.: um campo em notação
   húngara), junto com uma ressalva de que foi obtido por heurística.
3. **Given** a heurística de nome de campo erra, **When** o operador fixa o nome do campo por
   configuração e roda de novo, **Then** o nome fixado é usado no lugar da heurística.
4. **Given** credenciais ausentes ou incompletas, **When** o operador tenta rodar qualquer modo
   que não seja a auto-verificação, **Then** a execução aborta com mensagem acionável e código
   de saída 2, **sem** emitir nenhuma requisição.

---

### User Story 3 — Varredura completa de descoberta (Fases 0–3) (Priority: P2)

Com o smoke check verde, o engenheiro roda a descoberta completa: modelo de autenticação e de
erro, existência e campos de todos os controllers candidatos, mecânica de filtro/paginação/
data/rate limit, e sonda de anexos na leitura. O resultado reescreve os `[HIP]` do §7 em fato.

**Why this priority**: entrega o corpo do relatório de achados e a **bifurcação de arquitetura**
(existe filtro server-side por CNPJ? se não, sincronização local vira obrigatória), que é a
decisão de maior impacto para a Fase C depois do go/no-go.

**Independent Test**: executar o modo completo sem amostra e verificar que os quatro artefatos
de saída são gravados, que cada controller candidato tem um veredito (existe / não / erro), e
que o relatório mapeia cada bloco ao item correspondente do §7.

**Acceptance Scenarios**:

1. **Given** credenciais válidas, **When** o operador roda o modo completo, **Then** todos os
   controllers candidatos são sondados e cada um recebe um achado com status HTTP, existência,
   nº de registros, nomes de campo e 1 registro de exemplo com PII mascarada.
2. **Given** a sonda de autenticação, **When** ela roda, **Then** o relatório declara se a
   chamada válida autenticou e **por onde o erro chega** — pelo status HTTP, por um envelope no
   corpo da resposta, por ambos, ou indeterminado — testando token inválido e caminho inexistente.
3. **Given** a sonda de filtro por CNPJ, **When** ela roda com um CNPJ real da própria carteira,
   **Then** o relatório conclui explicitamente por uma das alternativas: *existe filtro
   server-side*, *sem filtro → sincronização local obrigatória*, ou *não conclusivo* quando a
   carteira visível for pequena demais para que um filtro pudesse estreitar o resultado; e, se
   não houver CNPJ conhecido, conclui *não testado* com a razão.
4. **Given** a sonda de rate limit, **When** ela roda, **Then** ela usa uma rajada deliberadamente
   pequena, interrompe imediatamente ao receber sinal de limite excedido, e registra os
   cabeçalhos de limite observados (ou a ausência deles).
5. **Given** um controller que não responde ou falha, **When** a varredura continua, **Then** o
   erro é registrado no achado daquele controller e **os demais continuam sendo sondados**.
6. **Given** uma resposta cujo corpo traz envelope de erro, **When** o achado é montado,
   **Then** o envelope é reportado como erro e **não** aparece como registro, campo descoberto
   ou amostra daquele controller.
7. **Given** um controller que responde reclamando de **parâmetro obrigatório faltando**,
   **When** o achado é montado, **Then** ele é registrado como **existente** — reclamar do
   parâmetro prova que o endpoint existe — e a ferramenta testa candidatos até achar o
   parâmetro que faz o endpoint responder com dados, registrando qual funcionou.

---

### User Story 4 — ⭐ Validação da regra de associação (Priority: P1)

Com uma **amostra rotulada** (documentos cujo condomínio correto já é conhecido), o engenheiro
mede se casar o CNPJ do papel-condomínio extraído pelo DocuParse contra a carteira do ERP
realmente acerta o condomínio — e recebe um **go/no-go com números**.

**Why this priority**: é a tarefa que decide se a regra central pode ser firmada. Um resultado
ruim aqui **não é fracasso**: é o achado mais valioso, porque impede construir a integração
sobre uma chave que erra.

**Independent Test**: executar com uma amostra rotulada e verificar que o CSV de associação é
gerado com uma linha por documento, que as métricas de cobertura e precisão são calculadas, e
que o relatório traz um parágrafo de go/no-go com os números.

**Acceptance Scenarios**:

1. **Given** o nome do campo de CNPJ identificado e uma amostra rotulada, **When** a validação
   roda, **Then** um índice `CNPJ normalizado → condomínio` é montado percorrendo as páginas da
   carteira até o teto de páginas configurado, e cada documento da amostra recebe exatamente um
   resultado classificado.
2. **Given** um documento cujo CNPJ casa no índice e cujo condomínio bate com o gabarito,
   **When** classificado, **Then** o resultado é `correto`.
3. **Given** um documento cujo CNPJ casa no índice mas aponta condomínio diferente do gabarito,
   **When** classificado, **Then** o resultado é `ERRADO` e ele conta para a métrica de
   associações erradas — o número de risco financeiro/jurídico.
4. **Given** documentos sem CNPJ, com CNPJ de dígito verificador inválido, ou com CNPJ válido
   ausente da carteira, **When** classificados, **Then** recebem respectivamente `sem_cnpj`,
   `cnpj_invalido` e `sem_match_no_cadastro`, e cada categoria tem sua própria métrica
   percentual.
5. **Given** uma amostra **sem** gabarito, **When** a validação roda, **Then** a cobertura é
   medida mas a precisão é reportada como indisponível, e o go/no-go declara explicitamente que
   a amostra precisa ser rotulada para decidir.
6. **Given** qualquer resultado de métricas, **When** o go/no-go é redigido, **Then** ele
   apresenta os números e afirma que **o limiar de auto-confirmação × revisão humana é decisão
   humana (H5)** — nenhum limiar é aplicado, sugerido como definitivo, ou embutido.
7. **Given** o nome do campo de CNPJ **não** identificado, **When** a validação é solicitada,
   **Then** ela não roda e registra o motivo, orientando a fixar o nome do campo por
   configuração.

---

### User Story 5 — Consolidação dos achados para a Fase C (Priority: P2)

O engenheiro (e quem lê depois dele) precisa de um artefato humano que diga, item por item do
§7, o que virou fato — e que sobreviva ao descarte da ferramenta.

**Why this priority**: é o entregável que persiste. Sem ele, o spike não deixa nada.

**Independent Test**: após qualquer execução real, abrir o relatório e verificar que ele está
organizado por item do §7, que traz o go/no-go (ou a ausência dele, explicitada) e que aponta o
que sobrou para a Fase C.

**Acceptance Scenarios**:

1. **Given** qualquer execução real concluída, **When** os artefatos são gravados, **Then** o
   relatório humano, o arquivo estruturado de achados e o CSV por endpoint existem no diretório
   de saída, e o console indica qual arquivo ler primeiro.
2. **Given** uma execução em que uma fase não rodou, **When** o relatório é gerado, **Then** a
   seção correspondente é **omitida ou explicitamente marcada como não rodada** — nunca
   preenchida com dado inventado.
3. **Given** limitações conhecidas (expiração de token não observável numa execução única,
   ambiguidade `DD/MM` × `MM/DD` só na leitura, confirmação de escrita de anexo), **When** o
   relatório é gerado, **Then** elas aparecem como ressalvas explícitas, não como fatos
   resolvidos.

---

### Edge Cases

- **Credenciais com permissão parcial**: o token herda as permissões do usuário que o criou. Se
  esse usuário não enxerga toda a carteira, a API filtra silenciosamente e o índice de
  condomínios fica incompleto — inflando `sem_match_no_cadastro` sem erro aparente. É
  pré-requisito operacional, não detectável pela ferramenta; deve constar como ressalva do
  relatório.
- **Carteira maior que o teto de páginas**: se a carteira excede o teto configurado, o índice
  fica truncado. O tamanho do índice é reportado para que o operador confirme se bate com a
  carteira real.
- **Campo de CNPJ mal adivinhado**: a heurística escolhe o campo mais frequente cujo valor tem
  14 dígitos — pode acertar um campo alheio (ex.: CNPJ da administradora). O escape hatch de
  fixar o nome por configuração existe justamente para isso, e o relatório sempre marca o nome
  como obtido por heurística.
- **Campo de identificador não descoberto**: o documento casa no índice mas não há identificador
  para comparar com o gabarito; o resultado é classificado à parte
  (`casou_mas_id_field_desconhecido`) em vez de contar falsamente como correto ou errado.
- **API responde HTTP 200 com erro no corpo**: um cliente que só olhasse o status HTTP trataria
  como sucesso com dados vazios. Ambos os sinais são capturados em todo achado.
- **Nenhuma despesa amostrada tem anexo**: a sonda de anexos conclui "nenhum campo óbvio", não
  "não existe anexo" — a diferença é registrada.
- **CNPJ alfanumérico** (rollout brasileiro em andamento): a normalização e validação atuais são
  numéricas; um CNPJ alfanumérico no cadastro seria tratado como ausente/inválido. Limitação
  conhecida e declarada.
- **Rajada da sonda de rate limit**: se o limite for atingido, a sonda para imediatamente para
  não penalizar a credencial do cliente.
- **Amostra malformada ou ilegível**: a validação da regra não deve produzir métricas parciais
  silenciosas — deve falhar de forma visível.

---

## Requirements *(mandatory)*

### Restrições invioláveis (nível Constitution)

- **RI-001 (READ-ONLY absoluto)**: a ferramenta MUST emitir **exclusivamente** requisições de
  leitura (`GET`). Qualquer tentativa de usar outro método MUST ser bloqueada com erro em tempo
  de execução, por guarda no próprio cliente HTTP — não por convenção. Nenhuma execução, em
  hipótese alguma, pode alterar estado no ERP.
- **RI-002 (PII minimizada)**: CPF e CNPJ MUST aparecer mascarados em **toda** saída persistida e
  em logs. Registros crus obtidos da API MUST ser usados apenas em memória (heurística e
  índice) e nunca gravados em disco.
- **RI-003 (sem limiar embutido)**: a ferramenta MUST NOT embutir, assumir ou aplicar qualquer
  limiar de auto-confirmação da associação. Ela mede e reporta; a política é decisão humana (H5)
  e MUST ser declarada como tal no relatório.
- **RI-004 (segredos fora do código)**: credenciais MUST vir de configuração de ambiente. Nenhum
  segredo MUST ser embutido no código ou versionado.
- **RI-005 (escopo travado)**: a ferramenta MUST NOT especificar, implementar ou pressupor a
  integração da Fase C, e MUST NOT tratar H1–H8 como resolvidos.

### Functional Requirements

**Execução e modos**

- **FR-001**: A ferramenta MUST oferecer um **modo de auto-verificação offline** que exercita as
  funções puras (validação/normalização/mascaramento de CNPJ e CPF, descoberta de nome de campo,
  extração de registros de diferentes envelopes, cálculo de métricas) **sem** rede, **sem**
  credenciais e **sem** gravar arquivos, imprimindo cada checagem como PASS/FAIL e encerrando com
  código 0 (todas passaram) ou diferente de 0.
- **FR-002**: A ferramenta MUST oferecer um **modo de teste** que restringe a descoberta ao
  controller `condominios` e **pula a sonda de anexos**, servindo como smoke check.
- **FR-003**: A ferramenta MUST oferecer um **modo completo** (padrão) que sonda todos os
  controllers candidatos definidos pelo §3 da Fase A.
- **FR-004**: O operador MUST poder selecionar um subconjunto de fases a executar, o diretório de
  saída, a URL base, o timeout e o teto de páginas do índice.
- **FR-005**: A validação da regra de associação MUST ser habilitada apenas quando uma amostra
  rotulada for fornecida explicitamente.
- **FR-006**: A ferramenta MUST abortar com mensagem acionável e código de saída 2 quando as
  credenciais obrigatórias não estiverem configuradas, **antes** de qualquer requisição.
- **FR-007**: Reexecutar a ferramenta MUST ser seguro e idempotente do ponto de vista do servidor
  (nenhuma execução muda nada no ERP).
- **FR-008**: Toda requisição emitida MUST ser registrada (destino e latência), permitindo
  auditar depois exatamente o que a ferramenta tocou.

**Fase 0 — autenticação e modelo de erro** *(resolve §7.4)*

- **FR-010**: A ferramenta MUST executar uma chamada válida e reportar se autenticou.
- **FR-011**: A ferramenta MUST forçar uma chamada com credenciais inválidas e uma chamada a um
  caminho inexistente, e MUST classificar **por onde o erro chega**: status HTTP, envelope no
  corpo da resposta, **ambos** (híbrido), ou indeterminado. O caso híbrido é obrigatório porque
  a API observada usa as duas vias ao mesmo tempo — o status diz que falhou, o corpo diz por quê.
- **FR-013**: A ferramenta MUST tratar um envelope de erro no corpo como **erro, nunca como
  registro de dados** — não pode contar como registro, virar campo descoberto, alimentar a
  heurística de nome de campo nem entrar no índice da Fase 4.
- **FR-014**: A ferramenta MUST NOT declarar autenticação bem-sucedida com base apenas na
  ausência de `401`/`403`. Quando o corpo indicar recusa de credencial sob outro status, o
  veredito MUST ser "não autenticou", com o motivo registrado; quando a resposta não permitir
  concluir, o veredito MUST ser explicitamente indeterminado.
- **FR-012**: A ferramenta MUST registrar como ressalva que a **expiração** de credencial não é
  verificável numa execução única.

**Fase 1 — endpoints e campos** *(resolve §7.1, §7.2-campo, §7.8)*

- **FR-015**: A ferramenta MUST enviar os **parâmetros obrigatórios** de cada controller e MUST
  distinguir *"faltou parâmetro"* de *"endpoint não existe"*: uma resposta que reclama de
  parâmetro faltando prova que o controller **existe**. Quando isso ocorrer, a ferramenta MUST
  testar candidatos de parâmetro até obter dados e MUST registrar qual funcionou.
- **FR-016**: A ferramenta MUST desembrulhar envelopes que aninham a entidade sob uma chave com
  o nome dela, em qualquer profundidade, antes de descobrir campos ou montar o índice.
- **FR-017**: A ferramenta MUST redigir, **pelo nome do campo**, valores de campos que aparentem
  credencial (token, senha, secret, chave), independentemente do formato do valor — o cadastro
  do condomínio expõe campos desse tipo, e gravá-los violaria RI-002 e RI-004.
- **FR-018**: Ao descobrir o nome do campo identificador, a ferramenta MUST priorizar o campo que
  identifica **a própria entidade** sobre chaves estrangeiras numéricas do mesmo registro.
  Escolher a errada corromperia o índice da Fase 4 **em silêncio**: o CNPJ casaria, mas o
  identificador comparado ao gabarito seria de outra entidade.
- **FR-020**: Para cada controller candidato, a ferramenta MUST produzir um achado contendo:
  identificação do controller, destino consultado, parâmetros usados, status HTTP, status do
  envelope no corpo, veredito de existência, nº de registros, nomes de campo descobertos, 1
  registro de exemplo com PII mascarada, indícios de paginação e erro (se houve).
- **FR-021**: A ferramenta MUST descobrir o **nome** do campo que guarda o CNPJ do condomínio no
  cadastro (não o valor), escolhendo o campo mais frequente cujo valor tenha 14 dígitos.
- **FR-022**: A ferramenta MUST descobrir o **nome** do campo identificador do condomínio.
- **FR-023**: O operador MUST poder **sobrescrever** ambos os nomes por configuração, quando a
  heurística errar.
- **FR-024**: Todo nome descoberto por heurística MUST ser marcado como tal no relatório, com
  indicação de confirmá-lo por inspeção do tráfego do ERP.

**Fase 2 — mecânica** *(resolve §7.2-filtro, §7.5, §7.6, §7.7)*

- **FR-030**: A ferramenta MUST testar um conjunto de parâmetros candidatos de **filtro
  server-side por CNPJ** usando um CNPJ real da própria carteira, e MUST concluir de forma
  explícita: *existe filtro* ou *sem filtro → sincronização local obrigatória*. Se não houver
  CNPJ conhecido, MUST concluir *não testado* com a razão. Quando a carteira visível tiver menos
  de 2 condomínios, a ferramenta MUST concluir **não conclusivo** — um filtro não teria como
  estreitar o resultado, e declarar "sem filtro" ali seria falsa confiança numa das decisões
  mais caras da Fase C. A mesma ressalva MUST acompanhar a conclusão de paginação.
- **FR-031**: A ferramenta MUST testar parâmetros candidatos de **itens por página** e reportar,
  para cada um, se o limite foi respeitado; e MUST reportar o nº de registros obtidos numa
  requisição de referência.
- **FR-032**: A ferramenta MUST observar os **formatos de data** presentes nas respostas
  (ISO × com barra), com exemplos, e MUST registrar que o formato com barra **não** distingue
  `DD/MM` de `MM/DD` só na leitura.
- **FR-033**: A ferramenta MUST sondar **rate limit** com uma rajada deliberadamente pequena,
  capturar cabeçalhos de limite, interromper ao primeiro sinal de limite excedido, e recomendar
  throttle conservador.
- **FR-034**: A ferramenta MUST registrar que a confirmação de **requisições em lote** depende do
  caminho de escrita e está **deferida** — não simulada.

**Fase 3 — anexos na leitura** *(resolve §7.3)*

- **FR-040**: A ferramenta MUST inspecionar despesas existentes em busca de campos candidatos a
  anexo e MUST classificar o **formato aparente** de cada valor (URL, provável base64,
  identificador numérico, ou outro com tamanho).
- **FR-041**: A ferramenta MUST distinguir "nenhum campo óbvio encontrado nas despesas amostradas"
  de "anexo não existe", e MUST registrar que confirmar a **escrita** de anexo só se resolve
  escrevendo — passo autorizado à parte.
- **FR-042**: Esta fase MUST ser pulada no modo de teste.

**Fase 4 — ⭐ regra de associação** *(resolve §7 ⭐ e o risco do §5)*

- **FR-050**: A ferramenta MUST montar um índice `CNPJ normalizado → condomínio` percorrendo a
  carteira de forma paginada até o teto de páginas configurado, e MUST reportar o tamanho do
  índice obtido.
- **FR-051**: Para cada documento da amostra, a ferramenta MUST normalizar o CNPJ do
  papel-condomínio, **validar os dígitos verificadores localmente** e buscá-lo no índice.
- **FR-052**: Cada documento MUST receber exatamente um resultado dentre: `sem_cnpj`,
  `cnpj_invalido`, `sem_match_no_cadastro`, `casou_mas_id_field_desconhecido`,
  `casou_sem_gabarito`, `correto`, `ERRADO`.
- **FR-053**: A ferramenta MUST calcular e reportar: **cobertura** (% que casou sobre o total),
  **precisão** (% correto entre os que casaram e têm gabarito), **% sem CNPJ**, **% com CNPJ
  inválido**, **% sem match no cadastro** e **% de associações erradas**.
- **FR-054**: Quando a amostra não trouxer gabarito, a precisão MUST ser reportada como
  indisponível — nunca estimada — e o go/no-go MUST orientar a rotular a amostra.
- **FR-057**: Quando o índice tiver **menos de 2 condomínios**, a ferramenta MUST reportar
  cobertura, % sem CNPJ e % CNPJ inválido normalmente, mas MUST declarar **precisão e % de
  associações erradas como não mensuráveis nesse ambiente** — sem outro condomínio no índice, a
  associação errada não tem como se manifestar, e um `% ERRADO` de zero seria artefato do
  ambiente, não evidência de acerto. O go/no-go MUST ser explicitamente retido nesse caso.
- **FR-055**: O go/no-go MUST apresentar os números, MUST destacar o **% de associações erradas**
  como o número de risco financeiro/jurídico, e MUST declarar que o limiar é decisão humana (H5).
- **FR-056**: A ferramenta MUST recusar-se a rodar esta fase quando o nome do campo de CNPJ não
  tiver sido identificado, registrando o motivo e a ação corretiva.

**Fase 5 — consolidação**

- **FR-060**: A ferramenta MUST gravar no diretório de saída os artefatos abaixo (schemas em
  *Contratos de dados*):
  - `RELATORIO-ACHADOS.md` — **o relatório humano**: narrativa em Markdown, feita para ser lida
    por uma pessoa, organizada por item do §7 da Fase A. É o artefato que persiste depois do
    descarte da ferramenta e o insumo do `Specify` da Fase C;
  - `achados.json` — os mesmos achados em formato estruturado, para consumo por máquina;
  - `achados.csv` — uma linha por controller sondado;
  - `associacao.csv` — uma linha por documento da amostra; gravado **apenas** quando a Fase 4
    rodou.
- **FR-061**: O `RELATORIO-ACHADOS.md` MUST estar organizado por item do §7 da Fase A, MUST
  indicar o modo de execução, a URL base e o instante de geração, e MUST conter o parágrafo de
  go/no-go da regra de associação (ou declarar explicitamente que a Fase 4 não rodou).
- **FR-062**: Seções de fases não executadas MUST ser omitidas ou marcadas explicitamente como
  não rodadas.
- **FR-063**: Ao terminar, a ferramenta MUST informar no console onde os achados foram gravados e
  apontar o `RELATORIO-ACHADOS.md` como **o arquivo a ler primeiro**.

---

## Contratos de dados *(mandatory)*

Consolidados aqui — esta seção é a fonte única dos formatos de entrada e saída.

### Entrada — amostra rotulada (*ground truth*)

Lista de objetos, um por documento.

| Campo | Obrigatório | Significado |
|---|---|---|
| `doc_id` | sim | Identificador livre do documento |
| `tipo` | recomendado | Tipo do documento; permite segmentar as métricas por tipo |
| `cnpj_papel_condominio` | sim | CNPJ do **lado condomínio** já extraído pelo DocuParse; com ou sem máscara; vazio quando ausente. É a **chave de busca** — vai contra o campo de CNPJ do cadastro |
| `condominio_esperado_id` | para medir precisão | O **identificador** do condomínio correto no ERP (**gabarito**) — mesma natureza do campo identificador descoberto na Fase 1, **nunca um CNPJ**. Sem ele, mede-se apenas cobertura |

> ⚠️ O gabarito MUST vir de fonte **independente da chave sob teste** — do arquivamento manual já
> correto no ERP, ou da origem do documento. Obtê-lo casando CNPJ produziria a resposta com a
> mesma chave que está sendo avaliada, e a precisão medida não significaria nada.

Exemplo mínimo:

```json
[
  {"doc_id": "nf-0001",   "tipo": "nota_fiscal",   "cnpj_papel_condominio": "11.222.333/0001-81", "condominio_esperado_id": "42"},
  {"doc_id": "agua-0003", "tipo": "conta_consumo", "cnpj_papel_condominio": "",                   "condominio_esperado_id": "57"}
]
```

### Saída 1 — achados estruturados (`achados.json`)

Documento único, legível por máquina, com todas as fases executadas.

| Chave | Conteúdo |
|---|---|
| `base_url` | URL base efetivamente usada |
| `gerado_em` | Instante da execução |
| `modo` | `completo` ou `teste (somente condominios)` |
| `fase0_auth_erro` | `chamada_valida` (status HTTP, status do envelope, `body_error`, `autenticou` tri-estado + `motivo`), `token_invalido` e `path_inexistente` (idem + `erro_via` ∈ `http_status` \| `envelope_no_corpo` \| `http_status+envelope_no_corpo` \| `indeterminado`), `nota` |
| `fase1_endpoints` | `endpoints` (mapa controller → achado), `campo_cnpj_condominio`, `campo_id_condominio`, `nota_campos` |
| `fase2_mecanica` | `filtro_cnpj` (por parâmetro candidato: nº de registros e se estreitou; + `conclusao`), `paginacao` (baseline e, por parâmetro candidato, se respeitou o limite), `data.formatos_observados` (contagens, exemplos, nota), `rate_limit` (status observados, cabeçalhos de limite, se atingiu o limite, nota), `lote` (nota de deferimento) |
| `fase3_anexos` | `num_despesas_amostradas`, `campos_suspeitos_anexo` (campo → formato aparente), `conclusao`, `nota_escrita` |
| `fase4_associacao` | `index_size`, `counters`, `metrics`, `rows`, `go_no_go` — ou `erro` quando não pôde rodar |

**Achado por endpoint** (unidade reutilizada em `fase1_endpoints.endpoints`):
`controller`, `url`, `params`, `http_status`, `body_status`, `body_error` (`campo` + `valor`, ou
nulo), `exists`, `num_records`, `fields`, `sample` (1 registro **com PII mascarada**),
`pagination_hint`, `error`.

### Saída 2 — achados por endpoint (`achados.csv`)

Uma linha por controller sondado.

| Coluna | Conteúdo |
|---|---|
| `controller` | Nome do controller |
| `http_status` | Status HTTP da sonda |
| `exists` | Veredito de existência |
| `num_records` | Nº de registros retornados |
| `num_fields` | Nº de campos descobertos |
| `body_error` | Mensagem de erro vinda no corpo da resposta, se houve |
| `error` | Erro capturado, se houve |

### Saída 3 — associação por documento (`associacao.csv`)

Uma linha por documento da amostra. Gerado **apenas** quando a Fase 4 rodou.

| Coluna | Conteúdo |
|---|---|
| `doc_id` | Identificador do documento |
| `tipo` | Tipo do documento |
| `cnpj_extraido` | CNPJ do papel-condomínio, **mascarado** |
| `condominio_casado_id` | Identificador do condomínio encontrado no índice (vazio se não casou) |
| `condominio_esperado_id` | Gabarito (vazio se a amostra não for rotulada) |
| `resultado` | `sem_cnpj` \| `cnpj_invalido` \| `sem_match_no_cadastro` \| `casou_mas_id_field_desconhecido` \| `casou_sem_gabarito` \| `correto` \| `ERRADO` |

### Saída 4 — relatório humano (`RELATORIO-ACHADOS.md`)

Leitura obrigatória; é o artefato que persiste depois do descarte da ferramenta.

| Seção | Conteúdo |
|---|---|
| Cabeçalho | Instante de geração, URL base, modo de execução |
| §7.4 | Autenticação e modelo de erro, com ressalva sobre expiração |
| §7.1 / §7.8 | Tabela controller × existe × HTTP × nº de campos; nome do campo de CNPJ e do identificador, marcados como heurística |
| §7.2 / §7.5 / §7.6 / §7.7 | Conclusão da bifurcação do filtro, baseline de paginação, formatos de data, rate limit, deferimento do lote |
| §7.3 | Conclusão sobre anexos na leitura e lacuna de escrita |
| ⭐ §5 / §7 ⭐ | Tamanho do índice, métricas e o parágrafo de **go/no-go** |
| Fecho | Encaminhamento: atualizar `[HIP]→[DOC]` na Fase A e alimentar o `Specify` da Fase C |

### Máscaras de PII

| Dado | Formato mascarado | Quando não se aplica |
|---|---|---|
| CNPJ (14 dígitos) | Dois primeiros dígitos + meio oculto + dois últimos dígitos | Valor sem 14 dígitos → marcador opaco |
| CPF (11 dígitos) | Três primeiros dígitos + meio oculto + dois últimos dígitos | Valor sem 11 dígitos → marcador opaco |

---

## Pré-requisitos de execução *(mandatory)*

Sem os três itens abaixo a ferramenta até *roda*, mas não *resolve* nada — apenas reformula as
hipóteses. São os primeiros bloqueios a destravar.

1. **Credencial de API que enxerga a carteira inteira.** Um par de tokens de aplicação criado por
   um usuário com visibilidade de **todos** os condomínios — a credencial herda as permissões de
   quem a criou, e uma credencial parcial faz a API filtrar **silenciosamente**, corrompendo o
   índice e, com ele, todas as métricas da Fase 4. Preferir ambiente de trial/sandbox; contra
   produção é aceitável porque a ferramenta só lê (RI-001).
2. **Amostra rotulada.** Documentos cujo condomínio correto já é conhecido. Caminho limpo de
   obtenção: documentos **já corretamente arquivados manualmente** no ERP, usando a associação
   existente como gabarito. Começar pelos tipos já confirmados: nota fiscal, boleto e conta de
   consumo (H7). Sem rótulo, mede-se "casou", não "acertou" — e é o "errou" que importa.
3. **Saída do DocuParse para esses mesmos documentos.** Os campos extraídos **com o papel do
   CNPJ** (tomador, fornecedor, pagador, titular…). É daqui que sai o `cnpj_papel_condominio` de
   cada linha da amostra.

Configuração operacional (via ambiente): credenciais obrigatórias; URL base, timeout, teto de
páginas do índice e sobrescrita dos nomes de campo são opcionais e têm padrão.

---

## Key Entities

- **Controller candidato**: uma entidade da API a sondar (condomínios, unidades, condôminos/
  contatos de unidade, fornecedores, despesas, cobranças, plano de contas, notas fiscais). Todos
  são hipótese até a sonda dizer o contrário.
- **Achado de endpoint**: o veredito de uma sonda sobre um controller — existência, sinais de
  erro (HTTP e envelope), campos descobertos, exemplo mascarado, indícios de paginação.
- **Nome do campo de CNPJ** (*chave de busca*): o **nome da coluna** onde o cadastro do condomínio
  guarda o CNPJ. É o elo que falta: o *valor* já vem do DocuParse; sem o *nome*, não há como
  montar o índice. É por onde se **entra** na busca.
- **Nome do campo identificador** (*resposta*): o **nome da coluna** que guarda a chave primária
  do condomínio no ERP. É o que se **obtém** do match, o que é comparado com o gabarito da
  amostra, e o que a integração usará depois para operar sobre aquele condomínio — o CNPJ não
  serve para isso. Confundir os dois campos inverte entrada e saída da regra de associação.
- **Índice de condomínios**: mapa `CNPJ normalizado → condomínio` construído a partir da carteira
  paginada. Existe apenas em memória durante a execução.
- **Documento da amostra**: uma linha do *ground truth* — identificador, tipo, CNPJ do
  papel-condomínio e (idealmente) o condomínio correto conhecido.
- **Resultado de associação**: a classificação de um documento contra o índice e o gabarito.
- **Métricas da regra**: cobertura, precisão, % sem CNPJ, % CNPJ inválido, % sem match, % errado.
- **Go/No-Go**: o parágrafo de recomendação sustentado pelas métricas — sem limiar embutido.
- **Relatório de achados**: o artefato que persiste; reescreve os `[HIP]` do §7 em fato.

---

## Success Criteria *(mandatory)*

### Definition of Done do spike

- **SC-001**: A auto-verificação offline executa **28 checagens** e todas passam, sem rede, sem
  credenciais e sem gravar arquivos.
- **SC-002**: O smoke check passa antes da varredura completa: `condominios` responde, a
  credencial autentica e o nome do campo de CNPJ é identificado.
- **SC-003**: **100%** dos itens do §7 da Fase A têm status resolvido no relatório — confirmado,
  não-encontrado, diferente do esperado, ou explicitamente marcado como não verificável nesta
  execução. Nenhum item fica sem veredito.
- **SC-004**: A bifurcação do filtro server-side por CNPJ está **decidida** no relatório, com uma
  das duas conclusões explícitas — porque ela define se a sincronização local da carteira é
  obrigatória.
- **SC-005**: O modelo de autenticação e de erro está descrito, incluindo por onde o erro chega
  (status HTTP × envelope no corpo).
- **SC-006**: A regra de associação tem **go/no-go acompanhado de métricas numéricas** —
  cobertura, precisão, % sem CNPJ, % CNPJ inválido, % sem match e % errado — e **nenhum** limiar
  de auto-confirmação foi assumido pela ferramenta. Em ambiente com índice de menos de 2
  condomínios, este critério é atendido pela **retenção explícita** do go/no-go (FR-057): as
  métricas de discriminação saem marcadas como não mensuráveis, nunca como zero.
- **SC-007**: Os quatro artefatos de saída estão persistidos e são autossuficientes: um leitor que
  nunca viu a ferramenta entende os achados só com eles. A ferramenta pode ser descartada sem
  perda de informação.
- **SC-008**: **Zero** requisições de escrita foram emitidas em qualquer execução — verificável
  pelo registro de chamadas, que contém exclusivamente leituras.
- **SC-009**: **Zero** ocorrências de CPF ou CNPJ não mascarados nos quatro artefatos de saída e
  nos logs.
- **SC-010**: Uma execução completa contra uma carteira de dezenas a poucas centenas de
  condomínios conclui em uma única sessão de trabalho (ordem de minutos), sem atingir rate limit.
- **SC-011**: O relatório declara explicitamente suas limitações — expiração de credencial não
  observável numa execução única, ambiguidade `DD/MM` × `MM/DD` na leitura, confirmação de
  escrita de anexo deferida, nomes obtidos por heurística, CNPJ alfanumérico não suportado.
- **SC-012**: O relatório lista o que **sobrou** para a Fase C, sem especificá-la.

### Critério de go/no-go da regra de associação

O go/no-go é uma **recomendação com números**, não um veredito automático:

| Sinal medido | Como é reportado |
|---|---|
| **Cobertura** (% que casou por CNPJ) | Número; indica quanto da amostra a regra sequer alcança |
| **Precisão** (% correto entre os que casaram, contra o gabarito) | Número; indisponível — nunca estimada — se a amostra não tiver gabarito |
| **% de associações erradas** | Número; destacado como o **risco financeiro/jurídico**. Se maior que zero, tratado como bloqueador até ser entendido caso a caso |
| **% sem CNPJ / CNPJ inválido / sem match** | Números; compõem a taxonomia de modos de falha |
| **Limiar de auto-confirmação** | **Não definido pela ferramenta** — decisão humana (H5), declarada como tal |

Precisão baixa **não é fracasso do spike**: é o resultado mais valioso, porque manda repensar a
chave de associação **antes** de construir a integração.

---

## Assumptions

**Defaults assumidos de H1–H8** (para o spike poder rodar sem travar; cada um permanece aberto):

- **H1** — Escopo restrito à descoberta read-only; caminho de escrita fora.
- **H2** — Superlógica é a fonte da verdade; a ferramenta apenas lê dela.
- **H3** — Uma administradora, um par de credenciais; configuração única.
- **H4** — Volume de dezenas a centenas de condomínios; ainda assim a paginação é testada.
- **H5** — **Nenhum** limiar assumido; a ferramenta só reporta métricas.
- **H6** — Idempotência fora de escopo (é preocupação de escrita).
- **H7** — Amostra começa por nota fiscal, boleto e conta de consumo.
- **H8** — PII minimizada: amostra reduzida/anonimizada; as próprias ações são logadas.

**Outras premissas**:

- A ferramenta é **executada manualmente por um engenheiro**, com credenciais fornecidas
  pontualmente; não é agendada, não roda em CI e não é orquestrada por nenhum serviço do
  DocuParse.
- A execução recomendada é sequencial: auto-verificação offline → smoke check → varredura
  completa → validação da regra com amostra.
- A validação da regra depende da descoberta de campos ter rodado na mesma execução (ou do nome
  do campo ter sido fixado por configuração).
- A conferência cruzada por **inspeção do tráfego do ERP** (a interface usa a mesma API) é
  atividade manual complementar, fora do escopo da ferramenta, e é o caminho recomendado para
  confirmar nomes descobertos por heurística e resolver controllers não encontrados.
- O CNPJ tratado é numérico; o rollout de CNPJ alfanumérico é limitação declarada, não tratada.
- Os artefatos de saída seguem o padrão CSV-intermediário já adotado no projeto, para serem
  auditáveis e servirem de insumo direto às fases seguintes.

**Dependências e lacunas conhecidas**:

- O material de referência menciona um arquivo de exemplo de variáveis de ambiente que **não
  existe** no repositório; ele precisa ser criado junto com a ferramenta para fechar o contrato
  de configuração descrito no README.
- Sem credencial com visibilidade total ou sem amostra rotulada, a ferramenta **não resolve** —
  destravar esses dois pré-requisitos tem precedência sobre qualquer trabalho de implementação.
