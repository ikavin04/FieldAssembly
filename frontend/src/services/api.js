const API_BASE = "";

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

export function getMaintenanceTickets(params = {}) {
  const query = new URLSearchParams();
  if (params.inspection_id) query.set("inspection_id", params.inspection_id);
  if (params.status) query.set("status", params.status);
  if (params.priority) query.set("priority", params.priority);
  const qs = query.toString();
  return requestJson(`/api/tickets${qs ? `?${qs}` : ""}`);
}

export function getInspectionTickets(inspectionId) {
  return requestJson(`/api/inspections/${inspectionId}/tickets`);
}

export function createMaintenanceTicket(payload) {
  return requestJson("/api/tickets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSafetyAlerts(params = {}) {
  const query = new URLSearchParams();
  if (params.inspection_id) query.set("inspection_id", params.inspection_id);
  if (params.status) query.set("status", params.status);
  if (params.severity) query.set("severity", params.severity);
  const qs = query.toString();
  return requestJson(`/api/safety-alerts${qs ? `?${qs}` : ""}`);
}

export function getInspectionAlerts(inspectionId) {
  return requestJson(`/api/inspections/${inspectionId}/alerts`);
}

export function createSafetyAlert(payload) {
  return requestJson("/api/safety-alerts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getInspectionReport(inspectionId) {
  return requestJson(`/api/reports/${inspectionId}`);
}

export function generateInspectionReport(inspectionId) {
  return requestJson(`/api/reports/${inspectionId}/generate`, {
    method: "POST",
  });
}

export function executeVoiceTool(name, argumentsObject) {
  const endpoints = {
    get_equipment_profile: "/api/tools/get-equipment-profile",
    save_observation: "/api/tools/save-observation",
    complete_inspection: "/api/tools/complete-inspection",
    create_maintenance_ticket: "/api/tools/create-maintenance-ticket",
    create_safety_alert: "/api/tools/create-safety-alert",
  };
  const endpoint = endpoints[name];
  if (!endpoint) throw new Error(`Unsupported voice tool: ${name}`);
  return requestJson(endpoint, {
    method: "POST",
    body: JSON.stringify(argumentsObject),
  });
}
