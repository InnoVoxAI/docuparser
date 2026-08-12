import { AlertTriangle } from 'lucide-react'

export function AcessoNaoAutorizado() {
    return (
        <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
            <AlertTriangle size={40} className="mb-4" />
            <p className="text-lg font-medium">Acesso não autorizado</p>
            <p className="mt-1 text-sm">Você não tem permissão para acessar esta área.</p>
        </div>
    )
}
