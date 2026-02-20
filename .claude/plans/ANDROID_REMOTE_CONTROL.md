# Claude Code Remote Control - Android App

## Vision
A mobile app that gives you **real-time visibility** into what Claude Code is doing and allows you to **send commands remotely** from your phone.

---

## Architecture Overview

```
┌─────────────────┐     WebSocket      ┌──────────────────┐     WebSocket     ┌─────────────────┐
│   Android App   │◄──────────────────►│   Relay Server   │◄─────────────────►│  Activity Agent │
│  (Your Phone)   │                    │  (FastAPI + WS)  │                   │ (This Machine)  │
└─────────────────┘                    └──────────────────┘                   └─────────────────┘
       │                                        │                                      │
       │ • Send commands                        │ • Route messages                     │ • Watch file changes
       │ • View live activity                   │ • Store history                      │ • Capture terminal output
       │ • Chat interface                       │ • Auth & sessions                    │ • Execute commands
       │ • Push notifications                   │ • Claude API proxy                   │ • Stream responses
       └────────────────────────────────────────┴──────────────────────────────────────┘
```

---

## Core Components

### 1. Activity Agent (Python - runs on dev machine)
**Location:** `backend/services/remote_agent/`

**Responsibilities:**
- Watch filesystem for changes (`watchdog` library)
- Monitor `.claude/AGENT_LOG.md` for agent activity
- Capture terminal/command output
- Connect to Relay Server via WebSocket
- Execute commands received from phone
- Stream Claude API responses back

**Key Events to Capture:**
```python
class ActivityEvent:
    type: Literal["file_change", "agent_log", "terminal", "task_status", "error"]
    timestamp: datetime
    agent: str | None  # Which agent is active
    data: dict  # Event-specific payload
```

### 2. Relay Server (FastAPI)
**Location:** `backend/services/relay_server/`

**Responsibilities:**
- WebSocket hub connecting all clients
- Authentication (API key or JWT)
- Message routing (phone ↔ dev machine)
- Command queue management
- Claude API integration (for remote chat)
- Session management

**Endpoints:**
```
WS  /ws/activity     - Real-time activity stream
WS  /ws/chat         - Chat with Claude
POST /api/command    - Send command (fallback)
GET  /api/history    - Activity history
GET  /api/status     - Current agent status
```

### 3. Android App (Kotlin + Jetpack Compose)
**Location:** `android/claude-remote/`

**Features:**

#### Screen 1: Live Activity Feed
```
┌────────────────────────────────────┐
│ 🟢 Claude Code - Live             │
├────────────────────────────────────┤
│ ⚡ Builder modifying auth.py       │
│    └─ Lines 45-67 updated         │
│                                    │
│ 📁 File saved: auth.py            │
│                                    │
│ ✅ Task: "Add login endpoint"      │
│    Status: COMPLETED              │
│                                    │
│ 🔄 Overseer delegating to...      │
│    Visualizer                      │
│                                    │
│ 📝 Creating: LoginForm.tsx        │
└────────────────────────────────────┘
```

#### Screen 2: Chat/Command Interface
```
┌────────────────────────────────────┐
│ 💬 Command Center                 │
├────────────────────────────────────┤
│                                    │
│ You: Add dark mode to the app     │
│                                    │
│ 🤖 Overseer: Analyzing task...    │
│ Delegating to Visualizer for UI   │
│ and Builder for state management. │
│                                    │
│ [See Live Progress →]             │
│                                    │
├────────────────────────────────────┤
│ [________________] [Send]         │
│                                    │
│ Quick: [Build] [Test] [Deploy]    │
└────────────────────────────────────┘
```

