# DocuParse — Como o sistema funciona (visão geral)

> **Para quem é este documento:** qualquer pessoa que precise entender o DocuParse sem ter
> participado do desenvolvimento — produto, operação, suporte, novos integrantes do time.
>
> Aqui não há código, nomes de arquivo ou detalhes de implementação. Se você precisa desse nível,
> veja [fluxo-aplicacao.md](fluxo-aplicacao.md).
>
> **Atualizado em:** 2026-07-27

---

## 1. O que o DocuParse faz, em três frases

O DocuParse recebe documentos (notas fiscais, boletos, contas de água, recibos), **lê o texto**
deles automaticamente, **identifica os campos importantes** (valor, CNPJ, número da nota, data…) e
apresenta tudo a uma pessoa para **conferência e aprovação**.

O objetivo é substituir a digitação manual: o sistema faz o trabalho pesado e o humano só confere
e corrige o que estiver errado.

Nada é aprovado sem uma pessoa decidir. O sistema **nunca aprova sozinho**.

---

## 2. O mapa do processo

### 2.1 Visão geral — o caminho completo

```mermaid
%%{init: {"flowchart": {"htmlLabels": true, "nodeSpacing": 45, "rankSpacing": 55, "padding": 14, "useMaxWidth": true}} }%%
flowchart TD
    subgraph ENTRADA["1 - ENTRADA"]
        A1["Upload pelo site"]
        A2["Anexo de e-mail"]
        A3["Arquivo por WhatsApp"]
    end

    subgraph RECEPCAO["2 - RECEPÇÃO"]
        B["Confere formato, tamanho<br/>e se já existe.<br/>Guarda o arquivo original"]
    end

    subgraph LEITURA["3 - LEITURA (OCR)"]
        C["Identifica o tipo de arquivo<br/>e transforma imagem em texto"]
    end

    subgraph EXTRACAO["4 - EXTRAÇÃO"]
        D["Escolhe o modelo de campos<br/>e usa IA para preencher<br/>cada campo a partir do texto"]
    end

    subgraph CONFERENCIA["5 - CONFERÊNCIA"]
        E["Pessoa revisa o documento<br/>lado a lado com os campos,<br/>corrige e decide"]
    end

    subgraph SAIDA["6 - SAÍDA"]
        F1(["APROVADO"])
        F2(["REJEITADO"])
    end

    A1 --> B
    A2 --> B
    A3 --> B
    B --> C --> D --> E
    E --> F1
    E --> F2
    F2 -.reprocessar.-> C

    style ENTRADA fill:#e8f0fe,stroke:#4285f4
    style RECEPCAO fill:#e8f0fe,stroke:#4285f4
    style LEITURA fill:#fff4e5,stroke:#f9a825
    style EXTRACAO fill:#fff4e5,stroke:#f9a825
    style CONFERENCIA fill:#e6f4ea,stroke:#34a853
    style SAIDA fill:#e6f4ea,stroke:#34a853
    style F1 fill:#34a853,color:#fff
    style F2 fill:#ea4335,color:#fff
```

**Legenda de cores:** 🔵 azul = entrada e recepção · 🟡 amarelo = processamento automático ·
🟢 verde = ação humana e resultado.

### 2.2 O que acontece quando algo dá errado

O sistema foi desenhado para **parar em um estado seguro e visível**, nunca para descartar o
documento em silêncio. Cada desvio abaixo deixa o documento parado numa etapa, aguardando ação.

```mermaid
%%{init: {"flowchart": {"htmlLabels": true, "nodeSpacing": 45, "rankSpacing": 55, "padding": 14, "useMaxWidth": true}} }%%
flowchart TD
    START(["Documento enviado"]) --> V{"Formato e<br/>tamanho válidos?"}
    V -->|não| E1["RECUSADO na hora<br/>Usuário vê o erro"]
    V -->|sim| DUP{"Já existe documento<br/>com esse nome?"}
    DUP -->|sim| E2["RECUSADO: duplicado<br/>Usuário vê o erro"]
    DUP -->|não| OK1["Documento registrado"]

    OK1 --> OCR{"Conseguiu ler<br/>o texto?"}
    OCR -->|não| E3["PARADO em 'Pendente'<br/>Ação: reprocessar leitura"]
    OCR -->|sim| MODEL{"Reconheceu o tipo<br/>de documento?"}

    MODEL -->|não| E4["PARADO com texto lido<br/>Ação: escolher o modelo<br/>na tela de conferência"]
    MODEL -->|sim| IA{"A IA respondeu?"}

    IA -->|não| E5["PARADO com texto lido<br/>Ação: rodar a extração<br/>novamente"]
    IA -->|sim, sem achar os valores| E6["ATENÇÃO: campos marcados<br/>como 'Valor não encontrado'<br/>Ação: preencher na conferência"]
    IA -->|sim| OK2["Campos preenchidos"]

    E4 --> CONF
    E5 --> CONF
    E6 --> CONF
    OK2 --> CONF{"Pessoa confere"}
    CONF -->|aprova| FIM1(["Aprovado"])
    CONF -->|rejeita, com motivo| FIM2(["Rejeitado"])
    CONF -->|corrige e salva| CONF

    style E1 fill:#fce8e6,stroke:#ea4335
    style E2 fill:#fce8e6,stroke:#ea4335
    style E3 fill:#fef7e0,stroke:#f9a825
    style E4 fill:#fef7e0,stroke:#f9a825
    style E5 fill:#fef7e0,stroke:#f9a825
    style E6 fill:#fef7e0,stroke:#f9a825
    style OK1 fill:#e8f0fe,stroke:#4285f4
    style OK2 fill:#e8f0fe,stroke:#4285f4
    style FIM1 fill:#34a853,color:#fff
    style FIM2 fill:#ea4335,color:#fff
```

