# Feature Specification: Fase A — Extração e geração do mapa de download

**Feature Branch**: `012-download-map-extraction`

**Created**: 2026-07-13

**Status**: Draft

**Input**: User description: "Gere uma nova spec para o arquivo descrito em docuparse-project/scripts/SELECT/downloads/fases/fase_a_extracao.md — Considere que as credentials estão no arquivo docuparse-project/scripts/SELECT/downloads/fases/credentials.json"

## Contexto

Um condomínio recebe centenas de PDFs de despesas. Cada despesa referencia o(s) documento(s) de comprovação por um **hyperlink** embutido dentro de PDFs-lista guardados em duas pastas privadas do Google Drive. Chegar a cada arquivo exige navegar por três saltos: (0) abrir os PDFs no Drive, (1) achar o hyperlink na linha da tabela do PDF, (2) abrir a página pública correspondente que lista os arquivos, e (3) baixar cada arquivo. Feito à mão, é um trabalho repetitivo, lento e propenso a erros de classificação.

Esta feature cobre a **Fase A** de um pipeline de duas fases: ela **descobre e cataloga** tudo que precisa ser baixado (saltos 0, 1 e 2), produzindo um **mapa de download** — um arquivo intermediário onde cada linha é um arquivo a baixar, já classificado por categoria de despesa e com a trilha de origem. A Fase A **não baixa** os arquivos-alvo; o download efetivo (salto 3) é responsabilidade da Fase B, que consome o mapa.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar o mapa de download completo a partir dos PDFs (Priority: P1)

O operador aponta o sistema para as duas pastas designadas do Google Drive e obtém um **mapa de download** onde cada arquivo referenciado (percorrendo os três saltos) vira exatamente uma linha, contendo tudo que a Fase B precisa para baixá-lo: a URL de download, o nome real do arquivo, o fornecedor e a origem. Uma mesma página pode listar vários arquivos; todos entram no mapa.

**Why this priority**: É a razão de existir da Fase A. Sem o mapa completo, a Fase B não tem o que baixar. É o menor incremento que já entrega valor: transforma navegação manual de três saltos em um catálogo pronto para consumo.

**Independent Test**: Executar a Fase A sobre um conjunto conhecido de PDFs e verificar que, para cada página de arquivos com N âncoras de download, o mapa contém N linhas correspondentes, cada uma com URL de download e nome de arquivo preenchidos.

**Acceptance Scenarios**:

1. **Given** as duas pastas do Drive com PDFs-lista, **When** o operador executa a Fase A, **Then** o sistema lista e lê os PDFs de ambas as pastas e gera o mapa de download.
2. **Given** uma linha de PDF com hyperlink no fornecedor, **When** o sistema resolve a página de arquivos de destino, **Then** cada âncora de download da página vira uma linha do mapa (nunca apenas a primeira).
3. **Given** uma âncora de download, **When** o sistema a registra, **Then** a linha do mapa contém a URL de download e o nome real do arquivo.
4. **Given** uma linha de PDF sem hyperlink no fornecedor, **When** o sistema a processa, **Then** ela é ignorada sem erro (não é uma despesa com anexo).

---

### User Story 2 - Classificar cada arquivo em uma pasta de destino por categoria (Priority: P1)

Cada arquivo mapeado é classificado em uma **pasta de destino** derivada da **categoria** da despesa (não da célula inteira). A categoria vem da coluna "Categoria - Complemento", que traz categoria e complemento concatenados e precisa ser dividida. Rótulos variantes da mesma categoria (por exemplo `AGUA`, `Água`, `água`) caem na mesma pasta, e famílias (por exemplo `Manut. de Piscina`, `Manutenção de Jardim`) são agrupadas de forma consistente.

**Why this priority**: Sem classificação consistente, a Fase B despejaria centenas de arquivos sem organização, ou criaria uma pasta por linha (o complemento é sempre diferente), inviabilizando a revisão contábil. A organização por categoria é parte do valor central do mapa.

**Independent Test**: Dado um conjunto de células "Categoria - Complemento" de exemplo, verificar que a divisão isola corretamente a categoria (parte antes do primeiro ` - `) e o complemento (depois), e que variantes/famílias mapeiam para a mesma pasta de destino de forma determinística.

**Acceptance Scenarios**:

