# FieldVoice API Contract

> **All endpoints listed below are PLANNED unless explicitly marked as IMPLEMENTED.**
> This document defines the future API surface so frontend and backend developers can work in parallel.

---

## IMPLEMENTED

### Health Check

```
GET /api/health
```

**Purpose:** Verify the backend is running.

**Response:**

```json
{
  "status": "ok"
}
```

---

## PLANNED

### Voice Token

```
GET /api/voice-token
```

**Purpose:** Generate a temporary AssemblyAI token so the frontend can open a WebSocket connection without exposing the API key.

**Response:**

```json
{
  "token": "temporary_token_string"
}
```

---

### Get Equipment

```
GET /api/equipment/:id
```

**Purpose:** Retrieve details for a specific equipment asset.

**Response:**

```json
{
  "id": "pump-101",
  "name": "Cooling Pump 101",
  "type": "centrifugal_pump",
  "location": "Building A, Floor 2",
  "last_inspection": "2026-08-15T10:00:00Z"
}
```

---

### Create Inspection

```
POST /api/inspections
```

**Purpose:** Start a new inspection session for an equipment asset.

**Request:**

```json
{
  "equipment_id": "pump-101",
  "inspector_name": "Jane Doe"
}
```

**Response:**

```json
{
  "id": "insp-001",
  "equipment_id": "pump-101",
  "status": "in_progress",
  "created_at": "2026-09-16T14:00:00Z"
}
```

---

### Add Observation

```
POST /api/observations
```

**Purpose:** Record a structured observation extracted from voice input during an inspection.

**Request:**

```json
{
  "inspection_id": "insp-001",
  "type": "measurement",
  "field": "temperature",
  "value": "85",
  "unit": "°C",
  "transcript_excerpt": "Temperature is reading eighty-five degrees Celsius."
}
```

**Response:**

```json
{
  "id": "obs-001",
  "inspection_id": "insp-001",
  "type": "measurement",
  "field": "temperature",
  "value": "85",
  "unit": "°C",
  "created_at": "2026-09-16T14:05:00Z"
}
```

---

### Get Inspection

```
GET /api/inspections/:id
```

**Purpose:** Retrieve a complete inspection with all observations.

**Response:**

```json
{
  "id": "insp-001",
  "equipment_id": "pump-101",
  "status": "completed",
  "observations": [],
  "created_at": "2026-09-16T14:00:00Z",
  "completed_at": "2026-09-16T14:30:00Z"
}
```

---

### Create Ticket

```
POST /api/tickets
```

**Purpose:** Create a maintenance ticket triggered by an inspection finding.

**Request:**

```json
{
  "inspection_id": "insp-001",
  "title": "Replace worn bearing on Pump 101",
  "priority": "high",
  "description": "Unusual vibration detected during inspection."
}
```

**Response:**

```json
{
  "id": "ticket-001",
  "inspection_id": "insp-001",
  "title": "Replace worn bearing on Pump 101",
  "priority": "high",
  "status": "open",
  "created_at": "2026-09-16T14:20:00Z"
}
```

---

### Create Safety Alert

```
POST /api/safety-alerts
```

**Purpose:** Create a safety alert for a critical finding during inspection.

**Request:**

```json
{
  "inspection_id": "insp-001",
  "severity": "critical",
  "description": "Hydrogen sulfide levels above safe threshold.",
  "recommended_action": "Evacuate area and notify safety team."
}
```

**Response:**

```json
{
  "id": "alert-001",
  "inspection_id": "insp-001",
  "severity": "critical",
  "status": "active",
  "created_at": "2026-09-16T14:22:00Z"
}
```

---

### Get Report

```
GET /api/reports/:id
```

**Purpose:** Retrieve the generated inspection report.

**Response:**

```json
{
  "id": "report-001",
  "inspection_id": "insp-001",
  "summary": "Routine inspection of Cooling Pump 101...",
  "observations_count": 5,
  "tickets_created": 1,
  "alerts_created": 0,
  "generated_at": "2026-09-16T14:35:00Z"
}
```
