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


function App() {
    const SYSTEM_ENGINE_VALUE = ''
    const [engines, setEngines] = useState([])
    const [selectedEngine, setSelectedEngine] = useState(SYSTEM_ENGINE_VALUE)
    const [file, setFile] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [result, setResult] = useState(null)

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

    const canStart = useMemo(() => Boolean(file) && !loading, [file, loading])
    const parsedResult = useMemo(() => {
        if (typeof result !== 'string') {
            return result
        }

        try {
            return JSON.parse(result)
        } catch {
            return result
        }
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
        } catch (requestError) {
            const backendError = requestError?.response?.data?.error
            setError(backendError || 'OCR processing failed.')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-800 px-6 py-10 text-slate-100 md:py-14">
            <div className="mx-auto max-w-3xl rounded-2xl border border-slate-700/70 bg-slate-900/90 p-7 shadow-2xl shadow-slate-950/50 backdrop-blur-sm md:p-9">
                <h1 className="text-3xl font-semibold tracking-tight text-slate-50">DocuParse OCR</h1>
                <p className="mt-2 text-sm text-slate-300">Upload an image or PDF, select an OCR engine and click Start.</p>

                <div className="mt-7 space-y-5">
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
                </div>

                {error && <div className="mt-4 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}

                {result !== null && (
                    <div className="mt-7 space-y-2">
                        <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-300">Result</h2>
                        <pre className="max-h-[420px] overflow-auto rounded-lg border border-slate-700 bg-slate-950/90 p-4 text-xs text-slate-100">
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
