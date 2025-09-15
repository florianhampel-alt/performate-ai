'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert } from '@/components/ui/alert'
import LoadingSpinner from '@/components/LoadingSpinner'
import { getAnalysisResults } from '@/lib/api'
import type { AnalysisResult } from '@/lib/types'

interface AnalysisResultsProps {
  analysisId: string
}

export default function AnalysisResults({ analysisId }: AnalysisResultsProps) {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)

  useEffect(() => {
    const fetchResults = async () => {
      try {
        setLoading(true)
        const results = await getAnalysisResults(analysisId)
        setAnalysis(results)
        
        // Fetch video URL from backend
        if (results.video_url) {
          console.log('Analysis has video_url:', results.video_url)
          try {
            const videoEndpoint = `https://performate-ai.onrender.com${results.video_url}`
            console.log('Fetching video from:', videoEndpoint)
            
            const videoResponse = await fetch(videoEndpoint)
            console.log('Video response status:', videoResponse.status)
            
            if (videoResponse.ok) {
              const videoData = await videoResponse.json()
              console.log('Video data received:', videoData)
              
              if (videoData.video_url) {
                setVideoUrl(videoData.video_url)
                console.log('✅ Video URL set successfully:', videoData.video_url)
                console.log('Video type:', videoData.type)
                if (videoData.debug) {
                  console.log('Debug info:', videoData.debug)
                }
              } else {
                console.error('❌ No video_url in response:', videoData)
              }
            } else {
              console.error('❌ Video response not OK:', videoResponse.status, videoResponse.statusText)
              const errorText = await videoResponse.text()
              console.error('Error response:', errorText)
              // Fallback: use the original URL as direct link
              setVideoUrl(`https://performate-ai.onrender.com${results.video_url}`)
            }
          } catch (videoErr) {
            console.error('❌ Error fetching video URL:', videoErr)
            setVideoUrl(`https://performate-ai.onrender.com${results.video_url}`)
          }
        } else {
          console.warn('⚠️ No video_url found in analysis results')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load analysis')
      } finally {
        setLoading(false)
      }
    }

    fetchResults()
  }, [analysisId])

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center">
          <LoadingSpinner className="mx-auto mb-4" />
          <h2 className="text-xl font-medium">Loading analysis results...</h2>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <Alert variant="destructive">
          <h3 className="font-medium">Error Loading Analysis</h3>
          <p>{error}</p>
        </Alert>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <Alert>
          <h3 className="font-medium">Analysis Not Found</h3>
          <p>The requested analysis could not be found.</p>
        </Alert>
      </div>
    )
  }

  const overallScore = analysis.overall_performance_score * 100

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Analysis Results
        </h1>
        <p className="text-gray-600">
          AI-powered analysis for your {analysis.sport_type} performance
        </p>
      </div>

      {/* Video Player with Analysis */}
      <Card className="p-8 mb-8">
        <h2 className="text-2xl font-semibold mb-6">Your Climbing Video with AI Analysis</h2>
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Video Player */}
          <div className="relative">
            <div className="aspect-video bg-gray-900 rounded-lg overflow-hidden relative">
              {/* Real HTML5 Video Player */}
              {videoUrl ? (
                <video 
                  className="w-full h-full object-cover"
                  controls
                  preload="metadata"
                  poster="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1920 1080'%3E%3Crect width='1920' height='1080' fill='%23111827'/%3E%3C/svg%3E"
                >
                  <source 
                    src={videoUrl} 
                    type="video/mp4" 
                  />
                  <p className="text-white text-center p-4">
                    Ihr Browser unterstützt keine HTML5-Videos. 
                    <a href={videoUrl} className="text-blue-400 underline">
                      Direkter Download
                    </a>
                  </p>
                </video>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-white text-center">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-blue-600 flex items-center justify-center">
                      <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M8 5v14l11-7z"/>
                      </svg>
                    </div>
                    <p className="text-lg font-medium">
                      {analysis.video_url ? 'Video wird geladen...' : 'Video nicht verfügbar'}
                    </p>
                    <p className="text-sm opacity-75">
                      {analysis.video_url ? 'S3 URL wird abgerufen...' : 'Das Video konnte nicht geladen werden'}
                    </p>
                  </div>
                </div>
              )}
              
              {/* Movement Quality Overlay */}
              <div className="absolute top-4 left-4 space-y-2">
                <div className="flex items-center space-x-2 bg-black bg-opacity-75 px-3 py-1 rounded">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <span className="text-white text-sm">Gute Bewegung</span>
                </div>
                <div className="flex items-center space-x-2 bg-black bg-opacity-75 px-3 py-1 rounded">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <span className="text-white text-sm">Verbesserungsbedarf</span>
                </div>
                <div className="flex items-center space-x-2 bg-black bg-opacity-75 px-3 py-1 rounded">
                  <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                  <span className="text-white text-sm">Ideallinie</span>
                </div>
              </div>
              
              {/* Difficulty Grade Overlay */}
              <div className="absolute top-4 right-4">
                <div className="bg-blue-600 text-white px-4 py-2 rounded font-bold">
                  {analysis.sport_specific_analysis?.difficulty_grade || '5a'}
                </div>
              </div>
            </div>
            
            {/* Video Controls */}
            <div className="mt-4 flex justify-center space-x-4">
              <Button variant="outline" size="sm">
                ⏮️ Vorherige Szene
              </Button>
              <Button variant="outline" size="sm">
                ⏯️ Play/Pause
              </Button>
              <Button variant="outline" size="sm">
                ⏭️ Nächste Szene
              </Button>
            </div>
          </div>
          
          {/* Movement Analysis Timeline */}
          <div>
            <h3 className="text-lg font-medium mb-4">Bewegungsanalyse Timeline</h3>
            <div className="space-y-3">
              {/* Mock timeline segments */}
              <div className="flex items-center space-x-3">
                <div className="w-4 h-4 bg-green-500 rounded"></div>
                <div className="flex-1">
                  <div className="text-sm font-medium">0:00 - 0:15 • Guter Start</div>
                  <div className="text-xs text-gray-600">Ausgezeichnete Balance und Körperspannung beim Einstieg</div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-4 h-4 bg-yellow-500 rounded"></div>
                <div className="flex-1">
                  <div className="text-sm font-medium">0:15 - 0:30 • Mittelteil</div>
                  <div className="text-xs text-gray-600">Fußtechnik könnte optimiert werden</div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-4 h-4 bg-red-500 rounded"></div>
                <div className="flex-1">
                  <div className="text-sm font-medium">0:30 - 0:45 • Schwierige Stelle</div>
                  <div className="text-xs text-gray-600">Übermäßige Armbelastung erkennbar</div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-4 h-4 bg-green-500 rounded"></div>
                <div className="flex-1">
                  <div className="text-sm font-medium">0:45 - 1:00 • Starkes Finish</div>
                  <div className="text-xs text-gray-600">Effiziente Schlüsselsequenz zum Top</div>
                </div>
              </div>
            </div>
            
            {/* Ideal Path Visualization */}
            <div className="mt-6 p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">💡 Ideallinie Empfehlung</h4>
              <p className="text-sm text-blue-800">
                Die optimale Route würde mehr Beinarbeit in Sekunde 15-30 beinhalten 
                und eine direktere Linie zum Schlüsselgriff in 0:35 nehmen.
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Overall Score */}
      <Card className="p-8 mb-8 text-center">
        <h2 className="text-2xl font-semibold mb-4">Overall Performance Score</h2>
        <div className="flex justify-center items-center mb-4">
          <div className="relative w-32 h-32">
            <Progress 
              value={overallScore} 
              className="w-32 h-32 rounded-full"
              style={{
                background: `conic-gradient(
                  #3b82f6 ${overallScore * 3.6}deg,
                  #e5e7eb ${overallScore * 3.6}deg
                )`
              }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-3xl font-bold text-blue-600">
                {Math.round(overallScore)}
              </span>
            </div>
          </div>
        </div>
        <p className="text-gray-600">
          {overallScore >= 80 ? 'Excellent' : 
           overallScore >= 60 ? 'Good' : 
           overallScore >= 40 ? 'Needs Improvement' : 'Beginner'}
        </p>
      </Card>

      {/* Key Insights */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {analysis.comprehensive_insights.map((insight, index) => (
          <Card key={index} className="p-6">
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-gray-900 capitalize">
                {insight.category.replace('_', ' ')}
              </h3>
              <span className={`insight-badge ${insight.priority}`}>
                {insight.priority}
              </span>
            </div>
            <p className="text-gray-600 text-sm">
              {insight.message}
            </p>
          </Card>
        ))}
      </div>

      {/* Recommendations */}
      <Card className="p-8 mb-8">
        <h2 className="text-2xl font-semibold mb-6">Training Recommendations</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {analysis.unified_recommendations.map((recommendation, index) => (
            <div key={index} className="recommendation-item">
              <div className="text-yellow-600 font-bold text-lg">•</div>
              <p className="text-gray-700">{recommendation}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Detailed Analysis */}
      {analysis.sport_specific_analysis && (
        <Card className="p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6">
            {analysis.sport_type} Specific Analysis
          </h2>
          
          {/* Key Metrics */}
          {analysis.sport_specific_analysis.key_metrics && (
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-4">Key Performance Metrics</h3>
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(analysis.sport_specific_analysis.key_metrics).map(([metric, data]) => (
                  <div key={metric} className="metric-card">
                    <h4 className="font-medium text-gray-900 capitalize mb-2">
                      {metric.replace('_', ' ')}
                    </h4>
                    <div className="flex items-center">
                      <div className={`w-3 h-3 rounded-full mr-2 ${
                        data.status === 'good' ? 'bg-green-500' : 
                        data.status === 'needs_improvement' ? 'bg-yellow-500' : 
                        'bg-gray-400'
                      }`} />
                      <span className="text-sm text-gray-600 capitalize">
                        {data.status?.replace('_', ' ') || 'Not analyzed'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Safety Considerations */}
          {analysis.sport_specific_analysis.safety_considerations && (
            <div>
              <h3 className="text-lg font-medium mb-4">Safety Considerations</h3>
              <ul className="space-y-2">
                {analysis.sport_specific_analysis.safety_considerations.map((tip, index) => (
                  <li key={index} className="flex items-start">
                    <span className="text-red-500 mr-2">⚠️</span>
                    <span className="text-gray-700">{tip}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Analysis Summary */}
      <Card className="p-8">
        <h2 className="text-2xl font-semibold mb-4">Analysis Summary</h2>
        <div className="grid md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {analysis.analysis_summary.analyzers_used}
            </div>
            <div className="text-sm text-gray-600">Analyzers Used</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {analysis.analysis_summary.total_insights}
            </div>
            <div className="text-sm text-gray-600">Insights Generated</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {analysis.analysis_summary.recommendations_count}
            </div>
            <div className="text-sm text-gray-600">Recommendations</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {Math.round(analysis.analysis_summary.overall_score)}%
            </div>
            <div className="text-sm text-gray-600">Overall Score</div>
          </div>
        </div>
      </Card>

      {/* Actions */}
      <div className="mt-8 flex justify-center space-x-4">
        <Button onClick={() => window.print()}>
          Download Report
        </Button>
        <Button variant="outline" onClick={() => window.location.href = '/upload'}>
          Analyze Another Video
        </Button>
        <Button variant="outline" onClick={() => window.history.back()}>
          Back to Upload
        </Button>
      </div>
    </div>
  )
}