1. **Given** uma célula `Construção-Reformas - IMPERMEABILIZAÇÃO DE RESERVATÓRIOS PARC 10/10`, **When** o sistema a divide, **Then** a categoria é `Construção-Reformas` e o complemento é `IMPERMEABILIZAÇÃO DE RESERVATÓRIOS PARC 10/10`.
2. **Given** categorias `AGUA`, `Água` e `água`, **When** o sistema determina a pasta de destino, **Then** as três apontam para a mesma pasta.
3. **Given** uma categoria sem separador ` - ` na célula, **When** o sistema a divide, **Then** a célula inteira é a categoria e o complemento fica vazio.
4. **Given** vários arquivos originados do mesmo hyperlink, **When** o sistema os registra, **Then** todos herdam a mesma categoria e complemento da linha de PDF de origem.

---

### User Story 3 - Rastreabilidade e rede de segurança: nada perdido em silêncio (Priority: P1)

Toda linha do mapa permite rastrear de qual PDF e de qual página ela veio e para onde vai. Quando a categoria não pode ser determinada com confiança, o arquivo vai para a pasta de fallback `_A_Revisar` e o caso é registrado em um **relatório de exceções** para decisão humana — em vez de ser descartado ou salvo no lugar errado silenciosamente.

**Why this priority**: A confiança no resultado depende de nada ser perdido ou misturado sem registro. A pasta `_A_Revisar` e o relatório de exceções são a garantia auditável de que o humano revê exatamente o que a heurística não teve confiança para classificar.

**Independent Test**: Introduzir casos ambíguos (linha desalinhada, categoria indeterminada, link quebrado) e verificar que cada um aparece no relatório de exceções e/ou é direcionado a `_A_Revisar`, e que toda linha do mapa carrega o PDF de origem, a página de origem e a pasta de destino.

**Acceptance Scenarios**:

1. **Given** uma categoria que não pôde ser determinada, **When** o sistema registra a linha, **Then** a pasta de destino é `_A_Revisar` e o caso consta no relatório de exceções.
2. **Given** qualquer linha do mapa, **When** ela é inspecionada, **Then** é possível identificar o PDF de origem, a página de origem do hyperlink e a pasta de destino.
3. **Given** um cruzamento link↔categoria ambíguo, **When** o sistema não tem confiança suficiente, **Then** a ocorrência é marcada para revisão no relatório em vez de ser adivinhada.

---

### User Story 4 - Execução resiliente e retomável (Priority: P2)

A execução não é interrompida por um PDF ilegível, um link quebrado, uma página sem arquivos ou um bloqueio temporário: cada problema é registrado e a execução segue (fail-soft). O mapa é gravado incrementalmente, de modo que uma interrupção no meio preserva o progresso já feito, e uma nova execução não duplica o que já foi mapeado.

**Why this priority**: O volume é grande e a rede é imperfeita. Sem resiliência e escrita incremental, uma única falha desperdiçaria todo o trabalho já feito e a re-execução criaria duplicatas. É P2 porque depende de US1 existir, mas é essencial para uso real.

**Independent Test**: Interromper a execução no meio e confirmar que o mapa em disco contém as linhas já descobertas; re-executar e confirmar que nenhuma linha é duplicada; simular PDF ilegível e link com erro e confirmar que a execução continua e registra as ocorrências.

**Acceptance Scenarios**:

1. **Given** um PDF ilegível/corrompido, **When** o sistema o encontra, **Then** ele é registrado no relatório e a execução prossegue para o próximo PDF.
2. **Given** uma página que retorna erro (404/403/500) ou `accesskey` expirado, **When** o sistema tenta resolvê-la, **Then** a ocorrência é registrada e a execução continua.
3. **Given** a execução interrompida no meio, **When** o operador inspeciona o disco, **Then** o mapa contém todas as linhas descobertas até o ponto de interrupção.
4. **Given** um mapa já contendo uma URL de download, **When** a Fase A é re-executada, **Then** essa entrada não é duplicada.

---

### User Story 5 - Passada de reconhecimento de categorias para revisão humana (Priority: P2)

Antes de comprometer o mapa final, o sistema oferece uma passada de reconhecimento que varre os PDFs e emite um **inventário das categorias distintas encontradas**, com a pasta de destino proposta para cada uma. Isso permite ao humano revisar e ajustar o agrupamento de famílias antes de gerar o mapa, tornando a classificação auditável em vez de uma caixa-preta.

**Why this priority**: Não existe plano de contas oficial; as pastas são derivadas dinamicamente das categorias reais. A passada de reconhecimento é o mecanismo que garante que o agrupamento reflita o universo real de categorias deste condomínio antes de comprometer o resultado. É P2 porque o mapa pode ser gerado sem ela, mas ela eleva muito a qualidade da classificação.

