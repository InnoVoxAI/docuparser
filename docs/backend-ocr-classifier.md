# Backend OCR Classifier

Este documento explica o arquivo `docuparse-project/backend-ocr/domain/classifier.py`.

O classificador decide, uma unica vez no inicio do pipeline OCR, qual e o tipo estrutural do documento. Essa decisao e usada depois pelo `engine_resolver.py` para escolher o OCR adequado.

## Responsabilidade

`classifier.py` nao executa OCR, nao chama APIs externas e nao extrai campos semanticos. Ele apenas recebe:

- `filename`: nome original do arquivo.
- `content`: bytes do arquivo.

E retorna uma das classes:

- `digital_pdf`
- `scanned_image`
- `handwritten_complex`

## Classes

### `digital_pdf`

Representa PDF com camada de texto real. E o caso esperado para PDFs gerados digitalmente, como documentos exportados por sistemas, boletos digitais ou faturas com texto selecionavel.

No roteamento atual, essa classe usa `docling` por padrao.

### `scanned_image`

Representa imagem de documento ou PDF escaneado, sem camada de texto confiavel. Pode ser uma foto, scan, PDF de imagem ou arquivo de imagem comum.

No roteamento atual, essa classe usa `openrouter` por padrao.

### `handwritten_complex`

Representa documento com manuscrito, assinatura, anotacoes ou alto grau de irregularidade visual.

No roteamento atual, essa classe tambem usa `openrouter` por padrao, pois o modelo visual tende a lidar melhor com esse tipo de entrada do que OCR tradicional.

## Fluxo Principal

A funcao publica e:

```python
classify_document(filename: str, content: bytes) -> str
```

Ela segue esta ordem:

1. Normaliza o nome do arquivo para minusculas.
2. Infere a extensao pelo nome ou pelos bytes.
3. Extrai sinais semanticos do nome do arquivo.
4. Se for PDF, chama `_classify_pdf`.
5. Se for imagem, chama `_classify_image`.
6. Se a extensao nao for confiavel, tenta detectar PDF por assinatura `%PDF`.
7. Se nao for PDF, tenta decodificar como imagem.
8. Se tudo falhar, retorna `scanned_image`.

O fallback final para `scanned_image` e proposital: documento desconhecido deve ir para OCR visual, nao para extracao de texto de PDF.

## Sinais por Nome

A funcao `_extract_name_signals` procura tokens no nome do arquivo:

- `handwritten`: `manuscrito`, `handwritten`, `assinatura`, `signature`, `anotacao`, `anotação`
- `scanned`: `scan`, `scanned`, `digitalizado`, `foto`, `image`, `camera`, `print`
- `table`: `tabela`, `table`, `invoice`, `fatura`, `nota`, `extrato`, `statement`
- `mixed`: `misto`, `mixed`, `hibrido`, `híbrido`, `completo`, `complex`

Esses sinais nao decidem todos os casos sozinhos. Eles ajudam no desempate quando as features visuais ou textuais estao perto dos limites.

## Classificacao de PDF

`_classify_pdf` usa primeiro PyMuPDF para contar blocos estruturais do PDF. Essa regra preserva o comportamento do pipeline antigo `ocr_openrouter_pipeline.py`, que evitava OpenRouter quando o PDF ja tinha camada textual clara.

Depois, se a contagem de blocos nao for conclusiva, usa `pypdfium2` para abrir o PDF e analisa no maximo as duas primeiras paginas com features visuais.

### Blocos PyMuPDF

A primeira etapa chama `page.get_text("dict")` e conta:

- blocos de texto: `block["type"] == 0`;
- blocos de imagem: `block["type"] == 1`;
- fontes presentes no documento.

Se `txtblocks > 0` e `txtblocks >= imgblocks`, o PDF e classificado como `digital_pdf`, exceto quando o nome sugere manuscrito sem tambem sugerir scan.

Exemplo real:

```text
txtblocks=76
imgblocks=3
mode=digital_pdf
```

Esse tipo de PDF deve ir para Docling, nao para OpenRouter.

Para cada pagina amostrada, ele mede:

- quantidade de texto embutido;
- caracteristicas visuais da pagina renderizada;
- densidade de linhas;
- score de estrutura tabular;
- score aproximado de manuscrito;
- se a pagina parece imagem.

### Texto Embutido

O classificador chama:

```python
page.get_textpage().get_text_bounded()
```

O tamanho do texto extraido entra em `text_chars_total`.

Regras importantes:

- muito texto embutido tende a `digital_pdf`;
- pouco texto embutido em PDF tende a `scanned_image` ou `handwritten_complex`;
- texto embutido com sinais visuais muito irregulares pode virar `handwritten_complex`.

### Features Visuais

O PDF e renderizado para imagem e processado com OpenCV por `_extract_visual_features`.

As principais features sao:

- `edge_density`: densidade de bordas detectadas por Canny.
- `line_density`: densidade de linhas retas detectadas por Hough.
- `table_score`: presenca de linhas horizontais/verticais, util para tabelas e formularios.
- `handwriting_score`: proxy para irregularidade de tracos e baixa linearidade.
- `is_image_like`: indica se a pagina parece uma imagem escaneada.

### Regras Principais para PDF

O classificador retorna `digital_pdf` quando encontra sinais fortes de PDF textual:

- criterio forte por PyMuPDF: `txtblocks > 0 and txtblocks >= imgblocks`;
- ou, quando a contagem por blocos nao decide, criterios visuais/textuais abaixo:

