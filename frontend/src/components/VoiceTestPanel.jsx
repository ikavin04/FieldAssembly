import { useState, useRef, useCallback, useEffect } from "react";
import { VoiceAgent, ConnectionState } from "../services/voiceAgent";

/**
 * VoiceTestPanel — Minimal test UI for Step 3 voice pipeline verification.
 *
 * Shows connection state, user/agent transcripts, and connect/disconnect controls.
 */
export default function VoiceTestPanel({ inspectionId, equipment }) {
  const [connState, setConnState] = useState(ConnectionState.DISCONNECTED);
  const [transcripts, setTranscripts] = useState([]); // {role, text, partial}
  const [error, setError] = useState(null);
  const agentRef = useRef(null);

  // Lazily create the VoiceAgent instance
  const getAgent = useCallback(() => {
    if (!agentRef.current) {
      agentRef.current = new VoiceAgent({ inspectionId, equipment });
    }
    return agentRef.current;
  }, []);

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
        // Replace the last partial user entry with the final version
        const last = prev[prev.length - 1];
        if (last && last.role === "user" && last.partial) {
          return [...prev.slice(0, -1), { role: "user", text, partial: false }];
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
          return [...prev.slice(0, -1), { role: "agent", text, partial: false }];
        }
        return [...prev, { role: "agent", text, partial: false }];
      });
    };

    agent.onError = (msg) => setError(msg);

    agent.onSessionEnded = () => {
      setTranscripts((prev) => [...prev, { role: "system", text: "Session ended", partial: false }]);
    };

    return () => {
      agent.disconnect();
    };
  }, [getAgent, inspectionId, equipment]);

  const handleConnect = () => {
    setError(null);
    setTranscripts([]);
    getAgent().connect({ inspectionId, equipment });
  };

  const handleDisconnect = () => {
    getAgent().disconnect();
  };

  const isActive = connState !== ConnectionState.DISCONNECTED && connState !== ConnectionState.ERROR;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>🎙️ FieldVoice — Voice Pipeline Test</h2>

      {/* Status */}
      <div style={styles.status}>
        <span style={styles.statusLabel}>Status:</span>
        <span style={{ ...styles.statusValue, color: stateColor(connState) }}>
          {connState}
        </span>
      </div>

      {/* Error */}
      {error && <div style={styles.error}>⚠️ {error}</div>}

      {/* Controls */}
      <div style={styles.controls}>
        {!isActive ? (
          <button style={styles.btnConnect} onClick={handleConnect}>
            🔌 Connect &amp; Start Voice
          </button>
        ) : (
          <button style={styles.btnDisconnect} onClick={handleDisconnect}>
            ✋ Disconnect
          </button>
        )}
      </div>

      {/* Transcript */}
      <div style={styles.transcriptBox}>
        <h3 style={styles.transcriptTitle}>Conversation</h3>
        {transcripts.length === 0 && (
          <p style={styles.placeholder}>Transcripts will appear here...</p>
        )}
        {transcripts.map((t, i) => (
          <div key={i} style={styles.transcriptEntry}>
            <span style={{ ...styles.role, color: t.role === "user" ? "#60a5fa" : t.role === "agent" ? "#34d399" : "#9ca3af" }}>
              {t.role === "user" ? "You" : t.role === "agent" ? "FieldVoice" : "System"}:
            </span>
            <span style={{ ...styles.text, opacity: t.partial ? 0.6 : 1 }}>
              {t.text}
              {t.partial && <span style={styles.typing}>…</span>}
            </span>
          </div>
        ))}
      </div>

      {/* State legend */}
      <div style={styles.legend}>
        <small>
          {connState === ConnectionState.LISTENING && "🎤 Listening — speak now"}
          {connState === ConnectionState.THINKING && "🤔 Agent is thinking..."}
          {connState === ConnectionState.SPEAKING && "🔊 Agent is speaking"}
          {connState === ConnectionState.CONNECTING && "⏳ Connecting..."}
          {connState === ConnectionState.WAITING_FOR_SESSION && "⏳ Waiting for session..."}
        </small>
      </div>
    </div>
  );
}

function stateColor(state) {
  switch (state) {
    case ConnectionState.LISTENING: return "#34d399";
    case ConnectionState.SPEAKING: return "#fbbf24";
    case ConnectionState.THINKING: return "#a78bfa";
    case ConnectionState.CONNECTING:
    case ConnectionState.CONNECTED:
    case ConnectionState.WAITING_FOR_SESSION: return "#60a5fa";
    case ConnectionState.ERROR: return "#f87171";
    default: return "#9ca3af";
  }
}

const styles = {
  container: {
    maxWidth: 600,
    margin: "2rem auto",
    padding: "1.5rem",
    backgroundColor: "#111827",
    borderRadius: 12,
    border: "1px solid #1f2937",
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    color: "#e5e7eb",
  },
  title: {
    margin: "0 0 1rem",
    fontSize: "1.25rem",
    fontWeight: 600,
  },
  status: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: "0.75rem",
  },
  statusLabel: {
    fontSize: "0.875rem",
    color: "#9ca3af",
  },
  statusValue: {
    fontSize: "0.875rem",
    fontWeight: 600,
    fontFamily: "monospace",
  },
  error: {
    padding: "0.5rem 0.75rem",
    backgroundColor: "#7f1d1d",
    borderRadius: 8,
    fontSize: "0.875rem",
    marginBottom: "0.75rem",
  },
  controls: {
    display: "flex",
    gap: 8,
    marginBottom: "1rem",
  },
  btnConnect: {
    padding: "0.5rem 1.25rem",
    backgroundColor: "#059669",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "0.875rem",
  },
  btnDisconnect: {
    padding: "0.5rem 1.25rem",
    backgroundColor: "#dc2626",
    color: "#fff",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "0.875rem",
  },
  transcriptBox: {
    backgroundColor: "#0d1117",
    borderRadius: 8,
    padding: "1rem",
    minHeight: 200,
    maxHeight: 400,
    overflowY: "auto",
    marginBottom: "0.75rem",
  },
  transcriptTitle: {
    margin: "0 0 0.5rem",
    fontSize: "0.875rem",
    color: "#6b7280",
    fontWeight: 500,
  },
  placeholder: {
    color: "#4b5563",
    fontSize: "0.875rem",
    fontStyle: "italic",
  },
  transcriptEntry: {
    marginBottom: "0.5rem",
    lineHeight: 1.5,
  },
  role: {
    fontWeight: 600,
    marginRight: 6,
    fontSize: "0.875rem",
  },
  text: {
    fontSize: "0.875rem",
  },
  typing: {
    animation: "pulse 1s infinite",
  },
  legend: {
    textAlign: "center",
    color: "#6b7280",
    fontSize: "0.75rem",
  },
};
