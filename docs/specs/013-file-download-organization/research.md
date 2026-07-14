# Phase 0 — Research: Fase B (Download e organização)

Resolve as decisões técnicas e as **5 decisões em aberto** do roteiro (`fase_b_download.md` §9). Nenhum `NEEDS CLARIFICATION` permanece: cada questão tem um default sensato e determinístico, calibrável na execução real. Formato: **Decisão / Justificativa / Alternativas consideradas**.

---

## D1 — Estratégia anti-colisão determinística (E-06, decisão em aberto §9.1)

- **Decisão**: nome final = `nome_arquivo` do mapa **quando não há colisão**; havendo colisão no caminho de destino, prefixar com o **`id` da `url_download`**: `{id}_{nome_arquivo}`. O `id` é extraído dos parâmetros da própria URL (`downloadarquivo?id=...`). É **estável** (mesma linha → sempre o mesmo `id`), portanto o nome final é **determinístico** entre execuções. Se, ainda assim, `{id}_{nome_arquivo}` colidir com um destino de **outra** `url_download`, é sinal de anomalia → linha vira erro (não sobrescreve).
- **Justificativa**: nomes de scanner (`img20260602_08372180.pdf`) repetem entre fornecedores; o `id` é o discriminador natural, já presente na URL e único por arquivo no Superlógica. Determinismo é pré-requisito da retomada idempotente (RN-4): numa reexecução, a mesma linha reencontra exatamente o mesmo caminho e é pulada.
- **Alternativas consideradas**: (a) sufixos incrementais `(1)`, `(2)` — **rejeitado** pelo roteiro: não-determinísticos, quebram a retomada (o mesmo arquivo poderia virar `(3)` numa reexecução). (b) `{fornecedor_sanitizado}__{nome}` — bom discriminador, mas o `fornecedor` é texto livre mais longo e menos único que o `id`; fica como fallback caso a URL não traga `id`.

## D2 — Validação de conteúdo: alvo sempre PDF (E-05, decisão em aberto §9.2)

- **Decisão**: validar por **assinatura de bytes** — os primeiros bytes do conteúdo devem começar com `%PDF` (`b"%PDF"`). Complementarmente, desconfiar do `Content-Type`: `text/html` numa resposta 200 é forte indício de página de erro/login. Conteúdo que falha a validação **não é salvo**; a linha vira erro (E-05). A verificação de bytes é a autoridade (o `Content-Type` pode mentir); é encapsulada numa função pura `looks_like_pdf(head_bytes) -> bool`, facilmente generalizável se surgirem outros tipos no futuro.
- **Justificativa**: um `200 OK` não garante o arquivo — `accesskey` expirado costuma devolver HTML de erro. A assinatura `%PDF` é barata, robusta e testável sem rede. O roteiro confirma que o alvo é sempre PDF por ora.
- **Alternativas consideradas**: confiar só no `Content-Type` — **rejeitado** (falsificável / ausente). Validar o PDF inteiro abrindo com PyMuPDF — **rejeitado**: traria a dependência pesada da Fase A para dentro da Fase B só para validar, contra a decisão de manter a Fase B enxuta (só `requests`). A assinatura basta para separar arquivo de página-de-erro.

## D3 — Detecção de "provável expiração" de `accesskey`/`hash` (E-04)

- **Decisão**: sinalizar `possível expiração` quando o erro casar um dos padrões: (a) HTTP **403/401/410** na `url_download`; ou (b) resposta **200 com conteúdo HTML** (falha em D2) cujo corpo contém marcadores de sessão/expiração (ex.: `accesskey`, `login`, `expirado`/`expired`, `acesso`). A classificação é uma função pura sobre `(status_code, content_type, head_bytes)`; o motivo do erro no relatório recebe o rótulo explícito e a recomendação de re-rodar a Fase A.
- **Justificativa**: a Fase B pode rodar muito depois da Fase A; expiração é o modo de falha operacional mais provável e o roteiro exige sinalizá-lo com caminho de recuperação claro (E-04). Tratar como erro comum (E-03) mas **rotulado** evita que o operador confunda expiração com link quebrado.
- **Alternativas consideradas**: tentar renovar o `accesskey` na Fase B — **fora de escopo** (isso é re-rodar a Fase A). Só marcar sem recomendar ação — **rejeitado**: perde o valor operacional.

## D4 — HTTP: sessão, pausa, timeout, retry/backoff (E-03/E-09/E-10, decisão em aberto §9.3)

