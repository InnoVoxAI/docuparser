import { Pencil } from 'lucide-react'
import { DocumentBlobPreview } from '../../../shared/components'
import { formatDate } from '../../../shared/utils'
import type { DocumentDetailState } from '../hooks'
import type { PaymentDocument } from '../schemas/payments'
import { BOLETO_FIELDS, INVOICE_FIELDS } from '../documentFields'
import { describeOrigin } from '../utils'
import { FieldGrid } from './FieldGrid'

// Largura útil do painel (100cqw) menos as margens do visualizador, vezes a proporção de uma
// página A4, mais a barra de ferramentas e uma folga, para o visualizador não criar barras de rolagem.
// Altura que o iframe passa do quadro, para esconder a barra horizontal do visualizador.
const CLIP_PX = 24
const PAGE_HEIGHT = 'calc((100cqw - 16px) * 1.4143 + 100px)'

interface Props {
    kind: 'Nota fiscal' | 'Boleto'
    doc: PaymentDocument
    state: DocumentDetailState | undefined
    /** Leva à tela de validação deste documento, para corrigir o que não foi lido. */
    onFix?: () => void
}

/** Um documento do popup: de onde veio, os campos importantes e o arquivo original. */
export function DocumentPane({ kind, doc, state, onFix }: Props) {
    const detail = state?.detail
    return (
        <section
            aria-label={`${kind}: ${doc.original_filename}`}
            className="flex min-h-0 flex-col gap-3 overflow-y-auto rounded-md border border-zinc-200 bg-white p-3"
        >
            <header className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{kind}</span>
                    <h3 className="truncate text-sm font-semibold text-zinc-900" title={doc.original_filename}>
                        {doc.original_filename || 'Sem nome'}
                    </h3>
                    <p className="text-xs text-zinc-500">
                        {describeOrigin(doc)} · recebido em {formatDate(doc.received_at)}
                    </p>
                </div>
                {onFix ? (
                    <button
                        type="button"
                        onClick={onFix}
                        title="Abre a tela de validação deste documento"
                        className="inline-flex shrink-0 items-center gap-1 rounded-md border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100"
                    >
                        <Pencil size={13} aria-hidden="true" /> Corrigir dados
                    </button>
                ) : null}
            </header>
            {state?.loading ? <p className="text-sm text-zinc-500">Carregando os dados…</p> : null}
            {state?.error ? (
                <p className="text-sm text-red-700">Não foi possível carregar os dados deste documento.</p>
            ) : (
                <FieldGrid specs={kind === 'Nota fiscal' ? INVOICE_FIELDS : BOLETO_FIELDS} detail={detail} />
            )}
            {/* A altura vem da largura do painel (proporção de uma página A4): a página aparece
                inteira, sem a rolagem do visualizador dentro da rolagem do painel. O iframe é um
                pouco mais alto que o quadro: a barra horizontal que o visualizador do Chrome
                desenha no pé fica recortada. */}
            <div className="[container-type:inline-size]">
                <div className="overflow-hidden rounded border border-zinc-200" style={{ height: PAGE_HEIGHT }}>
                    <DocumentBlobPreview
                        documentId={doc.id}
                        contentType={detail?.content_type}
                        filename={doc.original_filename}
                        pageFit
                        frameClassName="w-full"
                        frameStyle={{ height: `calc(${PAGE_HEIGHT} + ${CLIP_PX}px)` }}
                    />
                </div>
            </div>
        </section>
    )
}
