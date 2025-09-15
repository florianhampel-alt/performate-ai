'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert } from '@/components/ui/alert'
import { Select } from '@/components/ui/select'
import { Card } from '@/components/ui/card'
import LoadingSpinner from '@/components/LoadingSpinner'
import { uploadVideo, startAnalysis } from '@/lib/api'
import type { SportType, UploadStatus } from '@/lib/types'

const SUPPORTED_SPORTS: SportType[] = [
  'climbing',
  'bouldering',
  'skiing',
  'motocross',
  'mountainbike'
]

const SPORT_LABELS = {
  climbing: 'Rock Climbing',
  bouldering: 'Bouldering',
  skiing: 'Skiing',
  motocross: 'Motocross',
  mountainbike: 'Mountain Biking'
}

export default function VideoUpload() {
  const [selectedSport, setSelectedSport] = useState<SportType>('climbing')
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle')
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [analysisId, setAnalysisId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setError(null)
    setUploadedFile(file)
    setUploadStatus('uploading')
    setUploadProgress(0)

    // Declare progressInterval outside try block for cleanup
    let progressInterval: NodeJS.Timeout | null = null

    try {
      console.log('Starting upload for file:', file.name, 'Sport:', selectedSport)
      
      // Simulate upload progress
      progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 95) {
            if (progressInterval) clearInterval(progressInterval)
            return 95
          }
          return prev + Math.random() * 10
        })
      }, 500)

      console.log('Calling uploadVideo API...')
      const uploadResult = await uploadVideo(file, selectedSport)
      console.log('Upload result:', uploadResult)
      
      if (progressInterval) clearInterval(progressInterval)
      setUploadProgress(100)
      setUploadStatus('uploaded')
      
      // Start analysis
      setUploadStatus('analyzing')
      console.log('Starting analysis with fileId:', uploadResult.fileId || uploadResult.analysis_id)
      
      // The backend returns analysis_id directly in upload response
      if (uploadResult.analysis_id) {
        setAnalysisId(uploadResult.analysis_id)
        setUploadStatus('completed')
      } else if (uploadResult.fileId) {
        // Fallback: try startAnalysis if no analysis_id in upload response
        const analysisResult = await startAnalysis(uploadResult.fileId, selectedSport)
        setAnalysisId(analysisResult.analysisId)
        setUploadStatus('completed')
      } else {
        throw new Error('No analysis_id or fileId received from upload')
      }

    } catch (err) {
      console.error('Upload error:', err)
      if (progressInterval) clearInterval(progressInterval)
      const errorMessage = err instanceof Error ? err.message : 'Upload failed'
      console.error('Error details:', errorMessage)
      setError(`Upload failed: ${errorMessage}`)
      setUploadStatus('error')
      setUploadProgress(0)
    }
  }, [selectedSport])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.wmv']
    },
    maxFiles: 1,
    maxSize: 120 * 1024 * 1024, // 120MB
    disabled: uploadStatus === 'uploading' || uploadStatus === 'analyzing'
  })

  const resetUpload = () => {
    setUploadStatus('idle')
    setUploadProgress(0)
    setUploadedFile(null)
    setAnalysisId(null)
    setError(null)
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Upload Your Sports Video
        </h1>
        <p className="text-gray-600">
          Upload a video of your performance to get AI-powered analysis and insights
        </p>
      </div>

      <Card className="p-8">
        {/* Sport Selection */}
        <div className="mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Sport
          </label>
          <Select 
            value={selectedSport}
            onValueChange={(value: string) => setSelectedSport(value as SportType)}
          >
            {SUPPORTED_SPORTS.map(sport => (
              <option key={sport} value={sport}>
                {SPORT_LABELS[sport]}
              </option>
            ))}
          </Select>
        </div>

        {/* Upload Area */}
        {uploadStatus === 'idle' && (
          <div
            {...getRootProps()}
            className={`upload-area ${isDragActive ? 'drag-over' : ''}`}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center">
              <div className="text-4xl mb-4">📹</div>
              <p className="text-lg font-medium mb-2">
                {isDragActive 
                  ? 'Drop your video here' 
                  : 'Drag & drop your video here, or click to select'}
              </p>
              <p className="text-sm text-gray-500 mb-4">
                Supports MP4, MOV, AVI, MKV, WMV (max 120MB)
              </p>
              <Button variant="outline">
                Choose File
              </Button>
            </div>
          </div>
        )}

        {/* Upload Progress */}
        {(uploadStatus === 'uploading' || uploadStatus === 'analyzing') && (
          <div className="text-center">
            <LoadingSpinner className="mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">
              {uploadStatus === 'uploading' ? 'Uploading video...' : 'Analyzing video...'}
            </h3>
            {uploadStatus === 'uploading' && (
              <div className="mb-4">
                <Progress value={uploadProgress} className="w-full mb-2" />
                <p className="text-sm text-gray-600">{Math.round(uploadProgress)}% complete</p>
              </div>
            )}
            {uploadedFile && (
              <p className="text-sm text-gray-600">
                File: {uploadedFile.name} ({(uploadedFile.size / (1024 * 1024)).toFixed(1)} MB)
              </p>
            )}
          </div>
        )}

        {/* Success State */}
        {uploadStatus === 'completed' && analysisId && (
          <div className="text-center">
            <div className="text-4xl mb-4">✅</div>
            <h3 className="text-lg font-medium mb-2">Analysis Complete!</h3>
            <p className="text-gray-600 mb-6">
              Your {SPORT_LABELS[selectedSport]} video has been analyzed successfully.
            </p>
            <div className="flex justify-center space-x-4">
              <Button 
                onClick={() => window.location.href = `/analysis/${analysisId}`}
              >
                View Results
              </Button>
              <Button variant="outline" onClick={resetUpload}>
                Upload Another
              </Button>
            </div>
          </div>
        )}

        {/* Error State */}
        {uploadStatus === 'error' && (
          <div className="text-center">
            <Alert variant="destructive" className="mb-4">
              <h4 className="font-medium">Upload Failed</h4>
              <p>{error || 'An unexpected error occurred'}</p>
            </Alert>
            <Button onClick={resetUpload}>
              Try Again
            </Button>
          </div>
        )}
      </Card>

      {/* Upload Tips */}
      <div className="mt-8 grid md:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-3">📱 Recording Tips</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li>• Record in landscape mode for best results</li>
            <li>• Ensure good lighting and clear visibility</li>
            <li>• Keep the camera stable and focused on the athlete</li>
            <li>• Include the full movement from start to finish</li>
          </ul>
        </Card>
        
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-3">⚡ Best Practices</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li>• Upload videos up to 120MB supported with S3 storage</li>
            <li>• Select the correct sport for accurate analysis</li>
            <li>• Capture multiple attempts for comparison</li>
            <li>• Ensure clear view of technique and form</li>
          </ul>
        </Card>
      </div>
    </div>
  )
}
