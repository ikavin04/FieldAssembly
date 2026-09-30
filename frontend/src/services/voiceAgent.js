/**
 * FieldVoice — Voice Agent Service
 *
 * Manages the full voice pipeline:
 *   temporary token → WebSocket → session.update → microphone → input.audio
 *   → AssemblyAI → transcript + reply.audio → speaker playback
 *
 * No UI logic lives here. The service exposes callbacks for state changes,
 * transcripts, and errors so any React component can consume them.
 */

import { buildSessionConfig } from "./agentConfig.js";
import { executeVoiceTool } from "./api.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ASSEMBLYAI_WS_URL = "wss://agents.assemblyai.com/v1/ws";
const SAMPLE_RATE = 24_000; // AssemblyAI Voice Agent PCM format
const rawBackendBase = import.meta.env.VITE_API_BASE_URL || "";
const BACKEND_BASE = rawBackendBase.trim().replace(/[\r\n]/g, "").replace(/\/+$/, ""); // empty string = same-origin

/** Connection state machine */
export const ConnectionState = Object.freeze({
  DISCONNECTED: "DISCONNECTED",
  CONNECTING: "CONNECTING",
  CONNECTED: "CONNECTED",
  WAITING_FOR_SESSION: "WAITING_FOR_SESSION",
  LISTENING: "LISTENING",
  THINKING: "THINKING",
  SPEAKING: "SPEAKING",
  ERROR: "ERROR",
  ENDING: "ENDING",
});

// ---------------------------------------------------------------------------
// AudioWorklet processor inline source (runs on audio thread)
// ---------------------------------------------------------------------------

