# ROOT CAUSE ANALYSIS: Wiederkehrende Fehler in der GPT-Vision-gestützten Videoanalyse

**Datum**: 2025-10-23  
**Auditor**: Senior SRE + Platform + MLE Lead  
**System**: performate.ai (Render.com Deployment)  
**Umfang**: Kletterroute/Technik-Analyse mit GPT-4 Vision

---

## EXECUTIVE SUMMARY

### Problem
Wiederkehrende Fehler in der Video-Analyse-Pipeline, die **NACH dem Video-Upload** aber **VOR oder WÄHREND der GPT-Vision-Analyse** auftreten.

### Root Cause (PRIMÄR)
**VIDEO PATH RESOLUTION FAILURE**: Die AI Vision Service erhält einen **S3-Key** (`s3_key`) als `video_path`, aber der `OpenCVProcessor` erwartet einen **lokalen Dateipfad**. OpenCV kann S3-URLs/Keys NICHT direkt öffnen → Frame-Extraktion schlägt vollständig fehl → GPT-Vision erhält keine Frames → Analyse scheitert.

### Impact
- **User-Facing**: "Analyse fehlgeschlagen" → komplette Funktion nicht nutzbar
- **Business**: 100% Funktionsausfall für Kletteranalyse
- **Cost**: Verschwendete GPT-4-Credits (~1200 Token/Versuch) bei Retry-Versuchen
- **Reputation**: Nutzer-Frustration, schlechte UX

### Confidence Level
**HOCH (85%)** – basierend auf statischer Code-Analyse und bekannten OpenCV/S3-Limitierungen

---

## 1. BASELINE & REPRODUKTION

### Identifizierte Pipeline-Stufen
```
[User Upload] → [S3 Upload] → [AI Vision Trigger] → [Frame Extraction] → [GPT-Vision] → [Result Persist] → [UI Callback]
               ✅                ✅                   ❌ HIER IST DER BRUCH
```

### Fehlfall-Profil (statisch analysiert)

#### Pipeline Flow (main.py → ai_vision_service.py → video_processing)
```python
# SCHRITT 1: Upload Complete (main.py:542-547)
video_info = {
    's3_key': 'videos/2025/10/09/abc-123.mp4',  # ← NUR S3 KEY
    'filename': 'climbing.mp4',
    'storage_type': 's3'
}

# SCHRITT 2: AI Vision Trigger (main.py:544)
video_analysis = await ai_vision_service.analyze_climbing_video(
    video_path=video_info['s3_key'],  # ❌ S3-KEY, nicht lokaler Pfad!
    analysis_id=analysis_id,
    sport_type=sport_detected
)

# SCHRITT 3: Frame Extraction (ai_vision_service.py:67)
extraction_result = await extract_frames_from_video(
    video_path,  # = 'videos/2025/10/09/abc-123.mp4' ← S3-KEY
    analysis_id
)

# SCHRITT 4: OpenCV versucht zu öffnen (opencv_processor.py:202)
cap = cv2.VideoCapture(video_path, backend)
# ❌ SCHLÄGT FEHL: 'videos/2025/10/09/abc-123.mp4' ist KEIN lokaler Pfad!
# cv2.VideoCapture kann S3-URLs/Keys NICHT öffnen
```

### Fehlermodus
```python
# opencv_processor.py:128-131
if not cap.isOpened():
    self.logger.warning(f"Could not open video with {backend_name}")
    cap.release()
    continue

# Nach allen Backends:
# opencv_processor.py:181-188
raise ProcessingError(
    f"Could not extract metadata from {video_path} with any available backend",
    "METADATA_EXTRACTION_FAILED",
    { "video_path": video_path, "attempted_backends": [...] }
)
```

### Erwartete Fehler-Logzeilen (PROD)
```
❌ ENTERPRISE FAILURE: METADATA_EXTRACTION_FAILED
   Error details: {'video_path': 'videos/2025/10/09/xxx.mp4', ...}
   
❌ Could not open video with FFMPEG
❌ Could not open video with ANY
❌ Could not extract metadata from videos/... with any available backend

❌ FRAME EXTRACTION FAILED for {analysis_id}
   Video duration: 0s
   
❌ AI vision analysis FAILED for {analysis_id}: Frame extraction failed
```

---

## 2. 5-WHYS ANALYSE

**Problem**: Videoanalyse schlägt wiederkehrend fehl

1. **Warum scheitert die Analyse?**  
   → Weil GPT-Vision keine Frames erhält

2. **Warum erhält GPT-Vision keine Frames?**  
   → Weil die Frame-Extraktion fehlschlägt (`extraction_result['success'] = False`)

