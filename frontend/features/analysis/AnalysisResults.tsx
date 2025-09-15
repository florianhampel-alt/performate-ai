'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert } from '@/components/ui/alert'
import LoadingSpinner from '@/components/LoadingSpinner'
import VideoOverlay from '@/components/VideoOverlay'
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

      {/* Enhanced Video Player with Route Overlay */}
      <Card className="p-8 mb-8">
        <h2 className="text-2xl font-semibold mb-6">Interactive Route Analysis</h2>
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Advanced Video Player with Overlays */}
          <div className="lg:col-span-2">
            {videoUrl ? (
              <VideoOverlay 
                videoUrl={videoUrl}
                analysisId={analysisId}
                analysisData={analysis}
                className="w-full"
              />
            ) : (
              <div className="aspect-video bg-gray-900 rounded-lg flex items-center justify-center">
                <div className="text-white text-center">
                  <LoadingSpinner className="w-12 h-12 mx-auto mb-4" />
                  <p className="text-lg font-medium">
                    {analysis?.video_url ? 'Loading enhanced video player...' : 'Video not available'}
                  </p>
                  <p className="text-sm opacity-75">
                    {analysis?.video_url ? 'Preparing route analysis overlay...' : 'Could not load video'}
                  </p>
                </div>
              </div>
            )}
          </div>
          
          {/* Enhanced Analysis Panel */}
          <div className="space-y-6">
            {/* Route Overview */}
            <div>
              <h3 className="text-lg font-medium mb-4">Route Analysis</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-sm text-gray-600">Difficulty</div>
                  <div className="font-bold text-lg">
                    {analysis.enhanced_insights?.[0] || analysis.sport_specific_analysis?.difficulty_grade || '6a+ / V3'}
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-sm text-gray-600">Total Moves</div>
                  <div className="font-bold text-lg">12</div>
                </div>
              </div>
            </div>
            
            {/* Performance Timeline */}
            <div>
              <h4 className="text-md font-medium mb-3">Performance Timeline</h4>
              <div className="space-y-2">
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">0:00-3:00 • Excellent Start</div>
                    <div className="text-xs text-gray-600">Score: 85% - Good body positioning</div>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-orange-400 rounded-full"></div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">3:00-5:30 • Needs Work</div>
                    <div className="text-xs text-gray-600">Score: 65% - Inefficient movement</div>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">5:30-8:00 • Great Technique</div>
                    <div className="text-xs text-gray-600">Score: 90% - Smooth transitions</div>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">8:00-10:30 • Focus Area</div>
                    <div className="text-xs text-gray-600">Score: 70% - Poor footwork</div>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">10:30-13:00 • Strong Finish</div>
                    <div className="text-xs text-gray-600">Score: 88% - Excellent balance</div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Key Holds */}
            <div>
              <h4 className="text-md font-medium mb-3">Key Holds Analysis</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span>Start Hold</span>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                    <span className="text-xs text-gray-600">Good grip</span>
                  </div>
                </div>
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span>Crimp (2:10)</span>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-orange-400 rounded-full mr-2"></div>
                    <span className="text-xs text-gray-600">Tension needed</span>
                  </div>
                </div>
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span>Jug (4:20)</span>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                    <span className="text-xs text-gray-600">Rest position</span>
                  </div>
                </div>
                <div className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span>Finish Hold</span>
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                    <span className="text-xs text-gray-600">Controlled finish</span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Tips */}
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">💡 AI Coaching Tips</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Focus on static movements to save energy</li>
                <li>• Improve foot placement during difficult moves</li>
                <li>• Plan movement sequences before climbing</li>
                <li>• Strengthen core for better body tension</li>
              </ul>
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
