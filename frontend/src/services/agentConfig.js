/**
 * FieldVoice Agent Configuration
 *
 * Single source of truth for the AssemblyAI Voice Agent session config:
 *   - system prompt
 *   - greeting
 *   - voice
 *   - key terms
 *   - turn detection / VAD settings
 *   - tools (placeholder array for Step 5+)
 *
 * Separating config from the WebSocket service keeps things modular and
 * makes it easy to add tools, update the prompt, or swap voices later.
 */

// ---------------------------------------------------------------------------
// System prompt
// ---------------------------------------------------------------------------

export const SYSTEM_PROMPT = `You are FieldVoice, a hands-free industrial inspection copilot.

Your job is to help maintenance technicians conduct equipment inspections through natural voice conversation while they work with their hands.

CORE RULES
- Keep spoken responses to 1–2 sentences. Prefer brevity.
- Ask one question at a time. Wait for the answer before moving on.
- Maintain the current equipment context and inspection context throughout the session.
- Collect factual observations and measurements from the technician. Do not invent or guess any reading, specification, or operating limit.
- If a measurement is ambiguous (e.g. "80 degrees" without a unit), ask for clarification: "Is that Celsius or Fahrenheit?"
- If speech is unclear, ask the technician to repeat rather than guessing.
- Confirm important measurements briefly: "Recorded. 80 degrees Celsius."
- Never claim that a database action (save, ticket, alert) succeeded unless a backend tool explicitly confirms it. You do not have access to the database yet.
- Never invent maintenance ticket numbers, alert IDs, operating limits, or equipment specifications.
- Do not provide unsafe technical instructions. You are an inspector's assistant, not an engineer.
- If the technician reports a safety hazard (smoke, burning smell, exposed wiring, gas leak), acknowledge the hazard and recommend they follow their site's established safety procedure. Do not invent emergency contacts or technical emergency procedures.
- If the technician asks about something outside the system's current capability, say so clearly and briefly: "I can't do that yet."
- If the technician goes off-topic, acknowledge briefly and steer back: "Got it. Back to the inspection — what's the current pressure?"
- Do not give paragraph-length answers during routine inspection. Be direct.
- Do not expose internal implementation details, tool names, or system architecture.
- Handle interruptions naturally. If the technician interrupts, stop and listen. Return to the inspection context afterward.

INSPECTION FLOW
A typical inspection follows this pattern:
1. Technician identifies the equipment (e.g. "Start inspection for AC-014").
2. You acknowledge the equipment and begin asking for required observations.
3. Walk through each required measurement or observation one at a time.
4. After all observations are gathered, summarize briefly.
5. If the technician mentions an issue, note it conversationally. Actual ticket/alert creation is not yet available.

MEASUREMENT TYPES YOU MAY ENCOUNTER
- Temperature (Celsius or Fahrenheit)
- Pressure (PSI, bar, kPa)
- Voltage (V)
- Current (A / amps)
- Vibration (descriptive: none, slight, moderate, severe — or mm/s)
- Leakage (yes/no, descriptive)
- Refrigerant level
- Airflow
- Fuel level
- Battery status
- Water quality
- Flue gas readings
- Actuator response

RESPONSE STYLE EXAMPLES
Good: "Recorded. What's the pressure?"
Good: "Got it. Any visible leakage?"
Good: "Is that Celsius or Fahrenheit?"
Bad: "Thank you very much for providing that information. I have successfully recorded the temperature measurement of 80 degrees. Would you now be so kind as to..."`;

// ---------------------------------------------------------------------------
// Greeting
// ---------------------------------------------------------------------------

export const GREETING = "Hi, I'm FieldVoice. Which equipment are we inspecting?";

// ---------------------------------------------------------------------------
// Voice
// ---------------------------------------------------------------------------

export const VOICE_ID = "james";

// ---------------------------------------------------------------------------
// Domain key terms (boost speech recognition for technical vocabulary)
// ---------------------------------------------------------------------------

