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

export function executeVoiceTool(name, argumentsObject) {
  const endpoints = {
    get_equipment_profile: "/api/tools/get-equipment-profile",
    save_observation: "/api/tools/save-observation",
  };
  const endpoint = endpoints[name];
  if (!endpoint) throw new Error(`Unsupported voice tool: ${name}`);
  return requestJson(endpoint, {
    method: "POST",
    body: JSON.stringify(argumentsObject),
  });
}
