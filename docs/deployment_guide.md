# FieldVoice — Production Deployment Guide
## Architecture: Supabase (Database) + Render (Backend) + Vercel (Frontend)

This guide walks you through deploying the complete FieldVoice production stack with zero downtime and full voice agent capabilities.

```mermaid
flowchart LR
    A[Browser / Mobile] -->|HTTPS UI| B[Vercel: Vite React SPA]
    A -->|Microphone Audio Stream| C[AssemblyAI Voice Agent API]
    B -->|REST API Calls| D[Render: Flask + Gunicorn Web Service]
    D -->|PostgreSQL Protocol SSL| E[(Supabase: Hosted PostgreSQL)]
    D -->|Temporary Token Gen| C
```

---

## 📋 Pre-Deployment Checklist

Before starting, ensure you have:
- A [GitHub](https://github.com/) account with this repository pushed to `main`.
- A [Supabase](https://supabase.com/) account (Free tier supported).
- A [Render](https://render.com/) account (Free tier supported).
- A [Vercel](https://vercel.com/) account (Hobby/Free tier supported).
- Your [AssemblyAI](https://www.assemblyai.com/) API Key.

---

## Step 1: Set Up Supabase (PostgreSQL Database)

1. **Create Project**:
   - Go to [Supabase Dashboard](https://supabase.com/dashboard) and click **"New project"**.
   - Name: `fieldvoice-db`.
   - Set a strong **Database Password** (save this password securely).
   - Region: Choose the region closest to your Render service (e.g., *US East - North Virginia* or *EU Central*).
   - Click **"Create new project"** (takes ~60 seconds to provision).

2. **Run the Database Schema**:
   - In your Supabase project dashboard, navigate to the **SQL Editor** (icon on the left navigation bar).
   - Click **"New query"**.
   - Open `backend/database/schema.sql` in your project, copy the entire SQL script, and paste it into the Supabase SQL editor.
   - Click **"Run"** (Ctrl+Enter).
   - Verify all 8 tables are created (`equipment`, `inspections`, `observations`, `tickets`, `alerts`, `inspection_templates`, `audit_log`, `voice_sessions`).

3. **Seed Equipment & Operating Limits**:
   - In Supabase SQL Editor, run this script to seed equipment data:
   ```sql
   INSERT INTO equipment (asset_code, name, equipment_type, location, description, operating_limits, required_inspection_fields)
   VALUES
   ('AC-001', 'Main Lobby Air Handler', 'HVAC', 'Building A — Lobby', 'Central air handling unit serving the main lobby area.', '{"temperature_c": {"min": 0, "max": 60}, "pressure_psi": {"min": 40, "max": 100}}'::jsonb, '["temperature", "pressure", "vibration", "leakage"]'::jsonb),
   ('AC-002', 'Server Room Precision Cooler', 'HVAC', 'Building A — Server Room', 'Precision cooling unit for the main server room.', '{"temperature_c": {"min": 15, "max": 30}, "pressure_psi": {"min": 50, "max": 110}}'::jsonb, '["temperature", "pressure", "vibration", "leakage", "refrigerant_level"]'::jsonb),
   ('AC-003', 'Warehouse Rooftop Unit', 'HVAC', 'Warehouse — Roof', 'Rooftop packaged HVAC unit for the warehouse.', '{"temperature_c": {"min": -5, "max": 70}, "pressure_psi": {"min": 30, "max": 120}}'::jsonb, '["temperature", "pressure", "vibration", "leakage"]'::jsonb),
   ('PUMP-001', 'Chilled Water Pump A', 'Pump', 'Building A — Mechanical Room', 'Primary chilled water circulation pump.', '{"temperature_c": {"min": 2, "max": 25}, "pressure_psi": {"min": 20, "max": 90}, "vibration_mm_s": {"min": 0, "max": 7}}'::jsonb, '["temperature", "pressure", "vibration", "leakage"]'::jsonb),
   ('MTR-001', 'AHU Supply Fan Motor', 'Motor', 'Building A — Mechanical Room', 'Main supply fan motor for air handling unit AC-001.', '{"temperature_c": {"min": 10, "max": 80}, "voltage_v": {"min": 380, "max": 420}, "current_a": {"min": 0, "max": 30}}'::jsonb, '["temperature", "vibration", "voltage", "current"]'::jsonb),
   ('CMP-001', 'Chiller Compressor Unit 1', 'Compressor', 'Building A — Chiller Plant', 'Centrifugal compressor in chiller unit 1.', '{"temperature_c": {"min": -10, "max": 100}, "pressure_psi": {"min": 50, "max": 120}, "vibration_mm_s": {"min": 0, "max": 5}}'::jsonb, '["temperature", "pressure", "vibration", "leakage", "refrigerant_level"]'::jsonb)
   ON CONFLICT (asset_code) DO NOTHING;
   ```
   *(Or optionally run `python -m database.seed` locally with `DATABASE_URL` pointed to Supabase).*

4. **Copy Database Connection String**:
   - In Supabase, go to **Project Settings** (gear icon) -> **Database**.
   - Scroll down to **Connection parameters** / **Connection string**.
   - Select **URI**.
   - Choose **Session Pooler** (Port `5432`) or **Transaction Pooler** (Port `6543`).
   - Format: `postgresql://postgres.[ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require`
   - Replace `[YOUR-PASSWORD]` with your actual Supabase DB password.

---

## Step 2: Deploy Backend on Render

1. **Create Web Service**:
   - Go to [Render Dashboard](https://dashboard.render.com/) -> Click **"New +"** -> **"Web Service"**.
   - Connect your GitHub repository (`ikavin04/FieldAssembly`).
2. **Configure Settings**:
   - **Name**: `fieldvoice-backend`
   - **Region**: Choose the same geographic region as your Supabase DB.
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free or Starter
3. **Add Environment Variables**:
   In the **Environment Variables** section on Render, add:
   | Key | Value | Notes |
   | :--- | :--- | :--- |
   | `FLASK_ENV` | `production` | Enables production security checks |
   | `DATABASE_URL` | `postgresql://postgres.[ref]:[PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require` | From Supabase |
   | `ASSEMBLYAI_API_KEY` | `your_assemblyai_api_key_here` | Required for token generation and voice agent |
   | `SECRET_KEY` | `generate-a-random-32-char-string` | Must not be `dev-secret-key` |
   | `FRONTEND_ORIGIN` | `*` *(or your Vercel URL once created)* | Allows cross-origin API calls |

4. **Deploy Service**:
   - Click **"Create Web Service"**.
   - Wait ~2 minutes for the build to finish.
   - When deployment completes, note your Render URL:  
     `https://fieldvoice-backend.onrender.com`
   - Test health check in your browser:  
     `https://fieldvoice-backend.onrender.com/api/health`  
     Expected response: `{"status": "ok", "database": "connected", ...}`

---

## Step 3: Deploy Frontend on Vercel

1. **Import Project into Vercel**:
   - Go to [Vercel Dashboard](https://vercel.com/) -> Click **"Add New..."** -> **"Project"**.
   - Select your GitHub repository (`ikavin04/FieldAssembly`).
2. **Configure Build & Output Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click "Edit" and choose `frontend`.
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
3. **Add Environment Variable**:
   In the **Environment Variables** section on Vercel, add:
   | Key | Value |
   | :--- | :--- |
   | `VITE_API_BASE_URL` | `https://fieldvoice-backend.onrender.com` |
   *(Use your actual Render URL from Step 2, without a trailing slash).*
4. **Deploy**:
   - Click **"Deploy"**.
   - Vercel will install dependencies, compile the Vite app, and deploy the SPA using `frontend/vercel.json`.
   - Your live frontend URL will be generated:  
     `https://fieldvoice-frontend.vercel.app`

---

## Step 4: Final Production Lock-Down (CORS)

Once your Vercel URL is live:
1. Return to the **Render Dashboard** -> Your `fieldvoice-backend` service -> **Environment**.
2. Update `FRONTEND_ORIGIN` to your exact Vercel URL:  
   `FRONTEND_ORIGIN=https://fieldvoice-frontend.vercel.app`
3. Click **"Save Changes"** (Render will automatically redeploy with the strict CORS policy).

---

## Step 5: Live Verification & Testing

Verify end-to-end functionality on your live Vercel URL:
1. **Asset Selection**: Open your Vercel URL. Click on **AC-001** (or any equipment). Verify equipment details and operating limits load from Supabase.
2. **Microphone HTTPS Access**: Click **"Start Voice Inspection"**. Your browser will request microphone permissions (guaranteed to work because Vercel serves over HTTPS).
3. **Live Voice Interaction**:
   - Say: *"Temperature is 48 degrees Celsius and pressure is 65 PSI."*
   - Verify real-time extraction, visual evidence chips, and database updates.
4. **Natural Command & Clarification**:
   - Say: *"Show active alerts"* or *"Generate summary report"*.
   - Verify timeline entries and ticket creation.
