# Phase 0 — Research & Decisions: Fase A (mapa de download)

Resolve as escolhas técnicas e as **decisões em aberto** listadas na spec. Formato por item: **Decisão / Justificativa / Alternativas consideradas**.

## R1. Extração de PDF: links + texto com geometria (Salto 1)

- **Decisão**: usar **PyMuPDF** (`pymupdf`, já no `pyproject`). Por página: `page.get_links()` retorna as anotações de link com `uri` e `rect` (bounding box); `page.get_text("words")` retorna palavras com bounding box `(x0, y0, x1, y1, word, block, line, word_no)`. As duas camadas compartilham o mesmo sistema de coordenadas da página — exatamente o que o roteiro (Seção 5.1) exige.
- **Justificativa**: única lib do stack que expõe **anotações de link com coordenadas** e **texto com coordenadas** na mesma referência de página; performática e sem dependências de sistema. Já é dependência do projeto.
- **Alternativas**: `pdfplumber` (bom para texto/tabelas com coords, mas não expõe anotações de link de forma robusta); `pypdf`/`pdfminer` (anotações sim, geometria de texto mais trabalhosa). Rejeitadas por exigirem duas libs para as duas camadas.
- **Nota de import**: o `pyproject` lista tanto `pymupdf` quanto o pacote não relacionado `fitz`. Usar **`import pymupdf`** (API ≥1.24) para evitar ambiguidade com o pacote `fitz` do PyPI.

## R2. Cruzamento link ↔ categoria (heurística de linha, Seção 5.2)

- **Decisão**: (1) localizar as colunas pelos blocos de texto do **cabeçalho** conhecido (`Fornecedor`, `Categoria - Complemento`, ...), definindo a **faixa horizontal (x)** de cada coluna; (2) para cada link (na coluna Fornecedor), calcular o **centro vertical (y)** do seu `rect` e escolher, na faixa da coluna "Categoria - Complemento", o bloco de texto cujo centro-y esteja mais próximo, dentro de uma **tolerância** configurável (default `0.5 × altura média de linha`); (3) recuperar o fornecedor pelo texto sob o `rect` do link, com o parâmetro `itemRelacionado`/nome na URL como **validação cruzada**.
- **Justificativa**: o cabeçalho existe e é conhecido, tornando o mapeamento de colunas por `x` confiável; o casamento por proximidade-y é a forma natural de reconstruir "linhas" num PDF sem estrutura tabular. Espelha a Seção 5.2 do roteiro.
- **Ambiguidade (E-12)**: >1 candidato dentro da tolerância, ou nenhum → marcar a linha como **"revisar cruzamento"** no relatório em vez de adivinhar (FR-020, US3).
- **Alternativas**: detecção de tabela via `page.find_tables()` do PyMuPDF (frágil quando a "tabela" é só texto posicionado, sem linhas de grade) — usar apenas como reforço opcional, não como via principal.

## R3. Divisão categoria ↔ complemento (RN-8 / 5.2.1)

- **Decisão**: split no **primeiro** ` - ` (espaço-hífen-espaço). Antes → `categoria_bruta`; depois → `complemento`; `.strip()` em ambos. Sem ` - ` → célula inteira é `categoria_bruta`, `complemento` vazio. Múltiplos ` - ` → dividir só no primeiro. Implementar como função pura testável (`split(" - ", maxsplit=1)` sobre o separador exato).
- **Justificativa**: a categoria pode conter hífen **sem** espaços (`Construção-Reformas`), então o separador precisa ser estritamente ` - `. Regra determinística e trivialmente testável.
- **Alternativas**: split por regex de hífen simples — **rejeitado** (quebraria `Construção-Reformas`).

## R4. Heurística categoria → pasta (Seção 6)

