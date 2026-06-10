import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    server: {
        proxy: {
            '/api': {
                target: process.env.VITE_BACKEND_CORE_URL || 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            '/com': {
                target: process.env.VITE_BACKEND_COM_URL || 'http://127.0.0.1:8070',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/com/, ''),
            },
        },
    },
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
})
