# FieldVoice Frontend

React + Vite frontend for the FieldVoice voice-first inspection platform.

## Responsibility

The frontend is responsible for:

- Voice interface (start/stop recording, microphone access)
- Inspection workflow UI
- Live transcript display
- Observation and evidence display
- Dashboard, alerts, tickets, and report views
- Responsive and mobile-friendly UX

## Prerequisites

- Node.js 18+
- npm

## Setup

```bash
npm install
```

## Development

```bash
npm run dev
```

The dev server starts at `http://localhost:5173` by default.

## Build

```bash
npm run build
```

## Notes
- Custom CSS design system using curated industrial tokens and accessible contrast.
- Fully integrated with Flask backend REST API and tools endpoints.
- Voice agent panel features real-time audio capture, live transcription, and activity event telemetry.