const WORKLET_PROCESSOR_CODE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = new Float32Array(1200); // 50ms at 24000 Hz
    this._offset = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (input && input[0] && input[0].length > 0) {
      const channel = input[0];
      let i = 0;
      while (i < channel.length) {
        const toCopy = Math.min(channel.length - i, this._buffer.length - this._offset);
        this._buffer.set(channel.subarray(i, i + toCopy), this._offset);
        this._offset += toCopy;
        i += toCopy;

        if (this._offset >= this._buffer.length) {
          this.port.postMessage(new Float32Array(this._buffer));
          this._offset = 0;
        }
      }
    }
    return true; // keep processor alive
  }
}
registerProcessor("pcm-capture-processor", PcmCaptureProcessor);
`;

// ---------------------------------------------------------------------------
// Voice Agent class
// ---------------------------------------------------------------------------

export class VoiceAgent {
  constructor(context = {}) {
    // WebSocket
    this._ws = null;

    // Audio capture
    this._audioContext = null;
    this._mediaStream = null;
    this._workletNode = null;
    this._sourceNode = null;

    // Audio playback
    this._playbackCtx = null;
    this._playbackQueue = [];
    this._isPlaying = false;
    this._nextPlaybackTime = 0;

    // State
    this._state = ConnectionState.DISCONNECTED;
    this._sessionReady = false;
    this._pendingToolResults = [];
    this._latestUserTranscript = null;
    this._activeInspectionId = context.inspectionId ?? null;
    this._activeEquipment = context.equipment ?? null;

    // Callbacks
    this.onStateChange = null; // (newState) => {}
    this.onUserTranscriptDelta = null; // (text) => {}
    this.onUserTranscript = null; // (text) => {}
    this.onAgentTranscriptDelta = null; // (text) => {}
    this.onAgentTranscript = null; // (text) => {}
    this.onError = null; // (message) => {}
    this.onSessionEnded = null; // () => {}
    this.onObservationSaved = null; // (result) => {}
    this.onInspectionCompleted = null; // (result) => {}
    this.onTicketCreated = null; // (result) => {}
    this.onAlertCreated = null; // (result) => {}
    this.onActivityEvent = null; // (event) => {}
  }



  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  get state() {
    return this._state;
  }

  /**
   * Connect to AssemblyAI Voice Agent:
   *  1. Fetch temporary token from backend
   *  2. Open WebSocket
   *  3. Send session.update
   *  4. Wait for session.ready
   *  5. Start microphone
   */
  async connect(context = {}) {
    if (context.inspectionId !== undefined) this._activeInspectionId = context.inspectionId;
    if (context.equipment !== undefined) this._activeEquipment = context.equipment;
    if (!this._activeInspectionId) {
      this._setState(ConnectionState.ERROR);
      this.onError?.("An active inspection is required before starting voice");
      return;
    }
    if (this._state !== ConnectionState.DISCONNECTED && this._state !== ConnectionState.ERROR) {
      console.warn("[Voice] Already connected or connecting");
      return;
    }

    try {
      this._setState(ConnectionState.CONNECTING);

      // Start microphone capture immediately within the user click gesture stack
      console.log("[Voice] Initiating microphone and session in parallel");
      const micPromise = this._startMicrophone();

      console.log("[Voice] Requesting temporary token");

      // 1. Get temporary token
      const tokenRes = await fetch(`${BACKEND_BASE}/api/voice-token`);
      if (!tokenRes.ok) {
        const body = await tokenRes.json().catch(() => ({}));
        throw new Error(body.error || `Token request failed: ${tokenRes.status}`);
      }
      const { token } = await tokenRes.json();
      if (!token) throw new Error("Empty token received from backend");
      console.log("[Voice] Token received");

      // Ensure microphone pipeline is ready
      await micPromise;

      // 2. Open WebSocket
      const wsUrl = `${ASSEMBLYAI_WS_URL}?token=${encodeURIComponent(token)}`;
      this._ws = new WebSocket(wsUrl);

      this._ws.onopen = () => {
        console.log("[Voice] WebSocket connected");
        this._setState(ConnectionState.CONNECTED);
        this._sendSessionUpdate();
        this._setState(ConnectionState.WAITING_FOR_SESSION);
      };

      this._ws.onmessage = (event) => this._handleMessage(event);

      this._ws.onerror = (event) => {
        console.error("[Voice] WebSocket error", event);
        this._setState(ConnectionState.ERROR);
        this.onError?.("Realtime connection failed (WebSocket error)");
      };

      this._ws.onclose = (event) => {
        console.log("[Voice] WebSocket closed", event.code, event.reason);
        this._cleanup();
      };
    } catch (err) {
      console.error("[Voice] Connection failed:", err.message);
      this._setState(ConnectionState.ERROR);
      this.onError?.(err.message);
    }
  }

  /** Cleanly disconnect and release all resources. */
  disconnect() {
    console.log("[Voice] Disconnecting");
    this._setState(ConnectionState.ENDING);

    // Send session.end if WebSocket is open
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      try {
        this._ws.send(JSON.stringify({ type: "session.end" }));
      } catch { /* ignore */ }
    }

    this._cleanup();
  }

  // -------------------------------------------------------------------------
  // Session configuration
  // -------------------------------------------------------------------------

  _sendSessionUpdate() {
    const config = buildSessionConfig({
      inspectionId: this._activeInspectionId,
      equipment: this._activeEquipment,
    });
    this._ws.send(JSON.stringify(config));
    console.log("[Voice] session.update sent");
  }

  // -------------------------------------------------------------------------
  // Incoming message handler
  // -------------------------------------------------------------------------

  _emitActivity(type, message, status = "completed", metadata = {}) {
    const event = {
      id: `act_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      type,    // 'speech' | 'tool_call' | 'tool_result' | 'validation' | 'action' | 'system' | 'error'
      status,  // 'pending' | 'completed' | 'warning' | 'error'
      message,
      metadata,
    };
    this.onActivityEvent?.(event);
  }

  _handleMessage(event) {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      console.warn("[Voice] Non-JSON message received");
      return;
    }

    console.log("[Voice] Event from server:", msg.type, msg.text || msg.status || "");

    switch (msg.type) {
      case "session.ready":
      case "session.updated":
        if (!this._sessionReady) {
          console.log("[Voice] Session ready and active");
          this._sessionReady = true;
          this._setState(ConnectionState.LISTENING);
          if (!this._workletNode) {
            this._startMicrophone();
          }
          this._emitActivity("system", "Voice assistant ready (listening)", "completed");
        } else {
          console.log("[Voice] session.updated");
        }
        break;

      case "SpeechStarted":
      case "input.speech.started":
        console.log("[Voice] User started speaking");
        if (this._state === ConnectionState.SPEAKING) {
          // User interrupted the agent — flush queued audio
          this._flushPlayback();
        }
        this._setState(ConnectionState.LISTENING);
        break;

      case "SpeechStopped":
      case "input.speech.stopped":
        console.log("[Voice] User stopped speaking");
        this._setState(ConnectionState.THINKING);
        break;

      case "transcript.user.delta":
        this.onUserTranscriptDelta?.(msg.text || msg.delta || msg.transcript || "");
        break;

      case "transcript.user":
        const userText = msg.text || msg.transcript || msg.content || "";
        console.log("[Voice] User transcript received:", userText);
        this._latestUserTranscript = userText;
        this.onUserTranscript?.(userText);
        this._emitActivity("speech", userText, "completed", { role: "user" });
        break;

      case "reply.started":
        console.log("[Voice] Agent reply started");
        this._setState(ConnectionState.SPEAKING);
        break;

      case "reply.audio":
        this._handleReplyAudio(msg);
        break;

      case "transcript.agent.delta":
        this.onAgentTranscriptDelta?.(msg.text || msg.delta || msg.transcript || "");
        break;

      case "transcript.agent":
        const agentText = msg.text || msg.transcript || msg.content || "";
        console.log("[Voice] Agent transcript received:", agentText);
        this.onAgentTranscript?.(agentText);
        this._emitActivity("speech", agentText, "completed", { role: "agent" });
        break;

      case "reply.done":
        console.log("[Voice] Reply complete");
        if (msg.status === "interrupted") {
          this._pendingToolResults = [];
          break;
        }
        const hasPendingToolResults = this._pendingToolResults.length > 0;
        this._sendPendingToolResults();
        if (!hasPendingToolResults) {
          this._returnToListeningAfterPlayback();
        }
        // After audio finishes playing, state will return to LISTENING
        break;

      case "tool.call":
        this._handleToolCall(msg);
        break;

      case "session.error":
        console.error("[Voice] Session error:", msg.error || msg);
        this._setState(ConnectionState.ERROR);
        this._emitActivity("error", msg.error?.message || msg.error || "Session error", "error");
        this.onError?.(msg.error?.message || msg.error || "Session error");
        break;

      case "session.ended":
        console.log("[Voice] Session ended");
        this._emitActivity("system", "Voice session ended", "completed");
        this.onSessionEnded?.();
        this._cleanup();
        break;

      default:
        // Silently ignore unrecognized events
        break;
    }
  }

  async _handleToolCall(msg) {
    const callId = msg.call_id;
    const toolName = msg.name;
    if (!callId || !toolName) {
      console.warn("[Voice] Ignoring malformed tool.call");
      return;
    }

    const argumentsObject = { ...msg.arguments };
    const inspectionTools = [
      "save_observation",
      "complete_inspection",
      "create_maintenance_ticket",
      "create_safety_alert",
      "get_inspection_status",
    ];
    if (inspectionTools.includes(toolName) && !this._activeInspectionId) {
      this._emitActivity("error", `Cannot execute ${toolName}: No active inspection context`, "error");
      this._pendingToolResults.push({
        callId,
        result: Promise.resolve({ success: false, error: "No active inspection context" }),
      });
      return;
    }
    if (inspectionTools.includes(toolName)) {
      if (argumentsObject.inspection_id && Number(argumentsObject.inspection_id) !== Number(this._activeInspectionId)) {
        console.warn("[Voice] Replacing mismatched inspection_id from tool call");
      }
      argumentsObject.inspection_id = Number(this._activeInspectionId);
    }
    if (toolName === "save_observation" && !argumentsObject.evidence_text && this._latestUserTranscript) {
      argumentsObject.evidence_text = this._latestUserTranscript;
    }

    let toolDesc = `Executing ${toolName}`;
    if (toolName === "save_observation") {
      const unitStr = argumentsObject.unit ? ` ${argumentsObject.unit}` : "";
      toolDesc = `Saving ${argumentsObject.field_name || "observation"}: ${argumentsObject.value}${unitStr}`;
    } else if (toolName === "create_maintenance_ticket") {
      toolDesc = `Creating maintenance ticket...`;
    } else if (toolName === "create_safety_alert") {
      toolDesc = `Creating safety alert...`;
    } else if (toolName === "complete_inspection") {
      toolDesc = `Completing inspection...`;
    } else if (toolName === "get_inspection_status") {
      toolDesc = `Checking inspection status...`;
    }
    this._emitActivity("tool_call", toolDesc, "pending", { toolName, callId, arguments: argumentsObject });

    console.log("[Voice] Tool call arguments", toolName, argumentsObject);
    const toolPromise = Promise.resolve().then(async () => {
      const res = await executeVoiceTool(toolName, argumentsObject);
      if (res?.success) {
        if (toolName === "save_observation") {
          this.onObservationSaved?.(res);
          this._emitActivity("tool_result", `✓ Observation saved: ${res.field_name}`, "completed", { observationId: res.observation_id });
          if (res.validation) {
            if (res.validation.status === "out_of_range") {
              const lim = res.validation.limit ? ` (${res.validation.limit.min}–${res.validation.limit.max})` : "";
              this._emitActivity("validation", `⚠ ${res.field_name}: Out of range${lim}`, "warning", { validation: res.validation });
            } else if (res.validation.status === "normal") {
              this._emitActivity("validation", `✓ ${res.field_name}: Within operating limits`, "completed", { validation: res.validation });
            } else {
              this._emitActivity("validation", `○ ${res.field_name}: Status unknown`, "completed", { validation: res.validation });
            }
          }
        } else if (toolName === "complete_inspection") {
          this.onInspectionCompleted?.(res);
          this._emitActivity("action", `✓ Inspection completed`, "completed");
        } else if (toolName === "create_maintenance_ticket") {
          this.onTicketCreated?.(res);
          this._emitActivity("action", `✓ Maintenance ticket #${res.ticket_id} created (${res.priority || "medium"})`, "completed", { ticketId: res.ticket_id });
        } else if (toolName === "create_safety_alert") {
          this.onAlertCreated?.(res);
          this._emitActivity("action", `⚠ Safety alert #${res.alert_id} created (${res.severity})`, "warning", { alertId: res.alert_id });
        } else if (toolName === "get_inspection_status") {
          const comp = res.completed_fields?.length ?? 0;
          const req = res.required_fields?.length ?? 0;
          this._emitActivity("tool_result", `✓ Inspection status retrieved (${comp}/${req} completed)`, "completed");
        }
      } else {
        this._emitActivity("error", `Failed: ${res?.error || "Tool call failed"}`, "error", { toolName });
      }
      return res;
    }).catch((err) => {
      this._emitActivity("error", `Error: ${err.message}`, "error", { toolName });
      return { success: false, error: err.message };
    });

    this._pendingToolResults.push({ callId, result: toolPromise });
    console.log(`[Voice] Tool requested: ${toolName}`);
  }



  async _sendPendingToolResults() {
    const pending = this._pendingToolResults;
    this._pendingToolResults = [];
    if (!pending.length) return;

    const results = await Promise.all(pending.map(async ({ callId, result }) => ({
      callId,
      result: await result,
    })));

    if (this._ws?.readyState !== WebSocket.OPEN) return;
    for (const { callId, result } of results) {
      this._ws.send(JSON.stringify({
        type: "tool.result",
        call_id: callId,
        result: JSON.stringify(result),
      }));
    }
    this._setState(ConnectionState.THINKING);
  }

  _returnToListeningAfterPlayback() {
    if (!this._playbackCtx) {
      this._setState(ConnectionState.LISTENING);
      return;
    }

    const remaining = Math.max(0, this._nextPlaybackTime - this._playbackCtx.currentTime);
    window.setTimeout(() => {
      if (this._state === ConnectionState.SPEAKING) {
        this._setState(ConnectionState.LISTENING);
      }
    }, Math.ceil(remaining * 1000) + 100);
  }

  // -------------------------------------------------------------------------
  // Microphone capture (AudioWorklet + resampling + PCM16 + base64)
  // -------------------------------------------------------------------------

  async _startMicrophone() {
    try {
      console.log("[Voice] microphone request started");
      if (!navigator?.mediaDevices?.getUserMedia) {
        throw new Error("Microphone access is not supported by your browser or environment");
      }
      this._mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      console.log("[Voice] microphone permission granted");

      const tracks = this._mediaStream.getAudioTracks();
      console.log("[Voice] number of audio tracks:", tracks.length);
      if (tracks.length === 0) {
        throw new Error("No audio tracks found on microphone stream");
      }

      const audioTrack = tracks[0];
      console.log("[Voice] audio track state:", {
        enabled: audioTrack.enabled,
        readyState: audioTrack.readyState,
        muted: audioTrack.muted,
        label: audioTrack.label,
      });
      console.log("[Voice] audio track enabled:", audioTrack.enabled);
      console.log("[Voice] audio track readyState:", audioTrack.readyState);

      if (!audioTrack.enabled) {
        console.warn("[Voice] Audio track was disabled, enabling now");
        audioTrack.enabled = true;
      }

      if (audioTrack.muted) {
        console.warn("[Voice] ATTENTION: Microphone is MUTED at the Windows OS or hardware level! (e.g. laptop microphone mute key or Windows Sound Settings)");
        this._emitActivity("warning", "Microphone is muted in Windows. Please unmute.", "warning");
      }

      audioTrack.onmute = () => {
        console.warn("[Voice] Microphone was muted by Windows or hardware mute key");
        this._emitActivity("warning", "Microphone was muted", "warning");
      };

      audioTrack.onunmute = () => {
        console.log("[Voice] Microphone was unmuted by Windows/hardware");
        this._emitActivity("system", "Microphone unmuted", "completed");
      };

      if (audioTrack.readyState !== "live") {
        console.warn("[Voice] Audio track readyState is not 'live':", audioTrack.readyState);
      }

      // Create AudioContext at the target sample rate and ensure active running state
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this._audioContext = new AudioCtx({ sampleRate: SAMPLE_RATE });
      if (this._audioContext.state === "suspended") {
        await this._audioContext.resume();
      }
      console.log("[Voice] AudioContext active, sampleRate:", this._audioContext.sampleRate, "state:", this._audioContext.state);

      // Register worklet processor from inline source
      const blob = new Blob([WORKLET_PROCESSOR_CODE], { type: "application/javascript" });
      const workletUrl = URL.createObjectURL(blob);
      await this._audioContext.audioWorklet.addModule(workletUrl);
      URL.revokeObjectURL(workletUrl);

      // Create audio nodes
      this._sourceNode = this._audioContext.createMediaStreamSource(this._mediaStream);
      this._workletNode = new AudioWorkletNode(this._audioContext, "pcm-capture-processor");

      // Connect through a zero-gain node to destination: keeps AudioWorklet active without acoustic feedback
      const silenceGain = this._audioContext.createGain();
      silenceGain.gain.value = 0;
      this._sourceNode.connect(this._workletNode);
      this._workletNode.connect(silenceGain);
      silenceGain.connect(this._audioContext.destination);

      // Receive Float32 samples from audio thread and stream to WebSocket
      let sentCount = 0;
      let maxRecentPeak = 0;

      this._workletNode.port.onmessage = (e) => {
        const float32 = e.data;
        let peak = 0;
        for (let i = 0; i < float32.length; i++) {
          const abs = Math.abs(float32[i]);
          if (abs > peak) peak = abs;
        }
        if (peak > maxRecentPeak) maxRecentPeak = peak;

        if (!this._sessionReady) return;
        if (this._ws?.readyState !== WebSocket.OPEN) return;

        const pcm16 = this._float32ToPcm16(float32);
        const base64 = this._arrayBufferToBase64(pcm16.buffer);

        this._ws.send(JSON.stringify({
          type: "input.audio",
          audio: base64,
        }));
        sentCount++;

        if (sentCount === 1) {
          console.log("[Voice] Audio capture started. First chunk sent.");
        }
        if (sentCount % 40 === 0) { // Every ~2.0s
          console.log(`[Voice] Audio chunk sent: #${sentCount} (~${(sentCount * 0.05).toFixed(1)}s), size: ${pcm16.byteLength} bytes, current peak: ${(peak * 100).toFixed(1)}%, recent max peak: ${(maxRecentPeak * 100).toFixed(1)}%`);
          if (maxRecentPeak < 0.005) {
            console.warn("[Voice] Warning: Microphone audio levels are near zero (<0.5%). Check if microphone is physically muted, muted in Windows Sound Settings, or disabled in browser permissions.");
          }
          maxRecentPeak = 0;
        }
      };

      console.log("[Voice] Microphone started and listening");
    } catch (err) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        console.warn("[Voice] microphone permission denied");
      }
      console.error("[Voice] Microphone error:", err.name, err.message);

      let userFriendlyMsg = `Microphone access failed: ${err.message}`;
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        userFriendlyMsg = "Microphone permission denied. Please allow microphone access in your browser settings.";
      } else if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
        userFriendlyMsg = "Microphone unavailable. No microphone device found on this system.";
      } else if (err.name === "NotReadableError" || err.name === "TrackStartError") {
        userFriendlyMsg = "Microphone is in use by another application or unavailable.";
      }

      this._setState(ConnectionState.ERROR);
      this.onError?.(userFriendlyMsg);
    }
  }

  /** Convert Float32 audio samples to Int16 PCM. */
  _float32ToPcm16(float32) {
    const pcm16 = new Int16Array(float32.length);
    for (let i = 0; i < float32.length; i++) {
      const s = Math.max(-1, Math.min(1, float32[i]));
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return pcm16;
  }

  /** Convert ArrayBuffer to base64 string. */
  _arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const len = bytes.length;
    for (let i = 0; i < len; i += 1024) {
      binary += String.fromCharCode.apply(null, bytes.subarray(i, Math.min(i + 1024, len)));
    }
    return btoa(binary);
  }

  // -------------------------------------------------------------------------
  // Audio playback (continuous queue of PCM16 chunks)
  // -------------------------------------------------------------------------

  _handleReplyAudio(msg) {
    const audioData = msg.data;
    if (!audioData) return;

    // Decode base64 → Int16 → Float32
    const binaryStr = atob(audioData);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
      bytes[i] = binaryStr.charCodeAt(i);
    }
    const pcm16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) {
      float32[i] = pcm16[i] / 0x8000;
    }

    this._enqueuePlayback(float32);
  }

  _enqueuePlayback(float32) {
    if (!this._playbackCtx) {
      this._playbackCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
    }

    // Resume if suspended (browser autoplay policy)
    if (this._playbackCtx.state === "suspended") {
      this._playbackCtx.resume();
    }

    const buffer = this._playbackCtx.createBuffer(1, float32.length, SAMPLE_RATE);
    buffer.copyToChannel(float32, 0);

    const source = this._playbackCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(this._playbackCtx.destination);

    // Schedule seamlessly after previous chunk
    const now = this._playbackCtx.currentTime;
    const startTime = Math.max(now, this._nextPlaybackTime);
    source.start(startTime);
    this._nextPlaybackTime = startTime + buffer.duration;

    source.onended = () => {
      // When the last chunk finishes and we're still in SPEAKING state,
      // transition back to LISTENING
      if (this._playbackCtx && this._nextPlaybackTime <= this._playbackCtx.currentTime + 0.05) {
        if (this._state === ConnectionState.SPEAKING) {
          this._setState(ConnectionState.LISTENING);
        }
      }
    };
  }

  _flushPlayback() {
    console.log("[Voice] Flushing playback queue (interruption)");
    if (this._playbackCtx) {
      this._playbackCtx.close().catch(() => {});
      this._playbackCtx = null;
      this._nextPlaybackTime = 0;
    }
  }

  // -------------------------------------------------------------------------
  // State management
  // -------------------------------------------------------------------------

  _setState(newState) {
    if (this._state === newState) return;
    this._state = newState;
    this.onStateChange?.(newState);
  }

  // -------------------------------------------------------------------------
  // Cleanup
  // -------------------------------------------------------------------------

  _cleanup() {
    // Stop microphone
    if (this._workletNode) {
      this._workletNode.disconnect();
      this._workletNode = null;
    }
    if (this._sourceNode) {
      this._sourceNode.disconnect();
      this._sourceNode = null;
    }
    if (this._audioContext) {
      this._audioContext.close().catch(() => {});
      this._audioContext = null;
    }
    if (this._mediaStream) {
      this._mediaStream.getTracks().forEach((t) => t.stop());
      this._mediaStream = null;
      console.log("[Voice] Microphone tracks released");
    }

    // Stop playback
    this._flushPlayback();

    // Close WebSocket
    if (this._ws) {
      if (this._ws.readyState === WebSocket.OPEN || this._ws.readyState === WebSocket.CONNECTING) {
        this._ws.close();
      }
      this._ws = null;
    }

    this._sessionReady = false;
    this._latestUserTranscript = null;
    this._activeInspectionId = null;
    this._activeEquipment = null;
    this._setState(ConnectionState.DISCONNECTED);
  }
}
