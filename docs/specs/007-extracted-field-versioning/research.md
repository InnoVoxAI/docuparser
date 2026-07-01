# Phase 0 — Research: Edição e Versionamento de Campos Extraídos

Este documento consolida as decisões técnicas que resolvem os pontos em aberto do Technical Context. Não há marcadores `NEEDS CLARIFICATION` remanescentes (todos resolvidos no `/speckit-clarify` ou por decisão de design abaixo).

## D1 — Estratégia de armazenamento das versões

**Decision**: Snapshot completo por versão em uma nova tabela `ExtractionFieldVersion` (cada linha guarda a lista inteira de campos em um JSONField), mantendo o `ExtractionResult` (OneToOne com `Document`) como ponteiro de leitura sempre sincronizado com a versão ativa.

**Rationale**:
- A spec exige imutabilidade total e independência entre versões (FR-013, FR-016) e que "cada versão preserve seu próprio conjunto" (Key Entities). Snapshot completo é o modelo mais simples que garante isso sem reconstrução por diffs.
- Manter `ExtractionResult` como espelho da versão ativa preserva compatibilidade com tudo que já consome `document.extraction_result.fields` (serializers `DocumentListSerializer`/`DocumentDetailSerializer`, exportador aprovado, frontend) — FR-015/FR-023 ("processos subsequentes usam a versão ativa") são satisfeitos sem refatorar consumidores.
- O volume esperado é baixo (unidades/dezenas de versões, dezenas de campos), então o custo de duplicar o snapshot é desprezível.

**Alternatives considered**:
- *Versão por diffs/eventos*: reduz armazenamento mas exige reconstrução e complica auditoria/leitura do histórico (FR-020). Rejeitado: complexidade desnecessária para o volume real.
- *Substituir `ExtractionResult` por uma view/registro ativo*: forçaria refatorar todos os consumidores existentes e migrações de dados maiores. Rejeitado: risco e escopo maiores sem ganho.

## D2 — Versão ativa única e numeração

**Decision**: Numeração sequencial por documento (`version_number` inteiro começando em 1) e flag booleana `is_active`, com `UniqueConstraint` parcial garantindo no máximo uma versão ativa por documento. A criação de versão e a troca de ativa ocorrem dentro de uma transação atômica que desativa a versão ativa anterior e ativa a nova.

**Rationale**:
- FR-014 ("no máximo uma versão ativa por documento; ativa = mais recente"). A constraint parcial (`is_active=True`) no PostgreSQL (`condition=Q(is_active=True)`) impede inconsistência no nível do banco.
- `version_number` sequencial por documento dá identificação clara e ordenável no histórico (FR-017, FR-019) e é mais legível que UUID para o usuário.
- Transação atômica evita janela com zero ou duas versões ativas.

**Alternatives considered**:
- *Apenas ordenar por `created_at` sem flag*: leitura simples, mas não protege contra ambiguidade e dificulta consultas de "ativa". Rejeitado em favor da flag + constraint explícitas (FR-014).
- *`version_number` global*: perderia legibilidade por documento. Rejeitado.

## D3 — Concorrência ao salvar (FR-024)

**Decision**: Concorrência otimista. O endpoint de "Salvar Alterações" recebe o número da versão base (`base_version_number`) sobre a qual o usuário editou. Se essa não for mais a versão ativa, o servidor responde `409 Conflict` com mensagem orientando recarregar; nenhuma versão nova é criada.

**Rationale**:
- Implementa diretamente a decisão do clarify (FR-024 = bloquear e exigir recarregar). Simples, sem locks, sem estado de sessão no servidor.
- Alinhado ao Princípio III (mensagem de erro acionável: "A lista foi atualizada por outro processo. Recarregue a versão ativa antes de salvar.").

**Alternatives considered**:
- *Lock pessimista / lock de documento*: complexidade e risco de deadlock para um cenário raro. Rejeitado.
- *Merge automático*: contraria a decisão do clarify (opção A escolhida sobre C). Rejeitado.

