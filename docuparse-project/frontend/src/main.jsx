import React, { useEffect, useMemo, useState } from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import './index.css'

function JsonPrimitive({ value }) {
    if (value === null) {
        return <span className="text-slate-400 italic">null</span>
    }

    if (typeof value === 'string') {
        return <span className="text-emerald-300">{JSON.stringify(value)}</span>
    }

    if (typeof value === 'number') {
        return <span className="text-amber-300">{value}</span>
    }

    if (typeof value === 'boolean') {
        return <span className="text-violet-300">{String(value)}</span>
    }

    return <span className="text-slate-100">{String(value)}</span>
}

function JsonNode({ value, depth = 0, label = null, isLast = true }) {
    const isArray = Array.isArray(value)
    const isObject = value !== null && typeof value === 'object' && !isArray
    const isContainer = isArray || isObject
    const entries = isArray ? value.map((item, index) => [index, item]) : isObject ? Object.entries(value) : []
    const hasChildren = entries.length > 0
    const [isOpen, setIsOpen] = useState(depth < 1)

    const indentStyle = { paddingLeft: `${depth * 16}px` }
    const openToken = isArray ? '[' : '{'
    const closeToken = isArray ? ']' : '}'
    const compactToken = isArray ? '[...]' : '{...}'

    const labelPrefix = () => {
        if (label === null) {
            return null
        }

        if (typeof label === 'number') {
            return (
                <>
                    <span className="text-slate-400">{label}</span>
                    <span className="text-slate-300">: </span>
                </>
            )
        }

        return (
            <>
                <span className="text-sky-300">{JSON.stringify(label)}</span>
                <span className="text-slate-300">: </span>
            </>
        )
    }

    if (!isContainer) {
        return (
            <div className="font-mono text-xs leading-6" style={indentStyle}>
                {labelPrefix()}
                <JsonPrimitive value={value} />
                {!isLast ? <span className="text-slate-500">,</span> : null}
            </div>
        )
    }

    if (!hasChildren) {
        return (
            <div className="font-mono text-xs leading-6" style={indentStyle}>
                {labelPrefix()}
                <span className="text-slate-200">{openToken}{closeToken}</span>
                {!isLast ? <span className="text-slate-500">,</span> : null}
            </div>
        )
    }

    if (!isOpen) {
        return (
            <div className="font-mono text-xs leading-6" style={indentStyle}>
                <button
                    type="button"
                    onClick={() => setIsOpen(true)}
                    className="mr-1 text-slate-400 hover:text-slate-200"
                    aria-label="Expandir campo"
                >
                    ▸
                </button>
                {labelPrefix()}
                <span className="text-slate-200">{compactToken}</span>
                {!isLast ? <span className="text-slate-500">,</span> : null}
            </div>
        )
    }

    return (
        <div>
            <div className="font-mono text-xs leading-6" style={indentStyle}>
                <button
                    type="button"
                    onClick={() => setIsOpen(false)}
                    className="mr-1 text-slate-400 hover:text-slate-200"
                    aria-label="Recolher campo"
                >
                    ▾
                </button>
                {labelPrefix()}
                <span className="text-slate-200">{openToken}</span>
            </div>

            {entries.map(([entryKey, entryValue], index) => (
                <JsonNode
                    key={`${depth}-${String(entryKey)}-${index}`}
                    value={entryValue}
                    label={entryKey}
                    depth={depth + 1}
                    isLast={index === entries.length - 1}
                />
            ))}

            <div className="font-mono text-xs leading-6 text-slate-200" style={indentStyle}>
                {closeToken}
                {!isLast ? <span className="text-slate-500">,</span> : null}
            </div>
        </div>
    )
}

function JsonViewer({ value }) {
    if (value !== null && typeof value === 'object') {
        return <JsonNode value={value} />
    }

    return (
        <div className="font-mono text-xs leading-6">
            <JsonPrimitive value={value} />
        </div>
    )
}

