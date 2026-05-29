# Fluxo geral - Backend Com (WhatsApp, Email, Debounce)

Este arquivo contem um diagrama do fluxo atual, do inbound ao processamento interno.

<style>
    /* Deixa o SVG do Mermaid maior e sem limitar largura */
    .diagram-container svg {
        max-width: none;
        width: 1400px;
        height: auto;
    }
</style>

<div class="diagram-container" style="width: 100%; overflow: auto;">

```mermaid
%%{init: {'theme': 'base', 'flowchart': {'useMaxWidth': false, 'nodeSpacing': 50, 'rankSpacing': 70}, 'themeVariables': {'fontSize': '16px'}}}%%
flowchart LR
    subgraph WhatsApp_Twilio
        TW[Twilio WhatsApp] -->|POST /webhook/twilio| APIW[FastAPI webhook]
        APIW --> SIG[validate_twilio_signature]
        APIW --> RL[check_rate_limit]
        APIW --> HW[send_using_webhook]
        HW --> WB[Webhook interno]
    end

    subgraph Email_IMAP
        IMAP[IMAP Server] -->|fetch_unread| ER[EmailReader]
        ER --> APIE[FastAPI /fetch_unread]
        ER --> DAEMON[Daemon loop]
        DAEMON -->|attachments| HW2[send_using_webhook]
        HW2 --> WB
    end

    subgraph Debounce_Queue
        WEBHOOK[Webhook interno] --> Q[DebouncedQueue]
        Q -->|on_flush| HANDLER[Handler/Worker externo]
        Q -->|backend| BK[(Memory/Postgres/Celery)]
    end

    APIW --> WEBHOOK
    APIE --> WEBHOOK

    style WhatsApp_Twilio stroke:#888,fill:#f7f7f7
    style Email_IMAP stroke:#888,fill:#f7f7f7
    style Debounce_Queue stroke:#888,fill:#f7f7f7
```

</div>

## Observacoes

- O webhook interno representa o ponto de handoff para o processamento assincro.
- O handler/worker externo nao esta implementado neste modulo, mas e o destino final dos payloads.
- DebouncedQueue e opcional e depende de como o webhook interno foi implementado no sistema externo.
