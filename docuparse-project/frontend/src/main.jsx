import React, { useEffect, useMemo, useState } from 'react'
import ReactDOM from 'react-dom/client'
import axios from 'axios'
import './index.css'


function App() {
    const [engines, setEngines] = useState([])
    const [selectedEngine, setSelectedEngine] = useState('tesseract')
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

                if (options.length > 0) {
                    setSelectedEngine(options[0].value)
                }
            } catch (fetchError) {
                setError('Could not load OCR engine options.')
            }
        }

        fetchEngines()
    }, [])

    const canStart = useMemo(() => Boolean(file) && Boolean(selectedEngine) && !loading, [file, selectedEngine, loading])

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
        formData.append('engine', selectedEngine)

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

                {result && (
                    <div className="mt-7 space-y-2">
                        <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-slate-300">Result</h2>
                        <pre className="max-h-[420px] overflow-auto rounded-lg border border-slate-700 bg-slate-950/90 p-4 text-xs text-slate-100">
                            {JSON.stringify(result, null, 2)}
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
