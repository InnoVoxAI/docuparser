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
      // Não apaga a pasta inteira a cada run (preserva o coverage/README.md);
      // os relatórios (index.html, main.tsx.html, *.json, *.xml) são reescritos.
      clean: false,
      // Foco nos fluxos da aplicação; configs/dados são excluídos da métrica.
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/__tests__/**', 'src/vite-env.d.ts', 'src/models/**'],
      // Piso de regressão. A meta aspiracional (críticos ≥90%, demais ≥80%) é
      // medida por fluxo, não por arquivo: como a UI é um único monólito
      // (~4.3k linhas, sem split por decisão de US1), a métrica por arquivo é
      // uma mistura. Os fluxos críticos (auth, permissões, validação/007,
      // inbox, DLQ, settings save, CRUD, upload) estão cobertos; o restante
      // não coberto é majoritariamente UI de SettingsView (editores de
      // schema/exemplos/layout). Estes limiares travam regressões abaixo do
      // nível atingido.
      thresholds: {
        lines: 65,
        statements: 65,
        branches: 58,
        functions: 40,
      },
    },
  },
})
