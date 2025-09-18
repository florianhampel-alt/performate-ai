// Sport types
export type SportType = 'climbing' | 'bouldering' | 'skiing' | 'motocross' | 'mountainbike'

// Upload types
export type UploadStatus = 'idle' | 'uploading' | 'uploaded' | 'analyzing' | 'completed' | 'error'

export interface UploadResponse {
  fileId?: string
  analysis_id?: string  // Backend returns this directly
  uploadUrl?: string
  message?: string
  filename?: string
  status?: string
}

// Analysis types
export interface AnalysisRequest {
  video_url: string
  sport_type: SportType
  analysis_type?: string
  user_id?: string
}

export interface AnalysisInsight {
  category: string
  level: 'info' | 'warning' | 'success' | 'error'
  message: string
  priority: 'low' | 'medium' | 'high'
}

export type MetricStatus = 'good' | 'needs_improvement' | 'not_analyzed' | 'needs improvement' // Legacy support

export interface KeyMetric {
  status: MetricStatus
  value?: number
  score?: number
}

export interface SportSpecificAnalysis {
  sport_type: SportType
  difficulty_grade?: string  // Climbing grade like '5a', '6b+', etc.
  key_metrics: Record<string, KeyMetric>
  technique_points?: Array<{
    area: string
    score: number
    feedback: string
  }>
  safety_considerations: string[]
  training_recommendations: string[]
}

export interface AnalysisSummary {
  analyzers_used: number
  total_insights: number
  recommendations_count: number
  overall_score: number
}

export interface AnalysisResult {
  id: string
  sport_type: SportType
  analyzer_type: string
  overall_performance_score: number
  performance_score?: number  // AI analysis performance score
  comprehensive_insights: AnalysisInsight[]
  unified_recommendations: string[]
  recommendations?: string[]  // Alternative recommendations array
  sport_specific_analysis?: SportSpecificAnalysis
  analysis_summary?: AnalysisSummary
  video_url?: string  // URL to play the uploaded video
  ai_confidence?: number  // AI confidence score (0-1)
  metadata?: {
    analysis_type: string
    timestamp: string
  }
  // Enhanced analysis properties
  route_analysis?: {
    route_detected: boolean
    difficulty_estimated?: string
    total_moves?: number
    overall_score?: number
    key_insights?: string[]
    recommendations?: string[]
    ideal_route?: Array<{
      time: number
      x: number
      y: number
      hold_type: string
      source?: string
    }>
    performance_segments?: Array<{
      time_start: number
      time_end: number
      score: number
      issue?: string | null
    }>
  }
  overlay_data?: {
    has_overlay: boolean
    elements?: any[]
    video_dimensions?: { width: number; height: number }
    total_duration?: number
  }
  has_route_overlay?: boolean
  enhanced_insights?: string[]
  difficulty_estimated?: string
}

// UI Component types
export interface VideoUploadProps {
  onUploadComplete?: (result: AnalysisResult) => void
  allowedSports?: SportType[]
  maxFileSize?: number  // Default 120MB (120 * 1024 * 1024)
}

export interface AnalysisResultsProps {
  analysisId: string
  onError?: (error: string) => void
}

export interface SportSelectorProps {
  onSelect?: (sport: SportType) => void
  selectedSport?: SportType
  showDetails?: boolean
}

// API Response types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  page: number
  limit: number
  total: number
  totalPages: number
}

// User types (for future use)
export interface User {
  id: string
  email: string
  name?: string
  created_at: string
  subscription_tier?: 'free' | 'premium' | 'professional'
}

// Analysis History types
export interface AnalysisHistoryItem {
  id: string
  sport_type: SportType
  created_at: string
  status: 'completed' | 'failed' | 'processing'
  overall_score?: number
  video_filename?: string
}

// Settings types
export interface UserSettings {
  preferred_sports: SportType[]
  email_notifications: boolean
  analysis_detail_level: 'basic' | 'detailed' | 'comprehensive'
  theme: 'light' | 'dark' | 'auto'
}

// Error types
export interface ApiError {
  message: string
  status: number
  code?: string
  details?: any
}

// Form types
export interface UploadFormData {
  sport_type: SportType
  file: File
  analysis_type: 'basic' | 'comprehensive'
  notes?: string
}

// Performance Metrics types
export interface PerformanceMetrics {
  stability_score: number
  efficiency_score: number
  technique_score: number
  power_output?: number
  balance?: number
  coordination?: number
}

// Biomechanics types
export interface BiomechanicsData {
  joint_angles: Record<string, number[]>
  movement_patterns: string[]
  technique_score: number
  recommendations: string[]
}

// Video Processing types
export interface VideoMetadata {
  duration: number
  fps: number
  resolution: {
    width: number
    height: number
  }
  fileSize: number
  format: string
}

// Chart/Visualization types
export interface ChartDataPoint {
  timestamp: number
  value: number
  label?: string
}

export interface PerformanceChart {
  title: string
  data: ChartDataPoint[]
  type: 'line' | 'bar' | 'scatter'
  yAxisLabel: string
  xAxisLabel: string
}
