import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { LayoutConfig, SchemaConfig } from '../../../types'
import { ExtractionPanel } from '../components/ExtractionPanel'
import { renderSettingsPanel } from './renderSettingsPanel'

// spec 018 — o catálogo de modelos é global; sem `tenants.manage` a área de
// Extração é somente leitura. No ambiente de teste não há usuário autenticado,
// então `hasPermission('tenants.manage')` é falso → renderiza o modo leitura.

const schemas: SchemaConfig[] = [
    { id: 's1', schema_id: 'nota_fiscal_default', version: 'v1', definition: {}, is_active: true },
]
const layouts: LayoutConfig[] = [
    {
        id: 'l1',
        layout: 'nota_fiscal',
        document_type: '',
        schema_config_id: 's1',
        confidence_threshold: 0.75,
        is_active: true,
    },
]

describe('ExtractionPanel (catálogo global — spec 018)', () => {
    it('mostra o aviso de somente leitura e lista o catálogo sem controles de escrita', () => {
        renderSettingsPanel(<ExtractionPanel schemas={schemas} layouts={layouts} />)

        expect(screen.getByText(/somente leitura/i)).toBeInTheDocument()
        expect(screen.getByText('nota_fiscal_default')).toBeInTheDocument()
        expect(screen.queryByRole('button', { name: /excluir/i })).not.toBeInTheDocument()
    })
})
