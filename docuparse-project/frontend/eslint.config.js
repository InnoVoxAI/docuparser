import js from '@eslint/js'
import globals from 'globals'
import tsParser from '@typescript-eslint/parser'
import tsPlugin from '@typescript-eslint/eslint-plugin'
import reactHooks from 'eslint-plugin-react-hooks'
import jsxA11y from 'eslint-plugin-jsx-a11y'
import boundaries from 'eslint-plugin-boundaries'

// Config plano (ESLint 9). Ver research.md §7: rede de segurança antes de
// qualquer refactor estrutural. A regra de fronteira de módulo
// (eslint-plugin-boundaries) foi habilitada na Fase 5 (T047), agora que os
// módulos de src/modules/* existem de fato (Fase 4).
export default [
    {
        ignores: ['dist/**', 'coverage/**', 'node_modules/**'],
    },
    js.configs.recommended,
    {
        files: ['**/*.{ts,tsx}'],
        languageOptions: {
            parser: tsParser,
            parserOptions: {
                ecmaFeatures: { jsx: true },
                sourceType: 'module',
            },
            globals: {
                ...globals.browser,
                ...globals.es2021,
            },
        },
        plugins: {
            '@typescript-eslint': tsPlugin,
            'react-hooks': reactHooks,
            'jsx-a11y': jsxA11y,
        },
        rules: {
            ...tsPlugin.configs.recommended.rules,
            ...jsxA11y.configs.recommended.rules,
            'no-unused-vars': 'off',
            '@typescript-eslint/no-unused-vars': 'error',
            '@typescript-eslint/no-explicit-any': 'error',
            'react-hooks/rules-of-hooks': 'error',
            'react-hooks/exhaustive-deps': 'warn',
            'max-lines': ['error', { max: 200, skipBlankLines: true, skipComments: true }],
        },
    },
    {
        // Arquivos de dados/tipos e testes: FR-012/SC-002 limitam apenas
        // "arquivo de componente" a 200 linhas — dados/tipos e specs de
        // teste ficam de fora do limite (ver spec.md FR-012).
        files: ['src/types.ts', 'src/shared/types/**', 'src/models/**', '**/__tests__/**', '**/*.test.{ts,tsx}'],
        rules: {
            'max-lines': 'off',
        },
    },
    {
        files: ['*.config.{js,ts,cjs}', 'vite.config.ts', 'vitest.config.ts'],
        languageOptions: {
            globals: { ...globals.node },
        },
    },
    {
        // Fronteira de módulo (FR-001/FR-008, contracts/module-boundaries.md):
        // um módulo só pode ser consumido pelo seu barrel `index.ts`; `shared`
        // é a única exceção livremente importável por qualquer camada.
        files: ['src/**/*.{ts,tsx}'],
        plugins: { boundaries },
        settings: {
            // Sem isto, o resolver default (node) só tenta .js/.json/.node e
            // nunca encontra os alvos .ts/.tsx — toda dependência local vira
            // "unknown" e a regra de fronteira deixa de verificar qualquer coisa.
            'import/resolver': {
                node: { extensions: ['.js', '.jsx', '.ts', '.tsx'] },
            },
            'boundaries/elements': [
                { type: 'app', pattern: 'src/app' },
                { type: 'module', pattern: 'src/modules/*/**', partialMatch: false, capture: ['moduleName'] },
                { type: 'shared', pattern: 'src/shared' },
                { type: 'models', pattern: 'src/models' },
                { type: 'test', pattern: 'src/__tests__' },
            ],
            // `src/types.ts` é um arquivo solto na raiz (não uma pasta), por
            // isso é classificado como categoria de arquivo, não elemento.
            'boundaries/files': [{ category: 'types', pattern: 'src/types.ts' }],
        },
        rules: {
            'boundaries/dependencies': [
                'error',
                {
                    default: 'disallow',
                    policies: [
                        {
                            from: { element: { type: 'app' } },
                            allow: { to: { element: { type: ['module', 'shared', 'models'] } } },
                        },
                        { from: { element: { type: 'app' } }, allow: { to: { file: { categories: 'types' } } } },
                        {
                            from: { element: { type: 'module' } },
                            allow: { to: { element: { type: ['module', 'shared', 'models'] } } },
                        },
                        { from: { element: { type: 'module' } }, allow: { to: { file: { categories: 'types' } } } },
                        // Testes de a11y dentro de um módulo (`modules/*/__tests__`)
                        // reaproveitam helpers/mocks do harness global de testes.
                        { from: { element: { type: 'module' } }, allow: { to: { element: { type: 'test' } } } },
                        { from: { element: { type: 'shared' } }, allow: { to: { element: { type: ['shared'] } } } },
                        { from: { element: { type: 'shared' } }, allow: { to: { file: { categories: 'types' } } } },
                        // Specs de shared (ex.: shared/lib/tracing.test.ts) reaproveitam
                        // helpers/mocks do harness global de testes, mesma exceção já
                        // concedida a testes de módulo acima.
                        { from: { element: { type: 'shared' } }, allow: { to: { element: { type: 'test' } } } },
                        { from: { element: { type: 'models' } }, allow: { to: { file: { categories: 'types' } } } },
                        {
                            from: { element: { type: 'test' } },
                            allow: { to: { element: { type: ['app', 'module', 'shared', 'models'] } } },
                        },
                        { from: { element: { type: 'test' } }, allow: { to: { file: { categories: 'types' } } } },
                        // Um módulo só pode ser importado de fora pelo seu barrel
                        // (`index.ts`). "Internal" (mesmo diretório) já é ignorado
                        // automaticamente pela regra, mas arquivos do mesmo módulo
                        // em diretórios irmãos (ex.: routes/ -> components/) não
                        // contam como "internal" para o plugin — por isso a
                        // exceção explícita abaixo, via captured.moduleName.
                        { disallow: { to: { element: { type: 'module', fileInternalPath: '!(index.ts)' } } } },
                        {
                            from: { element: { type: 'module' } },
                            allow: {
                                to: { element: { type: 'module', captured: { moduleName: '{{from.moduleName}}' } } },
                            },
                        },
                    ],
                },
            ],
        },
    },
]