- `text_chars_total >= 800`;
- baixa proporcao de paginas image-like;
- presenca de tabela ou sinal semantico de tabela;
- ausencia de sinal de manuscrito.

Tambem pode retornar `digital_pdf` com menos texto se:

- houver texto suficiente;
- o score de tabela for alto;
- o score de manuscrito for baixo.

Retorna `handwritten_complex` quando:

- o nome sugere manuscrito e nao sugere scan;
- `handwriting_score` e alto;
- ha pouco texto e sinais de documento misto/complexo.

Retorna `scanned_image` quando:

- ha pouco texto embutido;
- o documento parece imagem;
- nao ha evidencia forte de manuscrito.

Se houver erro ao abrir ou analisar o PDF, o fallback usa sinais do nome. Se o nome sugerir manuscrito/misto, retorna `handwritten_complex`; caso contrario, retorna `scanned_image`.

## Classificacao de Imagem

`_classify_image` tenta decodificar os bytes com OpenCV.

Se nao conseguir decodificar:

- retorna `handwritten_complex` se o nome sugerir manuscrito ou misto;
- caso contrario retorna `scanned_image`.

Se a imagem for valida, calcula as mesmas features visuais usadas para PDF.

Retorna `handwritten_complex` quando:

- o nome sugere manuscrito e nao sugere scan;
- o nome sugere documento misto e `handwriting_score >= 0.40`;
- `handwriting_score >= 0.60`.

Caso contrario retorna `scanned_image`.

## CLASSIFICATION_ENGINE_PREPROCESSING_HINTS

`CLASSIFICATION_ENGINE_PREPROCESSING_HINTS` nao escolhe o engine. Ele informa qual pre-processamento ou estrategia combina com cada engine para uma determinada classe.

Mapa atual:

```python
{
    "digital_pdf": {
        "docling": "prefer_original_pdf",
        "llamaparse": "prefer_original_pdf",
    },
    "scanned_image": {
        "openrouter": "render_pdf_or_image_for_vision_ocr",
        "paddle": "natural_rgb_with_clahe_and_light_deskew",
        "easyocr": "denoise_contrast_deskew_upscale",
    },
    "handwritten_complex": {
        "openrouter": "render_pdf_or_image_for_vision_ocr_handwritten",
        "easyocr": "denoise_contrast_deskew_upscale_handwritten",
        "paddle": "natural_rgb_with_clahe_and_light_deskew",
        "trocr": "natural_image_denoise_clahe_blueink_resize",
        "handwritten_region": "segment_regions_then_specialized_ocr",
    },
}
```

A funcao publica relacionada e:

```python
get_engine_preprocessing_hints_for_class(classification: str) -> dict[str, str]
```

O pipeline usa isso para expor metadados de diagnostico, como:

- classificacao do documento;
- engine escolhido;
- hint aplicado.

Esses metadados aparecem na aba Validacao.

## Relacao com Engine Resolver

A escolha final do OCR acontece em `domain/engine_resolver.py`, nao no classificador.

Mapa atual:

```python
ENGINE_DEFAULTS = {
    "digital_pdf": "docling",
    "scanned_image": "openrouter",
    "handwritten_complex": "openrouter",
}
```

Portanto:

- PDF texto -> `digital_pdf` -> `docling`
- PDF imagem -> `scanned_image` -> `openrouter`
- imagem comum -> `scanned_image` ou `handwritten_complex` -> `openrouter`
- manuscrito/complexo -> `handwritten_complex` -> `openrouter`

`selected_engine` na API ainda pode sobrescrever essa decisao, quando usado explicitamente.

## Limites Atuais

O classificador e heuristico. Ele nao usa modelo de ML treinado para classificar documentos; usa regras e features visuais baratas.

Pontos sensiveis:

- PDFs escaneados com pequenas camadas de texto residual podem ser confundidos com `digital_pdf`.
- Imagens impressas com muito ruido podem elevar `handwriting_score`.
- Documentos manuscritos muito limpos podem cair em `scanned_image`.
- Nomes de arquivo com tokens como `scan`, `assinatura`, `complex` influenciam desempates.

Por isso os metadados de classificacao e hint sao expostos na validacao: eles ajudam a auditar se o roteamento foi correto.

## Como Depurar

Durante o processamento, o classificador registra logs como:

- `text_chars_total`
- `table_score_total`
- `handwriting_score_total`
- `image_like_pages`
- `Score table`
- `Score handwriting`
- `Image-like page ratio`

Na tela de Validacao, verificar:

- `OCR utilizado`
- `classificacao`
- `hint`

Se um PDF de imagem estiver indo para `docling`, provavelmente foi classificado como `digital_pdf`.

Se um PDF texto estiver indo para `openrouter`, provavelmente foi classificado como `scanned_image` ou `handwritten_complex`.

## Onde Alterar Regras

Para mudar a classe retornada:

- PDFs: editar `_classify_pdf`.
- Imagens: editar `_classify_image`.
- Tokens de nome: editar `_extract_name_signals`.

Para mudar o OCR escolhido por classe:

- editar `ENGINE_DEFAULTS` em `docuparse-project/backend-ocr/domain/engine_resolver.py`.

Para mudar apenas os metadados/hints mostrados:

- editar `CLASSIFICATION_ENGINE_PREPROCESSING_HINTS` em `classifier.py`.