- **Decisão**: reusar o **mesmo padrão da Fase A** (`superlogica.py::fetch_page`): `requests.Session` reutilizada, `timeout` por requisição, **N tentativas** (default 3) com **backoff progressivo** (base × tentativa) e **pausa** entre requisições. Erros não-repetíveis (`{400,401,403,404,410}`) **não** re-tentam (aborta cedo → erro, com possível rótulo de expiração via D3). O download usa **streaming** (`stream=True`) para gravar direto no `.part` sem carregar tudo em memória. Todos os valores são **configuráveis** (defaults: pausa 1,0s, timeout 30s, retries 3, backoff base 2,0s) — os mesmos defaults da Fase A, para consistência operacional, calibráveis conforme volume.
- **Justificativa**: o comportamento de rede desejado é idêntico ao da Fase A (educação com o Superlógica, resiliência a 5xx/rate-limit). Reusar o padrão reduz superfície de bug e mantém terminologia/config consistentes. A `Callable[[float], None]` de sleep injetável (como na Fase A) permite testar backoff **sem dormir**.
- **Alternativas consideradas**: `urllib3.Retry`/`HTTPAdapter` — funciona, mas o retry manual da Fase A já é testado e dá controle fino sobre o rótulo de expiração e a pausa entre linhas. Baixar tudo em memória e depois validar — **rejeitado**: streaming para `.part` casa naturalmente com a gravação atômica (D5) e com arquivos grandes.

## D5 — Gravação atômica (E-11)

- **Decisão**: baixar (streaming) para `<destino>.part` **no mesmo diretório** do destino final; só **após** o download completo **e** a validação de conteúdo (D2), renomear (`os.replace`) para o nome final. Se algo falhar antes disso, remover o `.part`. `os.replace` é atômico dentro do mesmo filesystem.
- **Justificativa**: garante que **nunca** exista um arquivo com nome definitivo e conteúdo incompleto (SC-002) — a retomada (RN-4) enxerga corretamente o que está concluído. O `.part` no mesmo diretório assegura que o rename não cruze filesystem.
- **Alternativas consideradas**: `tempfile` no diretório temporário do SO + `shutil.move` — **rejeitado**: pode cruzar filesystem (rename vira cópia não-atômica). Validar antes de escrever qualquer byte — impossível com streaming; por isso validamos o **head** (primeiros bytes) durante/apos o stream e promovemos só no fim.

## D6 — Retomada idempotente: status + presença em disco (RN-4/E-12)

- **Decisão**: a retomada combina **duas** fontes de verdade, como o roteiro pede: (a) a coluna `status` do mapa; e (b) a presença do arquivo no caminho final esperado. Uma linha é **pulada** só se `status = baixado` **E** o arquivo existe no destino determinístico (D1). Se o status diz `baixado` mas o arquivo sumiu, re-baixa (o status sozinho não basta). O conjunto de `url_download` já concluídas também é carregado do **CSV final existente** (via o mesmo padrão de dedup da Fase A) para não duplicar linhas (RN-6). Ao concluir, `status → baixado`; ao falhar em definitivo, `status → erro`. Linhas `erro` são **re-tentadas** numa reexecução (não são puladas).
- **Justificativa**: cobre interrupção a qualquer ponto sem rebaixar nem duplicar (SC-005/SC-006). Cruzar status com disco evita os dois enganos: pular algo que não existe, ou rebaixar algo que existe.
- **Alternativas consideradas**: confiar só no status — **rejeitado** (arquivo pode ter sido apagado/movido). Confiar só no disco — **rejeitado**: sem o status não se distingue "baixado" de "colisão de nome de outra linha".

## D7 — Atualização do `status` no mapa in-place (RN-4)

- **Decisão**: a Fase B **lê todo o mapa** (é pequeno — dezenas/centenas de linhas), processa linha a linha e **reescreve o mapa** com a coluna `status` atualizada, de forma segura (escrever em `mapa_download.csv.tmp` → `os.replace`), preservando **todas** as demais colunas exatamente como vieram (a Fase B trata as colunas de conteúdo como **somente leitura** — FR-004). A reescrita ocorre ao final de cada linha processada (ou em lote com flush frequente), para que uma interrupção deixe o mapa consistente. As colunas seguem o contrato 012 (`MAP_COLUMNS`).
- **Justificativa**: o mapa é o registro de progresso da retomada. Reescrever via arquivo temporário + rename evita corromper o mapa se a escrita for interrompida (mesmo princípio atômico de D5). O mapa é pequeno o suficiente para reescrita completa ser trivial; não há ganho em edição in-place byte a byte.
- **Alternativas consideradas**: um arquivo de estado separado (`.state.json`) — **rejeitado**: o roteiro define o mapa (coluna `status`) como o registro de retomada; um segundo arquivo divergiria. Append-only de deltas de status — complexidade desnecessária para este volume.

