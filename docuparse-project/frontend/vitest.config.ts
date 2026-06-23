import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

// Configuração de testes separada do vite.config.js para não afetar o runtime/dev.
// O Vitest reusa o transform do Vite (suporte nativo a TSX e ao alias "@").
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      reportsDirectory: './coverage',
      // Foco nos fluxos da aplicação; configs/dados são excluídos da métrica.
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/__tests__/**', 'src/vite-env.d.ts', 'src/models/**'],
    },
  },
})
