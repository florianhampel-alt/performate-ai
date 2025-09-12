'use client'

import { useState } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import type { SportType } from '@/lib/types'

const SPORTS_CONFIG = {
  climbing: {
    name: 'Rock Climbing',
    icon: '🧗',
    description: 'Analyze your climbing technique and route efficiency',
    features: ['Grip analysis', 'Body positioning', 'Route planning'],
    color: 'sport-climbing'
  },
  bouldering: {
    name: 'Bouldering',
    icon: '🏔️',
    description: 'Problem-solving technique and dynamic movement analysis',
    features: ['Problem solving', 'Power analysis', 'Fall technique'],
    color: 'sport-bouldering'
  },
  skiing: {
    name: 'Skiing',
    icon: '⛷️',
    description: 'Balance, edge control, and turn technique assessment',
    features: ['Balance analysis', 'Edge control', 'Turn technique'],
    color: 'sport-skiing'
  },
  motocross: {
    name: 'Motocross',
    icon: '🏍️',
    description: 'Body position and bike control evaluation',
    features: ['Body positioning', 'Throttle control', 'Jump technique'],
    color: 'sport-motocross'
  },
  mountainbike: {
    name: 'Mountain Biking',
    icon: '🚵',
    description: 'Trail riding technique and bike handling skills',
    features: ['Bike handling', 'Line choice', 'Climbing efficiency'],
    color: 'sport-mountainbike'
  }
}

interface SportSelectorProps {
  onSelect?: (sport: SportType) => void
  selectedSport?: SportType
  showDetails?: boolean
}

export default function SportSelector({ 
  onSelect, 
  selectedSport,
  showDetails = true 
}: SportSelectorProps) {
  const [hoveredSport, setHoveredSport] = useState<SportType | null>(null)

  const handleSportSelect = (sport: SportType) => {
    if (onSelect) {
      onSelect(sport)
    }
  }

  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
      {Object.entries(SPORTS_CONFIG).map(([sportKey, config]) => {
        const sport = sportKey as SportType
        const isSelected = selectedSport === sport
        const isHovered = hoveredSport === sport

        return (
          <Card
            key={sport}
            className={`
              cursor-pointer transition-all duration-200 hover:shadow-lg
              ${isSelected ? 'ring-2 ring-blue-500 shadow-lg' : ''}
              ${isHovered ? 'scale-105' : ''}
            `}
            onClick={() => handleSportSelect(sport)}
            onMouseEnter={() => setHoveredSport(sport)}
            onMouseLeave={() => setHoveredSport(null)}
          >
            <div className="p-6 text-center">
              {/* Sport Icon */}
              <div className="text-4xl mb-3">
                {config.icon}
              </div>

              {/* Sport Name */}
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {config.name}
              </h3>

              {/* Description */}
              {showDetails && (
                <>
                  <p className="text-sm text-gray-600 mb-4">
                    {config.description}
                  </p>

                  {/* Features */}
                  <ul className="text-xs text-gray-500 space-y-1 mb-4">
                    {config.features.map((feature, index) => (
                      <li key={index} className="flex items-center justify-center">
                        <span className="w-1 h-1 bg-gray-400 rounded-full mr-2" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {/* Action Button */}
              <Button 
                size="sm" 
                variant={isSelected ? "default" : "outline"}
                className={`w-full ${isSelected ? config.color : ''}`}
              >
                {isSelected ? 'Selected' : 'Select'}
              </Button>
            </div>
          </Card>
        )
      })}
    </div>
  )
}
