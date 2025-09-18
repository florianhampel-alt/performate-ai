import type { MetricStatus } from '../types'

/**
 * Translates metric status to German display text
 * Handles both snake_case and space-separated variants
 */
export function translateMetricStatus(status: MetricStatus | string | undefined): string {
  if (!status) return 'nicht analysiert'
  
  // Normalize status to handle both variants
  const normalizedStatus = status.toLowerCase().replace(/\s+/g, '_')
  
  switch (normalizedStatus) {
    case 'good':
      return 'gut'
    case 'needs_improvement':
      return 'verbesserung nötig'
    case 'not_analyzed':
      return 'nicht analysiert'
    default:
      // Fallback: convert snake_case to readable German
      return normalizedStatus.replace(/_/g, ' ')
  }
}

/**
 * Translates metric name to German
 */
export function translateMetricName(metric: string): string {
  switch (metric.toLowerCase()) {
    case 'balance':
      return 'Balance'
    case 'efficiency':
      return 'Effizienz'
    case 'technique':
      return 'Technik'
    case 'stability':
      return 'Stabilität'
    case 'power':
      return 'Kraft'
    case 'coordination':
      return 'Koordination'
    default:
      // Fallback: capitalize and replace underscores
      return metric.charAt(0).toUpperCase() + metric.slice(1).replace(/_/g, ' ')
  }
}

/**
 * Gets color class for metric status
 */
export function getMetricStatusColor(status: MetricStatus | string | undefined): string {
  if (!status) return 'bg-gray-400'
  
  const normalizedStatus = status.toLowerCase().replace(/\s+/g, '_')
  
  switch (normalizedStatus) {
    case 'good':
      return 'bg-green-500'
    case 'needs_improvement':
      return 'bg-yellow-500'
    case 'not_analyzed':
      return 'bg-gray-400'
    default:
      return 'bg-gray-400'
  }
}