import { useEffect, useRef } from "react";
import { MessageSquare, User, Bot, Trash2 } from "lucide-react";

export default function TranscriptFeed({ transcripts, onClearTranscripts, isLive }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcripts]);

  const formatTime = (ts) => {
    if (!ts) return "";
    const date = new Date(ts);
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  return (
    <div className="transcript-panel">
      <div className="transcript-header">
        <div className="transcript-title">
          <MessageSquare className="panel-icon" />
          <span>Live Conversation Transcript</span>
          {isLive && <span className="transcript-live-dot" title="Listening actively" />}
        </div>
        {transcripts.length > 0 && (
          <button
            type="button"
            className="clear-transcript-btn"
            onClick={onClearTranscripts}
            title="Clear transcript history"
          >
            <Trash2 className="btn-icon-sm" />
            <span>Clear</span>
          </button>
        )}
      </div>

      <div className="transcript-stream" ref={scrollRef}>
        {transcripts.length === 0 ? (
          <div className="transcript-empty-state">
            <p className="empty-lead">No speech transcribed yet.</p>
            <p className="empty-sub">
              Start talking to the receptionist. Transcribed turns will stream here in real time.
            </p>
          </div>
        ) : (
          transcripts.map((entry) => {
            const isAgent = entry.role === "agent";
            return (
              <div
                key={entry.id || `${entry.role}-${entry.timestamp}`}
                className={`transcript-message ${isAgent ? "agent-message" : "user-message"}`}
              >
                <div className="message-sender-tag">
                  {isAgent ? (
                    <>
                      <Bot className="sender-icon" />
                      <span className="sender-name">Receptionist</span>
                    </>
                  ) : (
                    <>
                      <User className="sender-icon" />
                      <span className="sender-name">You</span>
                    </>
                  )}
                  {entry.timestamp && (
                    <span className="message-timestamp">{formatTime(entry.timestamp)}</span>
                  )}
                </div>
                <div className="message-bubble">
                  <p>{entry.text}</p>
                  {!entry.isFinal && <span className="streaming-cursor">...</span>}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