## D8 — CSV final incremental + dedup (RN-5/RN-6, decisão em aberto §9.4)

- **Decisão**: escrever o `relatorio_final.csv` em modo **append**, uma linha **imediatamente** após cada download bem-sucedido, com flush em disco (mesmo padrão do `MapWriter` da Fase A). **Dedup por `url_download`**: ao iniciar, carregar as `url_download` já presentes no CSV final; não regravar. Colunas mínimas (roteiro §3.2): `nome_arquivo` (nome efetivamente salvo, com discriminador se houve colisão), `hyperlink_origem`, `categoria` (= `categoria_bruta`), `caminho_local`; **recomendadas** e incluídas: `pasta_destino`, `fornecedor`. Conjunto ajustável ao consumidor (contrato em `contracts/relatorio-final.md`).
- **Justificativa**: incrementalidade garante que interrupção não perca o registro do que já foi baixado (SC-006). Dedup por `url_download` (a mesma chave de idempotência do mapa) impede duplicatas na reexecução. Reusar o padrão de escrita da Fase A mantém consistência.
- **Alternativas consideradas**: escrever tudo no fim — **rejeitado** (perde progresso na interrupção). Dedup por caminho local — a `url_download` é a chave canônica e única (contrato 012), mais robusta.

## D9 — Reuso de código vs. duplicação (fronteira entre as fases)

- **Decisão**: **reusar** apenas `superlogica_download_map.sanitize` (import direto). **Replicar deliberadamente** o *padrão* de HTTP com retry/backoff e o *padrão* de escrita incremental/dedup — mas como **código próprio** da Fase B (`downloader.py`, `outputs.py`), não import — porque a semântica difere (a Fase A busca **HTML de página**; a Fase B baixa **bytes de arquivo** com streaming, validação de assinatura e gravação atômica). A interface entre as fases é o **arquivo** (`mapa_download.csv`), não a biblioteca.
- **Justificativa**: `sanitize` é lógica de segurança idêntica e estável — duplicá-la seria risco (duas cópias divergindo). Já o download difere o suficiente (streaming, `%PDF`, `.part`) que forçar reuso acoplaria as fases e importaria a semântica errada. Mantém cada fase enxuta e independente (a Fase B não arrasta as deps pesadas da Fase A).
- **Alternativas consideradas**: extrair um pacote `common/` compartilhado — **adiado**: com só uma função realmente comum (`sanitize`), um pacote compartilhado é over-engineering agora; se a fronteira crescer, extrai-se depois. Copiar `sanitize` — **rejeitado** (duplicação de código de segurança).

## D10 — Sem dependências novas; Constitution/Technology Standards

- **Decisão**: a Fase B **não adiciona nenhuma dependência** — usa `requests` e `Typer` já no `pyproject`, e reusa `sanitize`. Não há `google-*`, `pymupdf` nem `beautifulsoup4/lxml`.
- **Justificativa**: reforça o PASS em Technology Standards (nenhuma engine de OCR nem IA na nuvem; nem sequer uma dep nova a justificar). Menor superfície, execução mais leve que a Fase A.
- **Alternativas consideradas**: nenhuma — é o caminho de menor dependência.

---

## Resumo das decisões em aberto do roteiro (§9) → resolvidas

| # (roteiro) | Questão | Resolução |
|---|---|---|
| 9.1 | Formato anti-colisão | `{id}_{nome_arquivo}` determinístico (D1) |
| 9.2 | Tipos além de PDF | Alvo = PDF; validação por assinatura `%PDF` generalizável (D2) |
| 9.3 | Pausa/timeout/retry | Defaults da Fase A (1,0s / 30s / 3× backoff 2,0s), configuráveis (D4) |
| 9.4 | Colunas do CSV final | Mínimo + recomendadas; contrato em `contracts/relatorio-final.md` (D8) |
| 9.5 | Janela de expiração | Desconhecida; sinal E-04 + recomendação de re-rodar a Fase A (D3) |
