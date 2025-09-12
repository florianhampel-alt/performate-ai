import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import SportSelector from '@/features/sports/SportSelector'

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <h1 className="text-4xl font-bold text-gray-900 sm:text-6xl">
          AI-Powered Sports
          <span className="text-blue-600"> Performance Analysis</span>
        </h1>
        <p className="mt-6 text-xl text-gray-600 max-w-3xl mx-auto">
          Upload your sports videos and get instant, detailed performance analysis 
          powered by advanced AI technology. Improve your technique in climbing, 
          skiing, motocross, and more.
        </p>
        <div className="mt-10 flex justify-center gap-4">
          <Button size="lg" className="px-8 py-3">
            Upload Video
          </Button>
          <Button variant="outline" size="lg" className="px-8 py-3">
            Watch Demo
          </Button>
        </div>
      </div>

      {/* Sport Selection */}
      <div className="mb-16">
        <h2 className="text-3xl font-bold text-gray-900 text-center mb-8">
          Choose Your Sport
        </h2>
        <SportSelector />
      </div>

      {/* Features Section */}
      <div className="grid md:grid-cols-3 gap-8 mb-16">
        <Card className="p-6">
          <div className="text-2xl mb-4">🎯</div>
          <h3 className="text-xl font-semibold mb-2">Precise Analysis</h3>
          <p className="text-gray-600">
            Get detailed biomechanical analysis of your movements with AI-powered 
            computer vision technology.
          </p>
        </Card>
        
        <Card className="p-6">
          <div className="text-2xl mb-4">📊</div>
          <h3 className="text-xl font-semibold mb-2">Performance Metrics</h3>
          <p className="text-gray-600">
            Track your progress with comprehensive performance metrics and 
            personalized improvement recommendations.
          </p>
        </Card>
        
        <Card className="p-6">
          <div className="text-2xl mb-4">🏆</div>
          <h3 className="text-xl font-semibold mb-2">Expert Insights</h3>
          <p className="text-gray-600">
            Receive professional-level insights and training recommendations 
            tailored to your specific sport and skill level.
          </p>
        </Card>
      </div>

      {/* How It Works */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-8">
          How It Works
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center text-xl font-bold mb-4">
              1
            </div>
            <h3 className="text-lg font-semibold mb-2">Upload Your Video</h3>
            <p className="text-gray-600">
              Upload a video of your sports performance in supported formats.
            </p>
          </div>
          
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center text-xl font-bold mb-4">
              2
            </div>
            <h3 className="text-lg font-semibold mb-2">AI Analysis</h3>
            <p className="text-gray-600">
              Our AI analyzes your technique, biomechanics, and performance patterns.
            </p>
          </div>
          
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 bg-blue-600 text-white rounded-full flex items-center justify-center text-xl font-bold mb-4">
              3
            </div>
            <h3 className="text-lg font-semibold mb-2">Get Results</h3>
            <p className="text-gray-600">
              Receive detailed insights and personalized recommendations for improvement.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
