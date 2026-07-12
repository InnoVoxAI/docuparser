import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// On Cloudflare Pages, CF_PAGES_BRANCH is available at build time.
// Derive backend URLs from the branch so import.meta.env picks them up.
// Usa os MESMOS nomes que o código consome (VITE_BACKEND_CORE_URL /
// VITE_BACKEND_COM_URL). O `??=` mantém como default de conveniência: um valor
// definido explicitamente no painel do Cloudflare Pages tem precedência.
const branch = process.env.CF_PAGES_BRANCH
if (branch) {
    // K8s environments: main → prod (no prefix), staging → hml
    const k8sEnv = branch === 'main' ? '' : 'staging.'
    process.env.VITE_BACKEND_CORE_URL ??= `https://${k8sEnv}docuparser-core.innovox.ai`
    process.env.VITE_BACKEND_COM_URL ??= `https://${k8sEnv}docuparser-com.innovox.ai`
}

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        // Alvos do proxy do dev server (SERVER-SIDE). Usam nomes SEM o prefixo
        // `VITE_` de propósito: os `VITE_*` são expostos ao bundle do browser e
        // representam a URL pública do backend (ver src/main.tsx). O proxy, ao
        // contrário, precisa do endereço interno (ex.: hostname do Docker
        // `backend-core:8000`), que não deve vazar para o cliente.
        proxy: {
            '/api': {
                target: process.env.BACKEND_CORE_URL || 'http://127.0.0.1:8000',
                changeOrigin: true,
                proxyTimeout: 15000,
                timeout: 15000,
            },
            '/com': {
                target: process.env.BACKEND_COM_URL || 'http://127.0.0.1:8070',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/com/, ''),
                proxyTimeout: 15000,
                timeout: 15000,
            },
        },
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
})
