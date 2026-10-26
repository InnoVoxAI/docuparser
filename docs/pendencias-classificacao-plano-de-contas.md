# Pendências: identificação de condomínio e classificação no plano de contas

Estado em 2026-10-18. As stories 1.1 a 1.6c estão entregues: dá para sincronizar, listar, confirmar e rejeitar pelas telas. O backend identifica o condomínio de cada documento e sugere a conta do plano de contas, com auditoria em `DocumentEvent` e um painel de revisão na tela de Validação. O plano de contas agora é compartilhado entre condomínios, e já existem o cliente de leitura do Superlógica e a área de aprovação das propostas (stories 1.1 a 1.3, só backend, ainda sem testes automatizados).

Os dados (condomínios, plano de contas) ainda só podem ser cadastrados por API. O Épico 1 resolve isso importando do Superlógica, com aprovação do analista.

Escopo das telas por enquanto: **(1)** listagem dos dados, **(2)** botão de sincronizar com o Superlógica e cadastro manual de um condomínio, **(3)** tela em que o analista confirma ou rejeita o que foi importado. Nada além disso; o que ficou de fora está em "Adiado" no fim do documento.

---

## Épico 1: Importação de condomínios e planos de contas do Superlógica

Decisão da conversa com o CEO: em vez de cadastrar tudo à mão, um adapter lê o cadastro do Superlógica, grava propostas numa área de aprovação, e o operador aprova e resolve conflitos numa tela. Nada é aplicado sem aprovação.

Decisões já tomadas:
- O plano de contas é **compartilhado**: o condomínio aponta para um plano, como no Superlógica.
- A primeira versão importa **condomínios e planos de contas**. Fornecedores ficam para depois.
- **Nada é aprovado automaticamente.**
- O adapter fica **dentro do backend-core**, atrás de uma interface que permite uma segunda fonte no futuro.

Fatos verificados na API real (somente leitura, em 2026-10-17; detalhes em `memories/reference/`):
- Basta o par `app_token` e `access_token`. A lista completa de condomínios exige `id=-1` e paginação (`itensPorPagina`, `pagina`); sem `id=-1` a API devolve um só.
- O CNPJ do condomínio vem no campo `st_cpf_cond`; `st_cnpj_cond` vem vazio.
- O plano de contas é compartilhado: quase todos os condomínios usam o mesmo plano (`id_planoconta_plc`). A hierarquia está no código pontuado da conta (o pai de `2.1.10` é `2.1`), sem campo de pai.
- A sincronização completa da carteira leva poucos segundos.
- As respostas são lista JSON pura e todos os valores vêm como string (inclusive `fl_ativo_cond`). O nome do plano vem em `st_nome_plc`.
- Há CNPJs repetidos em registros diferentes. Pelo que foi examinado, são de três tipos:
  1. Mesmo condomínio cadastrado duas vezes: nome, endereço e plano iguais, um ativo e um inativo.
  2. CNPJ da própria administradora usado como CNPJ de condomínios diferentes, com nomes e endereços diferentes.
  3. Dois condomínios ativos, com nomes e endereços diferentes, no mesmo CNPJ (provável erro de cadastro).

### Story 1.1: Plano de contas compartilhado (refatoração do modelo)

**Contexto:** hoje cada `LedgerAccount` pertence a um condomínio. No Superlógica, o plano é compartilhado, e copiar as contas por condomínio geraria dezenas de milhares de linhas repetidas.

**O que deve ser feito:**
- Criar a entidade `ChartOfAccounts` (nome, `external_source`, `external_id`).
- `LedgerAccount` passa a apontar para o plano; código e natureza passam a ser únicos por plano.
- `Condominium` ganha o vínculo opcional com o plano e `external_source`, com `external_id` único por fonte.
- A regra de fornecedor continua por condomínio, mas a conta precisa ser do plano do condomínio.
- A classificação, a validação da conta manual e a rota que lista contas passam a usar o plano do condomínio.
- Migration de dados: cada conjunto atual de contas vira um plano, e os condomínios passam a apontar para ele.

**Critérios de aceite:**
- Dois condomínios podem usar o mesmo plano sem duplicar contas.
- Conta de outro plano é recusada na classificação manual e na regra de fornecedor.
- Os testes existentes de classificação, identificação e do painel de revisão continuam passando, adaptados.
- A migration roda sobre dados existentes sem perder contas, regras nem classificações.