function formatMetricValue(value) {
    if (value === null || value === undefined) {
        return '-'
    }

    if (typeof value === 'object') {
        return JSON.stringify(value)
    }

    return String(value)
}

function collectTextTerms(ocrMeta) {
    const byTerm = ocrMeta?.confidence_by_term
    if (!byTerm || typeof byTerm !== 'object') {
        return []
    }

    const terms = []
    Object.keys(byTerm).forEach((key, index) => {
        const separator = key.indexOf(':')
        const term = separator >= 0 ? key.slice(separator + 1).trim() : key.trim()
        if (!term) {
            return
        }

        terms.push({
            term,
            index,
        })
    })

    return terms
}

function normalizeText(value) {
    return String(value ?? '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
}

function buildFieldMarkers(fields, rawText, ocrMeta, fieldPositions) {
    if (!fields || typeof fields !== 'object') {
        return []
    }

    const terms = collectTextTerms(ocrMeta)
    const rawTextNormalized = normalizeText(rawText)
    const denominator = Math.max(rawTextNormalized.length, 1)

    const markers = []

    Object.entries(fields).forEach(([fieldName, fieldValue]) => {
        const valueText = typeof fieldValue === 'string' ? fieldValue.trim() : ''
        if (!valueText) {
            return
        }

        const exactPosition = fieldPositions?.[fieldName]?.normalized_bbox
        if (
            exactPosition
            && Number.isFinite(exactPosition.x)
            && Number.isFinite(exactPosition.y)
            && Number.isFinite(exactPosition.width)
            && Number.isFinite(exactPosition.height)
        ) {
            const xRatio = Math.min(0.99, Math.max(0.01, exactPosition.x + (exactPosition.width / 2)))
            const yRatio = Math.min(0.99, Math.max(0.01, exactPosition.y + (exactPosition.height / 2)))

            markers.push({
                key: fieldName,
                label: fieldName,
                value: valueText,
                xRatio,
                yRatio,
                source: 'field_positions',
                hasExactBox: true,
                boxRatio: {
                    x: Math.max(0, exactPosition.x),
                    y: Math.max(0, exactPosition.y),
                    width: Math.max(0.005, exactPosition.width),
                    height: Math.max(0.005, exactPosition.height),
                },
            })
            return
        }

        const normalizedValue = normalizeText(valueText)
        let yRatio = null
        let source = 'not-found'

        const matchInRawText = rawTextNormalized.indexOf(normalizedValue)
        if (matchInRawText >= 0) {
            yRatio = Math.min(0.95, Math.max(0.05, matchInRawText / denominator))
            source = 'raw_text'
        }

        if (yRatio === null && terms.length > 0) {
            const matchedTerm = terms.find(({ term }) => normalizeText(term).includes(normalizedValue) || normalizedValue.includes(normalizeText(term)))
            if (matchedTerm) {
                const termRatio = terms.length > 1 ? matchedTerm.index / (terms.length - 1) : 0.5
                yRatio = Math.min(0.95, Math.max(0.05, termRatio))
                source = 'ocr_meta'
            }
        }

        if (yRatio === null) {
            return
        }

        markers.push({
            key: fieldName,
            label: fieldName,
            value: valueText,
            xRatio: 0.5,
            yRatio,
            source,
            hasExactBox: false,
            boxRatio: null,
        })
    })

    return markers
}


function App() {
    const SYSTEM_ENGINE_VALUE = ''
    const RESULT_TABS = {
        FIELDS: 'fields',
        METRICS: 'metrics',
        RAW_TEXT: 'raw_text',
    }

    const metricsOrder = [
        'field_score',
        'ocr_confidence',
        'final_score',
        'fallback_needed',
        'source',
        'fallback_engine',
        'ocr_meta',
        'processing_time',
    ]

    const [engines, setEngines] = useState([])
    const [selectedEngine, setSelectedEngine] = useState(SYSTEM_ENGINE_VALUE)
    const [file, setFile] = useState(null)
    const [filePreviewUrl, setFilePreviewUrl] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [result, setResult] = useState(null)
    const [activeTab, setActiveTab] = useState(RESULT_TABS.FIELDS)
    const [activeMarkerKey, setActiveMarkerKey] = useState('')

    // Load engine options once so the dropdown reflects backend capabilities.
    useEffect(() => {
        const fetchEngines = async () => {
            try {
                const response = await axios.get('/api/ocr/engines')
                const options = response.data?.engines ?? []
                setEngines(options)
            } catch (fetchError) {
                setError('Could not load OCR engine options.')
            }
        }

        fetchEngines()
    }, [])

    useEffect(() => {
        if (!file) {
            setFilePreviewUrl('')
            return
        }

        const nextUrl = URL.createObjectURL(file)
        setFilePreviewUrl(nextUrl)

        return () => {
            URL.revokeObjectURL(nextUrl)
        }
    }, [file])

    const canStart = useMemo(() => Boolean(file) && !loading, [file, loading])
    const transcription = result?.transcription ?? null
    const fieldsEntries = useMemo(() => {
        const fields = transcription?.fields
        if (!fields || typeof fields !== 'object') {
            return []
        }

        return Object.entries(fields)
            .filter(([fieldName, fieldValue]) => String(fieldName ?? '').trim().length > 0 && String(fieldValue ?? '').trim().length > 0)
            .sort(([leftKey], [rightKey]) => String(leftKey).localeCompare(String(rightKey), 'pt-BR'))
    }, [transcription])
    const rawText = useMemo(() => {
        const rawValue = transcription?.raw_text
        return typeof rawValue === 'string' ? rawValue : ''
    }, [transcription])
    const fieldPositions = transcription?.field_positions
    const fieldPositionsMeta = transcription?.field_positions_meta
    const markers = useMemo(
        () => buildFieldMarkers(transcription?.fields, rawText, transcription?.ocr_meta, fieldPositions),
        [transcription, rawText, fieldPositions],
    )
    const metricsEntries = useMemo(() => {
        if (!transcription) {
            return []
        }

        return metricsOrder.map((metricKey) => {
            if (metricKey === 'processing_time') {
                return [metricKey, result?.processing_time ?? '-']
            }

            return [metricKey, transcription?.[metricKey]]
        })
    }, [metricsOrder, result?.processing_time, transcription])

    const parsedResult = useMemo(() => {
        if (typeof transcription !== 'string') {
            return transcription
        }

        try {
            return JSON.parse(transcription)
        } catch {
            return transcription
        }
    }, [transcription])

    useEffect(() => {
        setActiveMarkerKey('')
    }, [result])

    const onStart = async () => {
        if (!canStart) {
            return
        }

        setLoading(true)
        setError('')
        setResult(null)

        // Send file + selected engine to backend-core, which orchestrates backend-ocr.
        const formData = new FormData()
        formData.append('file', file)

        if (selectedEngine !== SYSTEM_ENGINE_VALUE) {
            formData.append('engine', selectedEngine)
        }

        try {
            const response = await axios.post('/api/ocr/process', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            })
            setResult(response.data)
            setActiveTab(RESULT_TABS.FIELDS)
        } catch (requestError) {
            const backendError = requestError?.response?.data?.error
            setError(backendError || 'OCR processing failed.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-800 px-6 py-10 text-slate-100 md:py-14">
            <div className="mx-auto max-w-7xl rounded-2xl border border-slate-700/70 bg-slate-900/90 p-7 shadow-2xl shadow-slate-950/50 backdrop-blur-sm md:p-9">
                <h1 className="text-3xl font-semibold tracking-tight text-slate-50">DocuParse OCR</h1>
                <p className="mt-2 text-sm text-slate-300">Envie o arquivo, visualize o documento e acompanhe os dados extraídos por abas.</p>

                <div className="mt-7 grid gap-6 lg:grid-cols-[1.15fr_1fr]">
                    <section className="min-w-0 space-y-5 rounded-xl border border-slate-700/70 bg-slate-900/70 p-4 md:p-5">
                        <div className="space-y-2">
                            <label className="block text-xs font-semibold uppercase tracking-[0.12em] text-slate-300">File</label>
                            <input
                                type="file"
                                accept=".pdf,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp"
                                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                                className="block w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 file:mr-4 file:rounded-md file:border-0 file:bg-blue-900 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-100 hover:file:bg-blue-950"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="block text-xs font-semibold uppercase tracking-[0.12em] text-slate-300">OCR Engine</label>
                            <select
                                value={selectedEngine}
                                onChange={(event) => setSelectedEngine(event.target.value)}
                                className="block w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-700/40"
                            >
                                <option value={SYSTEM_ENGINE_VALUE}>Utilizar a indicação do sistema</option>
                                {engines.map((engine) => (
                                    <option key={engine.value} value={engine.value}>
                                        {engine.label}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <button
                            type="button"
                            onClick={onStart}
                            disabled={!canStart}
                            className="inline-flex h-11 items-center justify-center rounded-lg bg-blue-900 px-5 text-sm font-semibold text-slate-50 transition-colors hover:bg-blue-950 disabled:cursor-not-allowed disabled:bg-slate-600 disabled:text-slate-300"
                        >
                            {loading ? 'Running...' : 'Start'}
                        </button>

                        <div className="space-y-2">
                            <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-300">Arquivo enviado</h2>

                            {!filePreviewUrl ? (
                                <div className="flex min-h-[320px] items-center justify-center rounded-lg border border-dashed border-slate-600 bg-slate-950/40 px-4 text-center text-sm text-slate-400">
                                    Selecione um arquivo para visualizar aqui.
                                </div>
                            ) : (
                                <div className="relative overflow-hidden rounded-lg border border-slate-700 bg-slate-950/50">
                                    <div className="max-h-[520px] overflow-auto">
                                        {file?.type === 'application/pdf' ? (
                                            <object data={filePreviewUrl} type="application/pdf" className="h-[520px] w-full">
                                                <div className="flex h-[520px] items-center justify-center px-4 text-sm text-slate-300">
                                                    Não foi possível renderizar o PDF no navegador.
                                                </div>
                                            </object>
                                        ) : (
                                            <img src={filePreviewUrl} alt="Preview do arquivo enviado" className="w-full" />
                                        )}
                                    </div>

                                    {markers.map((marker) => {
                                        const isActive = activeMarkerKey === marker.key

                                        return (
                                            <React.Fragment key={marker.key}>
                                                {marker.boxRatio && (
                                                    <div
                                                        className={`pointer-events-none absolute z-[8] border-2 transition ${isActive ? 'border-cyan-300 bg-cyan-400/20' : 'border-blue-300/80 bg-blue-500/10'}`}
                                                        style={{
                                                            left: `${marker.boxRatio.x * 100}%`,
                                                            top: `${marker.boxRatio.y * 100}%`,
                                                            width: `${marker.boxRatio.width * 100}%`,
                                                            height: `${marker.boxRatio.height * 100}%`,
                                                        }}
                                                    />
                                                )}

                                                <button
                                                    type="button"
                                                    title={`${marker.label}: ${marker.value}`}
                                                    onMouseEnter={() => setActiveMarkerKey(marker.key)}
                                                    onMouseLeave={() => setActiveMarkerKey('')}
                                                    onClick={() => setActiveMarkerKey((current) => (current === marker.key ? '' : marker.key))}
                                                    className={`absolute z-10 -translate-x-1/2 -translate-y-1/2 rounded-full border text-[10px] font-semibold transition ${isActive ? 'h-8 w-8 border-blue-200 bg-blue-500/80 text-white' : 'h-6 w-6 border-slate-100 bg-blue-500/65 text-slate-50 hover:bg-blue-500/80'}`}
                                                    style={{
                                                        left: `${marker.xRatio * 100}%`,
                                                        top: `${marker.yRatio * 100}%`,
                                                    }}
                                                    aria-label={`Local do campo ${marker.label}`}
                                                >
                                                    {marker.label.slice(0, 1).toUpperCase()}
                                                </button>
                                            </React.Fragment>
                                        )
                                    })}
                                </div>
                            )}

                            {markers.length > 0 && (
                                <div className="rounded-lg border border-slate-700/80 bg-slate-950/50 p-3 text-xs text-slate-300">
                                    {activeMarkerKey
                                        ? (() => {
                                            const activeMarker = markers.find((marker) => marker.key === activeMarkerKey)
                                            if (!activeMarker) {
                                                return 'Passe o mouse em um marcador para ver o campo correspondente.'
                                            }

                                            return `Campo: ${activeMarker.label} • Valor: ${activeMarker.value} • Origem da posição: ${activeMarker.source}`
                                        })()
                                        : 'Passe o mouse ou clique em um marcador para ver qual campo foi identificado nessa região.'}
                                </div>
                            )}

                            {result && (
                                <div className="rounded-lg border border-slate-700/80 bg-slate-950/50 p-3 text-xs text-slate-300">
                                    {fieldPositionsMeta?.available
                                        ? `Posicionamento por coordenadas reais ativo (${Object.keys(fieldPositions || {}).length} campos mapeados).`
                                        : 'Coordenadas reais indisponíveis neste arquivo; exibindo posição inferida quando possível.'}
                                </div>
                            )}
                        </div>
                    </section>

                    <section className="min-w-0 space-y-4 rounded-xl border border-slate-700/70 bg-slate-900/70 p-4 md:p-5">
                        <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-300">Resultado</h2>

                        <div className="flex flex-wrap gap-2">
                            <button
                                type="button"
                                onClick={() => setActiveTab(RESULT_TABS.FIELDS)}
                                className={`rounded-md px-3 py-2 text-xs font-semibold transition ${activeTab === RESULT_TABS.FIELDS ? 'bg-blue-800 text-slate-50' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
                            >
                                Fields
                            </button>

                            <button
                                type="button"
                                onClick={() => setActiveTab(RESULT_TABS.METRICS)}
                                className={`rounded-md px-3 py-2 text-xs font-semibold transition ${activeTab === RESULT_TABS.METRICS ? 'bg-blue-800 text-slate-50' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
                            >
                                Métricas
                            </button>

                            <button
                                type="button"
                                onClick={() => setActiveTab(RESULT_TABS.RAW_TEXT)}
                                className={`rounded-md px-3 py-2 text-xs font-semibold transition ${activeTab === RESULT_TABS.RAW_TEXT ? 'bg-blue-800 text-slate-50' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
                            >
                                Raw Text
                            </button>
                        </div>

                        {!result ? (
                            <div className="flex min-h-[340px] items-center justify-center rounded-lg border border-dashed border-slate-600 bg-slate-950/40 px-4 text-center text-sm text-slate-400">
                                O resultado aparecerá aqui após executar o OCR.
                            </div>
                        ) : (
                            <div className="max-h-[620px] overflow-auto rounded-lg border border-slate-700 bg-slate-950/70">
                                {activeTab === RESULT_TABS.FIELDS && (
                                    <div className="p-4">
                                        {/* Indicador de confiança baseado no final_score: < 0.75 → aviso, >= 0.75 → sucesso */}
                                        {transcription && typeof transcription.final_score === 'number' && (
                                            <div className={`mb-4 rounded-lg border px-3 py-2.5 text-xs ${
                                                transcription.final_score >= 0.75
                                                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                                                    : 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                                            }`}>
                                                <div className="font-semibold">
                                                    {transcription.final_score >= 0.75
                                                        ? 'Boa confiança! Valores extraídos corretamente'
                                                        : 'Confiança média baixa, recomenda-se inserir manualmente os valores dos campos do arquivo enviado'}
                                                </div>
                                                <div className="mt-0.5 text-slate-400">
                                                    Score de confiança: {(transcription.final_score * 100).toFixed(1)}%
                                                </div>
                                            </div>
                                        )}

                                        <div className="mb-3 text-xs text-slate-400">
                                            Campos capturados: {fieldsEntries.length}
                                        </div>
                                        {fieldsEntries.length === 0 ? (
                                            <div className="text-sm text-slate-400">Nenhum campo encontrado em fields.</div>
                                        ) : (
                                            <div className="overflow-x-auto">
                                                <table className="min-w-max border-collapse text-sm">
                                                    <thead>
                                                        <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-[0.12em] text-slate-400">
                                                            <th className="w-[220px] px-3 py-2 whitespace-nowrap">Campo</th>
                                                            <th className="px-3 py-2">Valor</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {fieldsEntries.map(([fieldName, fieldValue]) => (
                                                            <tr
                                                                key={fieldName}
                                                                className={`border-b border-slate-800/70 text-slate-200 ${activeMarkerKey === fieldName ? 'bg-blue-950/50' : ''}`}
                                                                onMouseEnter={() => setActiveMarkerKey(fieldName)}
                                                                onMouseLeave={() => setActiveMarkerKey('')}
                                                            >
                                                                <td className="px-3 py-2 font-medium whitespace-nowrap text-slate-100">{fieldName}</td>
                                                                <td className="px-3 py-2 whitespace-nowrap">{formatMetricValue(fieldValue)}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {activeTab === RESULT_TABS.METRICS && (
                                    <div className="p-4">
                                        <table className="w-full border-collapse text-sm">
                                            <thead>
                                                <tr className="border-b border-slate-700 text-left text-xs uppercase tracking-[0.12em] text-slate-400">
                                                    <th className="px-3 py-2">Métrica</th>
                                                    <th className="px-3 py-2">Valor</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {metricsEntries.map(([metricName, metricValue]) => (
                                                    <tr key={metricName} className="border-b border-slate-800/70 text-slate-200">
                                                        <td className="px-3 py-2 font-medium text-slate-100">{metricName}</td>
                                                        <td className="px-3 py-2 break-words">
                                                            {typeof metricValue === 'object' && metricValue !== null ? (
                                                                <JsonViewer value={metricValue} />
                                                            ) : (
                                                                formatMetricValue(metricValue)
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}

                                {activeTab === RESULT_TABS.RAW_TEXT && (
                                    <pre className="whitespace-pre-wrap break-words p-4 text-xs text-slate-100">
                                        {rawText || 'Sem conteúdo em raw_text.'}
                                    </pre>
                                )}
                            </div>
                        )}

                        {result && (
                            <div className="rounded-lg border border-slate-700/80 bg-slate-950/50 p-3 text-xs text-slate-300">
                                <div>Arquivo processado: {result.filename || '-'}</div>
                                <div>Tipo detectado: {result.detected_type || '-'}</div>
                                <div>Motores usados: {Array.isArray(result.tools_used) && result.tools_used.length > 0 ? result.tools_used.join(', ') : '-'}</div>
                            </div>
                        )}
                    </section>
                </div>

                {error && <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}

                {result !== null && (
                    <div className="mt-7 space-y-2">
                        <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-300">JSON completo (debug)</h2>
                        <pre className="max-h-[260px] overflow-auto rounded-lg border border-slate-700 bg-slate-950/90 p-4 text-xs text-slate-100">
                            <JsonViewer value={parsedResult} />
                        </pre>
                    </div>
                )}
            </div>
        </div>
    )
}

ReactDOM.createRoot(document.getElementById('root')).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