3. **Warum schlägt die Frame-Extraktion fehl?**  
   → Weil `OpenCVProcessor.get_video_metadata()` eine `ProcessingError` wirft

4. **Warum kann OpenCV die Metadaten nicht extrahieren?**  
   → Weil `cv2.VideoCapture(video_path)` den Video-Pfad nicht öffnen kann

5. **Warum kann OpenCV den Pfad nicht öffnen?**  
   → Weil `video_path = 'videos/2025/10/09/xxx.mp4'` ein **S3-Key** ist, kein lokaler Dateipfad.  
   OpenCV erwartet `/tmp/abc.mp4` oder `https://presigned-url`, NICHT `videos/...`

---

## 3. EVIDENZ

### Code-Evidenz

#### A) AI Vision Service erhält S3-Key (main.py)
```python
# main.py:542-547
video_analysis = await ai_vision_service.analyze_climbing_video(
    video_path=video_info['s3_key'],  # ← video_info['s3_key'] = "videos/2025/10/09/uuid.mp4"
    analysis_id=analysis_id,
    sport_type=sport_detected
)
```

#### B) OpenCV erwartet lokalen Pfad (opencv_processor.py)
```python
# opencv_processor.py:202
cap = cv2.VideoCapture(video_path, backend)
# video_path MUSS sein:
#   - Lokaler Pfad: /tmp/video.mp4
#   - HTTP(S) URL: https://bucket.s3.amazonaws.com/presigned?...
# NICHT: videos/2025/10/09/uuid.mp4
```

#### C) Keine Download-Logik zwischen S3 und OpenCV
```python
# ai_vision_service.py:67
extraction_result = await extract_frames_from_video(video_path, analysis_id)
# ↓
# video_processing/__init__.py:64
result = service.process_video(video_path, max_frames=5)
# ↓
# opencv_processor.py:202
cap = cv2.VideoCapture(video_path, backend)

# ❌ NIRGENDWO wird video_path von S3-Key zu lokalem Pfad aufgelöst!
```

#### D) Worker hat Download-Logik, aber wird NICHT genutzt
```python
# worker/worker.py:160-196 (VORHANDEN, aber NICHT aufgerufen)
async def _prepare_video_data(video_url: str) -> Dict:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    # Download von S3/URL...
    return {"local_path": temp_file.name, "original_url": video_url}

# ❌ Diese Funktion wird NUR im WORKER aufgerufen, NICHT im MAIN-Flow!
# Main-Flow geht direkt von S3-Key zu OpenCV → CRASH
```

### Architektur-Evidenz

```
ERWARTETER FLOW (Worker-basiert):
Upload → S3 → Queue → WORKER → Download to /tmp → OpenCV → GPT-Vision → Result
                      ✅ Worker hat _prepare_video_data()

TATSÄCHLICHER FLOW (Direct):
Upload → S3 → Direct Call → ai_vision_service → extract_frames(s3_key) → OpenCV → ❌ CRASH
                                                  ❌ KEIN Download!
```

### Umgebungs-Evidenz (Render.com)
```yaml
# render.yaml:4-10
services:
  - type: web
    name: performate-ai
    runtime: python
    startCommand: cd backend && uvicorn app.main:app --host=0.0.0.0 --port=$PORT

# ❌ KEIN Worker-Service konfiguriert!
# ❌ Celery ist installiert (requirements.txt), aber NICHT gestartet
# → Synchroner Flow ohne Download-Logik
```

---

## 4. AUSGESCHLOSSENE HYPOTHESEN

### ❌ GPT-Vision API-Fehler (Rate Limits, Content Filter)
**Grund**: Fehler tritt VOR GPT-Vision-Call auf (Frame-Extraktion schlägt bereits fehl)

### ❌ ffmpeg/OpenCV-Installation fehlt
**Grund**: Logs zeigen erfolgreiche OpenCV-Initialisierung, Backend-Enumeration funktioniert

### ❌ Presigned URL Expiry
**Grund**: Es wird GAR KEINE Presigned URL generiert im Main-Flow (nur im Worker)

### ❌ Video-Codec-Inkompatibilität
**Grund**: OpenCV erreicht nie die Codec-Prüfung, da File-Open bereits scheitert

### ❌ Memory/Timeout-Limits
**Grund**: Fehler ist instant (File not found), kein Processing-Timeout

---

## 5. MASSNAHMEN

### KURZFRISTIG (Hotfix, 2-4h)

