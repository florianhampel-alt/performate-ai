# Performate AI 🏔️

> AI-powered sports performance analysis for climbing, skiing, motocross, mountain biking, and more.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Development](#development)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Performate AI is a comprehensive platform that uses advanced AI and computer vision to analyze sports performance videos. Upload your climbing, skiing, motocross, or mountain biking videos and get detailed insights, technique analysis, and personalized training recommendations.

### Supported Sports
- 🧗 **Rock Climbing** - Route planning, grip analysis, body positioning
- 🏔️ **Bouldering** - Problem-solving technique, power analysis, fall technique
- ⛷️ **Skiing** - Balance analysis, edge control, turn technique
- 🏍️ **Motocross** - Body positioning, throttle control, jump technique
- 🚵 **Mountain Biking** - Bike handling, line choice, climbing efficiency

## ✨ Features

### 🤖 AI-Powered Analysis
- **Computer Vision**: Advanced pose estimation and movement tracking
- **GPT-4 Vision**: Natural language insights and recommendations
- **Biomechanics Analysis**: Joint angle analysis and movement patterns
- **Sport-Specific Insights**: Tailored analysis for each sport

### 📊 Performance Metrics
- Overall performance scoring
- Technique assessment
- Safety considerations
- Progress tracking
- Comparative analysis

### 🎯 Personalized Recommendations
- Training suggestions
- Technique improvements
- Safety reminders
- Equipment recommendations

### 🔧 Developer Features
- RESTful API
- Real-time analysis status
- Background processing with Celery
- Scalable microservices architecture

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI/ML**: OpenAI GPT-4 Vision, OpenCV, NumPy
- **Task Queue**: Celery with Redis
- **Storage**: AWS S3 (LocalStack for development)
- **Caching**: Redis
- **Testing**: Pytest

### Frontend
- **Framework**: Next.js 14 (React 18)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: Radix UI + custom components
- **State Management**: React hooks
- **File Upload**: react-dropzone

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Reverse Proxy**: Nginx (production)
- **Monitoring**: Health checks, logging
- **Development**: Hot reload, auto-restart

## 🚀 Getting Started

### Prerequisites
- [Docker](https://www.docker.com/get-started) and Docker Compose
- [Node.js 18+](https://nodejs.org/) (for local development)
- [Python 3.11+](https://www.python.org/) (for local development)
- [Make](https://www.gnu.org/software/make/) (optional, for convenience commands)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/performate-ai.git
   cd performate-ai
   ```

2. **Initialize the project**
   ```bash
   make init
   ```
   This will:
   - Copy `.env.example` to `.env`
   - Install dependencies
   - Build Docker images

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file and add your OpenAI API key
   ```

4. **Start development environment**
   ```bash
   make dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Manual Setup

If you prefer not to use Make:

```bash
# Copy environment file
cp .env.example .env

# Start supporting services
docker-compose up -d redis localstack

# Install backend dependencies
cd backend && pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install

# Start backend
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (in another terminal)
cd frontend && npm run dev

# Start worker (in another terminal)
cd backend && celery -A worker.worker worker --loglevel=info
```

## 💻 Development

### Available Commands

Use `make help` to see all available commands:

```bash
make help                 # Show all available commands
make dev                  # Start development environment
make build               # Build Docker images
make test                # Run all tests
make lint                # Lint and format code
make logs                # View logs
make clean               # Clean up environment
```

### Project Structure

```
performate-ai/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── analyzers/      # AI analysis engines
│   │   ├── models/         # Pydantic data models
│   │   ├── services/       # Business logic services
│   │   ├── utils/          # Utility functions
│   │   ├── config/         # Configuration files
│   │   └── main.py         # FastAPI application
│   ├── worker/             # Celery workers
│   ├── tests/              # Backend tests
│   └── requirements.txt    # Python dependencies
├── frontend/               # Next.js React frontend
│   ├── app/                # Next.js app directory
│   ├── components/         # Reusable UI components
│   ├── features/           # Feature-specific components
│   ├── lib/                # Utility libraries
│   └── package.json        # Node.js dependencies
├── docker-compose.yml      # Development stack
├── Makefile               # Development commands
└── README.md              # This file
```

### Adding New Sports

1. **Update sport configurations** in `backend/app/utils/sport_configs.py`
2. **Add sport icons** in `frontend/features/sports/SportSelector.tsx`
3. **Update type definitions** in `frontend/lib/types.ts`
4. **Add sport-specific analysis logic** in analyzers and services

### Testing

```bash
# Run all tests
make test

# Run backend tests only
make test-backend

# Run frontend tests only
make test-frontend

# Run specific test file
cd backend && python -m pytest tests/test_specific.py -v
```

### Code Quality

```bash
# Format and lint all code
make lint

# Backend only
make lint-backend

# Frontend only
make lint-frontend
```

## 📚 API Documentation

The API documentation is automatically generated and available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

```http
GET  /health                    # Health check
POST /upload                    # Upload video file
POST /analysis/start            # Start analysis
GET  /analysis/{id}             # Get analysis results
GET  /analysis/{id}/status      # Get analysis status
GET  /sports                    # List supported sports
```

### Example Usage

```python
import requests

# Upload a video
with open('climbing_video.mp4', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/upload',
        files={'file': f},
        data={'sport_type': 'climbing'}
    )

# Start analysis
analysis = requests.post(
    'http://localhost:8000/analysis/start',
    json={
        'file_id': response.json()['fileId'],
        'sport_type': 'climbing'
    }
)

# Get results
results = requests.get(
    f'http://localhost:8000/analysis/{analysis.json()["analysisId"]}'
)
```

## 🏗️ Architecture

### System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │     Worker      │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (Celery)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │     Redis       │    │   OpenAI API    │
                       │ (Cache/Queue)   │    │ (GPT-4 Vision)  │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │      S3         │
                       │  (File Storage) │
                       └─────────────────┘
```

### Analysis Pipeline

1. **Upload**: Video file uploaded to S3
2. **Queue**: Analysis task added to Celery queue
3. **Processing**: Worker extracts frames and runs AI analysis
4. **Analysis**: Multiple analyzers process the video:
   - Biomechanics analyzer (pose estimation)
   - AI analyzer (GPT-4 Vision)
   - Sport-specific analyzer
5. **Results**: Combined results cached and returned

### Scalability

- **Horizontal scaling**: Add more workers for increased throughput
- **Caching**: Redis for fast result retrieval
- **CDN**: S3/CloudFront for global file distribution
- **Load balancing**: Nginx for traffic distribution

## 🚢 Deployment

### Production Docker Compose

```bash
# Build for production
make prod-build

# Start production environment
make prod-up
```

### Environment Variables

See `.env.example` for all available configuration options. Key variables for production:

```env
# Production settings
NODE_ENV=production
DEBUG=false
SECRET_KEY=your-production-secret-key

# API Keys
OPENAI_API_KEY=sk-your-openai-api-key

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
S3_BUCKET=your-production-bucket

# Domains
ALLOWED_HOSTS=your-domain.com,api.your-domain.com
NEXT_PUBLIC_API_URL=https://api.your-domain.com
```

### Health Monitoring

```bash
# Check service health
make health

# View service status
make status
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `make test`
5. Lint code: `make lint`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Code Standards

- **Python**: Black, isort, flake8
- **TypeScript**: ESLint, Prettier
- **Commits**: Conventional commits
- **Documentation**: Keep README and docstrings updated

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAI](https://openai.com/) for GPT-4 Vision API
- [OpenCV](https://opencv.org/) for computer vision utilities
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent Python web framework
- [Next.js](https://nextjs.org/) for the React framework
- [Tailwind CSS](https://tailwindcss.com/) for utility-first CSS

## 📞 Support

- 📧 Email: support@performate-ai.com
- 💬 GitHub Issues: [Create an issue](https://github.com/your-username/performate-ai/issues)
- 📖 Documentation: [Wiki](https://github.com/your-username/performate-ai/wiki)

---

Built with ❤️ by the Performate AI Team