**Como ler:** vermelho = recusado na entrada (o usuário vê o erro na hora) · amarelo = documento
parado, esperando uma ação · azul = seguiu adiante · verde/vermelho no fim = decisão registrada.

**Regra de ouro:** erro na entrada = **rejeição imediata e visível**. Erro no processamento =
**documento parado, esperando uma ação** — nunca perdido.

---

## 3. Quem faz o quê

O sistema é dividido em partes independentes, cada uma com uma única responsabilidade:

| Parte | Responsabilidade | Analogia |
|---|---|---|
| **Portaria** | Recebe os arquivos pelos três canais, confere o básico e guarda o original | O recepcionista que protocola a entrega |
| **Coordenação** | É o único que sabe o estado de cada documento e comanda as demais etapas | O gerente do processo |
| **Leitura** | Converte o arquivo em texto | O leitor que transcreve |
| **Extração** | A partir do texto, preenche os campos do formulário | O analista que preenche a planilha |
| **Interface** | Onde a pessoa envia, acompanha, confere e decide | A mesa de trabalho |
| **Arquivo** | Guarda os arquivos originais e o texto lido | O arquivo morto |

Duas consequências importantes desse desenho:

- **A Leitura e a Extração não guardam nada.** Elas recebem uma entrada, devolvem uma saída e
  esquecem. Só a Coordenação sabe em que pé está cada documento.
- **A Portaria não sabe o que é o documento.** Ela só valida o básico e protocola. Toda a
  inteligência vem depois.

---

## 4. As etapas, uma a uma

### Etapa 1 — Entrada

| Aspecto | Descrição |
|---|---|
| **O que entra** | Um arquivo: PDF, JPEG, PNG, TIFF ou WEBP |
| **De onde** | Upload no site · anexo de e-mail (caixa monitorada ou webhook) · arquivo enviado por WhatsApp |
| **O que sai** | O arquivo protocolado, com um número único |

**O que é conferido, nesta ordem:** o formato está na lista permitida? O arquivo não está vazio?
Está dentro do tamanho máximo? Já existe um documento com esse mesmo nome de arquivo?

> ⚠️ **Ponto de atenção:** a checagem de duplicidade é **pelo nome do arquivo**, não pelo
> conteúdo. Dois arquivos idênticos com nomes diferentes entram como documentos separados; e
> reenviar um arquivo com um nome já usado é recusado, mesmo sendo outro documento.

**Se falhar:** o usuário recebe a recusa **imediatamente**, com o motivo. Nada é registrado.

---

### Etapa 2 — Recepção

| Aspecto | Descrição |
|---|---|
| **O que entra** | O arquivo aprovado na etapa 1 |
| **O que acontece** | O original é guardado no arquivo digital e o documento é registrado como **Pendente** |
| **O que sai** | Um documento visível na caixa de entrada, ainda sem texto e sem campos |

O usuário já vê o documento na lista neste momento. As etapas seguintes acontecem em segundo
plano, e a tela se atualiza sozinha enquanto houver documentos em processamento.

> ⚠️ **Ponto de atenção:** se a Coordenação estiver fora do ar no momento exato do envio, o
> arquivo é guardado mas **pode não aparecer na caixa de entrada**. É a única situação em que um
> documento enviado com sucesso não fica visível. Sintoma: o usuário vê "documento recebido" mas
> ele não surge na lista.

---

### Etapa 3 — Leitura (OCR)

| Aspecto | Descrição |
|---|---|
| **O que entra** | O arquivo original |
| **O que sai** | O texto do documento e a indicação de que tipo de arquivo era |

Esta é a etapa mais variável do processo, porque documentos chegam de formas muito diferentes.
O sistema classifica cada arquivo em uma de três categorias e escolhe a técnica adequada:

