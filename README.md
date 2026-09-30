# FieldVoice

## Talk while you work.

FieldVoice is a hands-free AI copilot for industrial and HVAC equipment inspections that allows technicians to speak observations naturally instead of stopping to type them manually. Built on the AssemblyAI Voice Agent API, FieldVoice runs in the technician's browser, connects via low-latency WebSocket audio streaming, extracts structured inspection checkpoints from conversational speech, validates measurements deterministically against PostgreSQL operating limits, generates maintenance tickets and safety alerts, and produces verifiable inspection reports.

---

## Problem

Field technicians working in mechanical rooms, chiller plants, and rooftop HVAC units face significant data-entry obstacles:
- **Work Interruption**: Technicians work with tools, gauges, and safety gloves. Stopping to remove gloves, tap greasy tablet screens, or write on paper forms interrupts inspection flow and attention.
- **Data Latency & Incomplete Checkpoints**: Technicians often write shorthand numbers on notepads and enter them hours later into a CMMS, resulting in forgotten readings and missing required checkpoints.
- **Delayed Maintenance & Safety Action**: When out-of-range readings or safety hazards are written on paper drafts, they sit unnoticed until the end of the shift rather than triggering immediate maintenance action.
- **Disconnected Evidence**: Traditional forms record only a single static number without preserving what the technician actually observed or stated during the inspection.

---

## Solution

FieldVoice transforms equipment inspections into a natural spoken dialogue while grounding all operational data in an authoritative backend:

```
Technician speaks naturally
       ↓
AssemblyAI Voice Agent API
       ↓
JSON-Schema Tool Calling
       ↓
Flask Backend
       ↓
PostgreSQL Database
       ↓
Deterministic Limits Validation
       ↓
Automated Tickets & Safety Actions
       ↓
Comprehensive Inspection Report
```

Spoken observations are converted into structured inspection data while preserving verbatim evidence text, audio timestamps, and extraction confidence.

---

## Key Features

- **Real-Time Voice Interaction**: Low-latency bi-directional voice streaming over a single WebSocket connection using the AssemblyAI Voice Agent API.
- **Natural Multi-Observation Capture**: Technicians can speak multiple inspection checkpoints in a single sentence (e.g. *"Temperature is 40 degrees Celsius, pressure is 137 PSI, vibration is normal, and I don't see any leakage."*), and the agent invokes tools for each observation independently.
- **Inspection Lifecycle Management**: Create, load, update, and complete inspections tied to specific industrial equipment assets.
- **Equipment Profile Lookup**: Instant access to equipment metadata, location, required checkpoints, and operating limits.
- **Structured Observation Storage**: Records observations with typed values, standardized units, verbatim evidence text, source timestamps, and extraction confidence.
- **Deterministic Limits Validation**: The backend evaluates readings against equipment operating limits stored in PostgreSQL; the LLM is never permitted to guess or invent threshold decisions.
- **Observation Correction Loop**: Recognizes natural corrections (*"Actually, correct that. Pressure is 96 PSI."*) without requiring the technician to re-state the field name, updating the active checklist while retaining historical evidence.
- **Smart Clarification**: Asks targeted questions only when spoken input is genuinely ambiguous (e.g. *"Pressure is about ninety"* ➔ *"90 PSI, correct?"*) without guessing units.
- **Natural Status Voice Commands**: Technicians can ask *"What have I recorded so far?"*, *"What's still missing?"*, or *"What did I say for pressure?"* to get concise verbal summaries.
- **Automated Maintenance Tickets**: Automatically flags out-of-range measurements and enables voice-driven creation of maintenance tickets.
- **Automated Safety Alerts**: Immediate detection of hazardous conditions (smoke, gas leak, extreme overpressure) with immediate incident logging.
- **Voice Interruption & Barge-In**: Web Audio Worklet and AssemblyAI Voice Activity Detection (VAD) immediately flush audio playback when the technician speaks.
- **Live Activity & Event Display**: Real-time visual timeline showing spoken events, tool executions, and backend validations as they occur.
- **Integrated Inspection Reports**: Generates complete inspection summaries with equipment specs, findings, tickets, alerts, and verbatim evidence trails.

