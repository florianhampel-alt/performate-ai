import type { SportType, AnalysisResult, UploadResponse } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://performate-ai.onrender.com'

// Debug logging
console.log('API Configuration:')
console.log('NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL)
console.log('API_BASE_URL:', API_BASE_URL)

export class ApiError extends Error {
  public readonly timestamp: string
  public readonly requestUrl: string
  public readonly requestMethod: string
  
  constructor(
    message: string,
    public readonly status: number,
    public readonly response?: any,
    requestUrl?: string,
    requestMethod?: string
  ) {
    super(message)
    this.name = 'ApiError'
    this.timestamp = new Date().toISOString()
    this.requestUrl = requestUrl || 'unknown'
    this.requestMethod = requestMethod || 'GET'
    
    // Ensure stack trace points to actual error location
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiError)
    }
  }
  
  /**
   * Get user-friendly error message with fallbacks
   */
  getUserMessage(): string {
    // Priority order for error messages
    if (this.response?.detail) {
      return this.response.detail
    }
    if (this.response?.message) {
      return this.response.message
    }
    if (this.response?.error) {
      return this.response.error
    }
    return this.message
  }
  
  /**
   * Get technical details for debugging
   */
  getTechnicalDetails(): Record<string, any> {
    return {
      status: this.status,
      message: this.message,
      response: this.response,
      timestamp: this.timestamp,
      requestUrl: this.requestUrl,
      requestMethod: this.requestMethod,
      stack: this.stack
    }
  }
  
  /**
   * Check if error is retryable
   */
  isRetryable(): boolean {
    return this.status >= 500 && this.status < 600 // 5xx server errors
  }
  
  /**
   * Check if error is client error (4xx)
   */
  isClientError(): boolean {
    return this.status >= 400 && this.status < 500
  }
}

/**
 * Enterprise-grade API request function with comprehensive error handling
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  const method = options.method || 'GET'
  
  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }

  console.log(`🔄 API Request: ${method} ${url}`)

  try {
    const response = await fetch(url, config)
    
    console.log(`📡 API Response: ${method} ${url} -> ${response.status} ${response.statusText}`)
    
    if (!response.ok) {
      let errorData: any = {}
      const contentType = response.headers.get('content-type')
      
      try {
        if (contentType?.includes('application/json')) {
          errorData = await response.json()
        } else {
          const textResponse = await response.text()
          errorData = { message: textResponse }
        }
      } catch (parseError) {
        console.warn('Failed to parse error response:', parseError)
        errorData = { message: `HTTP ${response.status}: ${response.statusText}` }
      }
      
      // Log error details for debugging
      console.error(`❌ API Error: ${method} ${url}`, {
        status: response.status,
        statusText: response.statusText,
        errorData,
        headers: Object.fromEntries(response.headers.entries())
      })
      
      const apiError = new ApiError(
        errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData,
        url,
        method
      )
      
      throw apiError
    }

    const result = await response.json()
    console.log(`✅ API Success: ${method} ${url}`, result)
    return result
    
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    
    // Network or other errors
    console.error(`🌐 Network Error: ${method} ${url}`, error)
    
    throw new ApiError(
      `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      0,
      { originalError: error },
      url,
      method
    )
  }
}

export async function uploadVideo(
  file: File,
  sportType: SportType
): Promise<UploadResponse> {
  console.log(`Uploading to: ${API_BASE_URL}/upload`)
  console.log('File:', file.name, file.size, 'bytes, Type:', file.type)
  console.log('Sport type:', sportType)
  
  const formData = new FormData()
  formData.append('file', file)
  formData.append('sport_type', sportType)

  // Realistic timeout for actual internet speeds
  const controller = new AbortController()
  const timeoutMs = Math.max(60000, (file.size / (1024 * 1024)) * 10000) // 10s per MB, minimum 60s
  const timeoutId = setTimeout(() => {
    controller.abort()
  }, timeoutMs)
  
  console.log(`Upload timeout set to: ${timeoutMs}ms (${Math.round(timeoutMs/1000)}s for ${(file.size/(1024*1024)).toFixed(1)}MB)`)

  try {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
      // Remove Content-Type header to let browser set it with boundary for FormData
    })

    console.log('Upload response status:', response.status, response.statusText)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('Upload failed with response:', errorText)
      
      let errorData
      try {
        errorData = JSON.parse(errorText)
      } catch {
        errorData = { message: errorText }
      }
      
      throw new ApiError(
        errorData.message || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      )
    }

    clearTimeout(timeoutId) // Clear timeout on success
    const result = await response.json()
    console.log('Upload successful:', result)
    return result
    
  } catch (error) {
    clearTimeout(timeoutId) // Clear timeout on error
    console.error('Upload request failed:', error)
    
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(
        `Upload timeout (${timeoutMs/1000}s): Try a smaller video or better connection.`,
        408,
        { timeout: true }
      )
    }
    
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError(
      `Network error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      0,
      error
    )
  }
}

export async function startAnalysis(
  fileId: string,
  sportType: SportType
): Promise<{ analysisId: string }> {
  return apiRequest('/analysis/start', {
    method: 'POST',
    body: JSON.stringify({
      file_id: fileId,
      sport_type: sportType,
    }),
  })
}

export async function getAnalysisResults(analysisId: string): Promise<AnalysisResult> {
  return apiRequest(`/analysis/${analysisId}`)
}

export async function getAnalysisStatus(analysisId: string): Promise<{
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress?: number
  error?: string
}> {
  return apiRequest(`/analysis/${analysisId}/status`)
}

export async function getSupportedSports(): Promise<SportType[]> {
  return apiRequest('/sports')
}

export async function getHealthStatus(): Promise<{ status: string; version: string }> {
  return apiRequest('/health')
}

// Polling function for analysis status
export async function pollAnalysisStatus(
  analysisId: string,
  onUpdate?: (status: any) => void,
  intervalMs: number = 2000
): Promise<AnalysisResult> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getAnalysisStatus(analysisId)
        
        if (onUpdate) {
          onUpdate(status)
        }

        if (status.status === 'completed') {
          const results = await getAnalysisResults(analysisId)
          resolve(results)
        } else if (status.status === 'failed') {
          reject(new ApiError(status.error || 'Analysis failed', 500))
        } else {
          // Continue polling
          setTimeout(poll, intervalMs)
        }
      } catch (error) {
        reject(error)
      }
    }

    poll()
  })
}