**Status: concluída em 2026-10-18 (backend), testes pendentes (1.9).**
- Migrations `accounting` 0004 a 0006 e `condominiums` 0003 a 0005, verificadas em Postgres com dados no formato antigo: contas, hierarquia, naturezas e regras de fornecedor preservadas. Cada condomínio que tinha contas virou dono de um plano só dele; unir planos fica para depois. A etapa de dados não tem volta.
- Escrita de contas em `/charts-of-accounts/...`. `GET /condominiums/<id>/ledger-accounts` ficou só leitura, porque o painel de revisão o usa.

### Story 1.2: Interface de fonte e cliente do Superlógica (somente leitura)

**Contexto:** a fonte de dados pode mudar no futuro, então o restante do sistema não pode depender do formato do Superlógica.

**O que deve ser feito:**
- Definir a interface de fonte: listar condomínios, listar planos e listar as contas de um plano, devolvendo objetos normalizados (nunca o payload bruto da API).
- Implementar a fonte do Superlógica, somente com requisições `GET`, com timeout, paginação, tratamento de erro e espera entre chamadas.
- Aplicar o que foi verificado: `id=-1`, CNPJ lido de `st_cpf_cond` (com `st_cnpj_cond` como alternativa) e validado pelos dígitos verificadores, e hierarquia montada pelo código pontuado, sinalizando contas sem pai.
- Descartar o campo `st_token_emp` e qualquer outro campo que seja segredo.

**Critérios de aceite:**
- Testes com respostas simuladas no formato real da API, sem dados de cliente.
- O cliente recusa qualquer método diferente de `GET`.
- Um teste garante que o token do payload nunca aparece nos objetos normalizados nem em logs.

**Status: concluída em 2026-10-18 (backend), testes pendentes (1.9).**
- `erp_import/sources/`. O formato real das respostas foi verificado com chamadas GET (só nomes e tipos de campo).

### Story 1.3: Área de aprovação e regras de conflito

**Contexto:** o sistema precisa comparar o que veio do Superlógica com o que já existe, sem aplicar nada automaticamente.

**O que deve ser feito:**
- Criar `ImportBatch` (fonte, quem iniciou, estado) e `ImportProposal` (tipo de entidade, id externo, ação, dados mínimos, diferenças, estado, quem decidiu e quando).
- Ações possíveis: novo, atualizar, desativar e conflito.
- A sincronização é idempotente: rodar de novo sem mudanças não cria propostas.
- Regras de conflito:
  - Mesmo CNPJ, mesmo nome e endereço, um ativo e um inativo: tratar como o mesmo condomínio, importar o ativo e registrar o inativo como duplicado, sem criar outro registro.
  - Mesmo CNPJ com nomes ou endereços diferentes: o CNPJ não é confiável para esses registros. Importar sem CNPJ, com aviso, e deixar o operador decidir qual registro fica com o CNPJ.
  - CNPJ igual ao da administradora do tenant: nunca vira CNPJ de condomínio.
  - Condomínio que sumiu da fonte: proposta de desativar, nunca de apagar.
  - Condomínio inativo na fonte: só entra na importação se já for conhecido.
  - Conta renomeada ou removida em um plano: proposta de atualizar ou desativar. A natureza e as regras de fornecedor nunca são alteradas pela importação, nem os nomes alternativos.
- Guardar nos dados da proposta só os campos necessários, sem o payload bruto.

**Critérios de aceite:**
- Cada tipo de conflito tem teste.
- Nada é gravado em `Condominium`, `ChartOfAccounts` ou `LedgerAccount` antes da aprovação.
- Aprovar, rejeitar e resolver ficam registrados com autor e data.

**Status: concluída em 2026-10-18 (backend), testes pendentes (1.9).**
- Verificado em Postgres: re-sincronizar sem mudanças não cria propostas, proposta pendente que mudou ou deixou de valer vira "substituída", falha na fonte deixa o lote em erro sem propostas, e nada é gravado em `Condominium`, `ChartOfAccounts` nem `LedgerAccount`.
- Aprovar, rejeitar e resolver só registram a decisão (autor e data). Aplicar a mudança é a 1.4.
- O CNPJ da administradora entra como parâmetro (`administrator_cnpj`) até a 1.8 guardá-lo na configuração do tenant.

