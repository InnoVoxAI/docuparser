import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll } from 'vitest'
import axios from 'axios'
import { server } from './mocks/server'

// O XMLHttpRequest do jsdom trava indefinidamente ao enviar um FormData que
// contenha um File/Blob (axios usa o adapter 'xhr' por padrão, já que jsdom
// sempre define XMLHttpRequest). Força o adapter 'http' do Node nos testes
// para que uploads multipart se comportem como em um navegador real.
axios.defaults.adapter = 'http'

// Inicia o MSW antes da suíte, reseta handlers entre testes e encerra ao final.
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
