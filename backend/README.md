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

## Notes

- The backend uses a Flask application factory pattern (`create_app`) for clean extensibility.
- Routes, services, tools, models, and database packages are prepared but not yet implemented.
- AssemblyAI integration, database connections, and tool calling will be added in future phases.
