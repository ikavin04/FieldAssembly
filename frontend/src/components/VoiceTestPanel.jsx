import { useState, useRef, useCallback, useEffect } from "react";
import { VoiceAgent, ConnectionState } from "../services/voiceAgent";

/**
 * VoiceTestPanel — Minimalist, theme-aligned Voice Assistant component.
 *
 * Extended with:
 * - Real-time Live Activity Timeline (Core 6)
 * - Tabs to switch between Conversation Transcript and Live Activity
 * - Direct hooks for observations, tickets, alerts, and inspection completion
 */
export default function VoiceTestPanel({
  inspectionId,
  equipment,
  onObservationSaved,
  onInspectionCompleted,
  onTicketCreated,
  onAlertCreated,
  onActivityEvent,
}) {
  const [connState, setConnState] = useState(ConnectionState.DISCONNECTED);
  const [transcripts, setTranscripts] = useState([]); // {role, text, partial}
  const [activities, setActivities] = useState([]); // {id, timestamp, type, status, message, metadata}
  const [activeTab, setActiveTab] = useState("transcript"); // 'transcript' | 'activity'
  const [error, setError] = useState(null);
  const agentRef = useRef(null);
  const transcriptEndRef = useRef(null);
  const activityEndRef = useRef(null);

  // Lazily create the VoiceAgent instance
  const getAgent = useCallback(() => {
    if (!agentRef.current) {
      agentRef.current = new VoiceAgent({ inspectionId, equipment });
    }
    return agentRef.current;
  }, [inspectionId, equipment]);

  // Wire up callbacks once
  useEffect(() => {
    const agent = getAgent();

    agent.onStateChange = (state) => setConnState(state);

    agent.onUserTranscriptDelta = (text) => {
      setTranscripts((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "user" && last.partial) {
          return [...prev.slice(0, -1), { role: "user", text: (last.text || "") + text, partial: true }];
        }
        return [...prev, { role: "user", text, partial: true }];
      });
    };

    agent.onUserTranscript = (text) => {
      setTranscripts((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "user" && last.partial) {
          return [...prev.slice(0, -1), { role: "user", text: (last.text || "") + text, partial: false }];
        }
        return [...prev, { role: "user", text, partial: false }];
      });
    };

    agent.onAgentTranscriptDelta = (text) => {
      setTranscripts((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "agent" && last.partial) {
          return [...prev.slice(0, -1), { role: "agent", text: (last.text || "") + text, partial: true }];
        }
        return [...prev, { role: "agent", text, partial: true }];
      });
    };

    agent.onAgentTranscript = (text) => {
      setTranscripts((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === "agent" && last.partial) {
          return [...prev.slice(0, -1), { role: "agent", text: (last.text || "") + text, partial: false }];
        }
        return [...prev, { role: "agent", text, partial: false }];
      });
    };

    agent.onActivityEvent = (event) => {
      setActivities((prev) => [...prev.slice(-49), event]);
      onActivityEvent?.(event);
    };

    agent.onObservationSaved = (res) => {
      onObservationSaved?.(res);
    };

    agent.onInspectionCompleted = (res) => {
      onInspectionCompleted?.(res);
    };

    agent.onTicketCreated = (res) => {
      onTicketCreated?.(res);
    };

    agent.onAlertCreated = (res) => {
      onAlertCreated?.(res);
    };

    agent.onError = (msg) => setError(msg);

    agent.onSessionEnded = () => {
      setTranscripts((prev) => [...prev, { role: "system", text: "Session ended", partial: false }]);
    };

    return () => {
      agent.disconnect();
    };
  }, [getAgent, inspectionId, equipment, onObservationSaved, onInspectionCompleted, onTicketCreated, onAlertCreated, onActivityEvent]);

  // Smooth scroll to bottom when new transcript lines arrive
  useEffect(() => {
    if (activeTab === "transcript") {
      transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [transcripts, activeTab]);

  // Smooth scroll when activity entries arrive
  useEffect(() => {
    if (activeTab === "activity") {
      activityEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [activities, activeTab]);

  const handleConnect = () => {
    setError(null);
    setTranscripts([]);
    setActivities([]);
    getAgent().connect({ inspectionId, equipment });
  };

  const handleDisconnect = () => {
    getAgent().disconnect();
  };

  const isActive = connState !== ConnectionState.DISCONNECTED && connState !== ConnectionState.ERROR;

  const statusMeta = getStatusMeta(connState);

  return (
    <div className="voice-panel-card">
      {/* Header */}
      <div className="voice-panel-header">
        <div className="voice-panel-title-wrap">
          <p className="eyebrow">Voice Assistant</p>
          <h2>Hands-free capture</h2>
        </div>
        <div className={`voice-panel-status-pill ${statusMeta.className}`}>
          <span className="voice-status-dot" />
          <span>{statusMeta.label}</span>
        </div>
      </div>

      {/* Error alert */}
      {error && (
        <div className="voice-panel-error" role="alert">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Action Controls & Visualizer */}
      <div className="voice-panel-controls">
        {!isActive ? (
          <button className="voice-btn-connect" onClick={handleConnect}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
            <span>Connect &amp; Start Voice</span>
          </button>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: "12px", width: "100%", justifyContent: "space-between", flexWrap: "wrap" }}>
            <div className="voice-active-indicator">
              <div className="voice-wave-bars">
                <span className="wave-bar" />
                <span className="wave-bar" />
                <span className="wave-bar" />
                <span className="wave-bar" />
                <span className="wave-bar" />
              </div>
              <span>{statusMeta.tip}</span>
            </div>
            <button className="voice-btn-disconnect" onClick={handleDisconnect}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect width="18" height="18" x="3" y="3" rx="2" />
              </svg>
              <span>Disconnect</span>
            </button>
          </div>
        )}
      </div>

      {/* Box Header with Tabs */}
      <div className="voice-transcript-box">
        <div className="voice-transcript-header">
          <div className="voice-tab-group" role="tablist">
            <button
              type="button"
              className={`voice-tab-btn ${activeTab === "transcript" ? "active" : ""}`}
              onClick={() => setActiveTab("transcript")}
            >
              Conversation {transcripts.length > 0 ? `(${transcripts.length})` : ""}
            </button>
            <button
              type="button"
              className={`voice-tab-btn ${activeTab === "activity" ? "active" : ""}`}
              onClick={() => setActiveTab("activity")}
            >
              Live Activity {activities.length > 0 ? `(${activities.length})` : ""}
            </button>
          </div>
          <span>
            {activeTab === "transcript"
              ? (transcripts.length > 0 ? `${transcripts.length} entries` : "Live feed")
              : `${activities.length} events`}
          </span>
        </div>

        {/* Tab 1: Conversation Transcript */}
        {activeTab === "transcript" && (
          transcripts.length === 0 ? (
            <div className="voice-transcript-empty">
              <div className="empty-mic-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="22" />
                </svg>
              </div>
              <p>
                {isActive
                  ? "Listening... speak observations naturally, like “Temperature is 40 degrees, pressure is 91 PSI, vibration normal, no leakage”."
                  : "Click “Connect & Start Voice” to begin speaking with FieldVoice."}
              </p>
            </div>
          ) : (
            <div>
              {transcripts.map((t, i) => (
                <div key={i} className={`voice-bubble ${t.role}`}>
                  {t.role !== "system" && (
                    <div className="voice-bubble-meta">
                      <span>{t.role === "user" ? "You" : "FieldVoice"}</span>
                    </div>
                  )}
                  <div className="voice-bubble-text" style={{ opacity: t.partial ? 0.75 : 1 }}>
                    {t.text}
                    {t.partial && <span className="voice-typing-dots">…</span>}
                  </div>
                </div>
              ))}
              <div ref={transcriptEndRef} />
            </div>
          )
        )}

        {/* Tab 2: Live Activity Timeline */}
        {activeTab === "activity" && (
          activities.length === 0 ? (
            <div className="voice-transcript-empty">
              <p>No voice, tool, or validation events recorded yet. Connect and speak to see live backend events.</p>
            </div>
          ) : (
            <div className="voice-activity-stream">
              {activities.map((act) => {
                const categoryLabel = {
                  speech: act.metadata?.role === "user" ? "YOU" : "FIELDVOICE",
                  tool_call: "TOOL",
                  tool_result: "BACKEND",
                  validation: "VALIDATION",
                  action: "ACTION",
                  system: "SYSTEM",
                  error: "ERROR",
                }[act.type] || "ACTIVITY";

                const badgeClass = {
                  completed: "act-badge-success",
                  warning: "act-badge-warning",
                  pending: "act-badge-pending",
                  error: "act-badge-error",
                }[act.status] || "act-badge-neutral";

                return (
                  <div key={act.id} className={`voice-activity-item ${badgeClass}`}>
                    <div className="voice-activity-meta">
                      <span className="voice-activity-time">{act.timestamp}</span>
                      <span className={`voice-activity-badge ${badgeClass}`}>{categoryLabel}</span>
                    </div>
                    <div className="voice-activity-message">{act.message}</div>
                  </div>
                );
              })}
              <div ref={activityEndRef} />
            </div>
          )
        )}
      </div>

      {/* Footer Helper */}
      <p className="voice-panel-tips">
        <span style={{ color: "#2f6558" }}>∿</span>
        <span>Voice assistant automatically records observations and validates operating limits in real time.</span>
      </p>
    </div>
  );
}

function getStatusMeta(state) {
  switch (state) {
    case ConnectionState.LISTENING:
      return { label: "Listening", tip: "Listening... speak now", className: "listening" };
    case ConnectionState.SPEAKING:
      return { label: "Speaking", tip: "Agent is speaking...", className: "speaking" };
    case ConnectionState.THINKING:
      return { label: "Thinking", tip: "Analyzing observation...", className: "thinking" };
    case ConnectionState.CONNECTING:
    case ConnectionState.WAITING_FOR_SESSION:
      return { label: "Connecting", tip: "Establishing voice session...", className: "connecting" };
    case ConnectionState.CONNECTED:
      return { label: "Connected", tip: "Voice session active", className: "connected" };
    case ConnectionState.ERROR:
      return { label: "Issue", tip: "Connection error", className: "error" };
    default:
      return { label: "Ready to connect", tip: "Click connect to begin", className: "disconnected" };
  }
}