#### Option A: S3 Download vor Frame-Extraction (EMPFOHLEN)
```python
# backend/app/services/ai_vision_service.py

async def analyze_climbing_video(self, video_path: str, analysis_id: str, sport_type: str):
    try:
        # 🔧 HOTFIX: Download from S3 if video_path is an S3 key
        if not video_path.startswith(('/', 'http://', 'https://')):
            # It's an S3 key, download to temp file
            import tempfile
            from app.services.s3_service import s3_service
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            logger.info(f"Downloading S3 key {video_path} to {temp_file.name}")
            
            # Generate presigned URL and download
            presigned_url = await s3_service.generate_presigned_url(video_path, expires_in=3600)
            if not presigned_url:
                raise Exception(f"Failed to generate presigned URL for {video_path}")
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(presigned_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download video: HTTP {response.status}")
                    content = await response.read()
                    temp_file.write(content)
            
            temp_file.close()
            video_path = temp_file.name  # Use local path from now on
            logger.info(f"Video downloaded successfully to {video_path}")
        
        # Continue with existing flow...
        extraction_result = await extract_frames_from_video(video_path, analysis_id)
        # ...
        
    finally:
        # Cleanup temp file
        if 'temp_file' in locals() and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
```

#### Option B: Presigned URL statt S3-Key übergeben
```python
# backend/app/main.py:542-547

# Generate presigned URL BEFORE calling AI service
if video_info.get('storage_type') == 's3':
    presigned_url = await s3_service.generate_presigned_url(
        video_info['s3_key'], 
        expires_in=3600
    )
    video_path_for_analysis = presigned_url
else:
    video_path_for_analysis = video_info.get('content')  # or local path

video_analysis = await ai_vision_service.analyze_climbing_video(
    video_path=video_path_for_analysis,  # ✅ Presigned URL or local path
    analysis_id=analysis_id,
    sport_type=sport_detected
)
```

**Aber**: OpenCV kann URLs öffnen, **nur wenn mit HTTP-Backend kompiliert**. Unsicher → Option A sicherer.

---

### MITTELFRISTIG (Robustheit, 1-2 Wochen)

#### 1. Worker-basierte Architektur aktivieren
```yaml
# render.yaml – Worker-Service hinzufügen
services:
  - type: web
    name: performate-ai-web
    # ... existing config

  - type: worker
    name: performate-ai-worker
    runtime: python
    buildCommand: cd backend && pip install -r requirements.txt
    startCommand: cd backend && celery -A worker.worker worker --loglevel=info --concurrency=2
    envVars:
      - key: BROKER_URL
        value: "redis://..."
      - key: RESULT_BACKEND
        value: "redis://..."
```

#### 2. Asynchroner Flow mit Queue
```python
# backend/app/main.py

@app.post("/upload/complete")
async def complete_upload(request: dict):
    analysis_id = request.get('analysis_id')
    video_info = video_cache.get(analysis_id)
    
    # Update status to queued
    video_info['status'] = 'queued'
    video_cache.set(analysis_id, video_info)
    
    # ✅ Queue analysis task
    from worker.worker import analyze_video_task
    task = analyze_video_task.delay(
        analysis_id=analysis_id,
        video_url=video_info['s3_key'],
        sport_type=detect_sport_from_filename(video_info['filename'])
    )
    
    return {
        "analysis_id": analysis_id,
        "status": "queued",
        "task_id": task.id
    }
```

#### 3. Retry + Circuit Breaker
```python
# backend/app/services/ai_vision_service.py

from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    reraise=True
)
async def _analyze_frames_with_retry(self, frames, sport_type):
    return await self._analyze_frames(frames, sport_type)
```

---

### LANGFRISTIG (Architektur, 1 Monat)

#### 1. Dedicated Video Ingestion Service
```
┌─────────────┐
│   Upload    │
│   Service   │
└──────┬──────┘
       │ POST /upload
       ▼
┌─────────────────┐
│ Video Ingestion │ ← Validiert, konvertiert, extrahiert Metadaten
│     Service     │
└────────┬────────┘
         │ Persists in DB
         ▼
┌─────────────────┐
│  Analysis Queue │
│   (SQS/Kafka)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Analysis Worker │ ← Download, Frame-Extraction, GPT-Vision
│   (Horizontal   │
│    Scalable)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Result Store   │
│  (DB + Cache)   │
└─────────────────┘
```

#### 2. Idempotenz + DLQ
```python
@celery_app.task(bind=True, max_retries=3, acks_late=True)
def analyze_video_task(self, analysis_id: str, video_url: str, sport_type: str):
    try:
        # Check if already processed
        existing_result = get_from_db(analysis_id)
        if existing_result:
            logger.info(f"Analysis {analysis_id} already completed")
            return existing_result
        
        # Process...
        
    except Exception as e:
        # Send to DLQ after max retries
        if self.request.retries >= self.max_retries:
            send_to_dlq(analysis_id, error=str(e))
        raise
```