### Story 1.4: API de importação

**O que deve ser feito:**
- Iniciar uma sincronização, que roda em segundo plano, e consultar o lote e as propostas.
- Decidir uma proposta (aprovar, rejeitar ou resolver conflito) e aprovar em lote.
- Permissão `models.edit`. Nada é aprovado automaticamente, nem por lote sem ação do operador.

**Critérios de aceite:**
- Aprovar uma proposta aplica a mudança de forma atômica e idempotente.
- Falha na fonte deixa o lote em estado de erro com mensagem legível, sem criar propostas parciais.

**Status: concluída em 2026-10-18.**
- `POST /import/sync` (202, segundo plano, um lote por vez), `GET /import/overview`, `GET /import/proposals` (filtros e paginação), aprovar, rejeitar e resolver por proposta (`/import/proposals/{id}/...`) e em lote (`/import/proposals/approve` e `/reject`, com os ids escolhidos). Permissão: leitura `inbox.view`, escrita `models.edit`.
- Decidir aplica a mudança na mesma transação; repetir a decisão não repete a mudança. O lote aplica planos antes das contas e dos condomínios. Aprovar um condomínio antes do plano dele é recusado com mensagem clara.
- Uma proposta rejeitada não volta enquanto a fonte não mudar. A escolha de CNPJ vale para o grupo inteiro do conflito, e "nenhum fica com o CNPJ" é lembrado nas próximas sincronizações.
- Verificado de ponta a ponta contra o Superlógica real (somente leitura) num tenant descartável: sincroniza, não propõe nada ao repetir, aplica planos e condomínios, resolve os conflitos de CNPJ e uma nova sincronização não deixa pendências.
- Pontos que ficam em aberto: desativar um duplicado que guarda o CNPJ (o registro desativado mantém o CNPJ).

### Story 1.5: Credenciais do Superlógica por tenant

**Contexto:** cada tenant precisa do próprio par de tokens, e hoje as configurações de integração só guardam a URL base.

**O que deve ser feito:**
- Guardar `app_token` e `access_token` por tenant, criptografados com uma chave vinda de variável de ambiente.
- A API aceita os tokens, mas nunca os devolve (somente indica se estão configurados).
- Permitir testar a conexão com uma chamada de leitura.

**Critérios de aceite:**
- Os tokens não aparecem em respostas de API, logs nem eventos.
- Sem credenciais configuradas, a sincronização informa o motivo e não faz nenhuma chamada.

**Status: concluída em 2026-10-18.**
- Tokens cifrados (Fernet) com `DOCUPARSE_SECRETS_KEY`, por tenant, em `IntegrationSettings`. A API aceita os dois tokens juntos e devolve só `superlogica_credentials_configured`. Sem a chave configurada, salvar os tokens responde com mensagem clara. Trocar a chave exige informar os tokens de novo.
- `POST /import/test-connection` faz uma leitura mínima. Sem credenciais a sincronização informa o motivo e não faz nenhuma chamada.
- Também guarda o CNPJ da administradora, que a sincronização já usa.

### Story 1.6a: Tela de listagem

**Status: concluída em 2026-10-18** (módulo `registry`, rota `/registry`, menu "Cadastros").

**Contexto:** hoje os condomínios e os planos de contas só podem ser vistos por API.

**O que deve ser feito:**
- Lista de condomínios: nome, CNPJ, plano de contas, origem (Superlógica ou manual) e situação, com busca.
- Lista de planos de contas; ao escolher um, mostrar as contas em árvore, pelo código pontuado, somente leitura.
- Estados de carregamento, erro e vazio tratados.

**Critérios de aceite:**
- Usa `GET /condominiums` e `GET /charts-of-accounts` (e as contas do plano).
- Sem ações de edição nesta tela.
- Testes de componente e de serviço.

### Story 1.6b: Botão de sincronizar e cadastro manual

**Status: concluída em 2026-10-18** (mesma tela de Cadastros; credenciais e teste de conexão em Configurações > Integrações).

