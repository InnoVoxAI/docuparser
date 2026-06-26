import { setupServer } from 'msw/node'
import { handlers } from './handlers'

// Servidor MSW para o ambiente Node/jsdom dos testes.
export const server = setupServer(...handlers)
