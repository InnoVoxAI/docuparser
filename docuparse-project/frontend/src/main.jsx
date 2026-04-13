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
        <div className="min-h-screen bg-slate-100 text-slate-900 p-6">
            <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-6 space-y-4">
                <h1 className="text-2xl font-bold">DocuParse OCR</h1>
                <p className="text-sm text-slate-600">Upload an image or PDF, select an OCR engine and click Start.</p>

                <div className="space-y-2">
                    <label className="block text-sm font-medium">File</label>
                    <input
                        type="file"
                        accept=".pdf,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp"
                        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                        className="block w-full border rounded px-3 py-2"
                    />
                </div>

                <div className="space-y-2">
                    <label className="block text-sm font-medium">OCR Engine</label>
                    <select
                        value={selectedEngine}
                        onChange={(event) => setSelectedEngine(event.target.value)}
                        className="block w-full border rounded px-3 py-2 bg-white"
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
                    className="px-4 py-2 rounded bg-blue-600 text-white disabled:bg-slate-400"
                >
                    {loading ? 'Running...' : 'Start'}
                </button>

                {error && <div className="text-sm text-red-600">{error}</div>}

                {result && (
                    <div className="space-y-2">
                        <h2 className="text-lg font-semibold">Result</h2>
                        <pre className="text-xs bg-slate-900 text-slate-100 rounded p-4 overflow-auto max-h-[420px]">
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
