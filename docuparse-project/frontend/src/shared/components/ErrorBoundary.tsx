import { Component, type ReactNode } from 'react'
import { Alert } from './Alert'

interface ErrorBoundaryProps {
    children?: ReactNode
}

interface ErrorBoundaryState {
    hasError: boolean
    error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    state: ErrorBoundaryState = { hasError: false, error: null }

    static getDerivedStateFromError(error: Error): ErrorBoundaryState {
        return { hasError: true, error }
    }

    componentDidCatch(error: Error, errorInfo: { componentStack: string }) {
        console.error('ErrorBoundary capturou um erro:', error, errorInfo.componentStack)
    }

    render() {
        if (this.state.hasError) {
            return (
                <Alert tone="error">
                    Ocorreu um erro inesperado nesta tela. Tente atualizar a página ou voltar mais tarde.
                </Alert>
            )
        }
        return this.props.children
    }
}