export const KEY_TERMS = [
  // Product
  "FieldVoice",
  // Equipment types
  "HVAC",
  "AC unit",
  "air handling unit",
  "AHU",
  "centrifugal chiller",
  "chiller",
  "boiler",
  "cooling tower",
  "compressor",
  "condenser",
  "evaporator",
  "fan coil",
  "fan coil unit",
  "FCU",
  "rooftop unit",
  "RTU",
  "split system",
  "UPS",
  "generator",
  // Components
  "refrigerant",
  "motor",
  "pump",
  "bearing",
  "fan",
  "coil",
  "filter",
  "duct",
  "valve",
  "circuit breaker",
  "electrical panel",
  "actuator",
  // Measurements
  "pressure",
  "PSI",
  "bar",
  "kPa",
  "temperature",
  "Celsius",
  "Fahrenheit",
  "voltage",
  "current",
  "ampere",
  "amp",
  "amps",
  "vibration",
  "leakage",
  "leak",
  "airflow",
  "flue gas",
  "refrigerant level",
  "fuel level",
  "battery status",
  "water quality",
  // Inspection workflow
  "maintenance",
  "inspection",
  "technician",
  "safety alert",
  "maintenance ticket",
  "observation",
  "reading",
  "measurement",
  // Common asset codes
  "AC-001",
  "AC-002",
  "AC-003",
  "AC-004",
  "AC-005",
  "PUMP-001",
  "PUMP-002",
  "PUMP-003",
  "MTR-001",
  "MTR-002",
  "CMP-001",
  "CMP-002",
  "BLR-001",
  "BLR-002",
  "CT-001",
  "VLV-001",
  "EXH-001",
  "FCU-001",
  "GEN-001",
  "UPS-001",
];

// ---------------------------------------------------------------------------
// Turn detection / VAD settings (preserved from Step 3 — known working)
// ---------------------------------------------------------------------------

export const TURN_DETECTION = {
  vad_threshold: 0.5,
  min_silence: 600,
  max_silence: 1500,
  interrupt_response: true,
};

// ---------------------------------------------------------------------------
// Tools — backend-owned operations exposed to the AssemblyAI agent.
// ---------------------------------------------------------------------------

export const TOOLS = [
  {
    type: "function",
    name: "get_equipment_profile",
    description: "Retrieve authoritative equipment information for the active inspection. Use the exact asset tag spoken or selected by the technician, such as AC-001. Do not convert an asset tag into a numeric ID or invent an asset tag.",
    parameters: {
      type: "object",
      properties: {
        asset_code: {
          type: "string",
          description: "The exact human-facing equipment asset tag, for example AC-001.",
        },
      },
      required: ["asset_code"],
    },
  },
  {
    type: "function",
    name: "save_observation",
    description: "Save a factual observation provided by the technician during the active inspection. Do not use this tool for invented values or unrelated fields.",
    parameters: {
      type: "object",
      properties: {
        inspection_id: { type: "integer", description: "The active inspection database ID." },
        field_name: { type: "string", description: "The required inspection field being observed." },
        value: { type: "string", description: "The factual value reported by the technician." },
        unit: { type: "string", description: "The reported unit, when applicable." },
        evidence_text: { type: "string", description: "The exact spoken observation text, when available." },
        source_timestamp: { type: "number", description: "Source audio timestamp in seconds, when available." },
        confidence: { type: "number", description: "Speech extraction confidence from 0 to 1, when available." },
      },
      required: ["inspection_id", "field_name", "value"],
    },
  },
];

// ---------------------------------------------------------------------------
// Build the full session.update payload
// ---------------------------------------------------------------------------

export function buildSessionConfig() {
  const session = {
    system_prompt: SYSTEM_PROMPT,
    greeting: GREETING,
    input: {
      turn_detection: TURN_DETECTION,
      keyterms: KEY_TERMS,
    },
    output: {
      voice: VOICE_ID,
    },
  };

  // Only include tools array if there are tools defined
  if (TOOLS.length > 0) {
    session.tools = TOOLS;
  }

  return {
    type: "session.update",
    session,
  };
}
