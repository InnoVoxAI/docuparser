# Feature Specification: Fase B — Download e organização dos arquivos

**Feature Branch**: `013-file-download-organization`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Gere uma nova spec para docuparse-project/scripts/SELECT/downloads/fases/fase_b_download.md — depende da spec 012 (consome o mapa_download.csv); desenvolver após a Fase A."

## Contexto

A **Fase A** (spec 012) descobriu todos os arquivos de despesas a baixar e produziu o **mapa de download** (`mapa_download.csv`) — uma linha por arquivo, já classificada por categoria/pasta, com a URL de download e o nome real do arquivo. Nada foi baixado lá.

A **Fase B** (esta feature) faz o **trabalho pesado**: lê o mapa, baixa cada arquivo (um GET público no Superlógica, sem login), salva-o na pasta de destino já decidida, e produz o **CSV final** — o entregável central do projeto. A separação em duas fases isola a parte frágil (extração de PDF) da parte demorada (download): se o download falhar no meio, a Fase B **retoma de onde parou** sem reprocessar nenhum PDF.

Esta feature **depende da Fase A** e deve ser desenvolvida **depois** dela; a interface entre as duas é o contrato do `mapa_download.csv` (ver spec 012, `contracts/mapa-download.md`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Baixar e organizar os arquivos do mapa (Priority: P1)

O operador aponta a Fase B para o mapa produzido pela Fase A e obtém, em disco, **todos os arquivos baixados e organizados em pastas por categoria** (`downloads/<pasta_destino>/<nome_arquivo>`). Cada linha do mapa com status pendente vira um arquivo salvo com o nome real.

**Why this priority**: É a razão de existir da Fase B e o produto tangível do projeto — transformar o catálogo (mapa) nos arquivos de fato, organizados para uso contábil. É o menor incremento que já entrega valor.

**Independent Test**: Dado um mapa com N linhas pendentes de URLs válidas, executar a Fase B e verificar que N arquivos são salvos nos caminhos `downloads/<pasta_destino>/<nome_arquivo>` corretos.

**Acceptance Scenarios**:

1. **Given** um mapa com linhas pendentes, **When** a Fase B executa, **Then** cada arquivo é baixado por GET simples na `url_download` e salvo em `downloads/<pasta_destino>/`.
2. **Given** uma pasta de destino que ainda não existe, **When** o arquivo é salvo, **Then** o diretório é criado (inclusive `_A_Revisar`).
3. **Given** uma linha cujo `nome_arquivo` está vazio, **When** o arquivo é salvo, **Then** um nome de fallback determinístico é usado.
4. **Given** o mapa de entrada ausente ou ilegível, **When** a Fase B inicia, **Then** ela aborta com mensagem clara instruindo rodar a Fase A primeiro.

---

### User Story 2 - Nunca salvar arquivo corrompido, truncado ou sobrescrito (Priority: P1)

Só é gravado em disco o que é, comprovadamente, o arquivo esperado e completo. Uma resposta que não é o arquivo (página de erro/expiração), um download interrompido no meio, ou uma colisão de nome **nunca** resultam em um arquivo inválido ou na perda silenciosa de outro.

**Why this priority**: Integridade dos dados. Sem isso, o entregável ficaria contaminado por arquivos-lixo (HTML de erro salvo como “.pdf”), arquivos pela metade, ou arquivos sobrescritos — corrompendo exatamente o resultado que a Fase B existe para produzir.

**Independent Test**: Simular (a) uma resposta HTTP 200 cujo corpo não é um PDF, (b) uma conexão que cai no meio do download, e (c) dois arquivos com o mesmo nome na mesma pasta — e confirmar que nenhum arquivo inválido/truncado é salvo e que nenhum arquivo é sobrescrito.

**Acceptance Scenarios**:

1. **Given** uma resposta 200 cujo conteúdo é uma página HTML de erro (não um PDF), **When** a Fase B a processa, **Then** o conteúdo é rejeitado, nada é salvo e a linha vira erro registrado.
2. **Given** um download interrompido no meio, **When** a execução para, **Then** não há arquivo com o nome definitivo e conteúdo incompleto (gravação atômica).
3. **Given** um arquivo com nome idêntico ao de outro já salvo na mesma pasta, **When** o segundo é gravado, **Then** ele recebe um nome alternativo **determinístico** e o primeiro não é sobrescrito.

---

### User Story 3 - CSV final incremental (entregável central) (Priority: P1)

Cada arquivo baixado com sucesso é registrado **imediatamente** numa linha do CSV final, contendo o nome do arquivo salvo, o hyperlink de origem, a categoria e o caminho local. Esse CSV é o entregável que consolida o resultado do projeto.

**Why this priority**: É o produto de consumo humano/contábil do projeto. Escrever incrementalmente garante que uma interrupção não apague o registro do que já foi baixado.

**Independent Test**: Baixar algumas linhas, interromper, e confirmar que o CSV final em disco já contém exatamente as linhas concluídas até ali, cada uma uma única vez.

**Acceptance Scenarios**:

1. **Given** um download concluído com sucesso, **When** ele termina, **Then** uma linha correspondente é acrescentada ao CSV final imediatamente (nome, hyperlink de origem, categoria, caminho local).
2. **Given** a execução interrompida no meio, **When** o operador inspeciona o CSV final, **Then** ele contém todas as linhas concluídas até o ponto de interrupção.
3. **Given** uma reexecução, **When** uma linha já concluída é reencontrada, **Then** ela não é registrada de novo no CSV final.

---

### User Story 4 - Execução interrompível e retomável, sem retrabalho (Priority: P1)

A execução pode ser interrompida e retomada a qualquer momento. Ao retomar, a Fase B **pula** o que já foi baixado (status concluído + arquivo presente em disco) e processa apenas o que falta, sem rebaixar nem duplicar.

**Why this priority**: O volume de downloads é grande e sujeito a falhas de rede/expiração. Sem retomada idempotente, uma interrupção obrigaria a rebaixar tudo e arriscaria duplicatas — inviável na prática.

**Independent Test**: Rodar até baixar parte das linhas, interromper, e rodar de novo; confirmar que os arquivos já baixados não são baixados de novo e que o CSV final não ganha duplicatas.

**Acceptance Scenarios**:

1. **Given** uma linha com status concluído e o arquivo presente no caminho esperado, **When** a Fase B é reexecutada, **Then** essa linha é pulada (não rebaixa).
2. **Given** uma linha que falhou anteriormente, **When** a Fase B é reexecutada, **Then** ela é tentada de novo.
3. **Given** a execução retomada, **When** ela conclui, **Then** nenhum arquivo já baixado foi rebaixado e nenhuma linha foi duplicada no CSV final.

---

### User Story 5 - Resiliência, relatório de erros e sinal de expiração (Priority: P2)

Nenhuma linha ruim derruba a execução: falhas são registradas e a execução continua (fail-soft). Erros de HTTP e bloqueios temporários são reprocessados com pausa e recuo; após esgotar, a linha vira erro registrado. Casos de **provável expiração** das URLs (accesskey/hash) são **sinalizados explicitamente**, recomendando re-rodar a Fase A para renovar as URLs.

**Why this priority**: Observabilidade e operação. É o que torna a Fase B utilizável em cenários reais (rede instável, execução muito depois da Fase A) e dá ao operador um caminho claro de recuperação. É P2 porque depende de US1 existir.

**Independent Test**: Simular erros HTTP (incluindo o padrão de expiração) e rate limiting; confirmar que a execução continua, que as falhas vão para o relatório de erros com motivo e nº de tentativas, e que os casos de expiração são destacados.

**Acceptance Scenarios**:

1. **Given** uma URL que retorna erro HTTP repetidamente, **When** as tentativas se esgotam, **Then** a linha vira erro no relatório (URL, motivo, tentativas) e a execução continua.
2. **Given** um padrão de resposta compatível com `accesskey`/`hash` expirado, **When** ele ocorre, **Then** o relatório sinaliza "possível expiração" e recomenda re-rodar a Fase A.
3. **Given** muitas requisições em sequência, **When** o serviço limita a taxa, **Then** a Fase B respeita uma pausa e tenta de novo com recuo antes de desistir.

---

### Edge Cases

- **Mapa de entrada ausente/ilegível**: erro fatal com mensagem clara (rode a Fase A). (E-01)
- **`url_download` vazia/malformada**: linha vira erro; registrada; continua. (E-02)
- **Erro HTTP (404/403/500)**: retry com backoff; esgotado → erro. (E-03)
- **`accesskey`/`hash` expirado**: tratado como erro, mas sinalizado como "possível expiração" com recomendação de re-rodar a Fase A. (E-04)
- **200 mas conteúdo não é o arquivo** (HTML de erro/login): rejeitar, não salvar, erro. (E-05)
- **Colisão de nome** (mesmo `nome_arquivo` em fornecedores diferentes): nome alternativo determinístico; nunca sobrescrever. (E-06)
- **Caracteres inválidos** em nome de arquivo/pasta: sanitizar antes de criar. (E-07)
- **Falha de escrita em disco**: permissão/espaço generalizado → fatal; pontual → erro e continua. (E-08)
- **Rate limiting**: pausa + retry/backoff. (E-09/E-10)
- **Download truncado** (conexão cai): gravação atômica (temporário → renomear); nunca arquivo pela metade com nome final. (E-11)
- **Reexecução após interrupção**: respeitar status + presença em disco; não rebaixar nem duplicar. (E-12)

## Requirements *(mandatory)*

### Functional Requirements

**Entrada e escopo**

- **FR-001**: O sistema MUST ler o mapa de entrada produzido pela Fase A; se ausente ou ilegível, MUST abortar (fatal) com mensagem clara instruindo rodar a Fase A primeiro.
- **FR-002**: O sistema MUST validar que as colunas essenciais do mapa existem; se faltarem, MUST abortar (fatal).
- **FR-003**: O sistema MUST NOT acessar o Google Drive nem usar credenciais OAuth — o único acesso externo é o GET público no Superlógica.
- **FR-004**: O sistema MUST tratar as colunas de conteúdo do mapa (URL, categoria, pasta) como somente leitura, atualizando apenas o `status` de cada linha.

**Download e organização**

- **FR-005**: Para cada linha com status diferente de concluído, o sistema MUST baixar o arquivo via GET simples na `url_download` (sem autenticação).
- **FR-006**: O sistema MUST validar a `url_download`; vazia/malformada → marcar a linha como erro, registrar e continuar.
- **FR-007**: O sistema MUST salvar cada arquivo em `downloads/<pasta_destino>/<nome_arquivo>`, criando os diretórios necessários (inclusive `_A_Revisar`), usando a `pasta_destino` já decidida pela Fase A (sem reclassificar).
- **FR-008**: O sistema MUST salvar com o `nome_arquivo` do mapa; se vazio, MUST derivar um nome de fallback determinístico.

**Integridade do que é salvo**

- **FR-009**: O sistema MUST validar o conteúdo baixado antes de considerá-lo sucesso (é o tipo de arquivo esperado, ex.: assinatura de PDF / tipo de conteúdo); conteúdo inválido (página de erro/HTML) MUST NOT ser salvo — a linha vira erro registrado.
- **FR-010**: O sistema MUST baixar de forma atômica: gravar em arquivo temporário e só promover ao nome final após download completo e validação; MUST NOT deixar arquivo truncado com nome definitivo.
- **FR-011**: Havendo colisão de nome na pasta de destino, o sistema MUST aplicar uma estratégia anti-colisão **determinística** (mesma linha → sempre o mesmo nome) e MUST NOT sobrescrever silenciosamente.
- **FR-012**: O sistema MUST sanitizar `nome_arquivo` e `pasta_destino` antes de criar diretórios/arquivos.

**Entregável (CSV final)**

- **FR-013**: O sistema MUST gravar o CSV final de forma **incremental** (append imediato após cada download bem-sucedido), contendo no mínimo: nome do arquivo salvo, hyperlink de origem, categoria e caminho local.
- **FR-014**: O sistema MUST NOT duplicar linhas no CSV final em reexecução (chave: `url_download`).
- **FR-015**: O sistema MUST gravar todas as saídas localmente, relativas ao diretório de execução.

**Retomada e idempotência**

- **FR-016**: O sistema MUST ser retomável: linha com status concluído e arquivo presente no caminho esperado MUST ser pulada (não rebaixar); uma interrupção a qualquer momento MUST NOT perder progresso nem causar duplicação.
- **FR-017**: Ao concluir um download com sucesso, o sistema MUST marcar a linha como concluída; ao falhar em definitivo, MUST marcá-la como erro.

**Resiliência e relatório**

- **FR-018**: O sistema MUST ser fail-soft: uma linha ruim MUST NOT derrubar a execução inteira (exceto falhas fatais — mapa ausente, ou falha de escrita generalizada).
- **FR-019**: O sistema MUST aplicar retry com recuo (backoff) e pausa entre requisições em erros HTTP e limitação de taxa; esgotadas as tentativas, a linha vira erro.
- **FR-020**: O sistema MUST produzir um relatório de erros com, no mínimo, a URL, o motivo e o número de tentativas de cada linha que falhou.
- **FR-021**: O sistema MUST sinalizar explicitamente no relatório os casos de **provável expiração** de `accesskey`/`hash`, recomendando re-rodar a Fase A para renovar as URLs.
- **FR-022**: O sistema MUST emitir um resumo final: total de linhas, baixadas, puladas (já existentes) e com erro por tipo, além de onde ficaram os arquivos, o CSV final e o relatório de erros.
- **FR-023**: Falha de escrita em disco generalizada (permissão/espaço) MUST ser tratada como fatal; falha pontual → linha vira erro e a execução continua.
- **FR-024**: O sistema MUST permitir ajustar por configuração: caminhos (mapa, raiz de downloads, saídas), pausa entre requisições, timeout e política de retry.

### Key Entities *(include if feature involves data)*

- **Entrada do mapa (linha)**: unidade de trabalho vinda da Fase A; traz `url_download`, `nome_arquivo`, `fornecedor`, `categoria`, `pasta_destino`, `hyperlink_origem`, `pdf_origem` e `status`. A Fase B lê tudo e escreve só o `status`.
- **Arquivo baixado**: o conteúdo binário salvo em `downloads/<pasta_destino>/<nome_final>`; produzido apenas após validação e de forma atômica.
- **Linha do CSV final**: o registro do entregável — nome do arquivo salvo, hyperlink de origem, categoria, caminho local (e, recomendado, pasta de destino e fornecedor).
- **Registro de erro**: ocorrência de falha definitiva — URL, motivo, nº de tentativas; casos de provável expiração são marcados.
- **Status da linha**: estado da unidade de trabalho — pendente → concluído (sucesso) ou erro (falha); base da retomada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das linhas pendentes com URL válida e conteúdo válido são baixadas e salvas no caminho `downloads/<pasta_destino>/<nome_arquivo>` correto.
- **SC-002**: Zero arquivos truncados/parciais com nome definitivo (gravação atômica), mesmo sob interrupção.
- **SC-003**: Respostas inválidas (HTML de erro, conteúdo não correspondente ao tipo esperado) nunca são salvas como arquivo; 100% viram erro registrado.
- **SC-004**: Colisões de nome nunca sobrescrevem arquivos; o nome final é determinístico (uma reexecução gera exatamente o mesmo nome).
- **SC-005**: Após interrupção e retomada, nenhum arquivo já concluído é rebaixado e nenhuma linha é duplicada no CSV final.
- **SC-006**: 100% das linhas concluídas aparecem no CSV final exatamente uma vez.
- **SC-007**: Zero acessos ao Google Drive e zero uso de credenciais OAuth durante a Fase B.
- **SC-008**: 100% das falhas definitivas aparecem no relatório de erros com motivo e nº de tentativas; os casos de provável expiração são sinalizados com a recomendação de re-rodar a Fase A.
- **SC-009**: A execução respeita a limitação de taxa (pausa entre requisições) e conclui sem ser bloqueada por excesso de requisições.
- **SC-010**: Todas as saídas (arquivos, CSV final, relatório de erros) ficam locais, relativas ao diretório de execução.
- **SC-011**: A execução completa roda sem intervenção humana (do início ao fim), e uma retomada só processa o que faltava.

## Assumptions

- A entrada é o `mapa_download.csv` produzido pela Fase A (spec 012), disponível no diretório de execução; o contrato das colunas é o definido na 012 (`contracts/mapa-download.md`).
- O alvo é **sempre PDF**; a validação de conteúdo usa a assinatura de PDF (e/ou o tipo de conteúdo da resposta). Outros tipos de arquivo estão fora de escopo por ora.
- Estratégia anti-colisão determinística preferida: discriminador estável derivado dos metadados (ex.: prefixar com o identificador da URL — `{id}_{nome_arquivo}`); **evitar** sufixos incrementais `(1)`/`(2)`, que não são determinísticos e quebram a retomada.
- Pausa entre requisições, timeout e número de tentativas são parametrizáveis, com defaults sensatos (ex.: 3 tentativas com espera crescente), calibráveis conforme o comportamento do Superlógica.
- O conjunto de colunas do CSV final é o mínimo definido (nome, hyperlink de origem, categoria, caminho local; recomendado pasta e fornecedor), ajustável ao consumidor do relatório.
- A janela de expiração do `accesskey`/`hash` é desconhecida; recomendação operacional: rodar Fase A e Fase B próximas no tempo. Se muitos erros de expiração ocorrerem, renovar as URLs re-rodando a Fase A.
- A Fase B pode reaproveitar padrões e utilidades já validados na Fase A (sanitização de nomes, retry/backoff, escrita incremental) — a forma concreta é decisão da fase de plan.

## Out of Scope

- **Geração do mapa, acesso ao Google Drive e extração de PDF**: são responsabilidade da **Fase A** (spec 012).
- **Reclassificação de categoria/pasta**: as pastas vêm prontas no mapa; a Fase B não re-executa a heurística de categoria.
- **Renovação de `accesskey`/`hash`**: feita re-rodando a Fase A; a Fase B apenas sinaliza a necessidade.
- **Decisões de implementação**: escolha de bibliotecas, desenho de módulos, valores finais de pausa/timeout/retry e formato exato dos arquivos de saída — responsabilidade da fase de plan.

## Dependencies

- **Depende da Fase A (spec 012)** e deve ser desenvolvida **após** ela. A interface é o `mapa_download.csv` (contrato em `docs/specs/012-download-map-extraction/contracts/mapa-download.md`). A Fase A produz e classifica; a Fase B consome, baixa e organiza. Sem um mapa válido, a Fase B não tem trabalho a fazer (aborta — FR-001).

## Adendo — Remessas incrementais (2026-07-23)

Contexto: uma **segunda remessa** de PDFs chegou numa nova pasta do Drive (`1qxZn3yINwegQnx3QU79d-Z3GV_ZHTMl8` — "2ª Remessa de plano de contas"), do **mesmo tipo** já processado. O objetivo é acrescentar esses arquivos (e suas produções) à árvore já existente, re-rodando o pipeline A→B→C sem reprocessar o que já está pronto. Isto exigiu três correções, todas nesta branch. As duas primeiras são da Fase B/C (escopo 013); a terceira toca a Fase A (pacote da 012) e vai anotada aqui por conveniência da remessa.

- **FR-B-01 (correção) — colisão superveniente na retomada.** A anti-colisão determinística recalcula os prefixos `{id}_` sobre o mapa **inteiro**. Uma remessa nova com arquivo homônimo (mesmo nome + pasta) fazia o nome calculado de uma linha **já baixada** mudar (ganhar prefixo), e a retomada — que exigia `status == baixado E arquivo no caminho calculado` — a dava por pendente, **rebaixando** o arquivo (órfão do antigo + linha duplicada no CSV final). Corrigido: a retomada aceita também o arquivo no **nome base** (sem prefixo); o já baixado permanece onde está e só o arquivo novo recebe o prefixo. Preserva SC-004/SC-005/SC-006. Coberto por `test_naming.py::settled_path` e `test_resume.py::test_new_homonym_does_not_redownload_the_already_saved_file`.

- **FR-C-01 (novo) — gate de pendentes do modo `--formatted` (raw_text_maker).** O modo `--formatted` reenviava a árvore **inteira** ao docling a cada execução (não tinha filtro de pendentes — correto quando o objetivo era o upgrade em lote padrão→formatado, custoso ao acrescentar remessas). Introduzido um **manifesto** (`raw_text_formatted.csv`, dedup por caminho de origem): documento já formatado não volta ao backend; só o novo (ou que perdeu o `.txt`) é reenviado. `--reformat-all` restaura o comportamento antigo; `--seed-formatted` migra uma árvore pré-existente sem custo de backend (semeado por camada de texto + `.txt` não-vazio). Coberto por `test_manifest.py` e `test_formatted_gate.py`.

- **FR-A-01 (correção, toca a 012) — pastas do Drive configuráveis.** Os IDs das pastas eram constantes fixas sem forma de sobrescrever. Adicionados o ID da nova remessa a `DRIVE_FOLDER_IDS` e a flag repetível `--folder-id` (permite varrer só a remessa nova sem re-resolver os hyperlinks já mapeados). O mapa cresce por **append**; o dedup por `url_download` — verificado estável entre execuções — preserva as linhas já `baixado`.

- **FR-B-02 (revisão de premissa) — aceitar imagens além de PDF.** A premissa original "o alvo é sempre PDF" (ver *Assumptions*) descartava, com erro `assinatura não-PDF`, os **comprovantes de pagamento fotografados** — que o Superlógica entrega como **imagem** (JPEG/PNG). Na 2ª remessa isso foram **24 arquivos** perdidos. Como o objetivo é ter texto bruto para **todo** documento e o backend-ocr já processa imagens, a Fase B passou a aceitar PDF **e** imagens (JPEG/PNG/TIFF/BMP/WEBP) por **assinatura de bytes**; HTML de erro/login segue rejeitado. A nomeação preserva a **extensão real** (um `.jpg` não vira `.jpg.pdf`). `--pdf-only` restaura a premissa antiga. Coberto por `test_content.py` (aceitação por formato + `--pdf-only`), `test_naming.py::preserves_image_extension` e `test_resume.py::image_comprovante`. **Atualiza a premissa PDF-only em *Assumptions* e *Out of Scope*.**