- **Decisão**: pipeline de 3 estágios sobre a **`categoria_bruta`**: (A) **chave canônica** = minúsculas + remoção de acentos (Unicode→ASCII) + remoção de pontuação→espaço + colapso de espaços; (B) **dicionário ordenado de famílias** (padrão/prefixo → nome de pasta), primeira regra que casa vence, aplicado sobre a chave canônica; (C) **fallback derivado** = Title Case da `categoria_bruta` sanitizada como nome de pasta própria; se vazia/indeterminada → `_A_Revisar` (E-07). Dicionário e regras vivem em `config.py` (parametrizável, FR-024).
- **Justificativa**: resolve variações triviais (acento/caixa) determinísticamente, agrupa famílias, e nunca descarta categoria legítima (cria pasta própria), com `_A_Revisar` como rede de segurança. Espelha a Seção 6.
- **Dicionário inicial**: apenas `Construção-Reformas` está confirmado no universo real; os demais padrões (Água/Energia/Limpeza/etc.) são **ponto de partida**, validados/expandidos pela **passada de reconhecimento** (R8) antes de comprometer o mapa.

## R5. Autenticação no Google Drive (Salto 0)

- **Decisão**: fluxo **OAuth 2.0 "Desktop app"** com `google-auth-oauthlib` (`InstalledAppFlow.run_local_server`) + `google-api-python-client` (Drive API v3). Escopo **`https://www.googleapis.com/auth/drive.readonly`** (precisa ler bytes dos PDFs). `credentials.json` lido do work-dir; `token.json` salvo/reutilizado no work-dir; se inválido/expirado → tentar `refresh`; se falhar → apagar `token.json` e refazer login; falha dura → **E-01 fatal** com instrução de re-login.
- **Justificativa**: é o fluxo padrão e exatamente o descrito na Seção 1.1 do roteiro; o humano fornece só `credentials.json`, e o `token.json` nasce do 1º login.
- **Segurança**: `credentials.json`/`token.json` **nunca** versionados (já cobertos pela regra `downloads/` do `.gitignore`; adicionar também regras explícitas `credentials.json`/`token.json` como defesa em profundidade — ver R10). FR-004 / SC-011.
- **Alternativas**: service account (rejeitado — o roteiro fixa OAuth de usuário; as pastas são compartilhadas com uma conta humana); API key (não autoriza recursos privados).

## R6. Listagem e leitura dos PDFs (Salto 0)

- **Decisão**: Drive API `files.list` com `q="'<folderId>' in parents and mimeType='application/pdf'"` + varredura **recursiva** de subpastas (mimeType de pasta) por default (E-11, configurável). Baixar bytes via `files.get_media` para memória/`tempfile` (um PDF por vez). Pastas identificadas pelos IDs `1uJ6cZYbThBxiKcfcMmrlS-9dn-aVJfzr` e `13r1wG8rj8YFvYefPoDYhFg-aVESRZMgE`.
- **Justificativa**: cobre subpastas sem risco (ler a mais é seguro; ler a menos perderia arquivos); um PDF por vez mantém memória constante.
- **Marco de validação**: imprimir os nomes dos PDFs das duas pastas antes de prosseguir (Passo 1 do roteiro).

## R7. Resolução do Superlógica e raspagem (Salto 2)

- **Decisão**: **GET simples** com `requests` na URL `publico/arquivos?accesskey=...` (sem login; o `accesskey` autoriza). Parse com **BeautifulSoup(lxml)**; para **cada** `<a>` de download coletar `href` (→ `url_download`) e o `title` do `<img>` interno (→ `nome_arquivo`); ignorar o `filename=` da URL. **Retry com backoff** (default 3 tentativas, pausa base configurável) + pausa curta entre requisições (E-10); erro HTTP/accesskey expirado → E-04; sem âncoras → E-05; sem `title` → nome de fallback determinístico `{fornecedor_sanitizado}_{id_da_url}.pdf` (E-06). URL-decode em `title`/params (E-09).
- **Justificativa**: HTML estático confirmado (sem JS/headless); `requests`+`bs4` são o caminho mais simples e já disponível. Espelha Seção 5/Passo 5.
- **Alternativas**: navegador headless (Playwright) — **rejeitado**, desnecessário e pesado (conteúdo é estático).