**O que deve ser feito:**
- Botão "Sincronizar com Superlógica": inicia o lote (1.4), mostra em andamento, pronto ou erro (com a mensagem legível) e leva à tela de confirmação (1.6c).
- Cadastro manual de um condomínio: nome, CNPJ e plano de contas (entre os existentes). Mostrar a mensagem da API quando houver CNPJ duplicado ou inválido.
- Botão e formulário só habilitados para quem tem `models.edit`.

**Critérios de aceite:**
- Sem credenciais configuradas (1.5), o botão informa o motivo e não inicia nada.
- Testes de componente e de serviço.

### Story 1.6c: Tela de confirmação do analista

**Status: concluída em 2026-10-18** (rota `/registry-import`, menu "Confirmar importação"). Verificada no Chrome com a stack rodando (fonte sintética). Melhorias de UX de 2026-10-26: redirecionamento após a sincronização, busca, "Confirmar todos", aviso de ordem (plano antes de condomínio), cabeçalho fixo e contagem no menu.

**O que deve ser feito:**
- Resumo do lote e tabela de propostas agrupadas por ação (novo, atualizar, desativar, conflito), com a diferença de cada campo e os avisos da proposta.
- Confirmar e rejeitar por linha e em lote; o lote só vale para as linhas selecionadas, nunca "aprovar tudo" automático.
- Diálogo de conflito de CNPJ: os registros envolvidos lado a lado; escolher qual fica com o CNPJ, ou nenhum. Para CNPJ já usado por cadastro local: informar se é o mesmo condomínio.
- Estados de carregamento, erro e vazio tratados.

**Critérios de aceite:**
- Ações só habilitadas para quem tem `models.edit`.
- Testes de componente e de serviço.

### Story 1.8: Identificação não pode usar o CNPJ da administradora

**Contexto:** na identificação por CNPJ no texto, um documento emitido pela própria administradora (por exemplo, a nota da taxa de administração) pode ser ligado ao condomínio errado se esse condomínio estiver cadastrado com o CNPJ dela.

**O que deve ser feito:**
- Guardar o CNPJ da administradora na configuração do tenant.
- Ignorar esse CNPJ na identificação por campo do pagador e por texto.
- Nesses casos, identificar pelo nome ou pelos nomes alternativos.

**Critérios de aceite:**
- Documento com o CNPJ da administradora como emitente não é ligado a condomínio por esse CNPJ.
- Teste com um caso real anonimizado.

**Status: parcial.** O CNPJ da administradora já é guardado na configuração do tenant e a sincronização o usa (nunca vira CNPJ de condomínio). Falta a identificação de documentos ignorar esse CNPJ no campo do pagador e no texto.

### Story 1.9: Testes das stories 1.1 a 1.3

**Status: parcial.** Já existem testes da API de importação, da aplicação das decisões e das credenciais (`erp_import/tests`, 19 testes) e das telas (`modules/registry/__tests__` e o painel de integrações, 22 + 4 testes). Faltam adaptar os testes antigos e cobrir o planejador e o cliente do Superlógica com testes fixos.

**Contexto:** as stories 1.1 a 1.3 foram entregues sem testes automatizados. Na área tocada (`accounting`, `condominiums` e `documents/tests/test_classification_pipeline.py`), 75 de 106 testes falham, porque criam contas pelo modelo antigo (`LedgerAccount` por condomínio).

**O que deve ser feito:**
- Adaptar os testes existentes ao plano compartilhado.
- Cobrir 1.1: dois condomínios no mesmo plano, conta de outro plano recusada na classificação manual e na regra de fornecedor, troca de plano bloqueada com regras de fornecedor.
- Cobrir 1.2: respostas simuladas no formato real, recusa de método diferente de GET, token nunca em objetos, erros nem logs, paginação e hierarquia.
- Cobrir 1.3: um teste por regra de conflito, idempotência, nada gravado antes da aprovação, decisões com autor e data.

**Critérios de aceite:**
- A suíte da área passa por inteiro em Postgres.

---

## Épico 3: Integração da conta com o ERP

### Story 3.1: Enviar o código da conta ao Superlógica

**Contexto:** o objetivo do negócio é lançar a despesa na conta certa. Hoje o payload enviado ao ERP leva só os campos extraídos.