#### Screen 3: Project Dashboard
```
┌────────────────────────────────────┐
│ 📊 Project Status                 │
├────────────────────────────────────┤
│ Active Agent: Visualizer          │
│ Current Task: Dark mode toggle    │
│ Files Changed: 3                  │
│ Tests: ✅ 47 passing              │
│                                    │
│ Recent Activity:                  │
│ • LoginForm.tsx created           │
│ • theme.ts modified               │
│ • 2 new components added          │
└────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Activity Agent | Python 3.11 + `watchdog` + `websockets` | Same stack as backend, easy integration |
| Relay Server | FastAPI + WebSockets | Already using FastAPI, native async |
| Android App | Kotlin + Jetpack Compose | Modern Android, reactive UI |
| Real-time | WebSockets | Bidirectional, low latency |
| State | Zustand (if React) / StateFlow (Android) | Simple, reactive |
| Auth | JWT + API Key | Secure remote access |
| Notifications | Firebase Cloud Messaging | Push when tasks complete |

---

## Implementation Phases

### Phase 1: Activity Agent (Foundation)
**Deliverables:**
- [ ] File watcher service (`watchdog`)
- [ ] AGENT_LOG.md parser and monitor
- [ ] WebSocket client to relay server
- [ ] Activity event schema
- [ ] Local testing mode

**Files:**
```
backend/services/remote_agent/
├── __init__.py
├── watcher.py          # File system monitoring
├── log_parser.py       # Parse AGENT_LOG.md
├── ws_client.py        # WebSocket connection
├── events.py           # Event types/schema
└── agent.py            # Main entry point
```

### Phase 2: Relay Server
**Deliverables:**
- [ ] WebSocket hub (activity + chat channels)
- [ ] Authentication middleware
- [ ] Claude API integration
- [ ] Command queue
- [ ] Activity history storage

**Files:**
```
backend/services/relay_server/
├── __init__.py
├── main.py             # FastAPI app
├── ws_hub.py           # WebSocket manager
├── auth.py             # JWT/API key auth
├── claude_proxy.py     # Anthropic API wrapper
├── models.py           # Pydantic schemas
└── storage.py          # Activity history (SQLite/Redis)
```

### Phase 3: Android App (MVP)
**Deliverables:**
- [ ] Project setup (Kotlin + Compose)
- [ ] WebSocket connection manager
- [ ] Live activity feed screen
- [ ] Basic chat interface
- [ ] Connection status indicator

**Files:**
```
android/claude-remote/
├── app/src/main/java/com/astats/clauderemote/
│   ├── MainActivity.kt
│   ├── ui/
│   │   ├── screens/ActivityFeedScreen.kt
│   │   ├── screens/ChatScreen.kt
│   │   ├── screens/DashboardScreen.kt
│   │   └── components/
│   ├── data/
│   │   ├── WebSocketManager.kt
│   │   ├── ActivityRepository.kt
│   │   └── models/
│   └── viewmodel/
│       ├── ActivityViewModel.kt
│       └── ChatViewModel.kt
└── build.gradle.kts
```

### Phase 4: Enhanced Features
**Deliverables:**
- [ ] Push notifications (Firebase)
- [ ] Quick command buttons
- [ ] File diff viewer
- [ ] Voice commands (speech-to-text)
- [ ] Dark/light theme
- [ ] Offline queue (send when reconnected)

### Phase 5: Security & Polish
**Deliverables:**
- [ ] End-to-end encryption
- [ ] Biometric auth on app
- [ ] Rate limiting
- [ ] Error recovery
- [ ] Battery optimization

---

## Data Flow: Sending a Command

```
1. User types "Add dark mode" in Android app
   │
2. App sends via WebSocket to Relay Server
   │  { "type": "command", "text": "Add dark mode", "session": "abc123" }
   │
3. Relay Server receives and forwards to Activity Agent
   │
4. Activity Agent writes to command queue file OR
   calls Claude API directly with project context
   │
5. Claude processes command, starts working
   │
6. Activity Agent detects:
   │  - File changes (watchdog)
   │  - AGENT_LOG.md updates
   │  - Terminal output
   │
7. Events streamed back through Relay → Android app
   │
8. User sees live updates on phone! 📱
```

---

## Security Considerations

1. **Authentication:**
   - API key generated on first setup
   - JWT tokens with expiration
   - Device binding (optional)

2. **Transport:**
   - WSS (WebSocket Secure) only
   - TLS 1.3 minimum

3. **Commands:**
   - Command allowlist (optional safety mode)
   - Confirmation for destructive operations
   - Audit log of all commands

4. **Network:**
   - Relay server can run locally (same network)
   - Or cloud-hosted with proper auth
   - Ngrok/Cloudflare tunnel for remote access

---

## Quick Start Commands

```bash
# Start Activity Agent (on dev machine)
python -m backend.services.remote_agent.agent

# Start Relay Server
uvicorn backend.services.relay_server.main:app --reload

# Build Android APK
cd android/claude-remote && ./gradlew assembleDebug
```

---

## Success Metrics

- [ ] Can see file changes within 500ms on phone
- [ ] Can send command and see response stream
- [ ] Works over mobile network (not just WiFi)
- [ ] Battery drain < 5% per hour when monitoring
- [ ] Reconnects automatically after network loss

---

## Next Steps

1. **Approve this plan** - Ready to start building?
2. **Choose hosting** - Local only or cloud relay?
3. **Security level** - Basic auth or full encryption?
4. **MVP scope** - Start with just activity feed, or include chat?

