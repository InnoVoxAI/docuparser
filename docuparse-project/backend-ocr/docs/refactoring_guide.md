# Guia de Reestruturação — DocuParser Backend OCR

**Público-alvo:** Qualquer engenheiro que precise entender o que está sendo feito e por quê, mesmo sem ter trabalhado no projeto antes.

---

## O que é esse projeto?

O DocuParser é uma aplicação que recebe um arquivo (PDF ou imagem) pelo navegador e devolve o texto extraído desse arquivo junto com campos estruturados — como CNPJ do fornecedor, valor da nota fiscal, descrição do serviço, etc.

Por baixo dos panos, a aplicação usa OCR (Optical Character Recognition) — tecnologia que "lê" o conteúdo de imagens e PDFs escaneados, transformando pixels em texto. Existem vários "motores" de OCR disponíveis (Tesseract, PaddleOCR, OpenRouter com IA visual, entre outros), e o sistema precisa escolher o melhor para cada tipo de documento.

---

## Como está o código hoje?

O backend atual funciona — mas cresceu de forma orgânica, sem uma estrutura bem definida. O resultado é um código difícil de ler, testar e evoluir. Os principais problemas são:

### Problema 1: O `router.py` faz tudo

Existe um arquivo chamado `agent/router.py` com uma função principal chamada `route_and_process`. Essa função sozinha é responsável por:

- Classificar o tipo do documento
- Decidir qual engine de OCR usar
- Preparar o arquivo para processamento
- Chamar o engine de OCR
- Extrair campos como CNPJ e valor da nota
- Validar os campos extraídos
- Calcular um score de qualidade da extração
- Calcular a posição de cada campo no documento
- Montar o response final para o frontend

Imagine um cozinheiro que colhe os legumes, lava, corta, cozinha, empresta e entrega — tudo sozinho. Funciona, mas fica impossível de organizar quando o restaurante cresce.

### Problema 2: Classificação acontece em dois lugares

O sistema classifica documentos em: `digital_pdf` (PDF com texto digitalizado), `scanned_image` (PDF ou imagem escaneada) e `handwritten_complex` (manuscrito).

Essa classificação acontece em `agent/classifier.py`. O problema é que o engine `openrouter_engine.py` **também classifica o documento por conta própria**, internamente, para decidir como vai processá-lo. Resultado: o mesmo documento é analisado duas vezes, de formas diferentes, gerando inconsistência potencial.

### Problema 3: `validate_fields.py` tem mais de 2000 linhas

Um único arquivo mistura três responsabilidades completamente diferentes:

1. **Extração** de campos — encontrar onde está o CNPJ, o valor, o nome do fornecedor no texto bruto
2. **Validação** — checar se o CNPJ tem dígito verificador válido, se a moeda está no formato correto
3. **Scoring** — calcular quanto "confio" em cada campo extraído e decidir se preciso chamar uma IA para verificar

### Problema 4: Engines sem contrato comum

Cada engine de OCR tem uma interface levemente diferente. Alguns recebem os argumentos em ordens distintas, alguns retornam dicionários com chaves diferentes. Isso faz com que o `router.py` precise saber os detalhes internos de cada engine — acoplamento desnecessário.

---

## O que vamos mudar?

A reestruturação organiza o código em **camadas**, onde cada camada tem uma responsabilidade única e bem definida. Nenhuma camada "invade" a responsabilidade da outra.

As camadas são:

```
[ API ]          — só HTTP: recebe o arquivo, devolve o resultado
    │
[ Application ]  — só orquestração: coordena as camadas abaixo
    │
[ Domain ]       — regras de negócio: classificar, extrair campos, decidir engine
    │
[ Infrastructure ] — integrações externas: os engines de OCR de fato
    │
[ Shared ]       — utilitários: preprocessing de imagem, validações genéricas
```

---

## A nova estrutura, explicada

### `api/` — A porta de entrada

Essa pasta contém apenas o que é necessário para receber e responder requisições HTTP. Nada de lógica de negócio aqui.

```
api/
├── app.py              ← Configura o FastAPI (CORS, middlewares, inclui os routers)
├── routes/
│   └── document.py     ← Define os endpoints: POST /process, GET /engines
└── schemas/
    └── ocr_schema.py   ← Modelos de dados: como o request chega, como o response sai
```

O endpoint `/process` fica assim simples:

```python
@router.post("/process")
async def process_document_endpoint(file: UploadFile):
    result = process_document(await file.read(), file.filename)
    return result
```

Só isso. Sem lógica de OCR, sem validação de campos, sem nada além de receber e delegar.

---

### `application/` — O maestro

Essa pasta tem apenas um arquivo: `process_document.py`. Ele é o coração da aplicação — mas seu papel é **coordenar**, não executar.

```python
def process_document(file_bytes, filename):
    doc_type = classifier.classify(file_bytes, filename)   # 1. classifica
    engine   = resolver.get_engine(doc_type)               # 2. escolhe engine
    raw_text = engine.process(file_bytes, doc_type)        # 3. executa OCR
    fields   = extractor.extract(raw_text)                 # 4. extrai campos
    return build_response(raw_text, fields)                # 5. monta resposta
```

Claro, direto, sem surpresas. Qualquer engenheiro que abrir esse arquivo entende o fluxo completo em 30 segundos.

