"use client"

import { AlertTriangle, RefreshCw, Home } from "lucide-react"
import Link from "next/link"
import * as React from "react"

import { Button } from "@/components/ui/button"
import { H1, H2, Body } from "@/components/ui/typography"


interface ErrorBoundaryProps {
  children: React.ReactNode
  fallback?: React.ComponentType<ErrorFallbackProps>
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

interface ErrorFallbackProps {
  error: Error
  resetError: () => void
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  override componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to error reporting service
    console.error('Error caught by boundary:', error, errorInfo)
    
    // In production, you would send this to your error tracking service
    // Example: Sentry.captureException(error, { contexts: { react: { componentStack: errorInfo.componentStack } } })
  }

  resetError = () => {
    this.setState({ hasError: false, error: null })
  }

  override render() {
    if (this.state.hasError && this.state.error) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback
      return <FallbackComponent error={this.state.error} resetError={this.resetError} />
    }

    return this.props.children
  }
}

function DefaultErrorFallback({ error, resetError }: ErrorFallbackProps) {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-6 text-center">
        <div className="flex justify-center">
          <div className="rounded-full bg-error/10 p-4">
            <AlertTriangle className="h-12 w-12 text-error" />
          </div>
        </div>
        
        <div className="space-y-2">
          <H1 color="error">Something went wrong</H1>
          <Body color="muted">
            We encountered an unexpected error. The error has been logged and we'll look into it.
          </Body>
        </div>

        {process.env.NODE_ENV === 'development' && (
          <details className="text-left bg-muted/20 rounded-lg p-4 space-y-2">
            <summary className="cursor-pointer font-medium text-sm">
              Error Details (Development Only)
            </summary>
            <pre className="text-xs overflow-auto whitespace-pre-wrap break-words text-muted-foreground">
              {error.message}
              {error.stack && `\n\n${  error.stack}`}
            </pre>
          </details>
        )}

        <div className="flex gap-3 justify-center">
          <Button
            variant="secondary"
            onClick={resetError}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Try Again
          </Button>
          
          <Link href="/">
            <Button variant="outline" className="gap-2">
              <Home className="h-4 w-4" />
              Go Home
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}

// Feature-specific error boundary with custom styling
export function FeatureErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary
      fallback={({ error, resetError }) => (
        <div className="rounded-lg border border-error/20 bg-error/5 p-6 space-y-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-error shrink-0 mt-0.5" />
            <div className="space-y-2 flex-1">
              <H2 color="error">Failed to load this section</H2>
              <Body color="muted" className="text-sm">
                {error.message || "An unexpected error occurred"}
              </Body>
            </div>
          </div>
          
          <Button
            variant="outline"
            size="sm"
            onClick={resetError}
            className="gap-2"
          >
            <RefreshCw className="h-3 w-3" />
            Retry
          </Button>
        </div>
      )}
    >
      {children}
    </ErrorBoundary>
  )
}

// Hook for error handling in functional components
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null)

  React.useEffect(() => {
    if (error) {
      throw error
    }
  }, [error])

  const resetError = React.useCallback(() => {
    setError(null)
  }, [])

  const captureError = React.useCallback((error: Error) => {
    setError(error)
  }, [])

  return { captureError, resetError }
}

// Async error boundary for handling async errors
export function useAsyncError() {
  const [, setError] = React.useState()
  
  return React.useCallback(
    (error: Error) => {
      setError(() => {
        throw error
      })
    },
    [setError]
  )
}