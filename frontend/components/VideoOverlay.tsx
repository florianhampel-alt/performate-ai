"use client";

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Play, Pause, RotateCcw, Info } from 'lucide-react';

interface RoutePoint {
  x: number;
  y: number;
  time: number;
  hold_type?: string;
}

interface OverlayElement {
  type: 'ideal_route_line' | 'performance_marker' | 'hold_marker';
  points?: RoutePoint[];
  x?: number;
  y?: number;
  time?: number;
  time_start?: number;
  time_end?: number;
  score?: number;
  issue?: string;
  hold_type?: string;
  style: {
    color: string;
    thickness?: number;
    size?: number | string;
    opacity?: number;
    position?: string;
  };
}

interface OverlayData {
  has_overlay: boolean;
  overlay_elements: OverlayElement[];
  video_dimensions: { width: number; height: number };
  total_duration: number;
  route_info: {
    difficulty: string;
    total_moves: number;
    overall_score: number;
  };
}

interface VideoOverlayProps {
  videoUrl: string;
  analysisId: string;
  className?: string;
  analysisData?: any; // Pass analysis data directly
}

export default function VideoOverlay({ videoUrl, analysisId, className = "", analysisData }: VideoOverlayProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const [overlayData, setOverlayData] = useState<OverlayData | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Fetch overlay data
  useEffect(() => {
    const fetchOverlayData = async () => {
      try {
        // Try to use passed analysis data first
        console.log('📊 Raw analysis data received:', analysisData);
        
        if (analysisData?.overlay_data) {
          console.log('📊 Using overlay data from analysis:', analysisData.overlay_data);
          console.log('🎯 Has overlay:', analysisData.overlay_data.has_overlay);
          console.log('📍 Overlay elements count:', analysisData.overlay_data.elements?.length || 0);
          
          const overlayData = {
            has_overlay: analysisData.overlay_data.has_overlay || false,
            overlay_elements: analysisData.overlay_data.elements || [],  // Backend uses 'elements', not 'overlay_elements'
            video_dimensions: analysisData.overlay_data.video_dimensions || { width: 640, height: 480 },
            total_duration: analysisData.overlay_data.total_duration || 15.0,
            route_info: {
              difficulty: analysisData.difficulty_estimated || 'Unknown',
              total_moves: analysisData.route_analysis?.total_moves || 0,
              overall_score: analysisData.route_analysis?.overall_score || 0
            }
          };
          
          if (overlayData.has_overlay && overlayData.overlay_elements?.length > 0) {
            console.log('✅ Overlay data from analysis looks good!');
            overlayData.overlay_elements.forEach((element: any, i: number) => {
              console.log(`Element ${i}:`, element.type, element);
            });
          }
          
          setOverlayData(overlayData);
          setLoading(false);
          return;
        }
        
        // Fallback to API endpoint
        const url = `${process.env.NEXT_PUBLIC_API_URL}/analysis/${analysisId}/overlay`;
        console.log('🔍 Fetching overlay data from API:', url);
        
        const response = await fetch(url);
        console.log('📡 Overlay response status:', response.status);
        
        if (response.ok) {
          const data = await response.json();
          console.log('📊 Overlay data received from API:', data);
          console.log('🎯 Has overlay:', data.has_overlay);
          console.log('📍 Overlay elements count:', data.overlay_elements?.length || 0);
          
          // Map API response to expected format
          const mappedData = {
            ...data,
            overlay_elements: data.overlay_elements || data.elements || []  // Handle both possible keys
          };
          
          if (mappedData.has_overlay && mappedData.overlay_elements?.length > 0) {
            console.log('✅ Overlay data looks good, setting up overlays...');
            mappedData.overlay_elements.forEach((element: any, i: number) => {
              console.log(`Element ${i}:`, element.type, element);
            });
          } else {
            console.warn('⚠️ No overlay elements found');
          }
          
          setOverlayData(mappedData);
        } else {
          console.warn('⚠️ No overlay data available, status:', response.status);
          const errorText = await response.text();
          console.log('Error response:', errorText);
          
          setOverlayData({ 
            has_overlay: false, 
            overlay_elements: [], 
            video_dimensions: { width: 640, height: 480 }, 
            total_duration: 0,
            route_info: { difficulty: 'Unknown', total_moves: 0, overall_score: 0 }
          });
        }
      } catch (err) {
        console.error('❌ Error fetching overlay data:', err);
        setError('Failed to load route analysis');
      } finally {
        setLoading(false);
      }
    };

    if (analysisId) {
      fetchOverlayData();
    }
  }, [analysisId]);

  // Video event handlers
  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  }, []);

  const handleLoadedMetadata = useCallback(() => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  }, []);

  const handlePlay = useCallback(() => setIsPlaying(true), []);
  const handlePause = useCallback(() => setIsPlaying(false), []);

  // Draw overlay on canvas
  const drawOverlay = useCallback(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    if (!canvas || !video) {
      console.log('🚫 Canvas or video not available for drawing');
      return;
    }
    
    if (!overlayData?.has_overlay) {
      console.log('🚫 No overlay data available for drawing');
      return;
    }
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      console.log('🚫 Could not get canvas context');
      return;
    }

    // Set canvas size to match video display size
    // Use actual video display dimensions
    const displayWidth = video.offsetWidth;
    const displayHeight = video.offsetHeight;
    
    canvas.width = displayWidth;
    canvas.height = displayHeight;
    
    console.log(`🎨 Drawing overlay: ${displayWidth}x${displayHeight}, video time: ${currentTime.toFixed(2)}s`);
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Calculate scale factors
    const scaleX = canvas.width / (overlayData.video_dimensions?.width || 640);
    const scaleY = canvas.height / (overlayData.video_dimensions?.height || 480);
    
    console.log(`📏 Scale factors: ${scaleX.toFixed(2)}x, ${scaleY.toFixed(2)}y`);
    
    // Draw overlay elements
    let elementsDrawn = 0;
    overlayData.overlay_elements?.forEach((element, index) => {
      console.log(`🎯 Drawing element ${index}: ${element.type}`);
      
      switch (element.type) {
        case 'ideal_route_line':
          drawRouteLine(ctx, element, scaleX, scaleY, currentTime);
          elementsDrawn++;
          break;
        case 'hold_marker':
          drawHoldMarker(ctx, element, scaleX, scaleY, currentTime);
          elementsDrawn++;
          break;
        case 'performance_marker':
          drawPerformanceMarker(ctx, element, currentTime);
          elementsDrawn++;
          break;
        default:
          console.warn(`❓ Unknown element type: ${element.type}`);
      }
    });
    
    console.log(`✏️ Drew ${elementsDrawn} elements on canvas`);
  }, [overlayData, currentTime]);

  const drawRouteLine = (
    ctx: CanvasRenderingContext2D,
    element: OverlayElement,
    scaleX: number,
    scaleY: number,
    time: number
  ) => {
    const points = element.points || [];
    if (points.length < 2) return;

    ctx.strokeStyle = element.style.color;
    ctx.lineWidth = (element.style.thickness || 2) * Math.min(scaleX, scaleY);
    ctx.globalAlpha = element.style.opacity || 1;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Draw line progressively based on time
    const visiblePoints = points.filter(point => point.time <= time + 1); // 1s preview
    
    if (visiblePoints.length >= 2) {
      const firstPoint = visiblePoints[0];
      if (firstPoint) {
        ctx.beginPath();
        ctx.moveTo(firstPoint.x * scaleX, firstPoint.y * scaleY);
        
        for (let i = 1; i < visiblePoints.length; i++) {
          const point = visiblePoints[i];
          if (point) {
            ctx.lineTo(point.x * scaleX, point.y * scaleY);
          }
        }
        
        ctx.stroke();
      }
    }
    
    ctx.globalAlpha = 1;
  };

  const drawHoldMarker = (
    ctx: CanvasRenderingContext2D,
    element: OverlayElement,
    scaleX: number,
    scaleY: number,
    time: number
  ) => {
    if (!element.x || !element.y || !element.time) return;
    
    // Show marker if current time is near the hold time
    const timeDiff = Math.abs(time - element.time);
    if (timeDiff > 2) return; // Show 2 seconds before/after
    
    const x = element.x * scaleX;
    const y = element.y * scaleY;
    const size = (element.style.size as number || 12) * Math.min(scaleX, scaleY);
    
    // Draw hold circle
    ctx.fillStyle = element.style.color;
    ctx.globalAlpha = element.style.opacity || 0.9;
    
    ctx.beginPath();
    ctx.arc(x, y, size, 0, 2 * Math.PI);
    ctx.fill();
    
    // Draw hold type label
    if (element.hold_type) {
      ctx.fillStyle = '#FFFFFF';
      ctx.font = `${Math.max(10, size * 0.8)}px Arial`;
      ctx.textAlign = 'center';
      ctx.fillText(element.hold_type.charAt(0).toUpperCase(), x, y + 4);
    }
    
    // Pulse effect for current hold
    if (timeDiff < 0.5) {
      ctx.strokeStyle = '#FFFFFF';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, y, size + 5, 0, 2 * Math.PI);
      ctx.stroke();
    }
    
    ctx.globalAlpha = 1;
  };

  const drawPerformanceMarker = (
    ctx: CanvasRenderingContext2D,
    element: OverlayElement,
    time: number
  ) => {
    if (!element.time_start || !element.time_end) return;
    
    // Show marker if current time is within segment
    if (time < element.time_start || time > element.time_end) return;
    
    // Draw performance indicator in top-right corner
    const canvas = ctx.canvas;
    const size = 20;
    const x = canvas.width - 40;
    const y = 40;
    
    ctx.fillStyle = element.style.color;
    ctx.globalAlpha = 0.8;
    
    ctx.beginPath();
    ctx.arc(x, y, size, 0, 2 * Math.PI);
    ctx.fill();
    
    // Add score text
    ctx.fillStyle = '#FFFFFF';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(Math.round((element.score || 0) * 100).toString(), x, y + 4);
    
    ctx.globalAlpha = 1;
  };

  // Update overlay on time change
  useEffect(() => {
    if (overlayData?.has_overlay) {
      drawOverlay();
    }
  }, [drawOverlay]);

  // Control handlers
  const togglePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
    }
  };

  const restart = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      setCurrentTime(0);
    }
  };

  const formatTime = (time: number) => {
    const mins = Math.floor(time / 60);
    const secs = Math.floor(time % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-gray-100 rounded-lg">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className={`relative bg-black rounded-lg overflow-hidden ${className}`}>
      {/* Video Container with Aspect Ratio */}
      <div className="relative w-full" style={{ maxHeight: '70vh' }}>
        {/* Video Element */}
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-auto max-h-[70vh] object-contain"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onPlay={handlePlay}
          onPause={handlePause}
          preload="metadata"
        />
        
        {/* Canvas Overlay */}
        {overlayData?.has_overlay && (
          <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none"
            style={{ zIndex: 1 }}
          />
        )}
      </div>
      
      {/* Info Panel */}
      {overlayData?.has_overlay && (
        <div className="absolute top-4 left-4 bg-black bg-opacity-70 text-white p-3 rounded-lg" style={{ zIndex: 2 }}>
          <div className="flex items-center gap-2 mb-2">
            <Info size={16} />
            <span className="text-sm font-semibold">Route Analysis</span>
          </div>
          <div className="text-xs space-y-1">
            <div>Grade: {overlayData.route_info.difficulty}</div>
            <div>Moves: {overlayData.route_info.total_moves}</div>
            <div>Score: {overlayData.route_info.overall_score}%</div>
          </div>
          <div className="flex items-center gap-2 mt-2 text-xs">
            <div className="w-3 h-3 bg-blue-400 rounded-full"></div>
            <span>Ideal Route</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <div className="w-3 h-3 bg-green-400 rounded-full"></div>
            <span>Good Technique</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <div className="w-3 h-3 bg-red-400 rounded-full"></div>
            <span>Needs Work</span>
          </div>
        </div>
      )}
      
      {/* Controls */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-4" style={{ zIndex: 2 }}>
        <div className="flex items-center gap-4 text-white">
          <button
            onClick={togglePlayPause}
            className="flex items-center justify-center w-10 h-10 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full transition-all"
          >
            {isPlaying ? <Pause size={20} /> : <Play size={20} />}
          </button>
          
          <button
            onClick={restart}
            className="flex items-center justify-center w-10 h-10 bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full transition-all"
          >
            <RotateCcw size={18} />
          </button>
          
          <div className="flex-1 flex items-center gap-2 text-sm">
            <span>{formatTime(currentTime)}</span>
            <div className="flex-1 h-1 bg-white bg-opacity-30 rounded-full">
              <div
                className="h-full bg-white rounded-full transition-all duration-200"
                style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
              />
            </div>
            <span>{formatTime(duration)}</span>
          </div>
          
          {overlayData?.has_overlay && (
            <div className="text-xs bg-white bg-opacity-20 px-2 py-1 rounded">
              Route Analysis Active
            </div>
          )}
        </div>
      </div>
      
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 text-white">
          <div className="text-center">
            <p className="text-red-400 mb-2">⚠️ {error}</p>
            <p className="text-sm">Video will play without route overlay</p>
          </div>
        </div>
      )}
    </div>
  );
}
