import js from '@eslint/js'
import globals from 'globals'
import tsParser from '@typescript-eslint/parser'
import tsPlugin from '@typescript-eslint/eslint-plugin'
import reactHooks from 'eslint-plugin-react-hooks'
import jsxA11y from 'eslint-plugin-jsx-a11y'

// Config plano (ESLint 9). Ver research.md §7: rede de segurança antes de
// qualquer refactor estrutural. A regra de fronteira de módulo
// (eslint-plugin-boundaries) é habilitada apenas na Fase 5 (T047), depois
// que os módulos de src/modules/* existirem de fato.
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
            'max-lines': ['error', { max: 150, skipBlankLines: true, skipComments: true }],
        },
    },
    {
        // Arquivos de dados/tipos e testes: FR-012/SC-002 limitam apenas
        // "arquivo de componente" a 150 linhas — dados/tipos e specs de
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
]