---

## AssemblyAI Integration

FieldVoice integrates directly with **AssemblyAI's Voice Agent API** using real-time WebSockets:

- **Endpoint**: `wss://agents.assemblyai.com/v1/ws`
- **Audio Format**: 24 kHz mono PCM16 raw audio stream captured via browser Web Audio API (`AudioWorkletNode`).
- **Secure Ephemeral Authentication**: The permanent `ASSEMBLYAI_API_KEY` is kept strictly on the Flask backend. Before opening the WebSocket, the browser calls `GET /api/voice-token` on the backend, which requests a single-use temporary token (`expires_in_seconds=300`) from AssemblyAI (`https://agents.assemblyai.com/v1/token`). The browser connects using this temporary token, ensuring server secrets are never exposed in client code.
- **Session Lifecycle Protocol**:
  - `session.update`: Frontend sends system instructions, active equipment context, turn detection parameters, key terms, voice persona, and JSON-schema tools upon connection.
  - `session.ready` / `session.updated`: Acknowledged by AssemblyAI once configuration and tools are registered; prompts the client to start microphone streaming.
  - `input.audio`: Client streams continuous base64-encoded PCM16 audio chunks to AssemblyAI.
  - `reply.audio`: AssemblyAI streams synthesized speech back to the browser for real-time playback via Web Audio API.
  - `SpeechStarted` / Interruption: AssemblyAI signals when the user starts speaking, enabling client-side barge-in by immediately muting and clearing pending audio buffers.
- **JSON-Schema Tool Calling**:
  - AssemblyAI sends `tool.call` events containing `call_id`, `tool_name`, and arguments.
  - The client executes the tool against the Flask backend API.
  - The client sends back `tool.result` containing the authoritative backend response and `call_id`.

---

## Tech Stack

### Frontend
- **Framework**: React 19 (`react` 19.2.8, `react-dom` 19.2.8)
- **Build Tool**: Vite 8 (`vite` 8.3.0)
- **Styling**: Vanilla CSS with modern dark mode design tokens & TailwindCSS 4
- **Audio Processing**: Browser Web Audio API (`AudioContext`, `AudioWorkletNode`, `navigator.mediaDevices.getUserMedia`)
- **Hosting**: Vercel (SPA routing configured in `vercel.json`)

### Backend
- **Language**: Python 3.10+
- **Framework**: Flask 3.1.3
- **CORS Support**: Flask-CORS 6.0.5
- **WSGI Production Server**: Gunicorn 26.2.0
- **Database Driver**: psycopg2-binary 2.9.13 (Threaded connection pool with auto-reconnect)
- **HTTP Client**: requests 2.34.2
- **Configuration**: python-dotenv 1.2.3
- **Hosting**: Render (Python Web Service)

### Voice & AI
- **Voice Agent**: AssemblyAI Voice Agent API (WebSocket, PCM16, Tool Calling, VAD)

### Database
- **Engine**: PostgreSQL (Hosted on Supabase in production, local PostgreSQL in development)

---

## Architecture

```
                    Technician (Microphone / Speaker)
                                  │
                                  ▼
                     React 19 Frontend (Vite)
             ├── Web Audio API (24 kHz PCM16 Stream)
             ├── AudioWorkletNode & Barge-In Handler
             └── Voice Agent State Machine
                  │                      │
   Audio Stream / │                      │ REST API Calls
   Tool Calls     │                      │ (/api/*)
                  ▼                      ▼
    AssemblyAI Voice Agent ◄─────── Flask Backend (Gunicorn)
    (wss://agents.assemblyai.com)    ├── /api/voice-token (Ephemeral Token)
                                     ├── Equipment Tools
                                     ├── Observation Tools
                                     ├── Deterministic Validation
                                     ├── Ticket & Alert Tools
                                     └── Report Generator
                                                │
                                                ▼
                                    PostgreSQL Database (Supabase)
                                     ├── equipment
                                     ├── inspections
                                     ├── observations (with evidence)
                                     ├── maintenance_tickets
                                     └── safety_alerts
```

