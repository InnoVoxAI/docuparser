/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_BACKEND_CORE_URL?: string
    readonly VITE_BACKEND_COM_URL?: string
    readonly VITE_OTEL_EXPORTER_OTLP_ENDPOINT?: string
    readonly VITE_OTEL_SERVICE_NAME?: string
    readonly VITE_DEPLOYMENT_ENVIRONMENT?: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}
