import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

export function CopySlugButton({ slug }: { slug: string }) {
    const [copied, setCopied] = useState(false)
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(slug)
        } catch {
            const ta = document.createElement('textarea')
            ta.value = slug
            document.body.appendChild(ta)
            ta.select()
            document.execCommand('copy')
            document.body.removeChild(ta)
        }
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
    }
    return (
        <button
            type="button"
            onClick={handleCopy}
            title="Copiar slug"
            className="ml-1.5 inline-flex items-center text-zinc-400 hover:text-zinc-700 transition-colors"
        >
            {copied ? <Check size={12} className="text-green-600" /> : <Copy size={12} />}
        </button>
    )
}
