import axios, { type InternalAxiosRequestConfig } from 'axios'

export const api = axios.create({ baseURL: '/api/ocr' })
export const authApi = axios.create({ baseURL: '/api/auth' })
// backend-com (upload/poll) autentica pelo JWT do usuário — anexado via
// interceptor abaixo, igual ao `api`. Nenhum segredo é embutido no frontend.
export const comApi = axios.create({ baseURL: '/com/api/v1' })

const attachToken = (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
}

api.interceptors.request.use(attachToken)
comApi.interceptors.request.use(attachToken)
