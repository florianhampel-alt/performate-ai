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
          <h2 className="text-xl font-medium">Lade Analyseergebnisse...</h2>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <Alert variant="destructive">
          <h3 className="font-medium">Fehler beim Laden der Analyse</h3>
          <p>{error}</p>
        </Alert>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <Alert>
          <h3 className="font-medium">Analyse nicht gefunden</h3>
          <p>Die angeforderte Analyse konnte nicht gefunden werden.</p>
        </Alert>
      </div>
    )
  }

  const overallScore = analysis.route_analysis?.overall_score || 
                        analysis.performance_score || 
                        analysis.overall_performance_score * 100 || 
                        78

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Analyseergebnisse
        </h1>
        <p className="text-gray-600">
          KI-gestützte Analyse deiner {analysis.sport_type === 'climbing' ? 'Kletter-' : analysis.sport_type === 'bouldering' ? 'Boulder-' : ''}performance
        </p>
      </div>

      {/* Enhanced Video Player with Route Overlay */}
      <Card className="p-8 mb-8">
        <h2 className="text-2xl font-semibold mb-6">Interaktive Routenanalyse</h2>
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
                    {analysis?.video_url ? 'Lade erweiterten Video-Player...' : 'Video nicht verfügbar'}
                  </p>
                  <p className="text-sm opacity-75">
                    {analysis?.video_url ? 'Bereite Routenanalyse-Overlay vor...' : 'Konnte Video nicht laden'}
                  </p>
                </div>
              </div>
            )}
          </div>
          
          {/* Enhanced Analysis Panel */}
          <div className="space-y-6">
            {/* Route Overview */}
            <div>
              <h3 className="text-lg font-medium mb-4">Routenanalyse</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-sm text-gray-600">Schwierigkeit</div>
                  <div className="font-bold text-lg">
                    {analysis.route_analysis?.difficulty_estimated || analysis.enhanced_insights?.[0] || analysis.sport_specific_analysis?.difficulty_grade || '6a+ / V3'}
                  </div>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <div className="text-sm text-gray-600">Gesamtzüge</div>
                  <div className="font-bold text-lg">
                    {analysis.route_analysis?.total_moves || analysis.route_analysis?.ideal_route?.length || 12}
                  </div>
                </div>
              </div>
            </div>
            
            {/* Performance Timeline */}
            <div>
              <h4 className="text-md font-medium mb-3">Performance-Verlauf</h4>
              <div className="space-y-2">
                {analysis.route_analysis?.performance_segments?.map((segment, index) => {
                  const score = Math.round(segment.score * 100)
                  const startTime = Math.floor(segment.time_start / 60) + ':' + String(Math.floor(segment.time_start % 60)).padStart(2, '0')
                  const endTime = Math.floor(segment.time_end / 60) + ':' + String(Math.floor(segment.time_end % 60)).padStart(2, '0')
                  const colorClass = score >= 80 ? 'bg-green-500' : score >= 65 ? 'bg-orange-400' : 'bg-red-500'
                  const status = score >= 80 ? 'Ausgezeichnet' : score >= 65 ? 'Gut' : 'Verbesserung nötig'
                  const description = segment.issue ? 
                    (segment.issue === 'technique_needs_work' ? 'Technik verbesserungswürdig' : 
                     segment.issue === 'efficiency_low' ? 'Energieeffizienz niedrig' :
                     segment.issue === 'technique_improvement_needed' ? 'Technik verbesserungswürdig' :
                     segment.issue) : 'Flüssige Ausführung'
                  
                  return (
                    <div key={index} className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${colorClass}`}></div>
                      <div className="flex-1">
                        <div className="text-sm font-medium">
                          {startTime}-{endTime} • {status}
                        </div>
                        <div className="text-xs text-gray-600">
                          Score: {score}% - {description}
                        </div>
                      </div>
                    </div>
                  )
                }) || (
                  // Fallback for when no performance segments available
                  <div className="text-sm text-gray-500 italic">
                    Performance-Verlaufsdaten nicht verfügbar
                  </div>
                )}
              </div>
            </div>
            
            {/* Key Holds */}
            <div>
              <h4 className="text-md font-medium mb-3">Schlüsselgriff-Analyse</h4>
              <div className="space-y-2 text-sm">
                {analysis.route_analysis?.ideal_route?.map((hold, index) => {
                  // Get corresponding performance score for this hold
                  const segmentIndex = analysis.route_analysis?.performance_segments?.findIndex(
                    seg => hold.time >= seg.time_start && hold.time <= seg.time_end
                  ) ?? -1
                  const score = segmentIndex >= 0 ? analysis.route_analysis?.performance_segments?.[segmentIndex]?.score ?? 0.8 : 0.8
                  const colorClass = score >= 0.8 ? 'bg-green-500' : score >= 0.65 ? 'bg-orange-400' : 'bg-red-500'
                  const quality = score >= 0.8 ? 'Ausgezeichneter Griff' : score >= 0.65 ? 'Guter Griff' : 'Herausfordernd'
                  const timeStr = Math.floor(hold.time / 60) + ':' + String(Math.floor(hold.time % 60)).padStart(2, '0')
                  
                  return (
                    <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <span className="capitalize">
                        {hold.hold_type === 'start' ? 'Startgriff' : 
                         hold.hold_type === 'finish' ? 'Zielgriff' :
                         `${hold.hold_type} (${timeStr})`}
                      </span>
                      <div className="flex items-center">
                        <div className={`w-2 h-2 rounded-full mr-2 ${colorClass}`}></div>
                        <span className="text-xs text-gray-600">{quality}</span>
                      </div>
                    </div>
                  )
                }) || (
                  // Fallback when no route data available
                  <div className="text-sm text-gray-500 italic">
                    Griff-Analysedaten nicht verfügbar
                  </div>
                )}
              </div>
            </div>
            
            {/* AI Coaching Tips */}
            <div className="p-4 bg-blue-50 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">💡 KI-Coaching-Tipps</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                {analysis.route_analysis?.recommendations?.map((tip, index) => (
                  <li key={index}>• {tip}</li>
                )) || analysis.unified_recommendations?.slice(0, 4).map((tip, index) => (
                  <li key={index}>• {tip}</li>
                )) || [
                  'Übe statische Bewegungen um Energie zu sparen',
                  'Verbessere Fußplatzierung während schwieriger Züge',
                  'Plane Bewegungssequenzen vor dem Klettern',
                  'Stärke den Core für bessere Körperspannung'
                ].map((tip, index) => (
                  <li key={index}>• {tip}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </Card>

      {/* Overall Score */}
      <Card className="p-8 mb-8 text-center">
        <h2 className="text-2xl font-semibold mb-4">Gesamt-Performance-Score</h2>
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
          {overallScore >= 80 ? 'Ausgezeichnet' : 
           overallScore >= 60 ? 'Gut' : 
           overallScore >= 40 ? 'Verbesserung nötig' : 'Anfänger'}
        </p>
      </Card>

      {/* Key Insights */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {analysis.comprehensive_insights?.length > 0 ? analysis.comprehensive_insights.map((insight, index) => (
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
        )) : analysis.route_analysis?.key_insights?.map((insight, index) => (
          <Card key={index} className="p-6">
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-gray-900">
                KI-Erkenntnis #{index + 1}
              </h3>
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                AI
              </span>
            </div>
            <p className="text-gray-600 text-sm">
              {insight}
            </p>
          </Card>
        )) || [
          {
            title: "Routenerkennung",
            message: analysis.route_analysis?.route_detected ? "Route erfolgreich von KI identifiziert" : "Routenerkennung in Bearbeitung",
            priority: "high"
          },
          {
            title: "Performance Score",
            message: `Gesamttechnik von KI mit ${analysis.route_analysis?.overall_score || 78}% bewertet`,
            priority: "medium"
          },
          {
            title: "KI-Vertrauen",
            message: `Analysegenauigkeit: ${Math.round((analysis.ai_confidence || 0.85) * 100)}%`,
            priority: (analysis.ai_confidence || 0.85) > 0.7 ? "high" : "medium"
          }
        ].map((insight, index) => (
          <Card key={index} className="p-6">
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-gray-900">
                {insight.title}
              </h3>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                insight.priority === 'high' ? 'bg-green-100 text-green-800' :
                insight.priority === 'medium' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
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
        <h2 className="text-2xl font-semibold mb-6">Trainingsempfehlungen</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {(
            analysis.unified_recommendations?.length ? analysis.unified_recommendations : 
            analysis.route_analysis?.recommendations?.length ? analysis.route_analysis.recommendations :
            analysis.recommendations || [
              "Fokussiere dich auf Balance während dynamischer Bewegungen",
              "Trainiere präzise Fußplatzierung auf kleineren Griffen",
              "Verbessere Rumpfkraft für bessere Stabilität",
              "Arbeite daran, Routensequenzen vor dem Klettern zu lesen"
            ]
          ).map((recommendation, index) => (
            <div key={index} className="flex items-start space-x-3 p-3 bg-yellow-50 rounded-lg">
              <div className="text-yellow-600 font-bold text-lg flex-shrink-0 mt-0.5">•</div>
              <p className="text-gray-700">{recommendation}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Detailed Analysis */}
      {analysis.sport_specific_analysis && (
        <Card className="p-8 mb-8">
          <h2 className="text-2xl font-semibold mb-6">
            {analysis.sport_type === 'climbing' ? 'Kletter-' : analysis.sport_type === 'bouldering' ? 'Boulder-' : analysis.sport_type}spezifische Analyse
          </h2>
          
          {/* Key Metrics */}
          {analysis.sport_specific_analysis.key_metrics && (
            <div className="mb-6">
              <h3 className="text-lg font-medium mb-4">Wichtige Performance-Metriken</h3>
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(analysis.sport_specific_analysis.key_metrics).map(([metric, data]) => (
                  <div key={metric} className="metric-card">
                    <h4 className="font-medium text-gray-900 capitalize mb-2">
                      {metric === 'balance' ? 'balance' : 
                       metric === 'efficiency' ? 'effizienz' : 
                       metric === 'technique' ? 'technik' : 
                       metric.replace('_', ' ')}
                    </h4>
                    <div className="flex items-center">
                      <div className={`w-3 h-3 rounded-full mr-2 ${
                        data.status === 'good' ? 'bg-green-500' : 
                        data.status === 'needs_improvement' ? 'bg-yellow-500' : 
                        'bg-gray-400'
                      }`} />
                      <span className="text-sm text-gray-600">
                        {data.status === 'good' ? 'gut' : 
                         (data.status === 'needs_improvement' || data.status === 'needs improvement') ? 'verbesserung nötig' : 
                         data.status ? String(data.status).replace('_', ' ') : 'nicht analysiert'}
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
              <h3 className="text-lg font-medium mb-4">Sicherheitshinweise</h3>
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
        <h2 className="text-2xl font-semibold mb-4">Analyse-Übersicht</h2>
        <div className="grid md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {analysis.analysis_summary?.analyzers_used || 'GPT-4o'}
            </div>
            <div className="text-sm text-gray-600">KI-Modell verwendet</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {analysis.analysis_summary?.total_insights || analysis.route_analysis?.key_insights?.length || 3}
            </div>
            <div className="text-sm text-gray-600">Erkenntnisse generiert</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {analysis.analysis_summary?.recommendations_count || 
               analysis.route_analysis?.recommendations?.length || 
               analysis.recommendations?.length || 4}
            </div>
            <div className="text-sm text-gray-600">Empfehlungen</div>
          </div>
          <div className="text-center">
            <div className={`text-2xl font-bold ${
              (analysis.ai_confidence || 0.85) >= 0.8 ? 'text-green-600' :
              (analysis.ai_confidence || 0.85) >= 0.6 ? 'text-orange-600' : 'text-red-600'
            }`}>
              {Math.round((analysis.ai_confidence || 0.85) * 100)}%
            </div>
            <div className="text-sm text-gray-600">KI-Vertrauen</div>
          </div>
        </div>
      </Card>

      {/* Actions */}
      <div className="mt-8 flex justify-center space-x-4">
        <Button onClick={() => window.print()}>
          Report herunterladen
        </Button>
        <Button variant="outline" onClick={() => window.location.href = '/upload'}>
          Weiteres Video analysieren
        </Button>
        <Button variant="outline" onClick={() => window.history.back()}>
          Zurück zum Upload
        </Button>
      </div>
    </div>
  )
}