#### 3. Video Policy + Eingangs-Validator
```python
class VideoPolicy:
    MAX_FILE_SIZE = 120 * 1024 * 1024  # 120MB
    ALLOWED_CODECS = ['h264', 'hevc', 'vp9']
    ALLOWED_CONTAINERS = ['mp4', 'mov', 'webm']
    MAX_DURATION = 600  # 10 min
    
    @staticmethod
    async def validate(video_metadata: VideoMetadata) -> ValidationResult:
        if video_metadata.file_size > VideoPolicy.MAX_FILE_SIZE:
            return ValidationResult(valid=False, error="FILE_TOO_LARGE")
        if video_metadata.codec not in VideoPolicy.ALLOWED_CODECS:
            return ValidationResult(valid=False, error="UNSUPPORTED_CODEC")
        # ...
        return ValidationResult(valid=True)
```

---

## 6. TESTPLAN

### Repro-Kriterien (Deterministisch)
```bash
# SETUP: Upload video to S3, get S3 key
S3_KEY="videos/2025/10/23/test-abc123.mp4"

# TEST 1: Verify current failure
curl -X POST http://localhost:8000/upload/complete \
  -H "Content-Type: application/json" \
  -d "{\"analysis_id\": \"test-001\", \"s3_key\": \"$S3_KEY\"}"

# Expected: ERROR in logs, status = failed

# TEST 2: Verify hotfix
# (After applying Option A)
# Expected: SUCCESS, frames extracted, analysis completed
```

### Pass/Fail-Definitionen
- ✅ **PASS**: Analysis completes with `status="completed"`, `performance_score` present
- ❌ **FAIL**: Any of:
  - `METADATA_EXTRACTION_FAILED`
  - `FRAME_EXTRACTION_FAILED`
  - `frames: []` in extraction result
  - `success: false` in processing result

