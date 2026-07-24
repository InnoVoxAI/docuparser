import { SETTINGS_TABS } from '../types'

export function SettingsStepActions({
    activeTab,
    onSaveDraft,
    onNext,
}: {
    activeTab: string
    onSaveDraft: () => void | Promise<unknown>
    onNext: () => void | Promise<unknown>
}) {
    const currentIndex = SETTINGS_TABS.findIndex((tab) => tab.id === activeTab)
    const nextTab = SETTINGS_TABS[currentIndex + 1]
    return (
        <div className="mt-4 flex flex-wrap items-center justify-end gap-2 border-t border-zinc-200 pt-4">
            <button
                type="button"
                onClick={onSaveDraft}
                className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm font-medium hover:bg-zinc-100"
            >
                Salvar rascunho
            </button>
            {nextTab ? (
                <button type="button" onClick={onNext} className="primary-button">
                    Salvar e ir para {nextTab.label}
                </button>
            ) : null}
        </div>
    )
}
