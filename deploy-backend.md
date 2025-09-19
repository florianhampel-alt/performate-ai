# Backend Deployment Guide - CORS & Redis Fix

## 🚀 Problem behoben: CORS und Redis-Konfiguration

### 1. ✅ CORS-Problem gelöst
Die aktuelle Frontend-URL `https://frontend-khx7r2ks6-flos-projects-6a1ae6b3.vercel.app` wurde zur `allowed_origins` Liste hinzugefügt.

### 2. ✅ Redis-Konfiguration angepasst  
Wechsel von lokaler Redis-Instanz zu Upstash Redis (Cloud-Service) für bessere Skalierbarkeit.

---

## 📋 Deployment-Schritte

### Schritt 1: Upstash Redis einrichten
1. Gehen Sie zu [upstash.com](https://upstash.com) 
2. Erstellen Sie einen kostenlosen Account
3. Erstellen Sie eine neue Redis-Datenbank (Region: US-East-1 empfohlen)
4. Kopieren Sie die **REST URL** und **REST TOKEN**

### Schritt 2: Render.com Backend konfigurieren
1. Loggen Sie sich in Render.com ein
2. Gehen Sie zu Ihrem Backend-Service
3. Klicken Sie auf "Environment"
4. Fügen Sie folgende Umgebungsvariablen hinzu:

```bash
UPSTASH_REDIS_REST_URL=https://your-redis-instance.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-upstash-rest-token
DEBUG=false
```

### Schritt 3: Code deployen
```bash
# 1. Änderungen committen
git add .
git commit -m "Fix CORS configuration and Redis setup for production"

# 2. Pushen (falls GitHub-Token funktioniert)
git push origin main

# 3. Alternativ: Manuelles Deployment in Render
# - Gehen Sie zu Render Dashboard
# - Klicken Sie "Deploy latest commit" 
```

### Schritt 4: Installation der fehlenden Dependencies
Falls beim Backend-Start noch Python-Pakete fehlen:

```bash
# Lokal testen
cd backend
python3 -m pip install -r requirements.txt
python3 -m pip install upstash-redis

# Uvicorn starten
uvicorn app.main:app --host=0.0.0.0 --port=8000
```

---

## 🔧 Geänderte Dateien

### `backend/app/main.py`
- ✅ Frontend-URL zu CORS `allowed_origins` hinzugefügt
- ✅ Beide Debug- und Produktionsmodus berücksichtigt

### `render.yaml`  
- ✅ Redis-Konfiguration auf Upstash umgestellt
- ✅ Lokale Redis-Service entfernt

### `.env.production`
- ✅ Upstash Redis-Variablen dokumentiert
- ✅ Fallback auf lokale Redis für Development

---

## 🧪 Nach dem Deployment testen

### 1. Backend-Health-Check
```bash
curl https://performate-ai-backend.onrender.com/health
```

### 2. CORS-Test vom Frontend
```bash
curl -X OPTIONS https://performate-ai-backend.onrender.com/upload \
  -H "Origin: https://frontend-khx7r2ks6-flos-projects-6a1ae6b3.vercel.app" \
  -H "Access-Control-Request-Method: POST"
```

### 3. Upload-Endpoint testen  
```bash
curl -X POST https://performate-ai-backend.onrender.com/upload/init \
  -H "Content-Type: application/json" \
  -H "Origin: https://frontend-khx7r2ks6-flos-projects-6a1ae6b3.vercel.app" \
  -d '{"filename": "test.mp4", "content_type": "video/mp4", "file_size": 1000000}'
```

---

## 🔄 Falls weiterhin Probleme auftreten

### Redis-Connection-Check
1. Prüfen Sie die Upstash-Credentials in Render
2. Testen Sie die Redis-Verbindung:

```python
# Test-Skript
import os
from upstash_redis import Redis

redis_client = Redis(
    url=os.getenv('UPSTASH_REDIS_REST_URL'),
    token=os.getenv('UPSTASH_REDIS_REST_TOKEN')
)

# Test
redis_client.set('test', 'hello')
print(redis_client.get('test'))  # Should print 'hello'
```

### CORS-Debug
Überprüfen Sie die Render-Logs auf CORS-bezogene Nachrichten:
```bash
# In Render Dashboard -> Logs
# Suchen nach: "CORS" oder "Origin"
```

---

## 💡 Nächste Schritte

Nach erfolgreichem Deployment:
1. ✅ Frontend kann Videos hochladen
2. ✅ AI-Analyse funktioniert 
3. ✅ Redis-Caching aktiv
4. 🚀 **Produktionsbereit!**

Falls Sie Unterstützung beim Setup von Upstash Redis oder beim manuellen Deployment in Render benötigen, kann ich Ihnen gerne dabei helfen.