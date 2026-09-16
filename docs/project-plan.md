# FieldVoice Project Plan

## Phase 1 — Project Setup

- [x] Initialize Vite + React frontend
- [x] Set up Tailwind CSS
- [x] Create Flask backend skeleton
- [x] Define folder structure for parallel development
- [x] Create documentation (architecture, API contract, project plan)
- [x] Create .gitignore and environment variable template

## Phase 2 — AssemblyAI Voice Connection

- [ ] Backend: Generate temporary AssemblyAI token (`GET /api/voice-token`)
- [ ] Frontend: Open WebSocket to AssemblyAI using the token
- [ ] Frontend: Capture microphone audio and stream to WebSocket
- [ ] Verify end-to-end audio streaming and transcription

## Phase 3 — Voice Agent Behavior

- [ ] Backend: Define AI system prompt for inspection context
- [ ] Backend: Configure AssemblyAI Voice Agent with system prompt
- [ ] Test basic conversational interaction with the agent

## Phase 4 — Database and Equipment Data

- [ ] Set up PostgreSQL schema (equipment, inspections, observations)
- [ ] Backend: Connect to PostgreSQL via `psycopg2`
- [ ] Backend: Implement `GET /api/equipment/:id`
- [ ] Seed sample equipment data

## Phase 5 — Inspection Workflow

- [ ] Backend: Implement `POST /api/inspections` (start inspection)
- [ ] Backend: Implement `POST /api/observations` (record observation)
- [ ] Backend: Implement `GET /api/inspections/:id` (retrieve inspection)
- [ ] Frontend: Equipment selection UI
- [ ] Frontend: Start / stop inspection flow

## Phase 6 — Tool Calling

- [ ] Backend: Define tool schemas for the voice agent
- [ ] Backend: Implement tool-call handlers (log observation, etc.)
- [ ] Register tools with AssemblyAI agent configuration
- [ ] Test agent-initiated tool calls during a voice session

## Phase 7 — Validation

- [ ] Backend: Detect missing required inspection fields
- [ ] Backend: Validate suspicious measurements (out-of-range values)
- [ ] Agent: Ask follow-up questions when information is incomplete

## Phase 8 — Maintenance Tickets and Safety Alerts

- [ ] Backend: Implement `POST /api/tickets`
- [ ] Backend: Implement `POST /api/safety-alerts`
- [ ] Agent: Trigger ticket/alert creation through tool calls
- [ ] Frontend: Display tickets and alerts

## Phase 9 — Evidence System

- [ ] Backend: Link extracted fields to transcript excerpts
- [ ] Frontend: Display evidence linking observations to spoken statements

## Phase 10 — Report Generation

- [ ] Backend: Implement `GET /api/reports/:id`
- [ ] Backend: Generate structured inspection reports
- [ ] Frontend: Report display view

## Phase 11 — Frontend / Backend Integration

- [ ] Connect all frontend views to backend API
- [ ] End-to-end testing of full inspection workflow
- [ ] Responsive and mobile UX polish

## Phase 12 — Testing

- [ ] Backend unit tests
- [ ] Frontend component tests
- [ ] Integration tests for critical paths

## Phase 13 — Deployment

- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to a suitable Python hosting platform
- [ ] Set up managed PostgreSQL
- [ ] Configure production environment variables

## Phase 14 — Hackathon Submission

- [ ] Record demo video
- [ ] Capture screenshots
- [ ] Write final project description
- [ ] Submit