**Independent Test**: Executar a passada de reconhecimento sobre os PDFs e verificar que o inventário lista cada categoria distinta encontrada com uma pasta de destino proposta, permitindo revisão antes da geração do mapa.

**Acceptance Scenarios**:

1. **Given** os PDFs das duas pastas, **When** o operador executa a passada de reconhecimento, **Then** o sistema emite um inventário das categorias distintas e da pasta proposta para cada uma.
2. **Given** o inventário revisado pelo humano, **When** o mapa é gerado, **Then** a classificação em pastas reflete os ajustes feitos.

---

### Edge Cases

- **PDF sem tabela reconhecível / corrompido**: registrado no relatório; segue para o próximo PDF.
- **Linha de PDF sem hyperlink**: ignorada silenciosamente (não é despesa com anexo).
- **Página de arquivos com erro HTTP ou `accesskey` expirado**: registrada; execução continua.
- **Página carrega mas não lista âncoras de download**: registrada; execução continua.
- **Âncora sem nome real do arquivo**: usa nome de fallback determinístico (fornecedor + identificador da URL).
- **Categoria com hífen sem espaço** (ex.: `Construção-Reformas`): não dividir no hífen simples — o separador é estritamente ` - ` (com espaços).
- **Célula com múltiplos ` - `**: dividir apenas no primeiro; o restante é complemento.
- **Categoria indeterminada/vazia**: pasta `_A_Revisar` + registro no relatório.
- **Cruzamento link↔categoria ambíguo** (linha desalinhada, célula mesclada, complemento longo que quebra em duas linhas): marcar "revisar cruzamento" em vez de adivinhar.
- **Nomes com percent-encoding ou espaços como `+`**: decodificar antes de usar como texto legível.
- **Nomes com caracteres inválidos para sistema de arquivos**: sanitizar antes de gravar.
- **Bloqueio temporário / rate limiting em requisições sequenciais**: pausar e tentar de novo com recuo; esgotadas as tentativas, tratar como link com erro.
- **Pastas do Drive com subpastas**: varredura recursiva por padrão.
- **Re-execução da Fase A**: idempotente — não duplica entradas com a mesma URL de download.
- **Falha de autenticação (token expirado/revogado)**: erro fatal com instrução clara de re-login; não produz mapa parcial inválido.

## Requirements *(mandatory)*

### Functional Requirements

**Autenticação e escopo de acesso**

- **FR-001**: O sistema MUST autenticar no Google Drive com acesso **somente leitura**, usando a credencial OAuth fornecida pelo operador, e MUST reutilizar a sessão salva em execuções seguintes sem exigir novo login.
- **FR-002**: O sistema MUST tratar falha de autenticação (sessão expirada/revogada) como **erro fatal**, abortando com mensagem clara instruindo o re-login, sem produzir um mapa parcial inválido.
- **FR-003**: O sistema MUST operar em modo estritamente de leitura sobre o Drive — nunca criar, mover, renomear ou apagar itens no Drive.
- **FR-004**: O sistema MUST manter as credenciais e o token de sessão fora do controle de versão (nunca commitados).

**Descoberta e extração**

- **FR-005**: O sistema MUST localizar e ler todos os PDFs-lista das duas pastas designadas do Drive, varrendo subpastas recursivamente por padrão.
- **FR-006**: Para cada linha de PDF que contenha um hyperlink no fornecedor, o sistema MUST extrair o hyperlink de origem, o nome do fornecedor e a célula "Categoria - Complemento" correspondentes à mesma linha da tabela.
- **FR-007**: O sistema MUST ignorar, sem gerar erro, linhas de PDF que não tenham hyperlink no fornecedor.
- **FR-008**: O sistema MUST resolver cada hyperlink até a página de arquivos correspondente e capturar **todas** as âncoras de download nela listadas — uma âncora gera uma entrada no mapa; nunca parar na primeira.
- **FR-009**: Para cada âncora, o sistema MUST registrar a URL de download e o nome real do arquivo; quando o nome real estiver ausente, MUST gerar um nome de fallback determinístico.

**Classificação por categoria**

