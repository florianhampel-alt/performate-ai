# 🚀 Performate AI - Professional Development Environment

Ein vollständig integriertes Entwicklungssetup mit automatischer Umgebungsverwaltung, persistenten Sessions und umfassendem Logging.

## ⚡ Quick Start

```bash
# 1. Ins Projektverzeichnis wechseln (direnv lädt automatisch alle Variablen)
cd /path/to/performate-ai

# 2. Entwicklungsumgebung starten
pa-start

# 3. Services starten
pa-up
```

## 🛠️ Komponenten

### 1. **direnv** - Automatische Umgebungsvariablen
- Lädt automatisch `.env` Datei beim Betreten des Projektverzeichnisses
- Setzt Docker-Pfade, OpenAI Keys, und alle Projekteinstellungen
- Aktiviert projekt-spezifische Aliases und Funktionen

### 2. **tmux** - Persistente Sessions
- **Session**: `performate-ai` - Hauptentwicklungsumgebung
- **Windows**:
  - `main` - Hauptarbeitsfenster
  - `backend` - Backend-Entwicklung (gesplittet: Code | Server)
  - `frontend` - Frontend-Entwicklung (gesplittet: Code | Dev Server)
  - `services` - Docker-Services (gesplittet: Status | Logs)
  - `logs` - Log-Monitoring (4-fach gesplittet für verschiedene Streams)

### 3. **Automatisches Logging**
- **tmux-Logs**: `logs/tmux/` - Alle Terminal-Sessions werden aufgezeichnet
- **Shell-History**: `logs/.zsh_history` - Erweiterte Befehlshistorie
- **Docker-Logs**: Automatische Container-Log-Erfassung
- **Application-Logs**: `logs/application/` - App-spezifische Logs

### 4. **Warp-Integration**
- Vordefinierte Workflows für häufige Entwicklungsaufgaben
- Ein-Klick-Zugriff auf Status, Tests, und Deployments

## 📋 Verfügbare Kommandos

### Haupt-Commands
```bash
pa-start      # Startet/verbindet tmux-Session
pa-up         # Startet alle Docker-Services
pa-down       # Stoppt alle Services
pa-status     # Zeigt Service-Status
pa-logs       # Folgt allen Logs
pa-restart    # Startet Services neu
```

### Development-Commands
```bash
pa-test-backend   # Backend-Tests ausführen
pa-test-frontend  # Frontend-Tests ausführen
pa-lint          # Code formatieren und linten
pa-build         # Docker-Images bauen
```

## 🎯 Typischer Workflow

1. **Terminal öffnen** → direnv lädt automatisch alle Umgebungsvariablen
2. **`pa-start`** → Startet tmux mit allen Fenstern
3. **Ctrl+A + 2** → Wechsel zum Backend-Fenster
4. **Ctrl+A + 3** → Wechsel zum Frontend-Fenster
5. **Ctrl+A + 4** → Services-Management
6. **Ctrl+A + 5** → Log-Monitoring

## ⌨️ tmux Shortcuts

```bash
Ctrl+A + |    # Horizontaler Split
Ctrl+A + -    # Vertikaler Split
Ctrl+A + h/j/k/l  # Pane-Navigation
Ctrl+A + 1-5      # Window-Wechsel
Ctrl+A + r        # Config neu laden
```

## 📂 Projektstruktur

```
performate-ai/
├── .envrc                    # direnv-Konfiguration
├── .tmux.conf               # tmux-Konfiguration
├── .warp/workflows/         # Warp-Workflows
├── logs/
│   ├── tmux/               # tmux-Session-Logs
│   ├── docker/             # Docker-Container-Logs
│   ├── application/        # App-Logs
│   └── .zsh_history       # Projekt-Shell-History
├── backend/                # FastAPI Backend
├── frontend/               # Next.js Frontend
└── docker-compose.yml     # Service-Definition
```

## 🔄 Session-Persistierung

- **tmux-Sessions** überleben Terminal-Schließungen
- **docker compose** mit Volume-Persistierung
- **Logs** werden automatisch rotiert und archiviert
- **Shell-History** bleibt projekt-spezifisch erhalten

## 🧪 AI Vision Service Testing

Das Setup enthält spezielle Tests für die Enhanced AI Vision Service Features:

```bash
# In Warp: "AI Vision Service Test" Workflow ausführen
# Oder manuell:
cd backend
python3 -c "
# Tests für Wall Angle Extraction
# Tests für Move Count mit VISIBLE UNIQUE MOVES Priority
# Tests für Hold Analysis und Difficulty Indicators
"
```

## 🚨 Troubleshooting

### direnv nicht aktiv
```bash
direnv allow
```

### tmux Session verloren
```bash
pa-start  # Erstellt neue Session oder verbindet bestehende
```

### Docker-Services reagieren nicht
```bash
pa-down && pa-up  # Kompletter Neustart
```

### Logs zu groß
```bash
# Logs bereinigen
rm -rf logs/tmux/*
rm -rf logs/docker/*
```

## 📊 Monitoring & Debugging

- **Service-Status**: `pa-status` zeigt alle Container
- **Live-Logs**: `pa-logs` für Echtzeit-Monitoring
- **tmux-Navigation**: Schneller Zugriff auf alle Komponenten
- **History-Search**: Durchsuchbare Befehlshistorie per `Ctrl+R`

---

**💡 Tipp**: Dieses Setup stellt sicher, dass alle Entwicklungsinformationen persistent gespeichert und für AI-Assistenten zugänglich sind. Jede Entwicklungsaktivität wird protokolliert und kann für Kontext und Debugging verwendet werden.