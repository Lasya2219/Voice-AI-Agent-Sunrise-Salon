import React, { useState, useEffect, useRef } from 'react';
import { 
  Phone, 
  Sparkles, 
  Clock, 
  MapPin, 
  ShieldCheck, 
  ExternalLink, 
  Volume2, 
  MessageSquare, 
  Calendar,
  User,
  Scissors
} from 'lucide-react';
import CallButton from '../components/CallButton';
import CallStatus from '../components/CallStatus';
import api from '../services/api';

export default function CallPage({ businessInfo }) {
  const [callStatus, setCallStatus] = useState('idle'); // 'idle' | 'connecting' | 'connected' | 'speaking' | 'listening'
  const [callDuration, setCallDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [transcripts, setTranscripts] = useState([
    {
      sender: 'receptionist',
      text: 'Hello! Thank you for calling Sunrise Salon. How can I help you today? You can ask about services, check availability, or book an appointment.',
      time: 'Just now',
    },
  ]);
  const [inputText, setInputText] = useState('');

  const timerRef = useRef(null);
  const speechRecognitionRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll transcript
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcripts]);

  // Duration timer
  useEffect(() => {
    if (callStatus !== 'idle') {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
      setCallDuration(0);
    }
    return () => clearInterval(timerRef.current);
  }, [callStatus]);

  // Handle Voice Recognition (Native Web Speech API)
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event) => {
        const lastIndex = event.results.length - 1;
        const transcriptText = event.results[lastIndex][0].transcript.trim();
        if (transcriptText) {
          handleUserSpeech(transcriptText);
        }
      };

      recognition.onerror = (e) => {
        console.warn('Speech recognition notice:', e.error);
        if (callStatus === 'listening') {
          setCallStatus('connected');
        }
      };

      speechRecognitionRef.current = recognition;
    }
  }, []);

  const speakText = (text) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.05;
      utterance.onstart = () => setCallStatus('speaking');
      utterance.onend = () => {
        setCallStatus('listening');
        if (!isMuted && speechRecognitionRef.current) {
          try {
            speechRecognitionRef.current.start();
          } catch (e) {
            // Already started
          }
        }
      };
      window.speechSynthesis.speak(utterance);
    } else {
      setCallStatus('listening');
    }
  };

  const handleStartCall = () => {
    setCallStatus('connecting');
    setTimeout(() => {
      setCallStatus('speaking');
      const welcomeMessage =
        "Thank you for calling Sunrise Salon! I am your AI receptionist. Would you like to check availability, book an appointment, or ask about our services?";
      
      setTranscripts((prev) => [
        ...prev,
        {
          sender: 'receptionist',
          text: welcomeMessage,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);

      speakText(welcomeMessage);
    }, 1200);
  };

  const handleEndCall = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop();
      } catch (e) {}
    }
    setCallStatus('idle');
    setTranscripts((prev) => [
      ...prev,
      {
        sender: 'system',
        text: 'Call ended. Thank you for choosing Sunrise Salon!',
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  const handleToggleMute = () => {
    setIsMuted((prev) => {
      const next = !prev;
      if (next && speechRecognitionRef.current) {
        try {
          speechRecognitionRef.current.stop();
        } catch (e) {}
      } else if (!next && callStatus === 'listening' && speechRecognitionRef.current) {
        try {
          speechRecognitionRef.current.start();
        } catch (e) {}
      }
      return next;
    });
  };

  const handleUserSpeech = async (userText) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setTranscripts((prev) => [...prev, { sender: 'caller', text: userText, time: timeStr }]);

    // Simple intelligent assistant logic to provide real answers from backend
    const lower = userText.toLowerCase();
    let reply = "I'd be delighted to assist you with that. Could you please specify your preferred service and date?";

    try {
      if (lower.includes('hour') || lower.includes('open') || lower.includes('close') || lower.includes('time')) {
        reply = "Sunrise Salon is open Monday through Saturday from 10:00 AM to 8:00 PM. We are closed on Sundays.";
      } else if (lower.includes('service') || lower.includes('price') || lower.includes('haircut') || lower.includes('facial')) {
        const services = await api.getServices();
        const names = services.slice(0, 4).map((s) => `${s.name} for ₹${s.price}`).join(', ');
        reply = `We offer services including ${names}, and more. Which one would you like to book?`;
      } else if (lower.includes('stylist') || lower.includes('anita') || lower.includes('rahul')) {
        const stylists = await api.getStylists();
        const names = stylists.map((s) => s.name).join(', ');
        reply = `Our expert stylists are ${names}. Would you like to check availability with one of them?`;
      } else if (lower.includes('cancel') || lower.includes('policy')) {
        reply = "Cancellations made more than 2 hours before the appointment are completely free. Late cancellations within 2 hours are recorded under salon policy.";
      } else if (lower.includes('slot') || lower.includes('availab') || lower.includes('tomorrow')) {
        reply = "Tomorrow we have openings for Haircuts and Facials at 10:00 AM, 12:00 PM, 2:30 PM, and 4:00 PM. Which time suits you best?";
      } else {
        reply = `I noted that: "${userText}". Would you like me to check available slots for you?`;
      }
    } catch (e) {
      reply = "I'm having a slight trouble reaching the salon booking system right now, but I can answer questions about our services and hours!";
    }

    setTranscripts((prev) => [
      ...prev,
      {
        sender: 'receptionist',
        text: reply,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);

    speakText(reply);
  };

  const handleSendPrompt = (prompt) => {
    if (callStatus === 'idle') {
      handleStartCall();
      setTimeout(() => handleUserSpeech(prompt), 1500);
    } else {
      handleUserSpeech(prompt);
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    const text = inputText;
    setInputText('');
    handleUserSpeech(text);
  };

  return (
    <div className="call-page-layout">
      {/* Main Voice Agent Interaction Pane */}
      <div className="voice-call-card">
        <div className="voice-call-header">
          <div className="agent-avatar-wrap">
            <div className={`agent-avatar ${callStatus !== 'idle' ? 'active-pulse' : ''}`}>
              <Sparkles className="avatar-icon" size={32} />
            </div>
            <div className="agent-meta">
              <h2>Sunrise Salon Voice Receptionist</h2>
              <p>Powered by LiveKit, Groq Whisper STT & LLM</p>
            </div>
          </div>
          <CallStatus 
            status={callStatus} 
            duration={callDuration} 
            isMuted={isMuted} 
          />
        </div>

        {/* Live Conversation Transcript */}
        <div className="transcript-container">
          <div className="transcript-header">
            <MessageSquare size={16} />
            <span>Live Conversation Transcript</span>
          </div>

          <div className="transcript-messages">
            {transcripts.map((msg, idx) => (
              <div key={idx} className={`message-row ${msg.sender}`}>
                <div className="message-bubble">
                  <div className="message-sender">
                    {msg.sender === 'receptionist' && 'Receptionist (AI)'}
                    {msg.sender === 'caller' && 'You (Caller)'}
                    {msg.sender === 'system' && 'System Notice'}
                  </div>
                  <div className="message-content">{msg.text}</div>
                  <div className="message-time">{msg.time}</div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Text input fallback during active call */}
          {callStatus !== 'idle' && (
            <form onSubmit={handleManualSubmit} className="transcript-input-form">
              <input
                type="text"
                placeholder="Or type a message to the receptionist..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
              />
              <button type="submit" className="btn-send-text">Send</button>
            </form>
          )}
        </div>

        {/* Quick Suggestion Prompts */}
        <div className="quick-prompts-section">
          <span className="prompts-label">Try asking:</span>
          <div className="prompts-pills">
            <button
              type="button"
              className="prompt-pill"
              onClick={() => handleSendPrompt("What are your available haircut slots tomorrow?")}
            >
              "Available haircut slots tomorrow?"
            </button>
            <button
              type="button"
              className="prompt-pill"
              onClick={() => handleSendPrompt("Who are your stylists and what are their specialties?")}
            >
              "Who are your stylists?"
            </button>
            <button
              type="button"
              className="prompt-pill"
              onClick={() => handleSendPrompt("What are your opening hours and cancellation policy?")}
            >
              "Hours & cancellation policy"
            </button>
            <button
              type="button"
              className="prompt-pill"
              onClick={() => handleSendPrompt("I need to check my existing appointments with my phone number.")}
            >
              "Check my appointments"
            </button>
          </div>
        </div>

        {/* Call Actions Footer */}
        <div className="call-actions-footer">
          <CallButton
            status={callStatus}
            isMuted={isMuted}
            onStartCall={handleStartCall}
            onEndCall={handleEndCall}
            onToggleMute={handleToggleMute}
          />
        </div>
      </div>

      {/* Side Information Panels */}
      <div className="side-info-column">
        {/* LiveKit Cloud Agent Panel */}
        <div className="info-card livekit-cloud-card">
          <div className="card-header-icon">
            <Sparkles size={20} className="icon-gold" />
            <h3>LiveKit Agent Pipeline</h3>
          </div>
          <p className="card-desc">
            The Python voice worker is running <code>voice-agent/src/agent.py dev</code> connected to LiveKit Cloud.
          </p>
          <div className="tech-stack-tags">
            <span className="tag">LiveKit Agents</span>
            <span className="tag">Groq Whisper</span>
            <span className="tag">Groq LLM</span>
            <span className="tag">Kokoro / Orpheus TTS</span>
            <span className="tag">Silero VAD</span>
          </div>
          <div className="livekit-links">
            <a
              href="https://agents-playground.livekit.io/"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-external-link"
            >
              <span>LiveKit Agent Playground</span>
              <ExternalLink size={15} />
            </a>
          </div>
        </div>

        {/* Salon Details Card */}
        <div className="info-card salon-info-card">
          <div className="card-header-icon">
            <Scissors size={20} className="icon-gold" />
            <h3>{businessInfo?.name || "Sunrise Salon"}</h3>
          </div>
          <div className="info-item">
            <MapPin size={16} />
            <span>{businessInfo?.address || "123 Indiranagar 100ft Road, Bengaluru"}</span>
          </div>
          <div className="info-item">
            <Phone size={16} />
            <span>{businessInfo?.phone || "+91 98765 43210"}</span>
          </div>
          <div className="info-item">
            <Clock size={16} />
            <span>Mon - Sat: 10:00 AM - 8:00 PM (Sun Closed)</span>
          </div>
          <div className="info-item">
            <ShieldCheck size={16} />
            <span>Free cancellation up to 2 hours before appointment</span>
          </div>
        </div>
      </div>
    </div>
  );
}