**O que deve ser feito:**
- Incluir no payload canônico (`_canonical_payload` em `erp_publisher.py`) o condomínio e a conta classificada, com `external_id` do condomínio e código da conta.
- Definir com o time do conector como o Superlógica espera receber a conta.

**Critérios de aceite:**
- O payload do documento aprovado traz a conta vigente no momento do envio.
- Documento aprovado sem conta continua sendo enviado, com o campo vazio, e isso fica registrado.
- Teste de contrato do evento `erp.integration.requested` atualizado.

**Ponto em aberto:** formato do campo de conta no Superlógica e se conta ausente deve bloquear o envio.

---

## Épico 4: Qualidade da classificação

Problemas encontrados na rodada com 9 documentos reais da cliente.

### Story 4.1: Casar fornecedor pela raiz do CNPJ

**Contexto:** o boleto de gás trazia o CNPJ da matriz e a nota anexa trazia o da filial. A regra cadastrada só com a filial não casou.

**O que deve ser feito:**
- Casar o fornecedor pelos 8 primeiros dígitos do CNPJ (a raiz), mantendo a opção de cadastrar um CNPJ completo quando matriz e filial forem para contas diferentes.

**Critérios de aceite:**
- Regra cadastrada com a filial casa com documento da matriz, e vice-versa.
- Regra com CNPJ completo continua tendo prioridade sobre a regra por raiz.
- Testes cobrindo matriz, filial e conflito.

### Story 4.2: Refazer a classificação quando o analista edita campos

**Contexto:** a classificação roda só depois da extração. Se o analista corrige o CNPJ do beneficiário ou o do pagador, a sugestão continua a antiga.

**O que deve ser feito:**
- Reclassificar (e identificar o condomínio, se estiver em branco) ao salvar uma nova versão dos campos.
- Manter a regra atual: escolha manual do operador nunca é sobrescrita.

**Critérios de aceite:**
- Salvar campos gera os eventos de identificação e classificação quando algo muda.
- Falha na classificação não impede o salvamento dos campos.

### Story 4.3: Sugerir regra de fornecedor ao trocar a conta

**Contexto:** quando o analista troca a conta de um documento cujo fornecedor foi identificado, o mesmo erro se repete no próximo documento.

**O que deve ser feito:**
- Depois da troca, oferecer "Usar sempre esta conta para este fornecedor", criando a regra de fornecedor.

**Critérios de aceite:**
- A sugestão só aparece quando há fornecedor identificado e ainda não existe regra para ele.
- Aceitar cria a regra no condomínio do documento.

### Story 4.4: Identificar o condomínio quando o CNPJ do pagador vem malformado

**Contexto:** a extração por LLM devolve o CNPJ do pagador errado com frequência (exemplos: `0281955600013Q`, `419932577799`). A identificação por nome cobriu esses casos, mas sem o nome por extenso o condomínio ficaria em branco.

**O que deve ser feito:**
- Tentar recuperar o CNPJ do texto bruto quando o campo extraído for inválido.
- Registrar no evento de identificação quando o campo extraído foi descartado.

**Critérios de aceite:**
- Documento com campo de pagador inválido, mas CNPJ válido no texto, é identificado.
- Testes com os casos reais acima.

### Story 4.5: Medir a taxa de acerto com o dataset completo

**Contexto:** a rodada ponta a ponta usou 9 documentos e cadastro montado olhando as pastas da cliente. Isso prova o fluxo, mas não mede acerto.

**O que deve ser feito:**
- Transformar o script de avaliação em comando reproduzível.
- Cadastrar apenas o plano de contas e os condomínios, sem fornecedores, e rodar os 95 documentos de `docs_por_plano_de_contas`.
- Relatar acertos, erros e documentos sem sugestão, por regra e por pasta.

**Critérios de aceite:**
- Relatório com número de acertos, erros e sem sugestão, e motivo de cada erro.
- O dataset e a saída não vão para o repositório (contêm dados pessoais).

### Story 4.6: Confirmar o formato do RPA com a cliente

**Contexto:** a regra atual trata como RPA qualquer recibo assinado por pessoa física com CPF. Nos exemplos só há recibos simples, nenhum boleto de RPA.

