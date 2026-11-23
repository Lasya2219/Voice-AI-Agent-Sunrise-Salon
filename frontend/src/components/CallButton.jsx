
export default function CallButton({
  status,
  muted,
  onStartCall,
  onEndCall,
  onToggleMute,
}) {
  const isConnected = status === "connected";
  const isConnecting = status === "connecting";

  return (
    <div className="call-controls">
      {!isConnected ? (
        <button
          className="call-button start-button"
          onClick={onStartCall}
          disabled={isConnecting}
        >
          {isConnecting ? "Connecting..." : "Start Conversation"}
        </button>
      ) : (
        <>
          <button
            className="call-button mute-button"
            onClick={onToggleMute}
          >
            {muted ? "Unmute" : "Mute"}
          </button>

          <button
            className="call-button end-button"
            onClick={onEndCall}
          >
            End Call
          </button>
        </>
      )}
    </div>
  );
}
