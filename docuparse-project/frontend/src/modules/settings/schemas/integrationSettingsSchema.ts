import { z } from 'zod'

export const integrationSettingsSchema = z.object({
    approved_export_enabled: z.boolean(),
    approved_export_dir: z.string(),
    approved_export_format: z.enum(['json', 'jsonl']),
    superlogica_base_url: z.string(),
    superlogica_mode: z.enum(['disabled', 'mock', 'sandbox']),
})

export type IntegrationSettingsFormValues = z.infer<typeof integrationSettingsSchema>

export const INTEGRATION_SETTINGS_DEFAULTS: IntegrationSettingsFormValues = {
    approved_export_enabled: true,
    approved_export_dir: 'docuparse-project/exports/approved',
    approved_export_format: 'json',
    superlogica_base_url: '',
    superlogica_mode: 'disabled',
}
