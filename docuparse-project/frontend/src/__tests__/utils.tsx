import { render } from '@testing-library/react'
import { AuthProvider, Root } from '../main'

// Renderiza a árvore real da aplicação (AuthProvider + Root), exatamente como em
// produção, exceto o bootstrap createRoot (que só roda quando existe #root).
export function renderApp() {
  return render(
    <AuthProvider>
      <Root />
    </AuthProvider>,
  )
}