| Categoria | O que é | Como é lido |
|---|---|---|
| **PDF digital** | Gerado por computador, já tem texto por dentro | Extração direta do texto — rápido e preciso |
| **Imagem escaneada** | Foto ou digitalização de papel | Leitura por inteligência artificial de visão |
| **Manuscrito / complexo** | Contém escrita à mão, assinaturas, layout difícil | Leitura por IA de visão, com tratamento reforçado |

**Como o sistema se protege:**

- Se a técnica escolhida falhar, ele **tenta automaticamente uma alternativa** e registra qual foi usada.
- Caso clássico: um PDF que *parece* digital mas é, na verdade, uma foto escaneada. A leitura
  direta volta vazia e o sistema **percebe, reclassifica e refaz** com IA de visão.

**Se falhar mesmo assim:** o documento fica parado como **Pendente**, sem texto. Ação disponível
na tela: **reprocessar a leitura**.

---

### Etapa 4 — Extração dos campos

| Aspecto | Descrição |
|---|---|
| **O que entra** | O texto lido na etapa anterior |
| **O que sai** | Os campos preenchidos (valor, CNPJ, número da nota…) com um grau de confiança |

Duas decisões acontecem aqui.

**Decisão 1 — qual modelo de campos usar?** Cada tipo de documento tem seu próprio conjunto de
campos. O sistema decide nesta ordem:

1. **Configuração explícita do administrador** para aquele tipo de documento — sempre vence.
2. **Reconhecimento automático pelo texto**: procura marcas típicas de nota fiscal, depois de
   conta de água, depois de boleto.
3. **Regra de reserva** por tipo de documento, para modelos personalizados.

Se nenhuma funcionar, o documento fica parado **com o texto já lido**, e o operador escolhe o
modelo manualmente na tela de conferência.

**Decisão 2 — o preenchimento.** O texto e a lista de campos esperados são enviados a um modelo de
IA, que devolve cada campo preenchido.

**Se a IA não achar um valor**, ela não inventa: o campo volta marcado como
**"Valor não encontrado"** e aparece assim na conferência, para a pessoa preencher.

**Se a IA falhar ou estiver indisponível**, o documento fica parado após a leitura, com o motivo
registrado e visível. Ação disponível: **rodar a extração novamente**, escolhendo o modelo.

---

### Etapa 5 — Conferência humana

| Aspecto | Descrição |
|---|---|
| **O que entra** | O documento com texto lido e campos preenchidos |
| **O que sai** | Uma decisão: aprovado, rejeitado ou corrigido |

Na tela de conferência a pessoa vê o **documento original lado a lado com os campos extraídos** e
pode:

- **Corrigir, adicionar ou remover campos** e salvar. Cada salvamento vira uma **versão numerada**
  e o histórico completo fica disponível — nada é sobrescrito de forma irrecuperável.
- **Aprovar** o documento.
- **Rejeitar**, informando obrigatoriamente o **motivo**.

**Três regras protegem esta etapa:**

| Regra | Por quê |
|---|---|
| Não é possível aprovar nem rejeitar um documento **sem extração feita** | Evita decisão sobre um documento em branco |
| A rejeição **exige motivo escrito** | Garante rastreabilidade da recusa |
| Se outra pessoa alterou os campos enquanto você editava, seu salvamento é **bloqueado** com um aviso | Evita que uma edição apague a de outra pessoa sem que ninguém perceba |

---

### Etapa 6 — Saída

| Resultado | O que significa | É definitivo? |
|---|---|---|
| **Aprovado** | Os dados foram conferidos e estão corretos | Sim |
| **Rejeitado** | O documento foi recusado, com motivo registrado | Não — pode ser reprocessado desde a leitura |

> ℹ️ **Estado atual:** o envio automático dos documentos aprovados para um ERP externo está
> **construído mas não ligado**. Hoje o fluxo termina em "Aprovado" dentro do DocuParse; a saída
> para sistemas externos ainda depende de um passo manual.

---

## 5. Os estados de um documento

Na tela, os documentos aparecem com três rótulos apenas — **Pendente**, **Aprovado** e
**Rejeitado**. "Pendente" agrupa todos os estágios intermediários:

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Pendente
    state Pendente {
        direction LR
        Registrado --> TextoLido: leitura ok
        TextoLido --> CamposExtraidos: extração ok
        CamposExtraidos --> AguardandoDecisao
    }
    Pendente --> Aprovado: pessoa aprova
    Pendente --> Rejeitado: pessoa rejeita (com motivo)
    Rejeitado --> Pendente: reprocessar
    Aprovado --> [*]
