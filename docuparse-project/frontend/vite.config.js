import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// On Cloudflare Pages, CF_PAGES_BRANCH is available at build time.
// Derive backend URLs from the branch so import.meta.env picks them up.
const branch = process.env.CF_PAGES_BRANCH
if (branch && !process.env.VITE_API_BASE_URL) {
    const prefix = branch === 'main' ? '' : `${branch}.`
    process.env.VITE_API_BASE_URL = `https://${prefix}docuparser-core.innovox.ai`
    process.env.VITE_COM_BASE_URL = `https://${prefix}docuparser-com.innovox.ai`
}

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            '/api': {
                target: process.env.VITE_BACKEND_CORE_URL || 'http://127.0.0.1:8000',
                changeOrigin: true,
                proxyTimeout: 15000,
                timeout: 15000,
            },
            '/com': {
                target: process.env.VITE_BACKEND_COM_URL || 'http://127.0.0.1:8070',
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
