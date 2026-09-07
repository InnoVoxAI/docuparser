import { Alert } from '../../../shared/components'
import type { LayoutConfig, SchemaConfig } from '../../../types'
import { useExtractionState } from '../hooks/useExtractionState'
import { SETTINGS_TABS } from '../types'
import { ActiveTemplateHeader } from './ActiveTemplateHeader'
import { CatalogScopeNotice } from './CatalogScopeNotice'
import { ExamplesEditor } from './ExamplesEditor'
import { ExtractionInstructionsTab } from './ExtractionInstructionsTab'
import { ExtractionPublishTab } from './ExtractionPublishTab'
import { ExtractionRulesTab } from './ExtractionRulesTab'
import { ExtractionSetupTab } from './ExtractionSetupTab'
import { ExtractionTestTab } from './ExtractionTestTab'
import { ReferenceDocumentPanel } from './ReferenceDocumentPanel'
import { SchemaFieldsEditor } from './SchemaFieldsEditor'
import { SettingsStepActions } from './SettingsStepActions'
import { TabHelp } from './TabHelp'

/**
 * Builder LangExtract completo — só renderizado para quem tem `tenants.manage`
 * (o catálogo é global, spec 018). O gate fica em `ExtractionPanel`.
 */
export function ExtractionBuilder({ schemas, layouts }: { schemas: SchemaConfig[]; layouts: LayoutConfig[] }) {
    const state = useExtractionState(schemas, layouts)

    return (
        <>
            <div className="flex gap-1 overflow-x-auto border-b border-zinc-200 px-3 py-2">
                {SETTINGS_TABS.map((tab) => (
                    <button
                        key={tab.id}
                        type="button"
                        onClick={() => state.setActiveTab(tab.id)}
                        className={`h-9 shrink-0 rounded-md px-3 text-sm font-medium ${state.activeTab === tab.id ? 'bg-zinc-900 text-white' : 'text-zinc-600 hover:bg-zinc-100'}`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>
            <div className="p-4">
                <CatalogScopeNotice canManage />
                {state.message ? <Alert>{state.message}</Alert> : null}
                <TabHelp tab={state.activeTab} />
                {state.activeTab !== 'setup' ? (
                    <ActiveTemplateHeader
                        schemaForm={state.schemaForm}
                        layoutForm={state.layoutForm}
                        activeLayout={state.activeLayout}
                        onChangeModel={() => state.setActiveTab('setup')}
                    />
                ) : null}

                {state.activeTab === 'setup' ? (
                    <ExtractionSetupTab
                        schemas={schemas}
                        layouts={layouts}
                        selectedSchemaId={state.selectedSchemaId}
                        onLoadExisting={(id) => state.loadExistingSchema(id, { source: 'manual' })}
                        onNewModel={state.startNewModel}
                        schemaForm={state.schemaForm}
                        setSchemaForm={state.setSchemaForm}
                        layoutForm={state.layoutForm}
                        setLayoutForm={state.setLayoutForm}
                    />
                ) : null}

                {state.activeTab === 'ocr' ? (
                    <ReferenceDocumentPanel
                        selectedDocumentId={state.selectedDocumentId}
                        onSelectDocument={state.setSelectedDocumentId}
                        referenceDocument={state.referenceDocument}
                        fields={state.fields}
                        review={state.referenceReview}
                        onReviewChange={state.setReferenceReview}
                    />
                ) : null}

                {state.activeTab === 'schema' ? (
                    <SchemaFieldsEditor
                        fields={state.fields}
                        onChange={state.setFields}
                        schemaForm={state.schemaForm}
                    />
                ) : null}

                {state.activeTab === 'instructions' ? (
                    <ExtractionInstructionsTab prompt={state.prompt} setPrompt={state.setPrompt} />
                ) : null}

                {state.activeTab === 'examples' ? (
                    <ExamplesEditor
                        examples={state.examples}
                        onChange={state.setExamples}
                        referenceText={state.referenceDocument?.full_transcription || ''}
                    />
                ) : null}

                {state.activeTab === 'test' ? (
                    <ExtractionTestTab
                        referenceDocument={state.referenceDocument}
                        fields={state.fields}
                        examples={state.examples}
                        testOutput={state.testOutput}
                        setTestOutput={state.setTestOutput}
                    />
                ) : null}

                {state.activeTab === 'rules' ? (
                    <ExtractionRulesTab
                        normalizationRules={state.normalizationRules}
                        setNormalizationRules={state.setNormalizationRules}
                    />
                ) : null}

                {state.activeTab === 'publish' ? (
                    <ExtractionPublishTab
                        schemaDefinition={state.schemaDefinition}
                        schemaIdValid={Boolean(state.schemaForm.schema_id.trim())}
                        onCreateSchema={state.createSchema}
                        layoutForm={state.layoutForm}
                        setLayoutForm={state.setLayoutForm}
                        schemas={schemas}
                        onCreateLayout={state.createLayout}
                    />
                ) : null}

                {state.activeTab !== 'publish' ? (
                    <SettingsStepActions
                        activeTab={state.activeTab}
                        onSaveDraft={state.saveDraft}
                        onNext={state.goToNextStep}
                    />
                ) : null}
            </div>
        </>
    )
}
