
export default function CallStatus({ status, agentSpeaking }) {
  const statusMessages = {
    idle: "Ready to assist you",
    connecting: "Connecting to your receptionist...",
    connected: agentSpeaking
      ? "Your receptionist is speaking"
      : "Listening to you...",
    disconnected: "Call ended",
    error: "Connection failed. Please try again.",
  };

  return (
    <div className={`call-status ${status}`}>
      <div className="status-indicator" />

      <p>{statusMessages[status] || "Ready to assist you"}</p>
    </div>
  );
}
