'use client'

import AnalysisResults from '@/features/analysis/AnalysisResults'

interface AnalysisPageProps {
  params: {
    id: string
  }
}

export default function AnalysisPage({ params }: AnalysisPageProps) {
  return <AnalysisResults analysisId={params.id} />
}
