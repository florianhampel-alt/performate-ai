'use client'

import { useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ApiError } from '@/lib/api'
import { AlertTriangle, RefreshCw, Bug, Copy, CheckCircle } from 'lucide-react'

interface ErrorDisplayProps {
  error: Error | ApiError | string
  title?: string
  showRetry?: boolean
  onRetry?: () => void
  showTechnicalDetails?: boolean
  className?: string
}

export default function ErrorDisplay({
  error,
  title = "Fehler aufgetreten",
  showRetry = false,
  onRetry,
  showTechnicalDetails = process.env.NODE_ENV === 'development',
  className = ""
}: ErrorDisplayProps) {
  const [showDetails, setShowDetails] = useState(false)
  const [copied, setCopied] = useState(false)

  // Normalize error to ApiError or Error object
  const normalizedError = typeof error === 'string' 
    ? new Error(error)
    : error

  const isApiError = normalizedError instanceof ApiError
  const userMessage = isApiError 
    ? normalizedError.getUserMessage()
    : normalizedError.message

  const errorSeverity = isApiError && isApiError.isClientError()
    ? 'warning'
    : 'destructive'

  const handleCopyDetails = async () => {
    if (!isApiError) return
    
    const details = JSON.stringify(isApiError.getTechnicalDetails(), null, 2)
    
    try {
      await navigator.clipboard.writeText(details)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <Alert variant={errorSeverity}>
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>{title}</AlertTitle>
        <AlertDescription className="mt-2">
          <div className="mb-4">
            {userMessage}
          </div>
          
          {/* Action buttons */}
          <div className="flex flex-wrap gap-2">
            {showRetry && onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                className="h-8"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Wiederholen
              </Button>
            )}
            
            {showTechnicalDetails && isApiError && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDetails(!showDetails)}
                className="h-8"
              >
                <Bug className="h-3 w-3 mr-1" />
                {showDetails ? 'Details ausblenden' : 'Technische Details'}
              </Button>
            )}
          </div>
        </AlertDescription>
      </Alert>

      {/* Technical Details Panel */}
      {showDetails && isApiError && (
        <Card className="p-4 bg-gray-50 border-gray-200">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-gray-700">
              Technische Fehlerdetails
            </h4>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyDetails}
              className="h-7 text-xs"
            >
              {copied ? (
                <>
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Kopiert
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3 mr-1" />
                  Kopieren
                </>
              )}
            </Button>
          </div>
          
          <div className="space-y-2 text-xs text-gray-600 font-mono">
            <div>
              <span className="font-semibold">Status:</span> {normalizedError.status || 'N/A'}
            </div>
            <div>
              <span className="font-semibold">Zeitpunkt:</span> {isApiError.timestamp}
            </div>
            <div>
              <span className="font-semibold">Request:</span> {isApiError.requestMethod} {isApiError.requestUrl}
            </div>
            {isApiError.response && (
              <div>
                <span className="font-semibold">Response:</span>
                <pre className="mt-1 p-2 bg-white border rounded text-xs overflow-x-auto">
                  {JSON.stringify(isApiError.response, null, 2)}
                </pre>
              </div>
            )}
            {isApiError.isRetryable() && (
              <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded">
                <span className="text-blue-700 text-xs">
                  💡 Dieser Fehler kann durch Wiederholen behoben werden (5xx Server Error)
                </span>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Error category info */}
      {isApiError && (
        <div className="text-xs text-gray-500">
          {isApiError.isClientError() && (
            <span>ℹ️ Client-Fehler - Überprüfen Sie Ihre Eingabe</span>
          )}
          {isApiError.status >= 500 && (
            <span>⚠️ Server-Fehler - Vorübergehendes Problem, versuchen Sie es später erneut</span>
          )}
          {isApiError.status === 0 && (
            <span>🌐 Netzwerk-Fehler - Überprüfen Sie Ihre Internetverbindung</span>
          )}
        </div>
      )}
    </div>
  )
}