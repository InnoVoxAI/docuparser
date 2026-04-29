Abaixo estão os **casos de uso completos (nível funcional + fluxo + UI)** cobrindo seus 5 cenários, já alinhados com a arquitetura que você definiu (orquestrador + OCR + LangExtract como microserviço).

---

# 📘 Casos de Uso – Sistema de Ingestão de Documentos

---

# 1. 📧 UC-01 – Entrada por Email → Aceitação no Superlógica

## 🎯 Atores

* Sistema de Email (externo)
* Backend Core (orquestrador)
* Operador

---

## 📌 Descrição

Processar documentos recebidos via email até envio aprovado ao **Superlógica Condomínios API**.

---

## 🔄 Fluxo Principal

1. Email recebido via API
2. Sistema extrai anexos
3. Cria `DocumentBatch`
4. Divide em `Documents`
5. Enfileira processamento
6. OCR executado
7. LangExtract extrai dados
8. Documento vai para validação
9. Operador revisa
10. Operador aprova
11. Sistema envia para Superlógica
12. Status atualizado

---

## ⚠️ Fluxos Alternativos

* Anexo inválido → status `REJECTED`
* OCR falha → `PROCESSING_ERROR`
* Dados incompletos → exige validação manual

---

## 🖥️ Interface Gráfica

### 📥 Tela: “Inbox de Documentos”

* Lista agrupada por email
* Campos:

  * remetente
  * data
  * nº de documentos
  * status do batch

👉 ação:

* “Abrir lote”

---

### 📄 Tela: “Detalhe do Documento”

Layout split:

| Documento        | Dados Extraídos |
| ---------------- | --------------- |
| PDF/Image viewer | JSON editável   |

👉 ações:

* editar campos
* aprovar
* rejeitar

---

---

# 2. 💬 UC-02 – Entrada via WhatsApp → Aceitação

## 🎯 Diferença principal

Entrada não estruturada e mais ruidosa

---

## 🔄 Fluxo Principal

1. Mensagem recebida via webhook
2. Arquivo extraído
3. Criação de `DocumentBatch`
4. Pipeline igual ao email

---

## ⚠️ Particularidades

* Imagens comprimidas
* Pode exigir mais intervenção humana
* Pode haver múltiplas imagens por mensagem

---

## 🖥️ Interface Gráfica

### 📱 Tela: “Origem WhatsApp”

* Identificação do número
* Preview da imagem
* Indicador de qualidade OCR (confidence)

👉 UX importante:

* destacar documentos com baixa confiança

---

---

# 3. 📄 UC-03 – Entrada via Paper Scan → Aceitação

## 🎯 Atores

* Operador (ação ativa)

---

## 🔄 Fluxo Principal

1. Operador escaneia documento
2. Faz upload no sistema
3. Informa metadados:

   * tipo (opcional)
   * origem = paper
4. Sistema cria `DocumentBatch`
5. Pipeline OCR → LangExtract → validação → integração

---

## ⚠️ Pontos críticos

* qualidade do scan
* múltiplas páginas
* desalinhamento de imagem

---

## 🖥️ Interface Gráfica

### 📤 Tela: “Upload Manual”

Campos:

* upload de arquivo
* tipo de documento (opcional)
* observações

👉 ação:

* “Processar documento”

---

### 🧠 UX importante:

* preview antes de enviar
* validação de formato (PDF/JPG)

---

---

# 4. 👨‍💼 UC-04 – Configuração do LangExtract (Supervisor)
Perfeito — segue o **UC-04 revisado no mesmo formato dos anteriores**, já pronto para substituir na sua spec.

---

# 4. 👨‍💼 UC-04 – Configuração do LangExtract (Supervisor)

## 🎯 Atores

* Supervisor

---

## 📌 Descrição

Permite ao supervisor configurar como o sistema realiza a extração de dados dos documentos, suportando **múltiplos tipos, layouts e versões de schemas**.

O sistema deve permitir a definição de padrões distintos para documentos com diferentes formatos (ex: boletos de bancos diferentes, faturas de concessionárias, etc.).

---

## 🧠 Conceitos Fundamentais

O modelo de configuração segue a hierarquia:

```text
Tipo de Documento → Layout → Versão do Schema
```

### Exemplo:

* boleto

  * banco_caixa

    * v1
    * v2
  * banco_bb
* fatura

  * energia
  * água

---

## 🔄 Fluxo Principal

1. Supervisor acessa módulo de configuração
2. Seleciona ou cria um **Tipo de Documento**
3. Cria ou seleciona um **Layout**
4. Cria ou edita um **Schema (versão)**
5. Define os campos a serem extraídos:

   * nome
   * tipo
   * obrigatório
6. Salva nova versão do schema
7. (Opcional) Testa o schema com um documento de exemplo (preview)
8. Ativa a versão
9. Sistema passa a utilizar automaticamente o novo schema

---

## 🧩 Exemplo de Configuração

