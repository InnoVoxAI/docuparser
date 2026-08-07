import { z } from 'zod'

export const activateAccountSchema = z
    .object({
        password: z.string().min(8),
        confirmPassword: z.string().min(1),
    })
    .refine((values) => values.password === values.confirmPassword, {
        message: 'As senhas não coincidem.',
        path: ['confirmPassword'],
    })

export type ActivateAccountFormValues = z.infer<typeof activateAccountSchema>

export const ACTIVATE_ACCOUNT_DEFAULTS: ActivateAccountFormValues = {
    password: '',
    confirmPassword: '',
}
