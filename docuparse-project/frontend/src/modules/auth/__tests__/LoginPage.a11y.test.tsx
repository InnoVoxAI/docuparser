import { render } from '@testing-library/react'
import { axe } from 'vitest-axe'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../context'
import { LoginPage } from '../components/LoginPage'

describe('LoginPage - acessibilidade (SC-006)', () => {
    it('não tem violações de acessibilidade', async () => {
        const { container } = render(
            <AuthProvider>
                <LoginPage />
            </AuthProvider>,
        )
        expect(await axe(container)).toHaveNoViolations()
    })
})
