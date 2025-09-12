# Performate AI - Ready for Deployment

This repository contains the complete Performate AI application:

## Backend (FastAPI)
- Port: 8000
- Start command: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Requirements: `backend/requirements.txt`

## Frontend (Next.js)
- Port: 3000
- Start command: `npm start`
- Build command: `npm run build`
- Package.json: `frontend/package.json`

## Environment Variables Needed:
- OPENAI_API_KEY
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- UPSTASH_REDIS_REST_URL
- UPSTASH_REDIS_REST_TOKEN

## Deployment Ready ✅
The application is fully configured and ready for deployment on Render.com

Created: $(date)
Commit: $(git rev-parse HEAD)