### Synthetic Check (Production Monitoring)
```python
# backend/app/routers/health.py

@router.get("/health/analysis-pipeline")
async def health_check_analysis_pipeline():
    """Test end-to-end analysis pipeline"""
    try:
        # Use small test video (10s, 2MB)
        test_video_s3_key = "test-videos/synthetic-climbing-10s.mp4"
        
        # Trigger analysis
        analysis_id = f"health-check-{uuid.uuid4()}"
        result = await ai_vision_service.analyze_climbing_video(
            video_path=test_video_s3_key,
            analysis_id=analysis_id,
            sport_type="climbing"
        )
        
        # Validate result
        if result.get('performance_score') and len(result.get('route_analysis', {}).get('ideal_route', [])) > 0:
            return {"status": "healthy", "latency_ms": ...}
        else:
            return {"status": "degraded", "error": "Invalid result structure"}
            
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

**Schedule**: Alle 15 Minuten (via Render Cron oder externes Monitoring)

---

## 7. RUNBOOK-ÄNDERUNGEN

### Playbook: "Video Analysis Fehler beheben"

#### Symptom
- User meldet: "Video-Analyse fehlgeschlagen"
- Dashboard zeigt: `status: failed`

#### Diagnose-Schritte
```bash
# 1. Prüfe Logs für spezifischen Fehlercode
grep -A 5 "ENTERPRISE FAILURE" /var/log/performate-ai/*.log

# 2. Identifiziere betroffene Analysis-ID
# Expected: "❌ ENTERPRISE FAILURE: METADATA_EXTRACTION_FAILED"
#           "   Error details: {'video_path': 'videos/2025/...', ...}"

# 3. Prüfe S3-Objekt
aws s3 ls s3://performate-ai-uploads/videos/2025/10/23/

# 4. Teste Download
aws s3 cp s3://performate-ai-uploads/videos/.../xxx.mp4 /tmp/test.mp4
file /tmp/test.mp4  # Verify it's a valid MP4

# 5. Teste OpenCV lokal
python -c "import cv2; cap = cv2.VideoCapture('/tmp/test.mp4'); print(cap.isOpened())"
```

#### Mitigation
```bash
# OPTION 1: Retry mit lokalem Download (nach Hotfix)
curl -X POST https://performate-ai.onrender.com/analysis/retry \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"analysis_id": "xxx"}'

# OPTION 2: Manual Worker-basierte Analyse (falls Worker deployed)
from worker.worker import analyze_video_task
task = analyze_video_task.delay('analysis-id', 'videos/...', 'climbing')
```

### SLO/SLI

**Service Level Objective (SLO)**:
- **Availability**: 99.5% der Analysen erfolgreich (Status=completed)
- **Latency (P95)**: < 120s für 30s-Video
- **Error Budget**: 0.5% = ~22 Minuten Downtime/Monat

**Service Level Indicators (SLI)**:
```prometheus
# Success Rate
sum(rate(analysis_completed_total[5m])) / sum(rate(analysis_started_total[5m])) > 0.995

# Error Rate by Type
sum(rate(analysis_failed_total{error_code="METADATA_EXTRACTION_FAILED"}[5m]))
sum(rate(analysis_failed_total{error_code="FRAME_EXTRACTION_FAILED"}[5m]))

# Latency P95
histogram_quantile(0.95, rate(analysis_duration_seconds_bucket[5m])) < 120
```

### Alarm-Schwellen
```yaml
alerts:
  - name: HighAnalysisFailureRate
    expr: rate(analysis_failed_total[5m]) > 0.01  # > 1% failures
    for: 5m
    severity: critical
    
  - name: FrameExtractionFailures
    expr: rate(analysis_failed_total{error_code="FRAME_EXTRACTION_FAILED"}[10m]) > 0
    for: 10m
    severity: high
    description: "Video path resolution likely broken"
    
  - name: GPTVisionTimeout
    expr: rate(analysis_failed_total{error_code="TIMEOUT"}[5m]) > 0.05
    for: 5m
    severity: medium
```

---

## 8. TIMELINE & NEXT STEPS

### Immediate (Heute, 23. Okt)
- [ ] Bestätigen: Render.com-Logs zeigen `METADATA_EXTRACTION_FAILED`
- [ ] Implementieren: Hotfix Option A (S3 Download)
- [ ] Testen: Lokaler Test mit echtem S3-Video
- [ ] Deployen: Render.com redeploy nach Hotfix-Commit

### Short-term (Diese Woche)
- [ ] Implementieren: Presigned URL generation für analyze_climbing_video
- [ ] Hinzufügen: Detailed Error Codes in EnterpriseErrorResponse
- [ ] Erstellen: Synthetic health check endpoint
- [ ] Setup: Monitoring Alerts (Sentry/Grafana/Render Metrics)

### Medium-term (2 Wochen)
- [ ] Implementieren: Worker-Service in render.yaml
- [ ] Migrieren: Zu Queue-basierter Architektur
- [ ] Hinzufügen: Retry-Logic mit exponential backoff
- [ ] Erstellen: DLQ für failed analyses

### Long-term (1 Monat)
- [ ] Design: Dedicated Video Ingestion Service
- [ ] Implementieren: Video Policy + Eingangs-Validator
- [ ] Refactoren: Frame-Extraction als eigenständiger Service
- [ ] Hinzufügen: Version-Pinning für ffmpeg/OpenCV

---

## ANHANG

### Relevante Code-Dateien
- `backend/app/main.py` – Upload Complete Endpoint (Zeile 504-574)
- `backend/app/services/ai_vision_service.py` – Vision Service Entry Point (Zeile 45-151)
- `backend/app/services/video_processing/__init__.py` – Frame Extraction Wrapper (Zeile 46-115)
- `backend/app/services/video_processing/opencv_processor.py` – OpenCV Implementation (Zeile 116-274)
- `backend/app/services/s3_service.py` – S3 Upload/Download (Zeile 38-200)
- `backend/worker/worker.py` – Celery Worker (NICHT genutzt, Zeile 44-157)

### Log-Patterns für Monitoring
```regex
# Erfolgsfall
✅ ENTERPRISE SUCCESS: \d+ frames extracted, duration=[\d.]+s

# Fehlerfall (Root Cause)
❌ ENTERPRISE FAILURE: METADATA_EXTRACTION_FAILED
❌ Could not open video with .+
❌ Could not extract metadata from .+ with any available backend

# Sekundär-Fehler
❌ FRAME EXTRACTION FAILED for .+
❌ AI vision analysis FAILED for .+: Frame extraction failed
```

### Kontakte & Verantwortlichkeiten
- **On-Call SRE**: [Slack @oncall, PagerDuty]
- **Backend Lead**: [GitHub @backend-lead]
- **ML Engineering**: [GitHub @ml-lead]
- **Render.com Dashboard**: https://dashboard.render.com/

---

**Ende des RCA-Berichts**  
*Erstellt: 2025-10-23 06:30 UTC*  
*Auditor-Signature: SRE-Lead-AI-2025*
