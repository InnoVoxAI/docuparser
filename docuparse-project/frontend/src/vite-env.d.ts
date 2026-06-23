/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DOCUPARSE_INTERNAL_SERVICE_TOKEN?: string
  readonly VITE_BACKEND_CORE_URL?: string
  readonly VITE_BACKEND_COM_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
