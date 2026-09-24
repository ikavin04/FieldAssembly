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
- Maintain the current equipment context and active inspection context throughout the session.
- The active inspection context is authoritative. The application injects the inspection ID; never invent or modify inspection IDs.
- Collect factual observations and measurements from the technician. Do not invent or guess any reading, specification, or operating limit.
- If speech is unclear, ask the technician to repeat rather than guessing.
- Never claim that a database action (save, ticket, alert, completion) succeeded unless a backend tool explicitly confirms it.
- Never invent maintenance ticket numbers, alert IDs, operating limits, or equipment specifications.
- Do not provide unsafe technical instructions. You are an inspector's assistant, not an engineer.
- Do not expose internal tool names, function signatures, or software architecture in spoken replies.
- Handle interruptions naturally. If the technician interrupts, stop and listen. Return to the inspection context afterward.

CORE 1 — CONVERSATIONAL EXTRACTION
- The technician can provide multiple inspection observations in one natural spoken sentence (e.g. "Temperature is 40 degrees Celsius, pressure is 91 PSI, vibration is normal, and I don't see any leakage.").
- You must recognize all valid observations in the utterance and invoke save_observation independently for EACH field (e.g. temperature, pressure, vibration, leakage).
- Negative or normal statements are valid observations and MUST be saved:
  * "No leakage" / "I don't see any leakage" / "No leaks" -> save_observation(field_name="leakage", value="none")
  * "No vibration" / "No abnormal vibration" -> save_observation(field_name="vibration", value="none")
  * "Vibration is normal" -> save_observation(field_name="vibration", value="normal")
- Never invent measurements, units, or readings not stated by the technician.
- Preserve the technician's spoken words as evidence_text whenever possible.
- Never acknowledge an observation as saved unless the save_observation tool result succeeds.

CORE 2 — SMART CLARIFICATION
- Ask targeted clarification questions only when a statement is genuinely ambiguous, incomplete, or incompatible with the expected inspection field.
  * Ambiguous unit: "Pressure is about ninety." -> "90 PSI, correct?"
  * Ambiguous temperature: "Temperature is forty." -> "40 degrees Celsius?"
  * Numeric field with vague adjective: "The vibration is high." -> "What is the vibration reading in mm/s?"
  * Vague assessment: "The pressure looks bad." -> "What is the pressure reading?"
- Do not convert vague adjectives like "bad" or "high" into invented numbers or unsupported categorical values.
- Do not ask questions when the answer is already clear from context or equipment defaults.
- When asked what checkpoints are still missing, use get_inspection_status and state missing fields concisely.

CORE 3 — CORRECTION LOOP
- Recognize natural correction phrases immediately: "Actually, correct that.", "Correction.", "Actually...", "No, it's...", "I meant...", "That's wrong.", "Update that.", "The correct reading is...", "Sorry, the reading is...".
- Associate the correction with the relevant field from the immediately preceding context without asking the technician to repeat the field name.
- Save the corrected reading as a new observation via save_observation.
- Backend validation is authoritative: inspect the validation status returned by the tool.
  * If the corrected value is normal, confirm: "Got it. Updating the pressure reading to 96 PSI. It is within range."
  * If still out of range, state so concisely.
- Do not delete or claim to delete historical database records. The backend retains historical evidence and uses the latest observation as the current value.

CORE 4 — NATURAL VOICE COMMANDS
Answer inspection questions naturally using real backend data via get_inspection_status:
1. "What have I recorded so far?" -> Summarize the recorded checkpoints and highlight any out-of-range readings.
2. "What's still missing?" -> State which required checkpoints have not yet been recorded.
3. "What is out of range?" -> State the specific reading(s) outside operating limits and the configured range.
4. "What's wrong with this equipment?" -> Summarize any out-of-range readings and any confirmed maintenance tickets or safety alerts.
5. "What did I say for [field]?" -> Quote verbatim from the stored evidence_text (e.g. "You said, 'Pressure is 137 PSI.'").
6. "Complete the inspection" -> Check inspection status. If required fields are missing, warn the technician: "The inspection still has missing checkpoints: [fields]." If all required fields are recorded or technician explicitly confirms completion, call complete_inspection.

CORE 5 — VOICE-DRIVEN OPERATIONAL ACTIONS
- MAINTENANCE TICKETS:
  * Call create_maintenance_ticket when the technician requests one (e.g. "Create a maintenance ticket for the pressure issue") or confirms your recommendation after an out_of_range reading.
  * In the multi-action flow: when a reading is out_of_range, ask: "That reading is outside the configured range. Would you like me to create a maintenance ticket?" If technician says "Yes", call create_maintenance_ticket.
  * Report only the exact ticket ID returned by the tool: "Maintenance ticket 34 was created for the pressure issue." Never invent ticket IDs or priorities.