### Layer Responsibilities
1. **Frontend**: Captures microphone audio, streams raw PCM chunks, handles audio playback, coordinates tool execution callbacks, and renders the real-time UI.
2. **AssemblyAI**: Performs real-time speech recognition, natural language reasoning, intent parsing, tool call generation, and voice synthesis.
3. **Flask Backend**: Serves as the authoritative business layer. Generates ephemeral voice tokens, enforces deterministic limits validation, isolates inspection contexts, and manages database persistence.
4. **PostgreSQL**: Stores persistent equipment specifications, operating ranges, inspections, verbatim evidence, maintenance tickets, and safety incidents.

---

## Voice Agent Workflow

```
1. Technician opens an equipment inspection (e.g. AC-001).
   ↓
2. Backend creates or loads the active inspection record.
   ↓
3. Frontend requests an ephemeral token from GET /api/voice-token.
   ↓
4. Browser establishes WebSocket session with AssemblyAI Voice Agent API.
   ↓
5. Browser sends session.update with active equipment context and registered tools.
   ↓
6. Technician speaks naturally while performing physical work.
   ↓
7. AssemblyAI interprets spoken intent and issues structured tool.call events.
   ↓
8. Frontend forwards tool calls to the Flask backend API.
   ↓
9. Backend saves observation and deterministically evaluates reading against operating limits.
   ↓
10. If reading is out-of-range or hazard detected, backend creates tickets/alerts.
    ↓
11. Tool result is returned to AssemblyAI; voice agent verbally confirms action to technician.
    ↓
12. Technician can query status ("What's missing?") or correct readings ("Pressure is 96 PSI").
    ↓
13. Technician completes the inspection verbally or via UI; final report is compiled.
```

---

## Backend Tools

FieldVoice registers 6 function tools with the AssemblyAI Voice Agent:

| Tool Name | Purpose | Data Read / Written |
| :--- | :--- | :--- |
| `get_equipment_profile` | Retrieves metadata, specs, operating limits, and required fields for a specified asset code. | **Reads**: `equipment` table by `asset_code`. |
| `save_observation` | Stores an observed reading with verbatim evidence text, timestamp, and confidence, running deterministic validation. | **Reads**: `equipment.operating_limits`.<br>**Writes**: `observations` table. |
| `get_inspection_status` | Returns active inspection progress, completed checkpoints, missing required fields, and out-of-range observations. | **Reads**: `inspections`, `equipment`, and `observations`. |
| `create_maintenance_ticket` | Creates a tracked maintenance work order for equipment defects or out-of-range readings. Idempotent. | **Writes**: `maintenance_tickets` table. |
| `create_safety_alert` | Logs an urgent safety hazard (overpressure, gas leak, electrical hazard, fire risk). Idempotent. | **Writes**: `safety_alerts` table. |
| `complete_inspection` | Validates completion criteria and transitions the inspection status from `started` to `completed`. | **Writes**: Updates `inspections.status` and `completed_at`. |

---

## Validation

FieldVoice enforces **deterministic, backend-authoritative validation**. The LLM voice agent is never allowed to invent operating thresholds or decide whether a measurement is safe.

Operating limits are stored as structured JSONB in PostgreSQL. When an observation is saved:
1. The backend parses the field name and unit (e.g. `temperature` in `C`, `pressure` in `PSI`).
2. The numeric value is compared strictly against the configured `min` and `max` limits.
3. The observation status is classified deterministically as `normal` or `out_of_range`.

### Concrete Example (Equipment AC-001)
Operating limits configured for AC-001 (Main Lobby Air Handler):
- **Temperature**: 0 °C to 60 °C
- **Pressure**: 40 PSI to 100 PSI

