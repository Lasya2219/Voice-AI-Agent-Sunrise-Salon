import React from 'react';
import { Volume2, VolumeX, Mic, Activity } from 'lucide-react';

export default function CallStatus({
  status, // 'idle' | 'connecting' | 'connected' | 'speaking' | 'listening'
  duration = 0,
  isMuted = false,
  agentSpeaking = false,
}) {
  const formatDuration = (secs) => {
    const mins = Math.floor(secs / 60);
    const remaining = secs % 60;
    return `${mins.toString().padStart(2, '0')}:${remaining.toString().padStart(2, '0')}`;
  };

  const getStatusText = () => {
    switch (status) {
      case 'connecting':
        return 'Connecting to Sunrise Salon...';
      case 'speaking':
        return 'Receptionist is speaking...';
      case 'listening':
        return isMuted ? 'Microphone Muted' : 'Listening... Speak naturally';
      case 'connected':
        return 'Call Connected';
      default:
        return 'AI Receptionist is Online & Ready';
    }
  };

  const getStatusBadgeClass = () => {
    switch (status) {
      case 'speaking':
        return 'status-badge speaking';
      case 'listening':
        return isMuted ? 'status-badge muted' : 'status-badge listening';
      case 'connecting':
        return 'status-badge connecting';
      case 'connected':
        return 'status-badge active';
      default:
        return 'status-badge idle';
    }
  };

  const isCallActive = status !== 'idle';

  return (
    <div className="call-status-wrapper">
      <div className="status-header">
        <div className={getStatusBadgeClass()}>
          <span className="pulse-dot"></span>
          <span className="status-label">{getStatusText()}</span>
        </div>

        {isCallActive && (
          <div className="call-duration">
            <Activity size={16} className="duration-icon" />
            <span>{formatDuration(duration)}</span>
          </div>
        )}
      </div>

      {isCallActive && (
        <div className={`audio-visualizer ${status === 'speaking' || status === 'listening' ? 'active' : ''}`}>
          <div className="wave-bar bar-1"></div>
          <div className="wave-bar bar-2"></div>
          <div className="wave-bar bar-3"></div>
          <div className="wave-bar bar-4"></div>
          <div className="wave-bar bar-5"></div>
          <div className="wave-bar bar-6"></div>
          <div className="wave-bar bar-7"></div>
          <div className="wave-bar bar-8"></div>
        </div>
      )}
    </div>
  );
}
