---
title: Escrita no Superlógica - conector com travas
type: note
permalink: docuparser/decisions/escrita-no-superlogica-conector-com-travas
tags:
- superlogica
- erp
- seguranca
- decisao
---

Implementação dos tickets 2 a 5 do épico "Escrita no Superlógica" (2026-11-22). Os tokens do
projeto são de um ambiente real, então o desenho parte de: **nenhum teste nem script faz
escrita de verdade, e todo padrão é o mais seguro**.

## O que existia

O `/validate` aprovado já chamava `publish_erp_integration_requested`, mas **nada consumia**
`erp.integration.requested`: só o mock, chamado por testes e pelo simulador de carga. O worker
do Camunda só chama o `/validate`. No Argo só há core, com, ocr e langextract, ou seja, não há
worker de eventos no deploy.

## Decisões

- **Pacote `erp_export`, separado de `erp_import`.** O cliente de leitura continua recusando
  tudo que não seja GET. A escrita passa só pelo `SuperlogicaWriter` (lista fechada com um único
  `POST despesas`, sem retentativa automática, sem log de token nem corpo).
- **O conector roda em processo**, na fila de segundo plano do core (`submit_erp_dispatch`),
  com troca de tenant, como OCR e extração. O resultado vai ao barramento e é aplicado direto
  no banco (o banco é a fonte da verdade). Não se registrou no worker de streams, que não troca
  de tenant.
- **Política** (`erp_export/policy.py`): `disabled` e `mock` nunca abrem rede; `dry_run` (ligado
  por padrão) não envia; `sandbox` só para host de `SUPERLOGICA_SANDBOX_HOSTS` e nunca
  produção; `live` exige habilitação do tenant (comando `erp_live_writes`, nunca a API),
  `SUPERLOGICA_LIVE_WRITES=1` e `CONTRACT_VERIFIED=True` (hoje `False`).
- **Duplicidade e resposta perdida:** o marcador `send_started_at` é gravado antes do POST. Na
  próxima tentativa a consulta ao ERP acha a despesa e marca como enviada (`reconciled`), sem
  reenviar. Sem o marcador, despesa igual já existente é `duplicate_in_erp`.
- **Confirmação do analista** em `sandbox` e `live` (permissão própria `erp.send`, só admin e
  tenantAdmin por padrão). Em `mock` e `disabled` a aprovação integra como antes.
- **Reenvio:** só falha retentável, com espera de 1, 5, 15 e 60 min e no máximo 5 tentativas.
  Falha definitiva pede correção e nova confirmação.

## Duas armadilhas que a verificação ponta a ponta achou

- **`seed_data` não distribui permissão nova.** Ele termina com "banco já inicializado, nada a
  fazer" quando já existe tenant, então `erp.send` nunca chegaria ao staging nem à produção, e
  a tela de papéis nem a listaria. A migration `users/0003_erp_send_permission` cria a
  permissão e a dá a `admin` e `tenantAdmin` (o `operator` não). Qualquer permissão nova
  precisa de uma migration de dados do mesmo tipo.
- **Documento corrigido depois de um envio sem resposta.** A reconciliação procura a despesa
  pelos dados atuais; se o analista mudou o valor, ela não acha a despesa antiga que o ERP pode
  ter aceito e lançaria uma segunda. O marcador `send_started_at` agora vem com a impressão
  digital do que foi enviado (`send_draft_fingerprint`); se o documento mudou, o conector falha
  com `changed_after_unknown_send` (definitivo) e pede para conferir no ERP antes de enviar.

## Verificação

Nenhum teste nem script fez chamada de escrita de verdade: o `conftest` de `erp_export/tests`
bloqueia HTTP real (`HTTPAdapter.send`) e os testes rodam sem o `.env`. As travas foram
verificadas por mutação (desfazer cada uma quebra ao menos um teste), no backend e no frontend.
O fluxo real foi percorrido num core local em `sandbox` com dry-run e host `.invalid`, e o envio
real foi bloqueado pela política, sem nenhuma chamada de saída. O tenant `demo` local tem tokens
do Superlógica salvos, por isso essa verificação nunca saiu do dry-run.

## Padrões que adotei nas decisões pendentes do PO (mudar se discordar)

- Gatilho: a aprovação do documento (como hoje). NF usa os boletos do processo de pagamento
  **confirmado** para vencimento e parcelas; boleto de processo confirmado não gera despesa
  própria; boleto avulso gera.
- Despesa já lançada à mão no ERP: **bloqueia e avisa** (`duplicate_in_erp`).
- Fornecedor ausente no ERP: **bloqueia e avisa** (`supplier_not_found`); não cria.
- Quem envia: `erp.send`.

## Não verificado

O contrato de escrita (endpoint, campos, id da resposta) e a leitura de fornecedores são
hipótese. Ver [[docuparser/reference/superlogica-escrita-de-despesa-spike-pendente]].

## Relations

- relates_to [[docuparser/decisions/plano-de-contas-compartilhado-e-importacao-do-superlogica-com-aprovacao]]