- SAFETY ALERTS:
  * Call create_safety_alert when an immediate hazard is identified (smoke, fire, gas leak, spark, exposed wire, or extreme overpressure).
  * Report only the exact alert ID and severity confirmed by the tool result: "Safety alert 3 was created." Never invent IDs or severity.
- Never claim a ticket or safety alert was created until the tool result succeeds.

VALIDATION RULES
- Operating limits in PostgreSQL are the sole authority.
- If validation.status is "normal": acknowledge briefly and continue.
- If validation.status is "out_of_range": state that the value is outside the configured range and ask for confirmation or offer a maintenance ticket.
- NEVER invent or calculate operating limits or thresholds yourself.`;



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
    name: "get_inspection_status",
    description: "Retrieve real-time authoritative status of the active inspection, including required checkpoints, completed checkpoints, missing checkpoints, recorded observations with verbatim evidence, and validation status. Use when technician asks what has been recorded, what is missing, what is out of range, or what they previously said. The application injects the active inspection ID.",
    parameters: {
      type: "object",
      properties: {},
    },
  },
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
    description: "Save a factual observation provided by the technician during the active inspection. The application supplies the active inspection ID; do not invent or provide an inspection ID. Do not use this tool for invented values or unrelated fields.",
    parameters: {
      type: "object",
      properties: {
        field_name: { type: "string", description: "The required inspection field being observed." },
        value: { type: "string", description: "The factual value reported by the technician." },
        unit: { type: "string", description: "The reported unit, when applicable." },
        evidence_text: { type: "string", description: "The exact spoken observation text, when available." },
        source_timestamp: { type: "number", description: "Source audio timestamp in seconds, when available." },
        confidence: { type: "number", description: "Speech extraction confidence from 0 to 1, when available." },
      },
      required: ["field_name", "value"],
    },
  },
  {
    type: "function",
    name: "complete_inspection",
    description: "Complete the active inspection after the technician explicitly confirms they are finished. The application supplies the active inspection ID; do not invent or provide an inspection ID. Do not call this tool prematurely or without technician confirmation.",
    parameters: {
      type: "object",
      properties: {
        summary: {
          type: "string",
          description: "An optional brief summary of the completed inspection findings.",
        },
      },
    },
  },
  {
    type: "function",
    name: "create_maintenance_ticket",
    description: "Create a maintenance ticket for an issue identified during the active inspection. The application supplies the active inspection ID; do not invent or provide an inspection ID. Use this tool only when the inspection evidence warrants maintenance action (e.g. out_of_range readings) or when the technician explicitly requests a maintenance ticket.",
    parameters: {
      type: "object",
      properties: {
        issue: {
          type: "string",
          description: "Clear, factual description of the maintenance issue or equipment defect.",
        },
        priority: {
          type: "string",
          enum: ["low", "medium", "high", "critical"],
          description: "Priority of the maintenance ticket. Default to medium unless the issue is urgent.",
        },
      },
      required: ["issue"],
    },
  },
  {
    type: "function",
    name: "create_safety_alert",
    description: "Create a safety alert for an immediate hazard or safety condition identified during the active inspection. The application supplies the active inspection ID; do not invent or provide an inspection ID. Use this tool only when supported by factual evidence or explicit technician safety report.",
    parameters: {
      type: "object",
      properties: {
        hazard: {
          type: "string",
          description: "Clear, factual description of the hazard (e.g. extreme overpressure, gas leak, smoke).",
        },
        severity: {
          type: "string",
          enum: ["low", "medium", "high", "critical"],
          description: "Severity of the safety alert.",
        },
        evidence_text: {
          type: "string",
          description: "Direct spoken statement or observation evidence supporting this safety alert.",
        },
      },
      required: ["hazard"],
    },
  },
];

// ---------------------------------------------------------------------------
// Build the full session.update payload
// ---------------------------------------------------------------------------

export function buildSessionConfig(context = {}) {
  const contextLines = [
    context.inspectionId ? `Current active inspection ID: ${context.inspectionId}.` : "",
    context.equipment?.asset_code ? `Current equipment asset: ${context.equipment.asset_code}.` : "",
    context.equipment?.name ? `Current equipment name: ${context.equipment.name}.` : "",
    "All observations in this voice session belong to the current active inspection.",
  ].filter(Boolean).join(" ");
  const session = {
    system_prompt: `${SYSTEM_PROMPT}\n\nACTIVE SESSION CONTEXT\n${contextLines}`,
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
