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
const BACKEND_BASE = ""; // empty string = same-origin (Vite proxy handles /api)

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
  process(inputs) {
    const input = inputs[0];
    if (input && input[0] && input[0].length > 0) {
      // Clone the Float32 samples and send to main thread
      this.port.postMessage(new Float32Array(input[0]));
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
        this.onError?.("WebSocket connection error");
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

  _handleMessage(event) {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      console.warn("[Voice] Non-JSON message received");
      return;
    }

    switch (msg.type) {
      case "session.ready":
        console.log("[Voice] session.ready");
        this._sessionReady = true;
        this._setState(ConnectionState.LISTENING);
        this._startMicrophone();
        break;

      case "session.updated":
        console.log("[Voice] session.updated");
        break;

      case "input.speech.started":
        console.log("[Voice] User started speaking");
        if (this._state === ConnectionState.SPEAKING) {
          // User interrupted the agent — flush queued audio
          this._flushPlayback();
        }
        this._setState(ConnectionState.LISTENING);
        break;

      case "input.speech.stopped":
        console.log("[Voice] User stopped speaking");
        this._setState(ConnectionState.THINKING);
        break;

      case "transcript.user.delta":
        this.onUserTranscriptDelta?.(msg.text || msg.delta || "");
        break;

      case "transcript.user":
        console.log("[Voice] User transcript received");
        this._latestUserTranscript = msg.text || "";
        this.onUserTranscript?.(msg.text || "");
        break;

      case "reply.started":
        console.log("[Voice] Agent reply started");
        this._setState(ConnectionState.SPEAKING);
        break;

      case "reply.audio":
        this._handleReplyAudio(msg);
        break;

      case "transcript.agent.delta":
        this.onAgentTranscriptDelta?.(msg.text || msg.delta || "");
        break;

      case "transcript.agent":
        console.log("[Voice] Agent transcript received");
        this.onAgentTranscript?.(msg.text || "");
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
        this.onError?.(msg.error?.message || msg.error || "Session error");
        break;

      case "session.ended":
        console.log("[Voice] Session ended");
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
    if (toolName === "save_observation" && !this._activeInspectionId) {
      this._pendingToolResults.push({
        callId,
        result: Promise.resolve({ success: false, error: "No active inspection context" }),
      });
      return;
    }
    if (toolName === "save_observation") {
      if (argumentsObject.inspection_id && Number(argumentsObject.inspection_id) !== Number(this._activeInspectionId)) {
        console.warn("[Voice] Replacing mismatched inspection_id from tool call");
      }
      argumentsObject.inspection_id = Number(this._activeInspectionId);
    }
    if (toolName === "save_observation" && !argumentsObject.evidence_text && this._latestUserTranscript) {
      argumentsObject.evidence_text = this._latestUserTranscript;
      this._latestUserTranscript = null;
    }

    console.log("[Voice] Tool call arguments", toolName, argumentsObject);
    const toolPromise = Promise.resolve().then(() =>
      executeVoiceTool(toolName, argumentsObject)
    ).catch((err) => ({ success: false, error: err.message }));

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
      console.log("[Voice] Requesting microphone");
      this._mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: SAMPLE_RATE,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // Create AudioContext at the target sample rate
      this._audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });

      // Register worklet processor from inline source
      const blob = new Blob([WORKLET_PROCESSOR_CODE], { type: "application/javascript" });
      const workletUrl = URL.createObjectURL(blob);
      await this._audioContext.audioWorklet.addModule(workletUrl);
      URL.revokeObjectURL(workletUrl);

      // Create nodes
      this._sourceNode = this._audioContext.createMediaStreamSource(this._mediaStream);
      this._workletNode = new AudioWorkletNode(this._audioContext, "pcm-capture-processor");

      // Receive Float32 samples from audio thread
      this._workletNode.port.onmessage = (e) => {
        if (!this._sessionReady) return;
        if (this._ws?.readyState !== WebSocket.OPEN) return;

        const float32 = e.data;
        const pcm16 = this._float32ToPcm16(float32);
        const base64 = this._arrayBufferToBase64(pcm16.buffer);

        this._ws.send(JSON.stringify({
          type: "input.audio",
          audio: base64,
        }));
      };

      this._sourceNode.connect(this._workletNode);
      this._workletNode.connect(this._audioContext.destination); // required to keep worklet alive
      console.log("[Voice] Microphone started");
    } catch (err) {
      console.error("[Voice] Microphone error:", err.message);
      this._setState(ConnectionState.ERROR);
      this.onError?.(`Microphone access failed: ${err.message}`);
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
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
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
      if (this._nextPlaybackTime <= this._playbackCtx.currentTime + 0.05) {
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
