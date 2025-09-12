import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Performate AI - Sports Performance Analysis',
  description: 'AI-powered sports performance analysis for climbing, skiing, motocross, and more',
  keywords: ['sports', 'performance', 'analysis', 'AI', 'climbing', 'skiing', 'motocross'],
  authors: [{ name: 'Performate AI Team' }],
  viewport: 'width=device-width, initial-scale=1',
  icons: {
    icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🏆</text></svg>'
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <h1 className="text-xl font-bold text-gray-900">
                  Performate AI
                </h1>
              </div>
              <nav className="hidden md:flex space-x-8">
                <a href="/" className="text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                  Home
                </a>
                <a href="/upload" className="text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                  Upload
                </a>
                <a href="/analysis" className="text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium">
                  Analysis
                </a>
              </nav>
            </div>
          </div>
        </header>
        
        <main className="min-h-screen bg-gray-50">
          {children}
        </main>
        
        <footer className="bg-white border-t">
          <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
            <div className="text-center text-gray-500 text-sm">
              © 2024 Performate AI. All rights reserved.
            </div>
          </div>
        </footer>
      </body>
    </html>
  )
}