```
Technician says: "Pressure is 137 PSI."
➔ Backend evaluation: 137 > 100 PSI
➔ Status: out_of_range
➔ Action: Observation flagged, automated maintenance ticket created.

Technician says: "Actually, correct that. Pressure is 96 PSI."
➔ Backend evaluation: 40 <= 96 <= 100 PSI
➔ Status: normal
➔ Action: New observation saved; active checklist reflects normal status.
```

**Correction Semantics**: The latest observation for a given field name governs the current inspection state, while all prior historical observations and verbatim audio transcripts are preserved for traceability.

---

## Evidence & Traceability

Every measurement recorded in FieldVoice is anchored to the technician's actual spoken statement:

```
Spoken Audio ➔ Transcript Evidence ➔ Structured Observation ➔ Validation ➔ Audit Report
```

Each record in the `observations` table captures:
- `evidence_text`: The verbatim sentence spoken by the technician (e.g. *"Pressure is 137 PSI on the discharge gauge"*).
- `source_timestamp`: The elapsed audio stream timestamp (in seconds) where the statement occurred.
- `confidence`: Extraction confidence score (0.0 to 1.0).
- `created_at`: Exact database timestamp of record insertion.

This guarantees that every recorded value on an inspection report can be traced back to the technician's original spoken words.

---

## Database