```json
{
  "document_type": "boleto",
  "layout": "banco_caixa",
  "version": "v2",
  "fields": [
    {"name": "valor", "type": "currency", "required": true},
    {"name": "vencimento", "type": "date", "required": true},
    {"name": "linha_digitavel", "type": "string", "required": true}
  ]
}
```

---

## 🔍 Seleção de Layout no Pipeline

Após o OCR, o sistema deve identificar automaticamente o layout:

### Estratégias possíveis:

* heurísticas (palavras-chave, regex)
* modelo de classificação
* LLM (classificação semântica)

### Fluxo:

```text
OCR → Classificação de Layout → LangExtract (com schema correto)
```

---

## ⚠️ Fluxos Alternativos

* Layout não identificado → usar schema genérico ou enviar para validação manual
* Schema inválido → impedir ativação
* Conflito de versões → manter versionamento ativo (não sobrescrever)
* Falha no preview → exibir erro e bloquear publicação

---

## 🖥️ Interface Gráfica

### ⚙️ Tela: “Configuração do LangExtract”

#### Estrutura de navegação (sidebar)

```
📁 Tipos de Documento
   ├── Boleto
   │     ├── Banco Caixa
   │     ├── Banco do Brasil
   ├── Fatura
         ├── Energia
         ├── Água
```

---

### 🧱 Área principal – Editor de Schema

Tabela de campos:

| Campo           | Tipo     | Obrigatório | Ação   |
| --------------- | -------- | ----------- | ------ |
| valor           | currency | ✔           | editar |
| vencimento      | date     | ✔           | editar |
| linha_digitavel | string   | ✔           | editar |

---

### ➕ Ações disponíveis

* “Adicionar campo”
* “Salvar versão”
* “Ativar versão”
* “Duplicar versão”

---

### 🔁 Versionamento

* Lista de versões por layout
* Exibição de versão ativa
* Histórico de alterações

---

### 🔍 Preview (Funcionalidade crítica)

Permite validar o schema antes de ativar:

#### Fluxo:

1. Upload de documento exemplo
2. Execução do LangExtract com schema atual
3. Exibição do resultado estruturado

#### Interface:

| Documento        | Resultado     |
| ---------------- | ------------- |
| Viewer PDF/Image | JSON extraído |

---

### ⚠️ Regras de UX importantes

* Impedir ativação sem validação mínima
* Destacar campos obrigatórios não mapeados
* Mostrar erros de extração claramente
* Exibir versão ativa de forma visível

---

## 📌 Impacto no Sistema

* Permite adaptação a múltiplos formatos de documentos
* Elimina necessidade de deploy para ajustes
* Melhora acurácia ao longo do tempo
* Habilita evolução contínua do modelo de extração

---

## 🚀 Resumo

O UC-04 define um sistema onde:

* A extração é **configurável e versionada**
* O LangExtract é **orientado a schema**
* O sistema suporta **múltiplos layouts por tipo de documento**
* O supervisor tem controle total sobre a lógica de extração

---

# 5. 📊 UC-05 – Gestão de Documentos

## 🎯 Atores

* Operador
* Supervisor

---

## 📌 Objetivo

Gerenciar documentos ao longo do pipeline

---

## 📂 Estados

* RECEIVED
* PROCESSING
* PENDING_VALIDATION
* APPROVED
* REJECTED
* ERROR

---

## 🔄 Fluxos

### 📥 Recebidos

* documentos recém-ingestados

---

### ⚙️ Em processamento

* OCR ou LangExtract em execução

---

### ✅ Processados

* aguardando validação ou já integrados

---

## 🖥️ Interface Gráfica

### 📊 Dashboard principal

Cards:

* Recebidos (count)
* Em processamento
* Pendentes de validação
* Aprovados hoje

---

### 📋 Tabela de documentos

Colunas:

* ID
* origem (email / whatsapp / paper)
* tipo
* status
* confiança OCR
* data

---

### 🔍 Filtros

* status
* origem
* tipo de documento
* data

---

### 🎯 Ações rápidas

* abrir documento
* reprocessar
* aprovar em massa (bulk)

---

---

# 🧠 UX Geral do Sistema

## 🔥 Princípios importantes

### 1. “Human-in-the-loop first”

* tudo passa por validação
* UI precisa ser rápida e eficiente

---

### 2. “Confidence-driven UI”

* destacar:

  * baixa confiança
  * campos suspeitos

---

### 3. “Batch thinking”

* operar em lote (email/whatsapp)

---

### 4. “Correção rápida”

* edição inline
* navegação com teclado (produtividade)

---

# 🚀 Resumo

Você tem um sistema com 3 camadas claras:

* 📥 Ingestão (email, WhatsApp, scan)
* 🧠 Processamento (OCR + LangExtract LLM)
* 👨‍💼 Validação + integração

E a UI é essencialmente:

> 📊 gestão + 🔍 validação + ⚙️ configuração