- **FR-010**: O sistema MUST dividir a célula "Categoria - Complemento" no **primeiro** separador ` - ` (espaço-hífen-espaço): a parte anterior é a **categoria**, a posterior é o **complemento**. Sem o separador, a célula inteira é a categoria e o complemento fica vazio; havendo múltiplos separadores, dividir apenas no primeiro.
- **FR-011**: O sistema MUST derivar a **pasta de destino** exclusivamente a partir da categoria (nunca da célula inteira), de forma determinística, agrupando rótulos variantes (ex.: diferenças de acento/caixa/pontuação) na mesma pasta e famílias afins em uma pasta comum.
- **FR-012**: Toda entrada do mapa MUST ter uma categoria e uma pasta de destino; quando a categoria não puder ser determinada, o sistema MUST atribuir a pasta de fallback `_A_Revisar` e registrar a ocorrência no relatório de exceções.
- **FR-013**: Todos os arquivos originados de um mesmo hyperlink MUST herdar a mesma categoria e o mesmo complemento da linha de PDF de origem.

**Saída, rastreabilidade e integridade**

- **FR-014**: Cada entrada do mapa MUST permitir rastrear o PDF de origem, a página de origem do hyperlink e a pasta de destino.
- **FR-015**: O sistema MUST gravar o mapa de forma **incremental** (cada entrada persistida assim que descoberta), de modo que uma interrupção preserve o progresso já feito em disco.
- **FR-016**: O sistema MUST ser **idempotente**: não duplicar entradas com a mesma URL de download ao (re)executar a Fase A.
- **FR-017**: O sistema MUST sanitizar nomes de arquivo e de pasta antes de gravar — decodificar codificação de URL, remover/substituir caracteres inválidos e aparar/colapsar espaços.
- **FR-018**: O sistema MUST gravar todas as saídas **localmente**, relativas ao diretório de execução (mapa de download, relatório de exceções, inventário de categorias e a estrutura de pastas de destino que a Fase B usará).
- **FR-019**: Cada entrada nova do mapa MUST iniciar com status `pendente` (a Fase B atualizará o status posteriormente).

**Resiliência**

- **FR-020**: O sistema MUST ser **fail-soft**: exceções não-fatais (PDF ilegível, link com erro/expirado, página sem âncoras, cruzamento ambíguo) MUST ser registradas e a execução continua.
- **FR-021**: O sistema MUST aplicar pausa e nova tentativa com recuo (backoff) em caso de bloqueio temporário/limite de taxa; esgotadas as tentativas, tratar a ocorrência como link com erro.
- **FR-022**: O sistema MUST produzir um **relatório de exceções** consolidando as ocorrências que exigem revisão humana.

**Reconhecimento e ajuste**

- **FR-023**: O sistema MUST oferecer uma **passada de reconhecimento** que colete as categorias distintas encontradas e a pasta de destino proposta para cada uma, permitindo revisão humana antes de comprometer o mapa.
- **FR-024**: O sistema MUST permitir ajustar, sem alterar a lógica, as decisões provisórias — pastas de origem no Drive, regras de agrupamento de categorias e parâmetros de tolerância/pausa/retry (por configuração).

**Fronteira de escopo**

- **FR-025**: O sistema MUST NOT baixar os arquivos-alvo — a Fase A apenas descobre e cataloga; o download efetivo é responsabilidade da Fase B.

### Key Entities *(include if feature involves data)*

