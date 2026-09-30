# FieldVoice

> **Hands-Free Voice AI Inspection Copilot for Industrial Maintenance**  
> Built for the **AssemblyAI — Voice Agent Hackathon** (Path A: Voice Agent API).

---

## Overview

**FieldVoice** is a voice-first industrial inspection copilot designed for maintenance technicians working in demanding physical environments (HVAC, chiller plants, boiler rooms, manufacturing facilities). 

Instead of stopping work to remove gloves, tap greasy tablet screens, or transcribe handwritten notes into CMMS platforms at the end of the day, technicians speak naturally while inspecting equipment. FieldVoice captures the speech in real time, extracts technical checkpoints, validates measurements against authoritative PostgreSQL operating limits, generates maintenance tickets and safety alerts, and produces traceable inspection reports.

---

## The Problem

- **Hands Busy, Work Interrupted**: Field technicians work with tools, gauges, and safety gloves. Stopping to type inspection readings into a phone or tablet interrupts physical tasks and slows workflows.
- **Data Latency & Incomplete Checkpoints**: Technicians often write shorthand numbers on notepads or paper forms and enter them hours later, resulting in forgotten readings and missing required checkpoints.
- **Unverified Readings**: Human error or delayed entry leads to out-of-range readings sitting unnoticed in unsubmitted drafts rather than triggering immediate maintenance action.
- **Lack of Spoken Evidence**: Traditional forms record only a single static number without preserving what the technician actually observed or stated during the inspection.

---

## The Solution

FieldVoice provides a hands-free conversational interface that stays locked to the active equipment context:

1. **Talk While You Work**: Technicians speak natural, composite observations (*"Temperature is 40 degrees Celsius, pressure is 137 PSI, vibration is normal, and I don't see any leakage."*).
2. **Deterministic Backend Validation**: Measurements are evaluated against PostgreSQL operating limits (e.g. AC-001 pressure range 40–100 PSI). The LLM is never allowed to invent limits or guess validation status.
3. **Automated Operational Actions**: Out-of-range readings prompt the voice agent to offer a maintenance ticket; critical hazards (gas leaks, sparks, smoke, >150% overpressure) immediately trigger safety alerts.
4. **Verbatim Spoken Evidence**: Every observation links to the verbatim spoken transcript, creating a traceable audit trail for plant managers.

---

## Why AssemblyAI?

FieldVoice is built on **AssemblyAI's Voice Agent API (Path A)**:

- **Integrated Pipeline**: Combines sub-second speech-to-text, LLM routing, and low-latency audio output over a single WebSocket connection (`wss://agents.assemblyai.com/v1/ws`).
- **Server-Managed Security**: Backend generates temporary, single-use session tokens (`/api/voice-token`) with configurable TTL (`expires_in_seconds=300`). The permanent `ASSEMBLYAI_API_KEY` never reaches the browser.
- **Bi-directional JSON-Schema Tools**: AssemblyAI invokes structured tools registered in `session.update`, enabling real-time database queries and mutations.
- **Natural Turn-Taking & Interruption**: Built-in VAD (Voice Activity Detection) handles pauses and immediately flushes audio playback when the technician interrupts.

---

## Core Implemented Capabilities

### Core 1 — Conversational Multi-Observation Extraction
The technician can provide multiple measurements in a single spoken utterance. FieldVoice extracts each checkpoint independently and saves each observation to PostgreSQL with verbatim evidence text intact.

### Core 2 — Smart Clarification
When an utterance is ambiguous (e.g. *"Pressure is about ninety"* or *"Vibration is high"*), the agent asks targeted clarifying questions (*"90 PSI, correct?"* or *"What is the vibration reading in mm/s?"*) instead of inventing numbers.

### Core 3 — Spoken Correction Loop
If a technician corrects themselves (*"Actually, correct that. Pressure is 96 PSI."*), FieldVoice records the new observation, recalculates validation (137 PSI out-of-range → 96 PSI normal), and updates the active checklist while retaining historical evidence.

### Core 4 — Natural Status Voice Commands
Technicians can query the inspection state hands-free:
- *"What have I recorded so far?"* → Summarizes checkpoints and flags any out-of-range readings.
- *"What's still missing?"* → Identifies remaining required checkpoints.
- *"What did I say for pressure?"* → Quotes verbatim from stored evidence text.
- *"Complete the inspection."* → Verifies all required fields and closes the inspection.

