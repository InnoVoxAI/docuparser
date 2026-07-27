import { SETTINGS_TAB_HELP } from '../types'

export function TabHelp({ tab }: { tab: string }) {
    const help = SETTINGS_TAB_HELP[tab]
    if (!help) {
        return null
    }
    return (
        <div className="mb-4 rounded-md border border-sky-200 bg-sky-50 px-4 py-3">
            <div className="text-sm font-semibold text-sky-950">{help.title}</div>
            <div className="mt-1 text-sm leading-6 text-sky-800">{help.text}</div>
        </div>
    )
}
