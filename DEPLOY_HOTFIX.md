# HOTFIX DEPLOYMENT GUIDE

## Problem
Video-Analyse schlägt fehl, weil OpenCV S3-Keys nicht direkt öffnen kann.

## Lösung
Download von S3 vor Frame-Extraktion (siehe `RCA_VIDEO_ANALYSIS_FAILURE.md` für Details).

---

## LOKALER TEST (EMPFOHLEN VOR PRODUCTION)

### 1. Backup erstellen
```bash
cd /Users/florianhampel/performate-ai
git stash  # Falls uncommitted changes
git checkout -b hotfix/s3-video-download
```

### 2. Patch anwenden
```bash
# OPTION A: Manuell (einfacher für kleine Änderungen)
# Kopiere die Code-Änderungen aus HOTFIX_S3_VIDEO_DOWNLOAD.patch manuell

# OPTION B: Mit git apply (falls Patch sauber anwendbar)
git apply HOTFIX_S3_VIDEO_DOWNLOAD.patch
```

### 3. Dependencies installieren
```bash
cd backend
pip install aiohttp>=3.9.0
```

### 4. Lokaler Test
```bash
# Terminal 1: Redis starten (falls nicht läuft)
docker run -d -p 6379:6379 redis:7-alpine

# Terminal 2: Backend starten
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Test-Upload
# (Verwende Frontend oder curl)
curl -X POST http://localhost:8000/upload/init \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.mp4", "content_type": "video/mp4", "file_size": 1048576}'

# Upload Video zu S3 (mit dem presigned URL aus Response)
# Dann complete:
curl -X POST http://localhost:8000/upload/complete \
  -H "Content-Type: application/json" \
  -d '{"analysis_id": "ANALYSIS_ID_FROM_INIT"}'

# Prüfe Logs auf:
# ✅ "🔽 Downloading S3 key videos/..."
# ✅ "✅ Video downloaded successfully: X.XMB"
# ✅ "✅ ENTERPRISE SUCCESS: N frames extracted"
# ✅ "AI vision analysis completed"
```

### 5. Validierung
```bash
# Prüfe Backend-Logs
tail -f backend/performate-ai.log | grep -E "(Downloading S3|Video downloaded|ENTERPRISE SUCCESS)"

# Erwartete Ausgabe:
# 🔽 Downloading S3 key videos/2025/10/23/xxx.mp4 to /tmp/tmpXXX.mp4
# 📡 Presigned URL generated, downloading video...
# ✅ Video downloaded successfully: 15.2MB
# 📂 Using local video path: /tmp/tmpXXX.mp4
# ✅ ENTERPRISE SUCCESS: 5 frames extracted, duration=30.5s
```

---

## PRODUCTION DEPLOYMENT (Render.com)

### Voraussetzungen
- [ ] Lokaler Test erfolgreich
- [ ] Git-Branch mit Hotfix gepusht
- [ ] Render.com Dashboard-Zugang

### Deployment-Schritte

#### 1. Code committen
```bash
cd /Users/florianhampel/performate-ai

git add backend/app/services/ai_vision_service.py
git add backend/app/services/s3_service.py
git add backend/requirements.txt

git commit -m "hotfix: Download S3 videos before frame extraction

Fixes METADATA_EXTRACTION_FAILED errors by downloading S3 videos
to temporary files before passing to OpenCV.

Changes:
- ai_vision_service.py: Add S3 download logic with aiohttp
- s3_service.py: Add generate_presigned_url method
- requirements.txt: Add aiohttp dependency

Closes: #VIDEO-ANALYSIS-FAILURE
"

git push origin hotfix/s3-video-download
```

#### 2. Render.com Deployment
```bash
# OPTION A: Auto-Deploy (wenn aktiviert in render.yaml)
# → Push to main/master branch triggers auto-deployment

# Merge Hotfix zu main
git checkout main
git merge hotfix/s3-video-download
git push origin main

# Warte ~2-5 Minuten auf Render auto-deploy
```

**ODER**

```bash
# OPTION B: Manuelles Deploy via Render Dashboard
# 1. Gehe zu https://dashboard.render.com/
# 2. Wähle "performate-ai" Service
# 3. Gehe zu "Manual Deploy"
# 4. Wähle Branch: hotfix/s3-video-download
# 5. Click "Deploy"
```

#### 3. Deployment überwachen
```bash
# Render.com Dashboard → performate-ai → Logs
# Suche nach:
# - "Starting deployment..."
# - "Build successful"
# - "✅ S3 service initialized"
# - "✅ OPENAI_API_KEY found"
# - "🚀 Starting Performate AI API initialization..."
# - "INFO:     Application startup complete."
```

#### 4. Smoke Test (Production)
```bash
# Health Check
curl https://performate-ai.onrender.com/health

# Expected Response:
# {
#   "status": "healthy",
#   "cache_stats": {...},
#   "services": {
#     "redis": "available",
#     "s3": "available",
#     "video_cache": "available"
#   }
# }

# Test Video Upload + Analysis
# (Use Frontend oder curl)
curl -X POST https://performate-ai.onrender.com/upload/init \
  -H "Content-Type: application/json" \
  -d '{"filename": "climbing-test.mp4", "content_type": "video/mp4", "file_size": 2097152}'

# ... Upload zu S3 Presigned URL ...

curl -X POST https://performate-ai.onrender.com/upload/complete \
  -H "Content-Type: application/json" \
  -d '{"analysis_id": "YOUR_ANALYSIS_ID"}'

# Check Status
curl https://performate-ai.onrender.com/upload/status/YOUR_ANALYSIS_ID

# Expected: "status": "completed"
```

