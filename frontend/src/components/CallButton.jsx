import React from 'react';
import { PhoneCall, PhoneOff, Mic, MicOff, Loader2 } from 'lucide-react';

export default function CallButton({
  status, // 'idle' | 'connecting' | 'connected' | 'speaking' | 'listening'
  isMuted,
  onStartCall,
  onEndCall,
  onToggleMute,
}) {
  const isCallActive = status !== 'idle';

  return (
    <div className="call-controls-container">
      {!isCallActive ? (
        <button
          className="btn-call-primary"
          onClick={onStartCall}
          type="button"
          aria-label="Call Receptionist"
        >
          <span className="btn-call-pulse"></span>
          <PhoneCall className="icon-pulse" size={28} />
          <div className="btn-call-text">
            <strong>Call Receptionist</strong>
            <small>Speak directly with AI</small>
          </div>
        </button>
      ) : (
        <div className="active-call-bar">
          <button
            className={`btn-control btn-mute ${isMuted ? 'muted' : ''}`}
            onClick={onToggleMute}
            type="button"
            title={isMuted ? 'Unmute microphone' : 'Mute microphone'}
          >
            {isMuted ? <MicOff size={22} /> : <Mic size={22} />}
            <span>{isMuted ? 'Unmute' : 'Mute'}</span>
          </button>

          <button
            className="btn-control btn-end-call"
            onClick={onEndCall}
            type="button"
            title="End Call"
          >
            <PhoneOff size={24} />
            <span>End Call</span>
          </button>
        </div>
      )}
    </div>
  );
}
