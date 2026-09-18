# FieldVoice Backend

Python Flask backend for the FieldVoice voice-first inspection platform.

## Responsibility

The backend is responsible for:

- REST API for the frontend
- AssemblyAI Voice Agent API integration (temporary token generation, agent configuration)
- Inspection logic and validation
- Tool calling (maintenance tickets, safety alerts)
- PostgreSQL database access
- Report generation

## Prerequisites

- Python 3.10+
- pip

## Setup

### 1. Create a virtual environment

```bash
python -m venv venv
```

### 2. Activate the virtual environment

**Windows:**

```bash
venv\Scripts\activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values. Never commit this file.

## Running the Server

```bash
python app.py
```

The server starts at `http://localhost:5000` by default.

## Implemented Endpoints

### Health Check

```
GET /api/health
```

Response:

```json
{
  "status": "ok"
}
```

### Voice tools

```text
POST /api/tools/get-equipment-profile
```

Accepts `{ "asset_code": "AC-001" }` and returns the public inspection profile
for that equipment asset. Invalid asset tags return `400`; unknown assets return
`404`.

### Inspections

```text
POST /api/inspections
GET  /api/inspections/<inspection_id>
```

Create an inspection with `{ "equipment_id": 1, "inspection_type": "routine" }`.
The retrieval response includes backend-derived required, completed, and missing
inspection fields.

### Observations

```text
POST /api/observations
GET  /api/inspections/<inspection_id>/observations
```

Observation requests accept `inspection_id`, `field_name`, `value`, and optional
`unit`, `evidence_text`, `source_timestamp`, and `confidence`. Fields are checked
against the selected equipment's required inspection fields.

### Observation voice tool

```text
POST /api/tools/save-observation
```

This is the browser-to-backend endpoint used by the AssemblyAI tool call. Exact
retries for the same inspection, field, value, and evidence are idempotent.

## Notes

- The backend uses a Flask application factory pattern (`create_app`) for clean extensibility.
- Inspection lifecycle, observation, ticket, alert, and report endpoints remain future phases.
