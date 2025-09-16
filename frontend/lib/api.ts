import type { SportType, AnalysisResult, UploadResponse } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://performate-ai.onrender.com'

// Debug logging
console.log('API Configuration:')
console.log('NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL)
console.log('API_BASE_URL:', API_BASE_URL)

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public response?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  
  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  }

  try {
    const response = await fetch(url, config)
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new ApiError(
        errorData.message || `HTTP error! status: ${response.status}`,
        response.status,
        errorData
      )
    }

    return await response.json()
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`, 0)
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

  // Realistic timeout: 2.3MB should upload in 10-15 seconds max
  const controller = new AbortController()
  const timeoutMs = Math.min(30000, Math.max(15000, file.size / 1024)) // 15s minimum, 30s max, ~1s per KB
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
