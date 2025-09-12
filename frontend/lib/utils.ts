import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import type { SportType } from "./types"

/**
 * Utility function to merge Tailwind CSS classes
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format file size in human-readable format
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * Format duration in human-readable format
 */
export function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const remainingSeconds = Math.floor(seconds % 60)
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`
  }
  
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
}

/**
 * Format timestamp in human-readable format
 */
export function formatTimestamp(timestamp: string | Date): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * Get sport display name
 */
export function getSportDisplayName(sport: SportType): string {
  const sportNames: Record<SportType, string> = {
    climbing: 'Rock Climbing',
    bouldering: 'Bouldering',
    skiing: 'Skiing',
    motocross: 'Motocross',
    mountainbike: 'Mountain Biking'
  }
  
  return sportNames[sport] || sport
}

/**
 * Get sport emoji
 */
export function getSportEmoji(sport: SportType): string {
  const sportEmojis: Record<SportType, string> = {
    climbing: '🧗',
    bouldering: '🏔️',
    skiing: '⛷️',
    motocross: '🏍️',
    mountainbike: '🚵'
  }
  
  return sportEmojis[sport] || '🏃'
}

/**
 * Get performance level based on score
 */
export function getPerformanceLevel(score: number): {
  level: string
  color: string
  description: string
} {
  if (score >= 0.9) {
    return {
      level: 'Expert',
      color: 'text-purple-600',
      description: 'Exceptional performance with mastery-level technique'
    }
  }
  
  if (score >= 0.7) {
    return {
      level: 'Advanced',
      color: 'text-green-600',
      description: 'Strong technique with room for fine-tuning'
    }
  }
  
  if (score >= 0.5) {
    return {
      level: 'Intermediate',
      color: 'text-blue-600',
      description: 'Solid foundation with areas for improvement'
    }
  }
  
  if (score >= 0.3) {
    return {
      level: 'Beginner+',
      color: 'text-orange-600',
      description: 'Developing skills with good progress potential'
    }
  }
  
  return {
    level: 'Beginner',
    color: 'text-gray-600',
    description: 'Starting journey with fundamental skills to develop'
  }
}

/**
 * Generate a random ID
 */
export function generateId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36)
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

/**
 * Throttle function
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let lastTime = 0
  
  return (...args: Parameters<T>) => {
    const now = Date.now()
    
    if (now - lastTime >= wait) {
      lastTime = now
      func(...args)
    }
  }
}

/**
 * Check if a file is a valid video format
 */
export function isValidVideoFormat(file: File): boolean {
  const validTypes = [
    'video/mp4',
    'video/avi',
    'video/quicktime',
    'video/x-msvideo',
    'video/x-matroska'
  ]
  
  const validExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv']
  
  return (
    validTypes.includes(file.type) ||
    validExtensions.some(ext => file.name.toLowerCase().endsWith(ext))
  )
}

/**
 * Validate file size
 */
export function validateFileSize(file: File, maxSizeMB: number): boolean {
  return file.size <= maxSizeMB * 1024 * 1024
}

/**
 * Get priority color class
 */
export function getPriorityColor(priority: 'low' | 'medium' | 'high'): string {
  const colors = {
    low: 'text-green-600 bg-green-100',
    medium: 'text-yellow-600 bg-yellow-100',
    high: 'text-red-600 bg-red-100'
  }
  
  return colors[priority] || colors.medium
}

/**
 * Calculate percentage
 */
export function calculatePercentage(value: number, total: number): number {
  if (total === 0) return 0
  return Math.round((value / total) * 100)
}

/**
 * Truncate text with ellipsis
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength - 3) + '...'
}

/**
 * Sleep utility for delays
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Check if device is mobile
 */
export function isMobile(): boolean {
  if (typeof window === 'undefined') return false
  return window.innerWidth < 768
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = text
    document.body.appendChild(textArea)
    textArea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textArea)
    return success
  }
}