---

### `domain/` — As regras de negócio

Aqui ficam as decisões inteligentes da aplicação — as que não dependem de tecnologia externa.

**`classifier.py`** — Classifica o documento UMA vez. Analisa o arquivo (estrutura do PDF, características visuais da imagem) e retorna um tipo: `digital_pdf`, `scanned_image` ou `handwritten_complex`. Essa classificação acontece uma única vez no início do fluxo e é repassada para quem precisar.

**`engine_resolver.py`** — Implementa o **Strategy Pattern**: recebe o tipo do documento e retorna qual engine deve ser usado. Remove o bloco de `if/elif` gigante que estava no `router.py`.

```python
class EngineResolver:
    def get_engine(self, doc_type: str) -> BaseOCREngine:
        return self._registry[doc_type]
```

**`field_extractor.py`** — Analisa o texto bruto retornado pelo OCR e extrai campos estruturados: CNPJ, nome do fornecedor, valor da nota, etc. Inclui o scoring de confiança de cada campo.

---

### `infrastructure/` — O mundo externo

Aqui ficam as integrações com tecnologias externas — os engines de OCR. Nenhum código de domínio fica aqui.

**`engines/base_engine.py`** — Uma classe abstrata que define o contrato que todos os engines devem seguir:

```python
class BaseOCREngine(ABC):
    @abstractmethod
    def process(self, file_bytes: bytes, metadata: dict) -> dict:
        ...
```

Isso garante que todos os engines "falem a mesma língua". O `engine_resolver.py` pode retornar qualquer engine e a aplicação sabe que vai funcionar do mesmo jeito.

**`engines/openrouter_engine.py`** (e todos os outros) — Fazem **apenas OCR**. A classificação do documento (texto vs imagem) que estava dentro do OpenRouter é removida. O engine recebe o `doc_type` já classificado pelo `classifier.py` e usa essa informação ao invés de reclassificar por conta própria.

**`fallback/fallback_handler.py`** — Isola a lógica de fallback: quando a confiança do resultado principal é baixa, quando acionar outro engine, como combinar resultados de múltiplos engines.

---

### `shared/` — Utilitários reutilizáveis

Funções que qualquer camada pode usar, sem criar dependências circulares.

**`preprocessing.py`** — Pipelines de pré-processamento de imagem: deskew, CLAHE, denoise, upscale. Cada engine tem seu próprio pipeline, mas o código fica centralizado aqui.

**`validators.py`** — Validações genéricas: verificar dígito verificador do CNPJ, parsear valor monetário, validar formato de data. Nada específico de nenhum engine ou caso de uso.

---

## O que muda em cada arquivo existente

| Arquivo atual | O que acontece |
|--------------|----------------|
| `main.py` | Fundido com `api/app.py`; endpoint migrado para `api/routes/document.py` |
| `agent/router.py` | **Removido** — lógica distribuída entre `application/`, `domain/` e `infrastructure/` |
| `agent/classifier.py` | Movido para `domain/classifier.py` (sem mudança de lógica) |
| `engines/openrouter_engine.py` | Movido para `infrastructure/engines/`; classificação interna removida |
| `engines/*.py` (demais) | Movidos para `infrastructure/engines/`; herdam de `BaseOCREngine` |
| `utils/preprocessing.py` | Movido para `shared/preprocessing.py` |
| `utils/validate_fields.py` | **Fragmentado**: extração → `domain/field_extractor.py`; validações → `shared/validators.py` |
| `utils/ocr_fallback.py` | Movido para `infrastructure/fallback/fallback_handler.py` |

---

## Por que isso é melhor?

### Testabilidade

Com a estrutura atual, para testar a extração de campos você precisa subir todo o fluxo de OCR. Com a nova estrutura, `domain/field_extractor.py` pode ser testado isoladamente com texto bruto de entrada — sem precisar de arquivo, sem precisar de engine.

### Facilidade de adicionar novos engines

Hoje, adicionar um novo engine significa entrar no `router.py` e adicionar mais um `if`. Amanhã, basta criar um arquivo que herda de `BaseOCREngine` e registrá-lo no `engine_resolver.py`.

### Leitura do código

Hoje, para entender o que acontece quando um documento é processado, você precisa ler ~600 linhas de `router.py`. Com a nova estrutura, você lê `process_document.py` em 20 linhas e entende o fluxo completo.

### Classificação confiável

A classificação acontece uma única vez, em um lugar único, e o resultado é passado adiante. Sem risco de inconsistência entre o que o classifier e o engine acham que o documento é.

---

## O fluxo completo, antes e depois

**Antes:**

```
Request → main.py → router.route_and_process() → [tudo dentro dessa função] → Response
```

**Depois:**

```
Request
  └─► api/routes/document.py          (recebe o arquivo)
        └─► application/process_document.py    (coordena)
              ├─► domain/classifier.py          (classifica)
              ├─► domain/engine_resolver.py     (escolhe engine)
              ├─► infrastructure/engines/*.py   (executa OCR)
              └─► domain/field_extractor.py     (extrai campos)
                    └─► shared/validators.py    (valida campos)
                          └─► Response
```

Cada seta é uma responsabilidade. Cada caixa faz exatamente uma coisa.
