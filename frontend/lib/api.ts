import type { SportType, AnalysisResult, UploadResponse } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
  const formData = new FormData()
  formData.append('file', file)
  formData.append('sport_type', sportType)

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new ApiError(
      errorData.message || 'Upload failed',
      response.status,
      errorData
    )
  }

  return await response.json()
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
