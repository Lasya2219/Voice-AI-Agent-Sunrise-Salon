import { Scissors, Sparkles, MapPin, Clock } from "lucide-react";

export default function Navbar({ agentState }) {
  const isCallActive = agentState !== "disconnected";

  return (
    <header className="salon-navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <div className="brand-logo-badge">
            <Scissors className="brand-scissors-icon" />
            <Sparkles className="brand-sparkle-icon" />
          </div>
          <div className="brand-text-block">
            <h1 className="brand-title">SUNRISE SALON</h1>
            <p className="brand-tagline">
              <MapPin className="inline-icon" /> Indiranagar, Bengaluru
            </p>
          </div>
        </div>

        <div className="navbar-meta">
          <div className="meta-pill hours-pill">
            <Clock className="inline-icon" />
            <span>Tue – Sun: 09:00 AM – 08:00 PM</span>
          </div>

          <div className={`meta-pill status-pill ${isCallActive ? "active" : ""}`}>
            <span className={`status-dot ${agentState}`} />
            <span className="status-label">
              {isCallActive ? `Voice AI: ${agentState.toUpperCase()}` : "AI Receptionist Ready"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
