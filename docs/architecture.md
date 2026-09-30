# FieldVoice Architecture

## Overview

FieldVoice follows a standard client–server architecture with a voice AI layer powered by AssemblyAI.

```
┌─────────────────────────┐
│   React + Vite Frontend │   ← Browser / mobile
│   (Tailwind CSS)        │
└───────────┬─────────────┘
            │  REST API / WebSocket
            ▼
┌─────────────────────────┐
│   Flask API Server      │   ← Python backend
└───────────┬─────────────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
┌────────┐   ┌─────────────┐
│ Postgre│   │ AssemblyAI   │
│ SQL    │   │ Voice Agent  │
└────────┘   └──────┬───────┘
                    │
                    ▼
             ┌─────────────┐
             │ Backend      │
             │ Tool Calls   │
             └─────────────┘
```

## Layer Responsibilities

### Frontend (React + Vite + Tailwind CSS)

- Captures microphone audio and streams it to AssemblyAI via WebSocket.
- Displays the live transcript, extracted observations, and evidence links.
- Provides the inspection workflow UI (equipment selection, start/stop, review).
- Renders dashboards, tickets, alerts, and reports.
- Communicates with the Flask backend through REST API calls.

### Flask API Server

- Serves REST endpoints consumed by the frontend.
- Generates temporary AssemblyAI tokens so the API key never reaches the client.
- Defines the AI agent's system prompt, tool schemas, and configuration.
- Implements tool-call handlers invoked by the AssemblyAI voice agent (e.g., create ticket, log observation).
- Orchestrates inspection logic, validation, and report generation.

### AssemblyAI Voice Agent

- Processes real-time audio via WebSocket.
- Converts speech to text.
- Runs the AI agent with the system prompt and tool definitions provided by the backend.
- Calls backend tools when the agent decides an action is needed.

### Backend Tools

- Callable functions registered with the voice agent.
- Planned tools include: log observation, create maintenance ticket, create safety alert, validate measurement, generate report.

### PostgreSQL

- Stores equipment data, inspections, observations, tickets, alerts, and reports.
- Will be accessed from the Flask backend using `psycopg2`.

## Current State

FieldVoice is fully implemented across all layers:
- **Frontend**: React 19 application with full dashboard, equipment catalog, inspection runner, tickets, alerts, reports, and real-time voice panel with live activity telemetry.
- **Backend**: Flask REST API + tools endpoints (`/api/tools/*`) with deterministic validation, connection pooling, and error handling.
- **Voice Pipeline**: Live AssemblyAI Voice Agent API integration (WebSocket, 24kHz PCM, VAD turn-taking, tools routing).
- **Database**: PostgreSQL with schema indexes, relational constraints, and equipment operating limits.
- **Test Suite**: 126 automated backend tests passing across validation, security, tools, tickets, alerts, and reports.