**O que deve ser feito:**
- Obter com a cliente de 3 a 5 RPAs reais completos, com a guia ou o boleto de cada um, e a conta em que são lançados.
- Ajustar a regra: o mesmo recibo também aparece para serviços lançados em Manutenções (eletricista), e a guia de INSS do autônomo hoje cai em INSS.

**Critérios de aceite:**
- Regra de RPA coberta por testes com documentos reais anonimizados.
- Decisão registrada sobre a guia de INSS do autônomo.

---

## Épico 5: Dívida técnica

### Story 5.1: Corrigir os testes do frontend que já falhavam

**Contexto:** 16 testes de `flows.test.tsx`, `pagination.test.tsx` e `screens.test.tsx` falham no `dev`, antes das mudanças desta frente.

**O que deve ser feito:**
- Investigar e corrigir as falhas, ou isolar o que estiver obsoleto.

**Critérios de aceite:**
- A suíte do frontend passa por inteiro.

### Story 5.2: Preencher o layout do documento

**Contexto:** na rodada ponta a ponta o campo `layout` ficou vazio em todos os documentos. O schema veio do classificador de texto.

**O que deve ser feito:**
- Investigar por que o layout não foi preenchido e se isso afeta a escolha do schema.

**Critérios de aceite:**
- Causa documentada e, se for defeito, corrigida.

---

## Adiado (fora do escopo atual das telas)

Mantido como estava, para retomar depois das telas 1.6a a 1.6c.

### Story 1.7 (adiada): Edição de nomes alternativos, naturezas e fornecedores

**Contexto:** esses dados não existem no Superlógica, então continuam exigindo cadastro manual, e a importação nunca os sobrescreve.

**O que deve ser feito:**
- Telas simples para editar os nomes alternativos do condomínio, marcar a natureza das contas (INSS, FGTS, serviço de pessoa física) e cadastrar regras de fornecedor.
- Restringir a marcação de natureza a contas de despesa, porque um mesmo nome (ex. "Água") pode existir como receita e como despesa.
- Mostrar a mensagem da API quando houver duplicidade ou conta de outro plano.

**Critérios de aceite:**
- A natureza só pode ser marcada em conta analítica de despesa.
- Testes de componente e de serviço.

## Épico 2 (adiado): Classificação visível para o analista

Hoje a conta e o condomínio só aparecem no painel da tela de Validação.

### Story 2.1: Condomínio e conta nas listas

**Contexto:** o analista precisa enxergar o resultado sem abrir cada documento.

**O que deve ser feito:**
- Incluir condomínio e conta nas listas da Inbox, de Processos e de Aprovados.
- Incluir `condominium` e `classification` na listagem de documentos do backend, sem gerar consultas repetidas.
- Permitir filtrar por condomínio e por documentos sem conta sugerida.

**Critérios de aceite:**
- Documento sem condomínio ou sem conta mostra um estado explícito, não uma célula vazia.
- A paginação e a busca atuais continuam funcionando.
- Testes no backend e no frontend.

### Story 2.2: Histórico de alterações na tela

**Contexto:** o histórico já é gravado em `DocumentEvent`, mas não há como o analista consultá-lo.

**O que deve ser feito:**
- Criar um endpoint de leitura do histórico de identificação e classificação de um documento.
- Exibir na tela de Validação a linha do tempo: sugestão automática, trocas do operador, quem fez e o de/para.

**Critérios de aceite:**
- A linha do tempo mostra os eventos `document.condominium_identified` e `document.classified` em ordem cronológica.
- Eventos em que a sugestão não foi aplicada (por haver escolha manual) aparecem identificados.
- Testes no backend e no frontend.

---

---

## Ordem sugerida

1. Épico 1, backend: 1.4 e 1.5; a 1.8 pode correr em paralelo.
2. Telas: 1.6a, depois 1.6b e 1.6c.
3. Story 1.9 (testes de 1.1 a 1.3) fecha o épico e pode correr em paralelo.
4. Story 3.1: leva a conta ao ERP, que é o objetivo do negócio.
5. Épico 4: aumenta o acerto, começando pelas stories 4.1 e 4.5.
6. Épico 5: pode correr em paralelo.
7. Adiado: story 1.7 e Épico 2.
