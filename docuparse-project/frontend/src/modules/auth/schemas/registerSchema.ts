import { z } from 'zod'

export const registerSchema = z
    .object({
        name: z.string().min(1),
        tenantSlug: z.string().regex(/^[a-z0-9-]+$/),
        email: z.string().min(1).email(),
        password: z.string().min(8),
        confirmPassword: z.string().min(1),
    })
    .refine((values) => values.password === values.confirmPassword, {
        message: 'As senhas não coincidem.',
        path: ['confirmPassword'],
    })

export type RegisterFormValues = z.infer<typeof registerSchema>

/** `tenantSlug` default lê `?tenant=` da URL — mesmo comportamento do `useState` original. */
export function getRegisterDefaults(): RegisterFormValues {
    return {
        name: '',
        tenantSlug: new URLSearchParams(window.location.search).get('tenant') ?? '',
        email: '',
        password: '',
        confirmPassword: '',
    }
}
