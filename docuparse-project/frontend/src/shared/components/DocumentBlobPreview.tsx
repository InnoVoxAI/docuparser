import { useEffect, useState } from 'react'
import { FileText } from 'lucide-react'
import { api } from '../lib/http'
import { readError } from '../utils'
import { EmptyState } from './EmptyState'

/**
 * Pré-visualização inline do documento original (feature 009). Busca o arquivo
 * como blob autenticado (o interceptor injeta o JWT → respeita as permissões,
 * FR-015) e renderiza inline sem forçar download (FR-011): PDF via iframe,
 * imagem via <img>, fallback amigável para os demais formatos.
 */
export function DocumentBlobPreview({
    documentId,
    contentType,
    filename,
    frameClassName = 'h-[420px] w-full rounded border border-zinc-200',
}: {
    documentId: string
    contentType?: string
    filename?: string
    frameClassName?: string
}) {
    const [blobUrl, setBlobUrl] = useState('')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        let ignore = false
        let objectUrl = ''
        setLoading(true)
        setError('')
        api.get(`/documents/${documentId}/file`, { responseType: 'blob' })
            .then((response) => {
                if (ignore) return
                objectUrl = URL.createObjectURL(response.data as Blob)
                setBlobUrl(objectUrl)
            })
            .catch((requestError) => {
                if (!ignore)
                    setError(readError(requestError, 'Nao foi possivel carregar a pre-visualizacao do documento.'))
            })
            .finally(() => {
                if (!ignore) setLoading(false)
            })
        return () => {
            ignore = true
            if (objectUrl) URL.revokeObjectURL(objectUrl)
        }
    }, [documentId])

    if (loading) {
        return (
            <div className="flex min-h-[200px] items-center justify-center text-sm text-zinc-500">
                Carregando documento...
            </div>
        )
    }
    if (error) {
        return (
            <div className="flex min-h-[200px] items-center justify-center px-4 text-center text-sm text-red-600">
                {error}
            </div>
        )
    }
    if (!blobUrl) {
        return <EmptyState icon={FileText} text="Documento indisponivel." />
    }
    const isPdf = contentType === 'application/pdf' || (filename ?? '').toLowerCase().endsWith('.pdf')
    const isImage = (contentType ?? '').startsWith('image/')
    if (isPdf) {
        return <iframe title={`Documento ${filename ?? documentId}`} src={blobUrl} className={frameClassName} />
    }
    if (isImage) {
        return (
            <div className="max-h-[420px] overflow-auto p-2">
                <img
                    src={blobUrl}
                    alt={`Documento ${filename ?? documentId}`}
                    className="max-w-full rounded border border-zinc-200"
                />
            </div>
        )
    }
    return <EmptyState icon={FileText} text="Formato sem pre-visualizacao inline." />
}