### Core 5 — Voice-Driven Operational Actions
- **Maintenance Tickets**: Triggered by technician request or upon out-of-range confirmation.
- **Safety Alerts**: Generated when immediate hazard keywords (smoke, fire, gas leak, spark) or severe overpressure (>150% max limit) are detected.
- Real database IDs (e.g. Ticket #34, Alert #12) are returned and announced.

### Core 6 — Live Activity Timeline
A real-time telemetry panel visualizes speech, tool calls, backend validations, ticket creations, and system events alongside the conversation transcript.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│               Browser / Mobile Client                  │
│  React 19 + Vite + Vanilla CSS Industrial Design       │
│  AudioWorklet PCM Capture (24kHz) + Live Activity Log  │
└──────────────┬──────────────────────────┬──────────────┘
               │ HTTP (REST)              │ WebSocket
               │                          │ (w/ Temporary Token)
               ▼                          ▼
┌──────────────────────────────┐   ┌──────────────────────────────┐
│       Flask Backend          │   │  AssemblyAI Voice Agent API  │
│  - /api/voice-token          │   │  - Real-time STT             │
│  - Deterministic Validation  │   │  - LLM Orchestration         │
│  - Tool Endpoints (/api/tools)◀───┤  - Tool Calling              │
│  - Reports & Dashboards      │   │  - TTS Audio Playback        │
└──────────────┬───────────────┘   └──────────────────────────────┘
               │ psycopg2 pool
               ▼
┌──────────────────────────────┐
│    PostgreSQL Database       │
│  - equipment (limits & specs)│
│  - inspections & observations│
│  - maintenance_tickets       │
│  - safety_alerts             │
└──────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Voice AI Engine** | AssemblyAI Voice Agent API (WebSocket, PCM 24kHz, James voice) |
| **Frontend** | React 19, Vite, Vanilla CSS design tokens, Web Audio API, AudioWorklet |
| **Backend** | Python 3.10+, Flask, Werkzeug, requests |
| **Database** | PostgreSQL, psycopg2 connection pool (2–20 connections) |
| **Security** | Ephemeral AssemblyAI tokens, parameterized SQL queries, active context enforcement |

---

## Tool Definitions (JSON-Schema)

| Tool Name | Purpose | Authority |
|---|---|---|
| `get_inspection_status` | Retrieve completed/missing checkpoints and validation status | Read-only |
| `get_equipment_profile` | Retrieve equipment specs, type, and operating limits by asset code | Read-only |
| `save_observation` | Record factual measurement with verbatim spoken evidence | Active Inspection |
| `complete_inspection` | Mark inspection completed and generate completion summary | Active Inspection |
| `create_maintenance_ticket` | Create CMMS maintenance ticket with issue and priority | Idempotent |
| `create_safety_alert` | Create immediate safety alert with hazard description and severity | Idempotent |

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL database
- AssemblyAI API Key ([assemblyai.com](https://www.assemblyai.com/))

### 1. Database Setup

Create a PostgreSQL database and run the seed script:

```bash
# In PostgreSQL
CREATE DATABASE fieldvoice;
```

Configure `backend/.env`:
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```env
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
DATABASE_URL=postgresql://postgres:password@localhost:5432/fieldvoice
FLASK_ENV=development
FRONTEND_ORIGIN=http://localhost:5173
```

Run seed script:
```bash
cd backend
python database/seed.py
```

### 2. Backend Server

```bash
cd backend
pip install -r requirements.txt
python app.py
```
*Backend runs on `http://localhost:5000` (Health check: `http://localhost:5000/api/health`).*

### 3. Frontend Dev Server

```bash
cd frontend
npm install
npm run dev
```
*Frontend runs on `http://localhost:5173`.*

---

## Running the Automated Test Suites

The repository contains 126 automated test cases covering validation, security, reporting, tools, and the voice agent pipeline:

```bash
cd backend

# 1. Comprehensive Suite (38 tests)
python test_comprehensive_suite.py

# 2. Core Voice Expansion (22 tests)
python test_core_voice_expansion.py

# 3. Security & Production Hardening (10 tests)
python test_step10_security.py

# 4. Deterministic Validation (26 tests)
python test_step7_validation.py

# 5. Maintenance Tickets & Safety Alerts (16 tests)
python test_step8_tickets_alerts.py

# 6. Integrated Report Generation (14 tests)
python test_step9_reports.py

# Frontend quality checks
cd ../frontend
npm run lint
npm run build
```

---

## Live Demo Script

1. **Navigate to Catalog**: Open `http://localhost:5173/equipment` and select **AC-001 (Main Lobby Air Handler)**.
2. **Start Inspection**: Click **Start Inspection**. Active inspection session is initialized with required checkpoints: `temperature`, `pressure`, `vibration`, `leakage`.
3. **Connect Voice**: Click **Start Voice**. Grant microphone permission. The agent greets: *"Hi, I'm FieldVoice. Which equipment are we inspecting?"*
4. **Speak Multi-Observation**:
   > *"Temperature is 40 degrees Celsius, pressure is 137 PSI, vibration is normal, and there is no leakage."*
5. **Observe Real-Time Behavior**:
   - `temperature` validates as **normal** (limit: 0–60 °C).
   - `pressure` validates as **out_of_range** (limit: 40–100 PSI).
   - Live Activity Timeline visualizes each tool execution and validation result.
6. **Voice Correction**:
   > *"Actually, correct that. Pressure is 96 PSI."*
   - Reading updates to 96 PSI and immediately revalidates to **normal**.
7. **Query Missing**:
   > *"What have I recorded so far?"*
8. **Complete Inspection**:
   > *"Complete the inspection."*
   - Status switches to completed; view detailed report at `/inspection/<id>/result` or `/reports/<id>`.

---

## License

This project is licensed under the [MIT License](LICENSE).