## D4 — Tipos de geração (origem da versão)

**Decision**: `TextChoices` `SourceType` com os valores: `INITIAL_EXTRACTION`, `PROCESSING`, `REPROCESSING`, `MANUAL_EDIT`. Mapeamento dos gatilhos existentes:
- `document_langextract_view` (primeira extração) → `INITIAL_EXTRACTION` se não houver versão anterior, senão `REPROCESSING`.
- Pipeline automático de processamento/extração → `PROCESSING`/`REPROCESSING`.
- Endpoint "Salvar Alterações" → `MANUAL_EDIT`.

**Rationale**: Cobre exatamente os eventos de FR-011 e a rastreabilidade de FR-017. Enum no modelo mantém consistência de terminologia (Princípio III).

**Alternatives considered**: String livre — rejeitado por permitir valores inconsistentes e dificultar testes.

## D5 — Confiança em edição manual e campos adicionados (FR-025, FR-027)

**Decision**: Ao criar uma versão de origem manual, qualquer campo cujo valor foi alterado pelo usuário e qualquer campo novo adicionado é persistido com `confidence = 1.0` (100%). Campos não alterados preservam sua confiança da versão base. A detecção de "alterado" é feita comparando valor do campo com o valor correspondente na versão ativa base.

**Rationale**: Atende FR-025/FR-027. O formato de campo já suportado pelo frontend (`parseFieldEntry`) e backend é `{ "value": ..., "confidence": <0..1> }`, então 100% é representado como `1.0`. Mantém o significado de "confiança" coerente.

**Alternatives considered**:
- *Marcar origem manual sem mexer na confiança* (opção A do clarify) — descartado pela decisão do usuário (opção B).
- *Setar 100% em todos os campos da versão manual* — incorreto: campos não tocados devem manter a confiança original para auditoria.

## D6 — Autorização (FR-026)

**Decision**: Reusar a permissão existente `documents.validate` (via `require_permission("documents.validate")`) para os endpoints de salvar campos e — minimamente — leitura. A permissão de validação já representa "acesso à função de validação de documentos", exatamente o critério definido no clarify (não vinculado a um perfil específico).

**Rationale**: FR-026 define acesso vinculado à função de validação, não a um perfil. A app já modela isso em `users/permissions.py` e o frontend já usa `permission: 'documents.validate'` para a aba Validação. Sem novo perfil/permissão.

**Alternatives considered**: Criar nova permissão `documents.edit_fields` — rejeitado: introduz superfície de permissão nova sem necessidade; o clarify ancorou no acesso de validação.

## D7 — Representação do histórico (FR-018–FR-022)

**Decision**: Endpoint `GET /documents/{id}/field-versions` retorna todas as versões (ativa + anteriores) ordenadas desc por `version_number`, cada uma com seus campos/valores/confiança e metadados (id, número, tipo de origem, data/hora, autor, número da versão anterior, flag ativa). O frontend exibe um painel/modal somente leitura. Nenhuma rota de edição/remoção é exposta sobre versões.

**Rationale**: Atende FR-019/FR-020/FR-021/FR-022. Retornar também a ativa simplifica o frontend (uma única fonte para a linha do tempo) sem violar "somente leitura".

**Alternatives considered**: Retornar só versões anteriores (excluir a ativa) — adiciona casos especiais no frontend sem ganho. Rejeitado.

## D8 — Migração de dados existentes

**Decision**: Data migration que, para cada `ExtractionResult` existente, cria uma `ExtractionFieldVersion` inicial (`version_number=1`, `source_type=INITIAL_EXTRACTION`, `is_active=True`, `previous_version=null`) copiando `fields`/`confidence`. Documentos sem `ExtractionResult` não geram versão.

**Rationale**: Garante consistência: todo documento já extraído passa a ter uma versão ativa, evitando estados sem versão na introdução da feature.

**Alternatives considered**: Lazy backfill na primeira leitura — torna a lógica de leitura mais complexa e mistura responsabilidades. Rejeitado.
