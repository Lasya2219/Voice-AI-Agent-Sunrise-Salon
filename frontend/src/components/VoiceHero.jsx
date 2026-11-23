import {
  Mic,
  MicOff,
  PhoneCall,
  PhoneOff,
  Sparkles,
  Loader2,
  Volume2,
  AlertCircle,
  FileText,
  Radio,
} from "lucide-react";

export default function VoiceHero({
  agentState,
  isMuted,
  callDuration,
  errorMessage,
  onStartCall,
  onEndCall,
  onToggleMute,
  onToggleTranscripts,
  showTranscripts,
  transcriptCount,
}) {
  const isConnected = agentState !== "disconnected" && agentState !== "connecting";
  const isConnecting = agentState === "connecting";

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const stateDetails = {
    disconnected: {
      label: "Ready to assist you",
      subtitle: "Speak naturally to book, check availability, reschedule, or ask questions.",
      badgeClass: "badge-disconnected",
      icon: <Sparkles className="state-badge-icon" />,
    },
    connecting: {
      label: "Connecting to receptionist...",
      subtitle: "Establishing secure voice channel with Sunrise Salon...",
      badgeClass: "badge-connecting",
      icon: <Loader2 className="state-badge-icon spin" />,
    },
    listening: {
      label: "Listening to you...",
      subtitle: "Go ahead, speak clearly into your microphone.",
      badgeClass: "badge-listening",
      icon: <Mic className="state-badge-icon pulse" />,
    },
    thinking: {
      label: "Checking details...",
      subtitle: "Processing your request with the salon system...",
      badgeClass: "badge-thinking",
      icon: <Sparkles className="state-badge-icon pulse" />,
    },
    speaking: {
      label: "Receptionist is speaking...",
      subtitle: "Feel free to interrupt at any time if you want to clarify.",
      badgeClass: "badge-speaking",
      icon: <Volume2 className="state-badge-icon soundwave" />,
    },
  };

  const current = stateDetails[agentState] || stateDetails.disconnected;

  return (
    <section className="voice-hero-card">
      {/* Top Card Badge Bar */}
      <div className="voice-hero-header">
        <div className={`live-badge ${current.badgeClass}`}>
          {current.icon}
          <span className="live-badge-text">
            {isConnected ? `LIVE • ${formatDuration(callDuration)}` : isConnecting ? "CONNECTING" : "AI RECEPTIONIST"}
          </span>
        </div>

        {isConnected && (
          <button
            type="button"
            className={`transcript-toggle-btn ${showTranscripts ? "active" : ""}`}
            onClick={onToggleTranscripts}
            title="Toggle live conversation transcripts"
          >
            <FileText className="btn-icon" />
            <span>Transcript</span>
            {transcriptCount > 0 && <span className="transcript-counter">{transcriptCount}</span>}
          </button>
        )}
      </div>

      {/* Luxury Voice Visualizer / Orb */}
      <div className="orb-wrapper">
        <div className={`salon-voice-orb state-${agentState}`}>
          <div className="orb-halo-outer" />
          <div className="orb-halo-middle" />
          <div className="orb-core">
            {isConnecting ? (
              <Loader2 className="orb-center-icon spin" />
            ) : agentState === "speaking" ? (
              <Volume2 className="orb-center-icon" />
            ) : agentState === "listening" ? (
              <Mic className="orb-center-icon" />
            ) : agentState === "thinking" ? (
              <Sparkles className="orb-center-icon" />
            ) : (
              <Radio className="orb-center-icon" />
            )}
          </div>
        </div>
      </div>

      {/* Dynamic Status Text */}
      <div className="voice-status-content">
        <h2 className="voice-status-title">{current.label}</h2>
        <p className="voice-status-subtitle">{current.subtitle}</p>
      </div>

      {/* Error notification banner if any */}
      {errorMessage && (
        <div className="voice-error-banner" role="alert">
          <AlertCircle className="error-icon" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Interactive Call Controls */}
      <div className="voice-controls-bar">
        {!isConnected && !isConnecting ? (
          <button
            type="button"
            className="control-btn call-start-btn"
            onClick={onStartCall}
          >
            <PhoneCall className="btn-icon-lg" />
            <span>Call Salon Receptionist</span>
          </button>
        ) : (
          <div className="active-controls-group">
            <button
              type="button"
              className={`control-btn mute-toggle-btn ${isMuted ? "muted" : ""}`}
              onClick={onToggleMute}
              title={isMuted ? "Unmute Microphone" : "Mute Microphone"}
            >
              {isMuted ? <MicOff className="btn-icon" /> : <Mic className="btn-icon" />}
              <span>{isMuted ? "Unmute" : "Mute Mic"}</span>
            </button>

            <button
              type="button"
              className="control-btn call-end-btn"
              onClick={onEndCall}
              title="End conversation"
            >
              <PhoneOff className="btn-icon" />
              <span>End Call</span>
            </button>
          </div>
        )}
      </div>

      {/* Subtle feature reassurance points */}
      <div className="hero-features-ribbon">
        <span className="ribbon-tag">✨ Real-time slot checks</span>
        <span className="ribbon-tag">🔒 Double-confirmation booking</span>
        <span className="ribbon-tag">⚡ Natural interruptions supported</span>
      </div>
    </section>
  );
}
