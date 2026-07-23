# 🗺️ Roadmap visual — DocuParse × API Superlógica

Passo a passo resumido das fases **A → B → C** rumo ao objetivo central, com o que já foi feito, o gargalo atual e o que ainda falta. Cada caixa traz um status.

## Fluxo entre as fases

```mermaid
flowchart TD
    %% ============ FASE A ============
    subgraph FA["🅰️ FASE A · Entendimento + Specify — ✅ CONCLUÍDA"]
        direction TB
        A1["📄 Estudo exploratório da API<br/>entidades · endpoints · relacionamentos<br/>(estudo-api-...md)"]
        A2["🔑 Chave de associação definida<br/>CNPJ do papel-condomínio → id_condominio<br/>⚠️ ainda é HIPÓTESE a validar"]
        A3["🧩 Achado crítico<br/>fornecedor é compartilhado ·<br/>despesa é por condomínio"]
        A4["❓ Lacunas mapeadas<br/>§7 técnicas [HIP] + H1–H8 humanas<br/>(pontos-a-esclarecer-...md)"]
        A1 --> A2 --> A3 --> A4
    end

    %% ============ FASE B ============
    subgraph FB["🅱️ FASE B · Spike de descoberta descartável — 🟡 PARCIAL"]
        direction TB
        B1["📝 Plano do spike (Plan/Tasks)<br/>fases 0–5 · ✅ pronto<br/>(plano-fase-b-...md)"]
        B2["🐍 Script read-only implementado + testado<br/>self-test 13/13 · guarda GET-only · ✅ pronto<br/>(discovery_spike.py + README)"]
        B3{{"🔴 PRÉ-REQUISITOS p/ RODAR — FALTAM<br/>① credencial de API que vê a carteira toda<br/>② amostra rotulada (gabarito)<br/>③ saída do DocuParse"}}
        B4["▶️ Rodar o spike<br/>⬜ pendente — bloqueado pelos pré-requisitos"]
        B5["📊 RELATÓRIO DE ACHADOS<br/>⬜ converte [HIP] → [DOC]<br/>+ go/no-go da regra de associação"]
        B1 --> B2 --> B3 --> B4 --> B5
    end

    %% ============ TRACK HUMANO (paralelo) ============
    H{{"👤 Validação humana H1–H8<br/>⬜ em paralelo · prioridade H3 e H7<br/>objetivo final · dono da escrita · volume · tolerância a erro"}}

    %% ============ FASE C ============
    subgraph FC["🅲 FASE C · Specify real da integração — ⬜ NÃO INICIADA"]
        direction TB
        C1["📐 Specify da integração<br/>comportamento observável ·<br/>critérios de aceite · read-only × escrita"]
        C2["🛠️ Plan → Tasks → Implement<br/>a integração de verdade"]
        C1 --> C2
    end

    %% ============ OBJETIVO ============
    OBJ(["🎯 OBJETIVO CENTRAL<br/>associar cada documento do DocuParse ao condomínio correto<br/>na API Superlógica · validar os campos · (a definir) arquivar ou lançar despesa"])

    %% ============ LIGAÇÕES ENTRE FASES ============
    A4 -->|"lacunas a resolver"| B1
    B5 -->|"achados que viram fato"| C1
    H  -->|"decisões de negócio"| C1
    C2 -->|"entrega"| OBJ

    %% ============ ESTILOS DE STATUS ============
    classDef done fill:#d4f4dd,stroke:#2e7d32,color:#14351b;
    classDef todo fill:#eceff1,stroke:#90a4ae,color:#37474f;
    classDef blocker fill:#ffdede,stroke:#c62828,color:#6f1414;
    classDef goal fill:#fff3cd,stroke:#f9a825,color:#5a4600;

    class A1,A2,A3,A4,B1,B2 done;
    class B4,B5,C1,C2,H todo;
    class B3 blocker;
    class OBJ goal;
```

**Legenda:** ✅ concluído · 🟡 parcial · ⬜ a fazer · 🔴 bloqueador

---

## Onde estamos agora

Fase A **fechada**. Fase B com **plano e script prontos e testados**, mas **ainda não rodados** — travados nos três pré-requisitos. Fase C **depende de rodar o spike** (para os `[HIP]` virarem fato) e das respostas humanas.

## 🔴 Gargalo atual → próximo passo
Destravar os **3 pré-requisitos do §3 da Fase B**: **① credencial de API** (usuário que vê toda a carteira), **② amostra rotulada** (documentos com condomínio correto conhecido) e **③ saída do DocuParse** para esses documentos. Em **paralelo** (não depende do spike): responder **H3** (multi-tenancy) e **H7** (taxonomia de documentos).

## Artefatos produzidos

| Arquivo | Fase | O que é | Status |
|---|---|---|---|
| `estudo-api-superlogica-condominios-docuparse.md` | A | Estudo + Specify (entidades, fluxo, §7, §8) | ✅ |
| `pontos-a-esclarecer-validacao-humana.md` | A | Registro H1–H8 (validação humana) | ✅ aberto p/ resposta |
| `plano-fase-b-spike-descoberta.md` | B | Plano do spike (Plan/Tasks) | ✅ |
| `discovery_spike.py` | B | Script de descoberta read-only (Implement) | ✅ testado · ⬜ não rodado |
| `README-discovery-spike.md` + `requirements.txt` + `.env.example` + `amostra.exemplo.json` | B | Suporte para rodar o script | ✅ |
| *(RELATÓRIO DE ACHADOS)* | B | Saída do spike | ⬜ gerado ao rodar |
| *(Specify da integração)* | C | Especificação real | ⬜ não iniciada |
