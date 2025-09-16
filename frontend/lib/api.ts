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
  console.log(`Starting S3 presigned upload for: ${file.name} (${file.size} bytes)`)
  console.log('Sport type:', sportType)
  
  try {
    // Step 1: Initialize upload and get presigned URL
    console.log('📋 Initializing upload...')
    const initResponse = await apiRequest<{
      analysis_id: string
      upload_url: string
      upload_fields: Record<string, string>
      s3_key: string
      expires_in: number
      max_file_size: number
    }>('/upload/init', {
      method: 'POST',
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || 'video/mp4',
        file_size: file.size,
        sport_type: sportType
      })
    })
    
    console.log('✅ Upload initialized:', initResponse.analysis_id)
    console.log('📤 S3 upload URL received, expires in:', initResponse.expires_in, 'seconds')
    
    // Step 2: Upload directly to S3 using presigned URL
    console.log('⬆️ Uploading to S3...')
    const formData = new FormData()
    
    // Add all the required fields from presigned URL
    Object.entries(initResponse.upload_fields).forEach(([key, value]) => {
      formData.append(key, value)
    })
    
    // Add the file last (important for S3)
    formData.append('file', file)
    
    // Upload to S3 with generous timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 300000) // 5 minutes
    
    const s3Response = await fetch(initResponse.upload_url, {
      method: 'POST',
      body: formData,
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    
    if (!s3Response.ok) {
      const errorText = await s3Response.text()
      console.error('❌ S3 upload failed:', errorText)
      throw new ApiError(`S3 upload failed: ${s3Response.statusText}`, s3Response.status)
    }
    
    console.log('✅ S3 upload successful!')
    
    // Step 3: Complete upload and start analysis
    console.log('🔄 Completing upload and starting analysis...')
    const completeResponse = await apiRequest<{
      analysis_id: string
      status: string
      sport_detected: string
      video_url: string
    }>('/upload/complete', {
      method: 'POST',
      body: JSON.stringify({
        analysis_id: initResponse.analysis_id
      })
    })
    
    console.log('🎉 Upload complete! Analysis started:', completeResponse.analysis_id)
    
    return {
      analysis_id: completeResponse.analysis_id,
      fileId: completeResponse.analysis_id, // For backward compatibility
      status: completeResponse.status,
      message: 'Upload successful, analysis started'
    }
    
  } catch (error) {
    console.error('💥 Upload failed:', error)
    
    if (error instanceof DOMException && (error.name === 'TimeoutError' || error.name === 'AbortError')) {
      throw new ApiError(
        'Upload timeout: Please try again or use a smaller video.',
        408,
        { timeout: true }
      )
    }
    
    if (error instanceof ApiError) {
      throw error
    }
    
    throw new ApiError(
      `Upload error: ${error instanceof Error ? error.message : 'Unknown error'}`,
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