The PostgreSQL schema consists of 5 core relational tables defined in [backend/database/schema.sql](file:///d:/fieldport/backend/database/schema.sql):

- **`equipment`**: Equipment registry containing asset tags, equipment types, physical locations, required inspection fields (`JSONB`), and operating limit thresholds (`JSONB`).
- **`inspections`**: Inspection sessions linked to equipment assets, tracking status (`started`, `completed`, `cancelled`), start/completion timestamps, and summary notes.
- **`observations`**: Granular measurement records linked to inspections, capturing field names, values, units, verbatim `evidence_text`, `source_timestamp`, and `confidence`.
- **`maintenance_tickets`**: Work orders generated for equipment defects or out-of-range observations, tracking issue descriptions, priorities (`low`, `medium`, `high`, `critical`), and statuses (`open`, `in_progress`, `resolved`).
- **`safety_alerts`**: Immediate hazardous safety conditions identified during inspections, tracking hazard descriptions, severity ratings, evidence text, and resolution timestamps.

---

## Project Structure

```
fieldport/
├── frontend/
│   ├── public/                 # Static assets and favicon
│   ├── src/
│   │   ├── components/         # UI components and VoiceTestPanel
│   │   ├── services/
│   │   │   ├── agentConfig.js  # Voice Agent prompts, tools, and VAD config
│   │   │   ├── api.js          # REST API client with URL sanitization
│   │   │   └── voiceAgent.js   # AssemblyAI WebSocket & Web Audio manager
│   │   ├── App.jsx             # Main application layout, routing, and UI
│   │   ├── index.css           # Design tokens, typography, and styling
│   │   └── main.jsx            # Application entry point
│   ├── package.json            # Frontend dependencies (React 19, Vite 8)
│   ├── vercel.json             # Vercel SPA routing configuration
│   └── vite.config.js          # Vite build configuration
├── backend/
│   ├── database/
│   │   ├── connection.py       # Thread-safe PostgreSQL connection pool
│   │   ├── schema.sql          # Authoritative DDL schema
│   │   └── seed.py             # 20 industrial demo equipment assets
│   ├── models/                 # Database data access objects
│   ├── routes/                 # Flask route blueprints (health, voice, equipment, etc.)
│   ├── services/               # Business logic, validation, and token generator
│   ├── tools/                  # Function tool execution handlers
│   ├── app.py                  # Flask application factory and root API index
│   ├── config.py               # Environment configuration and validation
│   └── requirements.txt        # Python dependencies (Flask, Gunicorn, psycopg2)
├── docs/
│   ├── architecture.md         # System architecture specification
│   └── deployment_guide.md     # Production deployment instructions
├── .env.example                # Environment configuration template
├── .gitignore                  # Git exclusion rules
├── LICENSE                     # MIT License
├── README.md                   # Project documentation
└── render.yaml                 # Render Blueprint configuration
```

---

## Setup Instructions

### Prerequisites
- **Node.js**: v18.0.0 or higher
- **Python**: v3.10 or higher
- **PostgreSQL**: v14.0 or higher (or a free Supabase project)
- **AssemblyAI API Key**: Obtainable from [assemblyai.com](https://www.assemblyai.com/)

---

### 1. Clone Repository

```bash
git clone https://github.com/ikavin04/FieldAssembly.git
cd FieldAssembly
```

---

### 2. Backend Setup

```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
```

---

### 3. Environment Configuration

Copy the template to create your backend configuration:

```bash
# In backend/ directory:
cp ../.env.example .env
```

Edit `backend/.env`:
```ini
ASSEMBLYAI_API_KEY=your_actual_assemblyai_api_key
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/fieldvoice
FLASK_ENV=development
SECRET_KEY=dev-secret-key-fieldvoice
FRONTEND_ORIGIN=http://localhost:5173
```

---

### 4. PostgreSQL Setup

Create the local database and run the schema:

```bash
# Create database (if not exists)
psql -U postgres -c "CREATE DATABASE fieldvoice;"

# Apply authoritative schema
psql -U postgres -d fieldvoice -f database/schema.sql

# Seed 20 industrial demo equipment assets
python -m database.seed
```

---

### 5. Start Backend

```bash
# From backend/ directory with venv activated:
python app.py
```
*Backend will be running at `http://127.0.0.1:5000`.*

---

### 6. Start Frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```
*Frontend dev server will be running at `http://localhost:5173`.*

---

### 7. Open Application

Navigate to **`http://localhost:5173`** in Google Chrome or Microsoft Edge (ensure microphone permissions are granted).

---

## Demo Walkthrough

Follow this step-by-step flow to demonstrate the live capabilities using **AC-001**:

1. **Select Asset**: Click on **Equipment** in the navigation bar and select **AC-001 (Main Lobby Air Handler)**.
2. **Start Inspection**: Click **Start Voice Inspection** and allow microphone access.
3. **Multi-Observation Voice Capture**:
   Speak naturally into your microphone:
   > *"Temperature is 40 degrees Celsius, pressure is 137 PSI, vibration is normal, and I don't see any leakage."*
4. **Observe Real-Time Extraction & Validation**:
   - The Live Activity timeline displays 4 tool executions.
   - Temperature (40 °C) validates as **normal** (range: 0–60 °C).
   - Pressure (137 PSI) deterministically validates as **out_of_range** (range: 40–100 PSI).
   - Vibration and leakage validate as **normal**.
   - A maintenance ticket is automatically queued for the high-pressure reading.
5. **Correction Loop**:
   Speak a natural correction:
   > *"Actually, correct that. The pressure is 96 PSI."*
   - FieldVoice updates the observation to 96 PSI.
   - Pressure validation status immediately updates to **normal**.
6. **Hands-Free Status Query**:
   Ask the assistant:
   > *"What have I recorded so far?"*
   - The assistant verbally summarizes the recorded observations.
7. **Complete Inspection**:
   Say:
   > *"Complete the inspection."*
   - The assistant confirms completion and transitions the inspection status.
8. **View Report**:
   Navigate to the generated report view to see the finalized findings, equipment details, and verbatim spoken evidence trail.

---

## Environment Variables

| Variable | Scope | Required | Description |
| :--- | :--- | :---: | :--- |
| `ASSEMBLYAI_API_KEY` | Backend | **Yes** | Secret AssemblyAI API key used strictly server-side for ephemeral token creation. |
| `DATABASE_URL` | Backend | **Yes** | PostgreSQL connection URI (supports local PostgreSQL and hosted Supabase pooler). |
| `FLASK_ENV` | Backend | No | Execution environment (`development` or `production`). Default: `development`. |
| `SECRET_KEY` | Backend | **Yes** (Prod) | Flask session encryption key. Must be set to a strong random secret in production. |
| `FRONTEND_ORIGIN` | Backend | No | Allowed frontend origin for CORS (e.g. `http://localhost:5173` or Vercel URL). |
| `VITE_API_BASE_URL` | Frontend | No | Base URL of the backend API (empty string in dev; Render URL in production). |

---

## API Overview

### Core & Health Endpoints
- `GET /` — Root API service status and endpoint directory.
- `GET /api/health` — Backend health check and database connectivity status.
- `GET /api/voice-token` — Generates a single-use ephemeral token for AssemblyAI WebSocket auth.

### Equipment & Dashboard
- `GET /api/equipment` — Lists all registered equipment assets with operating limits.
- `GET /api/equipment/:id` — Retrieves detailed specifications for a single equipment asset.
- `GET /api/dashboard/summary` — Returns active inspections, work orders, and safety alert statistics.

### Inspections & Observations
- `POST /api/inspections` — Initializes a new equipment inspection session.
- `GET /api/inspections/:id` — Fetches current inspection status, timestamps, and findings.
- `PATCH /api/inspections/:id/status` — Updates inspection lifecycle state.
- `POST /api/inspections/:id/complete` — Concludes the inspection and compiles final summary.
- `POST /api/observations` — Records a checkpoint reading with evidence text and validates limits.
- `GET /api/inspections/:id/observations` — Retrieves all observations associated with an inspection.

### Tickets, Alerts & Reports
- `GET /api/tickets` — Lists maintenance tickets (supports filtering by `inspection_id` and `status`).
- `POST /api/tickets` — Creates an explicit maintenance work order.
- `GET /api/safety-alerts` — Lists active safety hazards and alert incidents.
- `POST /api/safety-alerts` — Logs a safety condition requiring immediate intervention.
- `GET /api/reports/:id` — Generates comprehensive, verifiable inspection report payload.

### Function Tool Endpoints
- `POST /api/tools/get-equipment-profile` — Retrieves asset profile for tool calling.
- `POST /api/tools/save-observation` — Records observation and executes deterministic validation.
- `POST /api/tools/get-inspection-status` — Queries checklist completion and missing required fields.
- `POST /api/tools/create-maintenance-ticket` — Idempotent ticket creation tool.
- `POST /api/tools/create-safety-alert` — Idempotent safety alert tool.
- `POST /api/tools/complete-inspection` — Formally closes the inspection session.

---

## Hackathon Highlights

- **Real-Time Voice Architecture**: Uses AssemblyAI's low-latency Voice Agent API over WebSockets to enable genuine hands-free conversation in industrial environments.
- **Bi-Directional Tool Calling**: Implements bi-directional JSON-schema tools that empower the agent to query database state and trigger operational actions in real time.
- **Auditable Spoken Evidence**: Anchors every recorded measurement to verbatim spoken evidence, eliminating transcription discrepancies.
- **Deterministic Industrial Validation**: Protects physical equipment by enforcing strict backend limits validation rather than relying on non-deterministic LLM calculations.
- **Production-Hardened Deployment**: Publicly deployed on **Vercel** (Frontend HTTPS), **Render** (Flask + Gunicorn), and **Supabase** (Hosted PostgreSQL).

---

## Security Notes

- **Zero Client Secret Exposure**: The permanent `ASSEMBLYAI_API_KEY` is never sent to or bundled with the frontend client. The client authenticates using short-lived ephemeral tokens (`expires_in_seconds=300`) generated by the backend.
- **Database Credential Protection**: Database connection strings and passwords are restricted to server environment variables and strictly ignored by Git.
- **Deterministic Safety**: All threshold validations occur within the server layer using trusted limits from PostgreSQL.

---

## License

This project is licensed under the terms of the [MIT License](file:///d:/fieldport/LICENSE).
