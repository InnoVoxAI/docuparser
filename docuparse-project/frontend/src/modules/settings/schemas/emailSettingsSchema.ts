import { z } from 'zod'

/**
 * Espelha as validações manuais atuais da aba Email. O único bloqueio
 * verdadeiramente condicional hoje (host/usuário obrigatórios apenas para
 * "Testar captura IMAP", só quando `provider === 'imap'`) NÃO entra aqui de
 * propósito — é um guard imperativo no handler de teste (ver
 * `EmailSettingsPanel.tsx`), porque `Salvar email` continua tão permissivo
 * quanto hoje (é possível salvar host/usuário vazios). Um `.refine`
 * condicional aqui bloquearia o save também, o que seria uma regressão.
 */
export const emailSettingsSchema = z.object({
    provider: z.enum(['imap', 'webhook', 'manual_test']),
    inbox_folder: z.string(),
    imap_host: z.string(),
    imap_port: z.number().min(1).max(65535),
    username: z.string(),
    webhook_url: z.string(),
    accepted_content_types: z.string(),
    max_attachment_mb: z.number().min(1).max(200),
    blocked_senders: z.string(),
    is_active: z.boolean(),
})

export type EmailSettingsFormValues = z.infer<typeof emailSettingsSchema>

export const EMAIL_SETTINGS_DEFAULTS: EmailSettingsFormValues = {
    provider: 'imap',
    inbox_folder: 'INBOX',
    imap_host: '',
    imap_port: 993,
    username: '',
    webhook_url: 'http://127.0.0.1:8070/api/v1/email/messages',
    accepted_content_types: 'application/pdf,image/jpeg,image/png,image/tiff,image/webp',
    max_attachment_mb: 20,
    blocked_senders: '',
    is_active: true,
}
