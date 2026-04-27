# DocuParse

O **DocuParse** é um sistema experimental de processamento de documentos focado na extração de dados estruturados de arquivos complexos e manuscritos. O projeto utiliza uma abordagem de microserviços e integra múltiplos motores de OCR, incluindo inteligência artificial de ponta (DeepSeek).

## 🚀 O que o projeto faz?

O objetivo principal é transformar conteúdo não estruturado em documentos (PDFs ou imagens) em dados estruturados (JSON). Ele é especialmente eficaz em cenários desafiadores, como:
- Documentos manuscritos.
- Layouts complexos e não padronizados.
- Formulários e notas fiscais.

## 🏗️ Arquitetura do Sistema

O sistema é composto por três microserviços principais que trabalham em conjunto:

1.  **Frontend (React + Vite)**: Interface de usuário moderna e responsiva para upload de arquivos e visualização dos dados extraídos. (Porta `3000`)
2.  **Backend Core (Django)**: Gateway principal do sistema, responsável pela gestão de usuários, autenticação e orquestração do fluxo de documentos. (Porta `8000`)
3.  **Backend OCR (FastAPI)**: O núcleo de processamento e inteligência. (Porta `8080`)
    - **Classificação Inteligente**: Analisa o documento para decidir qual motor de extração é o mais adequado.
    - **Motores Suportados**: Tesseract, EasyOCR, Docling e LlamaParse.
    - **Integração DeepSeek**: Para casos complexos e manuscritos, utiliza o modelo **DeepSeek-V2** através de uma instância local do **Ollama**.

## 🛠️ Tecnologias Utilizadas

- **Linguagens**: Python, JavaScript
- **Frameworks**: Django (Backend Core), FastAPI (Backend OCR), React (Frontend)
- **IA/OCR**: DeepSeek, Tesseract, Docling, EasyOCR
- **Infraestrutura**: Docker, Docker Compose, Ollama

## 🚦 Como Executar

A forma mais simples de rodar o DocuParse é utilizando o Docker Compose, que orquestra todos os serviços automaticamente.

### Pré-requisitos
- [Docker](https://www.docker.com/) e Docker Compose instalados.
- [Ollama](https://ollama.com/) instalado e rodando (necessário para o motor DeepSeek).

### Passo a Passo

1.  **Clonar o repositório**:
    ```bash
    git clone <url-do-repositorio>
    cd docuparser
    ```

2.  **Configurar Variáveis de Ambiente**:
    - Navegue até a pasta do projeto principal:
      ```bash
      cd docuparse-project
      ```
    - Crie um arquivo `.env` baseado no exemplo disponível (se houver) ou configure as chaves de API necessárias e endpoints.

3.  **Subir os containers**:
    Na raiz do repositório, execute:
    ```bash
    bash run-pipe.sh
    ```

4.  **Acessar as Aplicações**:
    - **Frontend**: [http://localhost:5173](http://localhost:5173)
    - **API Core (Django)**: [http://localhost:8000](http://localhost:8000)
    - **API OCR (FastAPI)**: [http://localhost:8080](http://localhost:8080)

5.  **Parar os containers**:
    ```bash
    cd docuparse-project
    docker compose down
    ```

---

## 📝 Notas de Desenvolvimento
O motor DeepSeek utiliza a API compatível com OpenAI do Ollama. Certifique-se de que o Ollama esteja acessível via `http://host.docker.internal:11434` (no Windows/Mac) ou configure o endereço correto no seu arquivo `.env`.