```

| O que você vê | O que está acontecendo por trás | O que fazer |
|---|---|---|
| Pendente (acabou de chegar) | Registrado, leitura em andamento | Aguardar |
| Pendente (parado, sem texto) | A leitura falhou | Reprocessar a leitura |
| Pendente (com texto, sem campos) | Não reconheceu o tipo, ou a extração falhou | Abrir e escolher o modelo, rodar a extração |
| Pendente (com campos) | Pronto para conferência | Conferir e decidir |
| Aprovado / Rejeitado | Decisão registrada | — |

---

## 6. Tabela rápida de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| "O Documento X já existe" no envio | Já há um documento com esse **nome de arquivo** | Renomear o arquivo ou verificar se é mesmo repetido |
| Envio recusado por formato | Extensão fora da lista permitida | Converter para PDF, JPEG, PNG, TIFF ou WEBP |
| Envio recusado por tamanho | Arquivo acima do limite | Reduzir ou dividir o arquivo |
| Enviou, mas não aparece na lista | Falha de comunicação interna no momento do envio | Reenviar; se persistir, é problema de infraestrutura |
| Fica "Pendente" e nunca mostra texto | A leitura falhou | Reprocessar a leitura |
| Tem texto, mas nenhum campo | Tipo de documento não reconhecido, ou IA indisponível | Abrir, escolher o modelo, rodar a extração |
| Todos os campos dizem "Valor não encontrado" | A IA não localizou os valores — ou está sem configuração de acesso | Preencher manualmente; se for sistemático, é configuração |
| Não consegue aprovar | O documento não tem extração feita | Rodar a extração antes de decidir |
| "A lista foi atualizada por outro processo" | Outra pessoa salvou campos enquanto você editava | Recarregar a versão atual e refazer a edição |
| Documento demora muito | Fila de processamento cheia (poucos documentos em paralelo por vez) | Aguardar |

---

## 7. Coisas importantes de saber

**Separação entre clientes.** Cada cliente (tenant) tem seus dados completamente isolados — um
nunca enxerga documentos do outro. Usuários pertencem a um cliente, e administradores podem
alternar entre clientes quando têm permissão para isso.

**Permissões.** O que cada pessoa vê e pode fazer é controlado por papéis: enviar documentos, ver
a caixa de entrada, conferir e decidir, acessar operações, administrar usuários, papéis e
clientes. Quem não tem a permissão não vê o menu correspondente.

**Nada é aprovado automaticamente.** Toda aprovação passa por uma pessoa, mesmo quando a IA
devolve confiança alta.

**Histórico preservado.** Toda alteração de campos é versionada e o histórico é consultável. As
decisões ficam registradas com autor, data e motivo.

**Processamento em segundo plano.** Leitura e extração não travam a tela: o documento aparece
imediatamente e evolui sozinho. A contrapartida é que uma falha nessas etapas **não gera um alerta
para o usuário** — ela se manifesta como um documento que "não avança". Por isso a tabela da
seção 6 é importante para a operação.

**Capacidade.** Os documentos são processados alguns por vez, não todos simultaneamente. Um lote
grande é processado em fila, na ordem de chegada.

---

## 8. Limites conhecidos hoje

| Limite | Impacto prático |
|---|---|
| Duplicidade é verificada pelo **nome do arquivo**, não pelo conteúdo | O mesmo documento com dois nomes entra duas vezes |
| A **saída para ERP** existe mas não está ligada | Documentos aprovados não são enviados automaticamente a sistemas externos |
| Falhas de processamento **não notificam ninguém** | Dependem de alguém observar a caixa de entrada |
| O reconhecimento automático de tipo cobre **nota fiscal, conta de água e boleto** | Outros tipos exigem configuração de modelo pelo administrador |
| A leitura por IA depende de um serviço externo | Sem ele configurado, os campos voltam vazios (sinalizados, não silenciosos) |

---

## 9. Glossário

| Termo | Significado |
|---|---|
| **OCR / Leitura** | Processo de transformar imagem em texto |
| **Extração** | Preencher campos estruturados (valor, CNPJ…) a partir do texto |
| **Modelo / Schema** | A lista de campos esperados para um tipo de documento e as instruções de como encontrá-los |
| **Layout** | Formato visual reconhecido de um documento (ex.: boleto de determinado banco) |
| **Confiança** | Estimativa de quão certo o sistema está sobre um valor extraído |
| **Versão de campos** | Uma "foto" imutável da lista de campos num momento; cada salvamento cria uma nova |
| **Tenant / Cliente** | Organização cujos dados ficam isolados dos demais |
| **Canal** | Por onde o documento chegou: upload, e-mail ou WhatsApp |
| **Pendente** | Qualquer estágio antes da decisão humana |
| **Reprocessar** | Refazer a leitura do documento desde o arquivo original |
