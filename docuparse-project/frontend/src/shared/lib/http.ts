import axios, { type InternalAxiosRequestConfig } from 'axios'

// Base dos backends: URL absoluta no deploy (Cloudflare Pages, via
// VITE_BACKEND_*_URL) e caminho relativo em dev/testes (fallback pelo proxy do
// Vite / handlers MSW). Se a env estiver vazia, mantém o comportamento relativo.
const CORE = import.meta.env.VITE_BACKEND_CORE_URL ?? ''
const COM = import.meta.env.VITE_BACKEND_COM_URL ?? ''

export const api = axios.create({ baseURL: `${CORE}/api/ocr` })
export const authApi = axios.create({ baseURL: `${CORE}/api/auth` })
// backend-com (upload/poll) autentica pelo JWT do usuário — anexado via
// interceptor abaixo, igual ao `api`. Nenhum segredo é embutido no frontend.
// Em dev, COM vazio → '/com/api/v1' (o proxy do Vite remove o '/com'); no deploy → absoluto.
export const comApi = axios.create({ baseURL: COM ? `${COM}/api/v1` : '/com/api/v1' })
export const adminApi = axios.create({ baseURL: `${CORE}/api/admin` })

const attachToken = (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
}

api.interceptors.request.use(attachToken)
comApi.interceptors.request.use(attachToken)
adminApi.interceptors.request.use(attachToken)
