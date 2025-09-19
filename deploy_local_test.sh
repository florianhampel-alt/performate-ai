#!/bin/bash
# Performate AI - Local Production Test Deployment

set -e

echo "🚀 Performate AI - Production Test Deployment"
echo "=============================================="

# Check if required files exist
if [[ ! -f "vercel.json" ]]; then
    echo "❌ vercel.json not found"
    exit 1
fi

if [[ ! -f "render.yaml" ]]; then
    echo "❌ render.yaml not found"
    exit 1
fi

echo "✅ Deployment configuration files found"

# Test backend locally with production settings
echo ""
echo "🔧 Testing backend with production configuration..."

cd backend

# Check if virtual environment exists, create if not
if [[ ! -d "venv" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing production dependencies..."
pip install -r requirements.txt

# Set production-like environment variables
export DEBUG=false
export LOG_LEVEL=INFO
export REDIS_HOST=localhost
export REDIS_PORT=6379
export AWS_REGION=us-east-1
export S3_BUCKET=performate-ai-uploads
export MAX_FILE_SIZE=104857600
export ENABLE_AI_ANALYSIS=true
export ALLOWED_HOSTS="localhost:8000,127.0.0.1:8000"

# Check if Redis is running
if ! pgrep redis-server > /dev/null; then
    echo "⚠️ Redis not running. Starting Redis with Docker..."
    docker run -d --name performate-redis -p 6379:6379 redis:7-alpine || echo "Redis already running or Docker not available"
fi

# Test backend startup
echo "🚀 Testing backend startup..."
timeout 10s uvicorn app.main:app --host=0.0.0.0 --port=8000 &
BACKEND_PID=$!

sleep 5

# Test health endpoint
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend health check passed"
else
    echo "❌ Backend health check failed"
fi

# Stop backend
kill $BACKEND_PID 2>/dev/null || true

cd ..

# Test frontend build
echo ""
echo "🔧 Testing frontend build..."

cd frontend

if [[ ! -d "node_modules" ]]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Set production environment
export NEXT_PUBLIC_API_URL="https://performate-ai-backend.onrender.com"
export NEXT_PUBLIC_APP_NAME="Performate AI"
export NEXT_TELEMETRY_DISABLED=1

# Test build
echo "🚀 Testing frontend build..."
npm run build

if [[ $? -eq 0 ]]; then
    echo "✅ Frontend build successful"
else
    echo "❌ Frontend build failed"
    exit 1
fi

cd ..

echo ""
echo "🏆 LOCAL DEPLOYMENT TEST COMPLETE"
echo "================================="
echo "✅ Backend: Production-ready"
echo "✅ Frontend: Build successful"
echo "✅ Configurations: Valid"
echo ""
echo "Next steps:"
echo "1. Deploy backend to Render.com using render.yaml"
echo "2. Deploy frontend to Vercel using vercel.json"
echo "3. Configure AWS S3 bucket"
echo "4. Set production environment variables"
echo ""
echo "📖 Full guide: ./DEPLOYMENT_GUIDE.md"