#### 5. Log-Überwachung (15 Minuten)
```bash
# Render Dashboard → Logs → Live Tail
# Suche nach diesen Patterns:

# ✅ ERFOLG:
# "🔽 Downloading S3 key videos/..."
# "✅ Video downloaded successfully"
# "✅ ENTERPRISE SUCCESS: N frames extracted"
# "AI vision analysis completed"

# ❌ FEHLER (sollten verschwunden sein):
# "❌ ENTERPRISE FAILURE: METADATA_EXTRACTION_FAILED"
# "❌ Could not open video with FFMPEG"
# "❌ Could not extract metadata from videos/..."

# Falls FEHLER auftreten → ROLLBACK (siehe unten)
```

---

## ROLLBACK (Falls Hotfix Probleme verursacht)

### Schnell-Rollback (Render.com)
```bash
# Render Dashboard → performate-ai Service
# → "Rollback" Button (oben rechts)
# → Wähle vorherige erfolgreiche Deployment
# → "Confirm Rollback"
```

### Git-Rollback
```bash
cd /Users/florianhampel/performate-ai
git checkout main
git revert HEAD --no-edit
git push origin main
# Warte auf Render auto-redeploy
```

---

## POST-DEPLOYMENT VALIDIERUNG

### Metriken prüfen (1h nach Deploy)
- [ ] **Error Rate**: < 1% (aus Render Metrics oder Logs)
- [ ] **Success Rate**: > 99% für Analysen
- [ ] **Latency P95**: < 120s (sollte unverändert sein)
- [ ] **Keine neuen Fehler** in Sentry/Logs

### User-Feedback
- [ ] Test mit echten User-Videos (verschiedene Größen, Codecs)
- [ ] Frontend zeigt "completed" Status korrekt an
- [ ] Performance-Score und Overlay-Daten vorhanden

---

## MONITORING QUERIES (Render Logs)

```bash
# Success Rate (letzte Stunde)
# Count "AI vision analysis completed" vs "AI vision analysis FAILED"
grep -c "AI vision analysis completed" logs.txt
grep -c "AI vision analysis FAILED" logs.txt

# Frame Extraction Erfolg
grep "ENTERPRISE SUCCESS" logs.txt | tail -20

# S3 Download Performance
grep "Video downloaded successfully" logs.txt | \
  sed -n 's/.*successfully: \([0-9.]*\)MB/\1/p' | \
  awk '{sum+=$1; count++} END {print "Avg MB:", sum/count}'

# Temp File Cleanup
grep "Cleaned up temp file" logs.txt | wc -l
# Sollte gleich der Anzahl "Video downloaded successfully" sein
```

---

## NÄCHSTE SCHRITTE (nach erfolgreichem Hotfix)

### Diese Woche
- [ ] **Monitoring Alerts** einrichten (Sentry/Grafana)
- [ ] **Synthetic Health Check** implementieren (`/health/analysis-pipeline`)
- [ ] **Detailed Error Codes** in EnterpriseErrorResponse

### 2 Wochen
- [ ] **Worker-Service** in render.yaml aktivieren
- [ ] **Queue-basierte Architektur** (Celery + Redis)
- [ ] **Retry-Logic** mit exponential backoff

### 1 Monat
- [ ] **Video Ingestion Service** (separater Service)
- [ ] **Video Policy + Validator** (Codec/Size-Checks)
- [ ] **DLQ** für failed analyses

---

## SUPPORT & TROUBLESHOOTING

### Häufige Probleme

#### 1. "Failed to generate presigned URL"
**Ursache**: AWS Credentials fehlen/invalid  
**Fix**: Prüfe Render.com Environment Variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

#### 2. "Failed to download video: HTTP 403"
**Ursache**: S3 Bucket Policy oder IAM-Permissions  
**Fix**: Prüfe S3 Bucket Policy (GetObject für IAM User)

#### 3. "No space left on device" (beim Download)
**Ursache**: Render.com /tmp ist voll  
**Fix**: Mittelfristig: Worker-Service mit mehr Disk-Space; Kurzfristig: Cleanup nach Analyse

#### 4. Analyse dauert >2min
**Ursache**: Large Videos (>50MB) + Download-Zeit  
**Fix**: Langfristig: Worker-Service mit Timeout-Erhöhung

### Log-Debugging
```bash
# Render Dashboard → Logs → Filter
# Suche nach analysis_id:
# "Starting AI vision analysis for abc-123"
# ... alle relevanten Log-Zeilen für diese ID ...
# "AI vision analysis completed for abc-123"

# Falls stuck bei "Downloading S3 key":
# → Prüfe Network/S3 Erreichbarkeit
# → Prüfe Presigned URL Expiry (sollte 3600s sein)

# Falls stuck bei "Frame extraction":
# → Prüfe Video-Größe (temp file wurde erstellt?)
# → Prüfe OpenCV Backends verfügbar
```

---

## KONTAKTE

- **On-Call SRE**: [Slack/PagerDuty]
- **Backend Lead**: [GitHub]
- **Render Support**: https://render.com/support
- **AWS Support**: (falls S3-Issues)

---

**Ende der Deployment-Anleitung**  
*Version: 1.0*  
*Letzte Aktualisierung: 2025-10-23*
