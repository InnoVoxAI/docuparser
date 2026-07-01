# Pasta `coverage/` — Relatório de cobertura de testes

Esta pasta **não é código da aplicação**. Ela contém o **relatório de cobertura de
testes** gerado automaticamente pelo Vitest (provider `v8`) toda vez que a suíte
roda com cobertura. É um artefato de saída — você lê, não edita (exceto este
`README.md`).

> Cobertura = quanto do código-fonte foi efetivamente executado pelos testes
> automatizados. Ajuda a enxergar o que **não** está sendo testado.

---

## Como gerar / atualizar

A partir de `docuparse-project/frontend/`:

```bash
npm run coverage      # = vitest run --coverage
```

No ambiente Docker:

```bash
docker compose exec frontend npm run coverage
```

A configuração fica em [`../vitest.config.ts`](../vitest.config.ts) (bloco
`test.coverage`): provider, pasta de saída (`./coverage`), arquivos incluídos/
excluídos e os limiares mínimos (thresholds).

---

## Como interpretar

### Visão rápida (terminal)
Ao rodar `npm run coverage`, sai uma tabela como:

```
File      | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s
----------|---------|----------|---------|---------|------------------
main.tsx  |   66.6  |   62.1   |   42.7  |   66.6  | 1234-1240, ...
```

### Visão detalhada (navegador)
Abra **[`index.html`](./index.html)** no navegador para a tabela-resumo e clique
no arquivo para ver o código **linha a linha**:

- **Verde** = linha executada pelos testes.
- **Vermelho** = linha **não** coberta.
- Os marcadores `x N` indicam quantas vezes cada trecho/branch foi executado.

### As 4 métricas
| Métrica | O que mede |
|---|---|
| **Statements (Stmts)** | % de instruções executadas |
| **Branches** | % de ramos de decisão cobertos (cada lado de um `if`, `? :`, `&&`) |
| **Functions (Funcs)** | % de funções/métodos chamados ao menos uma vez |
| **Lines** | % de linhas executadas |

Branch costuma ser a métrica mais reveladora: 100% de linhas mas 60% de branches
significa que há caminhos condicionais (ex.: o lado `else`) sem teste.

---

## Arquivos importantes

| Arquivo | Para que serve |
|---|---|
| **`index.html`** | Ponto de entrada do relatório HTML — abra no navegador. Tabela-resumo com as 4 métricas. |
| **`main.tsx.html`** | Relatório linha a linha do `src/main.tsx` (o monólito da UI). É aqui que se vê **o que** não está coberto. |
| **`coverage-final.json`** | Dados brutos da cobertura (formato Istanbul). Consumido por ferramentas/CI; não é para leitura humana. |
| **`clover.xml`** | Mesma cobertura no formato Clover XML — para integrações de CI (ex.: badges, dashboards). |
| `base.css`, `prettify.css`, `prettify.js`, `sorter.js`, `block-navigation.js`, `favicon.png`, `sort-arrow-sprite.png` | Assets do relatório HTML (estilo, ordenação, navegação). Não editar. |

---

## Limiares (thresholds) — piso de regressão

O `vitest.config.ts` define mínimos de cobertura. Se a cobertura cair abaixo
deles, **`npm run coverage` falha** (exit code ≠ 0), servindo de trava de
regressão no CI:

```
lines: 65 · statements: 65 · branches: 58 · functions: 40
```

Esses valores refletem o estado atual: os **fluxos críticos** (autenticação,
permissões, validação/versionamento, inbox, DLQ, settings, CRUD, upload) estão
cobertos. O percentual por arquivo é "diluído" porque a UI é um **monólito**
(`src/main.tsx`, ~4 mil linhas, mantido sem split por decisão da migração 008) —
a meta aspiracional (críticos ≥90%, demais ≥80%) é avaliada por fluxo, não pela
média do arquivo. Veja [`../TYPESCRIPT_MIGRATION.md`](../TYPESCRIPT_MIGRATION.md).

---

## Notas

- O conteúdo (exceto este README) é **regenerado** a cada `npm run coverage`.
- `clean: false` está habilitado no `vitest.config.ts` justamente para que este
  `README.md` **não** seja apagado entre as gerações.
- A pasta é excluída da imagem Docker (`.dockerignore`).