## R8. Passada de reconhecimento de categorias (US5)

- **Decisão**: sub-passada opcional (`--recon`) que varre todos os PDFs, coleta as `categoria_bruta` **distintas** (já isoladas) + suas chaves canônicas + a pasta proposta, e emite `categorias_encontradas.csv` (`categoria_bruta | chave_canonica | pasta_destino_proposta`). Ponto de parada recomendado para o humano revisar/ajustar o dicionário (config) antes de gerar o mapa.
- **Justificativa**: torna a classificação auditável e ancora o dicionário no universo real do condomínio antes de comprometer o mapa (Seção 6, recomendação operacional).

## R9. Escrita incremental + idempotência (RN-6, FR-015/FR-016)

- **Decisão**: mapa em **CSV** (default; JSON aceitável). **Append linha a linha** conforme cada âncora é descoberta (arquivo aberto/flush por linha), com header escrito uma vez. Idempotência: manter em memória o **conjunto de `url_download` já presentes** (carregado do mapa existente na inicialização) e **pular** duplicatas; re-execução respeita o mapa existente. `status` inicial = `pendente`.
- **Justificativa**: sobrevive a interrupção no meio (progresso em disco) e não duplica em re-execuções; `url_download` é a chave natural (também é a chave de idempotência da Fase B — ver contrato).
- **Alternativas**: montar tudo em memória e salvar no fim — **rejeitado** (perde progresso em falha; viola FR-015).

## R10. Segurança de credenciais no git (FR-004 / SC-011)

- **Decisão**: `credentials.json` e `token.json` já caem sob a regra `downloads/` do `.gitignore` (confirmado por `git check-ignore`). Como o work-dir pode ser sobreposto via `--work-dir`, adicionar regras **explícitas** `credentials.json` e `token.json` ao `.gitignore` como defesa em profundidade. O pacote de código (rastreável) **não** contém segredos.
- **Justificativa**: garante SC-011 mesmo se o operador rodar de outro diretório.

## R11. Formato do mapa e demais saídas (decisão em aberto nº4)

- **Decisão**: **CSV** por padrão (`mapa_download.csv`), UTF-8, colunas conforme `contracts/mapa-download.md`. JSON permanece alternativa aceitável, mas o default é CSV por ser o esperado pela Fase B (`fase_b_download.md` assume `./mapa_download.csv`).
- **Justificativa**: alinha o contrato A↔B; a Fase B lê `mapa_download.csv` e atualiza a coluna `status`.

## Resolução das "Decisões em aberto" da spec

| Item | Resolução no plano |
|---|---|
| Varredura recursiva vs. só raiz do Drive | **Recursiva por default**, flag `--recursive/--no-recursive` (R6). Seguro; confirmável com o humano sem mudar código. |
| Composição do dicionário de famílias | Ponto de partida em `config.py`, **validado/expandido pela passada de reconhecimento** (R4/R8). |
| Tolerância de cruzamento, pausas, retry | **Parametrizáveis** em `config.py` com defaults sensatos (tolerância `0.5×linha`; 3 retries; pausa base configurável); calibrar com PDFs reais (R2/R7). |
| Formato do mapa (CSV vs JSON) | **CSV default** (R11); JSON opcional. |

## Escolhas de tooling

- **Gerência de deps**: `uv add google-api-python-client google-auth-oauthlib google-auth-httplib2 beautifulsoup4 lxml` (as duas últimas promovidas de transitivas a diretas). PyMuPDF/requests/typer já presentes.
- **CLI**: Typer (já no stack) — subcomandos/flags `--work-dir`, `--recon`, `--recursive/--no-recursive`, `--map-format csv|json`.
- **Lint/format**: ruff (padrão do projeto); type hints em tudo.
- **Testes**: pytest; mocks para Drive/Superlógica; fixtures de PDF/HTML.