- **PDF-lista (fonte)**: documento no Drive com uma tabela de despesas (colunas conhecidas: Vencimento, Fornecedor, Categoria - Complemento, Compet., Valor). O hyperlink clicável está na coluna Fornecedor.
- **Página de arquivos (origem)**: página pública, autorizada pelo `accesskey` presente na própria URL (sem login), que lista uma ou mais âncoras de download.
- **Entrada do mapa de download**: unidade central; representa **um arquivo a baixar na Fase B**. Atributos lógicos: URL de download, nome real do arquivo, fornecedor, categoria, complemento, pasta de destino, página de origem do hyperlink, PDF de origem e status inicial (`pendente`).
- **Categoria e complemento**: a categoria (isolada da célula) determina a classificação/pasta; o complemento é preservado para rastreabilidade e apoio à nomeação, podendo ficar vazio.
- **Pasta de destino**: agrupamento derivado da categoria (incluindo o fallback `_A_Revisar`) onde a Fase B salvará o arquivo.
- **Relatório de exceções**: inventário das ocorrências não-fatais (links quebrados, PDFs ilegíveis, categorias indeterminadas, cruzamentos ambíguos) para revisão humana.
- **Inventário de categorias (reconhecimento)**: lista das categorias distintas encontradas e a pasta de destino proposta para cada uma.
- **Credencial de acesso**: a credencial OAuth fornecida pelo operador (arquivo `credentials.json`) e o token de sessão gerado no primeiro login (`token.json`), reutilizado depois; dependência para ler o Drive.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos PDFs legíveis nas duas pastas são processados; PDFs ilegíveis são registrados sem interromper a execução.
- **SC-002**: Para toda página de arquivos com N âncoras de download, o mapa contém exatamente N entradas correspondentes — nenhuma âncora perdida, nenhuma duplicada.
- **SC-003**: 100% das entradas do mapa possuem os campos essenciais preenchidos: URL de download, nome de arquivo (real ou fallback), fornecedor, categoria, complemento (quando existir), pasta de destino, página de origem e PDF de origem.
- **SC-004**: Rótulos variantes da mesma categoria (ex.: `AGUA`/`Água`/`água`) mapeiam para a mesma pasta em 100% dos casos; categorias indeterminadas caem em `_A_Revisar` e são registradas.
- **SC-005**: A célula "Categoria - Complemento" é dividida corretamente em 100% das linhas — inclusive quando a categoria contém hífen sem espaços e quando não há separador.
- **SC-006**: Nenhuma entrada do mapa fica sem categoria/pasta de destino (zero entradas sem classificação).
- **SC-007**: Interrompida no meio, a execução deixa em disco todas as entradas descobertas até o ponto de interrupção; ao re-executar, nenhuma entrada é duplicada.
- **SC-008**: Zero arquivos-alvo são baixados durante a Fase A.
- **SC-009**: Um relatório de exceções é produzido listando 100% das ocorrências não-fatais encontradas.
- **SC-010**: Todas as saídas são gravadas localmente, relativas ao diretório de execução.
- **SC-011**: Nenhuma credencial (`credentials.json`/`token.json`) é adicionada ao controle de versão.
- **SC-012**: A execução completa exige no máximo uma interação humana (o login inicial); todo o restante ocorre sem intervenção manual.

## Assumptions

- A credencial OAuth do Google fornecida pelo operador está disponível no diretório de execução da Fase A — para esta implementação, em `docuparse-project/scripts/SELECT/downloads/fases/credentials.json`. O token de sessão (`token.json`) nasce do primeiro login e é reutilizado nas execuções seguintes; antes disso não existe, o que é esperado.
- O escopo de acesso ao Drive é **somente leitura** (suficiente para ler o conteúdo dos PDFs).
- As duas pastas designadas do Drive são identificadas por: `1uJ6cZYbThBxiKcfcMmrlS-9dn-aVJfzr` e `13r1wG8rj8YFvYefPoDYhFg-aVESRZMgE`.
- Por padrão, a varredura das pastas do Drive é **recursiva** (inclui subpastas). *A confirmar: se apenas a raiz de cada pasta deve ser lida.*
- As páginas de arquivos são **públicas via `accesskey`** (sem login) e as âncoras de download estão em conteúdo estático (sem necessidade de navegador/JavaScript).
- O nome real do arquivo vem do rótulo (`title`) da imagem dentro da âncora; o parâmetro `filename` da URL é ignorado por não ser o nome real.
- **Não existe plano de contas oficial**: as pastas são derivadas dinamicamente das categorias encontradas, com um dicionário de famílias como agrupador e `_A_Revisar` como fallback. O dicionário inicial é um ponto de partida a validar/expandir pela passada de reconhecimento contra o universo real de categorias.
- O formato do mapa de download é **CSV** por padrão (JSON é alternativa aceitável).
- A saída é local, relativa ao diretório de execução; a estrutura de pastas de destino que a Fase B usará nasce localmente a partir daqui.
- Tolerância de cruzamento vertical entre link e categoria, pausas entre requisições e política de retry são **parametrizáveis** e serão calibradas com os PDFs reais.

## Out of Scope

- **Download dos arquivos-alvo (salto 3)** e o preenchimento das pastas de destino com esses arquivos — responsabilidade da **Fase B**.
- **Login/credencial na página de arquivos (salto 2)**: não há — o `accesskey` na URL já autoriza o acesso.
- **Decisões de implementação**: escolha de bibliotecas, desenho de módulos, algoritmo de extração de PDF, valores finais de tolerância/pausa/retry e formato exato dos arquivos de saída — responsabilidade da fase de plan/implementação.

## Decisões em aberto (revisar no plan)

Todas têm um default sensato aplicado acima; revisar contra os PDFs reais antes de fechar a implementação:

- Varredura recursiva vs. apenas a raiz das pastas do Drive.
- Composição final do dicionário de famílias de categorias (validado pela passada de reconhecimento).
- Valores de tolerância de cruzamento, pausa entre requisições e política de retry.
- Formato do mapa intermediário (CSV assumido; JSON aceitável).
