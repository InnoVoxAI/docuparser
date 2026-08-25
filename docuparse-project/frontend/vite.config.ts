import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
    // Terceiro argumento '' = carrega TODAS as vars do .env, não só as
    // prefixadas com VITE_ (loadEnv por padrão só pega VITE_*). Precisa
    // disso pra enxergar BACKEND_CORE_URL/BACKEND_COM_URL aqui no config.
    const env = { ...loadEnv(mode, process.cwd(), ''), ...process.env }

    // On Cloudflare Pages, CF_PAGES_BRANCH is available at build time.
    // Derive backend URLs from the branch so import.meta.env picks them up.
    // Usa os MESMOS nomes que o código consome (VITE_BACKEND_CORE_URL /
    // VITE_BACKEND_COM_URL). O `??=` mantém como default de conveniência: um
    // valor definido explicitamente no painel do Cloudflare Pages (ou no
    // .env local) tem precedência.
    const branch = env.CF_PAGES_BRANCH
    if (branch) {
        // K8s environments: main → prod (no prefix), staging → hml
        const k8sEnv = branch === 'main' ? '' : 'staging.'
        env.VITE_BACKEND_CORE_URL ??= `https://${k8sEnv}docuparser-core.innovox.ai`
        env.VITE_BACKEND_COM_URL ??= `https://${k8sEnv}docuparser-com.innovox.ai`
    }

    return {
        plugins: [react()],
        define: {
            'import.meta.env.VITE_BACKEND_CORE_URL': JSON.stringify(env.VITE_BACKEND_CORE_URL ?? ''),
            'import.meta.env.VITE_BACKEND_COM_URL': JSON.stringify(env.VITE_BACKEND_COM_URL ?? ''),
        },
        server: {
            port: 5173,
            host: '0.0.0.0',
            // Alvos do proxy do dev server (SERVER-SIDE). Usam nomes SEM o prefixo
            // `VITE_` de propósito: os `VITE_*` são expostos ao bundle do browser e
            // representam a URL pública do backend (ver src/main.tsx). O proxy, ao
            // contrário, precisa do endereço interno (ex.: hostname do Docker
            // `backend-core:8000`), que não deve vazar para o cliente.
            proxy: {
                '/api': {
                    target: env.BACKEND_CORE_URL || 'http://127.0.0.1:8000',
                    changeOrigin: true,
                    // 15s era curto demais para chamadas de LLM (extração via
                    // langextract-service já passou de 90s em teste real) — o
                    // proxy abortava a conexão com o backend (não o backend em
                    // si, que seguia rodando), e o que quer que reagisse a essa
                    // falha no cliente acabava disparando uma nova chamada,
                    // empilhando execuções concorrentes pro mesmo retry.
                    proxyTimeout: 120000,
                    timeout: 120000,
                },
                '/com': {
                    target: env.BACKEND_COM_URL || 'http://127.0.0.1:8070',
                    changeOrigin: true,
                    rewrite: (path) => path.replace(/^\/com/, ''),
                    // 15s era curto demais para chamadas de LLM (extração via
                    // langextract-service já passou de 90s em teste real) — o
                    // proxy abortava a conexão com o backend (não o backend em
                    // si, que seguia rodando), e o que quer que reagisse a essa
                    // falha no cliente acabava disparando uma nova chamada,
                    // empilhando execuções concorrentes pro mesmo retry.
                    proxyTimeout: 120000,
                    timeout: 120000,
                },
            },
        },
        resolve: {
            alias: {
                '@': path.resolve(__dirname, './src'),
            },
        },
    }
})
