import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Scissors,
  Sparkles,
  Clock,
  MapPin,
  Phone,
  User,
  Calendar,
  ShieldCheck,
  CheckCircle2,
  CalendarCheck,
} from 'lucide-react';
import { LiveKitVoiceSession } from '../services/livekit';
import CallButton from '../components/CallButton';
import CallStatus from '../components/CallStatus';

const rawBackendUrl =
  import.meta.env.VITE_BACKEND_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'http://localhost:8000';
const BACKEND_URL = rawBackendUrl.replace(/\/+$/, '').replace(/\/api$/, '');

export default function CallPage() {
  // Call session state
  const [status, setStatus] = useState('disconnected'); // 'disconnected' | 'connecting' | 'connected' | 'error'
  const [isAgentSpeaking, setIsAgentSpeaking] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [callDuration, setCallDuration] = useState(0);

  // Customer identity state
  const [customerPhone, setCustomerPhone] = useState('');
  const [customerName, setCustomerName] = useState('');

  // Business and services state
  const [services, setServices] = useState([
    { id: 1, name: 'Haircut & Styling', price: 500, duration_minutes: 45 },
    { id: 2, name: 'Beard Grooming & Trim', price: 300, duration_minutes: 30 },
    { id: 3, name: 'Hair Coloring & Highlights', price: 1500, duration_minutes: 90 },
    { id: 4, name: 'Deep Cleansing Facial', price: 800, duration_minutes: 60 },
  ]);
  const [stylists, setStylists] = useState([
    { id: 1, name: 'Priya Sharma', title: 'Senior Stylist & Colorist' },
    { id: 2, name: 'Rahul Verma', title: 'Grooming & Fade Specialist' },
  ]);

  // Customer bookings check state
  const [myBookings, setMyBookings] = useState(null);
  const [isLoadingBookings, setIsLoadingBookings] = useState(false);

  // Refs
  const sessionRef = useRef(null);
  const timerRef = useRef(null);

  // Fetch business info & services on mount
  useEffect(() => {
    async function loadSalonData() {
      try {
        const [servicesRes, stylistsRes] = await Promise.allSettled([
          axios.get(`${BACKEND_URL}/api/services`),
          axios.get(`${BACKEND_URL}/api/stylists`),
        ]);

        if (servicesRes.status === 'fulfilled' && Array.isArray(servicesRes.value.data) && servicesRes.value.data.length > 0) {
          setServices(servicesRes.value.data);
        }
        if (stylistsRes.status === 'fulfilled' && Array.isArray(stylistsRes.value.data) && stylistsRes.value.data.length > 0) {
          setStylists(
            stylistsRes.value.data.map((s) => ({
              id: s.id,
              name: s.name,
              title: s.title || (s.name.toLowerCase().includes('priya') ? 'Senior Stylist' : 'Hair Specialist'),
            }))
          );
        }
      } catch (e) {
        console.warn('Backend data fetch skipped, using default salon catalog:', e);
      }
    }
    loadSalonData();
  }, []);

  // Call duration counter
  useEffect(() => {
    if (status === 'connected') {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [status]);

  // Clean up session on unmount
  useEffect(() => {
    return () => {
      if (sessionRef.current) {
        sessionRef.current.stop();
      }
    };
  }, []);

  // Start Call Handler
  const handleStartCall = async () => {
    setErrorMessage(null);
    setCallDuration(0);
    try {
      const session = new LiveKitVoiceSession({
        onStateChange: (newState) => {
          setStatus(newState);
          if (newState === 'disconnected') {
            setIsAgentSpeaking(false);
            setIsUserSpeaking(false);
          }
        },
        onSpeakerChange: ({ isAgentSpeaking: agentActive, isUserSpeaking: userActive }) => {
          setIsAgentSpeaking(agentActive);
          setIsUserSpeaking(userActive);
        },
        onError: (err) => {
          console.error('LiveKit session error:', err);
          setErrorMessage(err.message || 'Failed to establish voice call. Check mic permissions.');
        },
      });

      sessionRef.current = session;

      const identity = customerPhone ? `customer-${customerPhone.replace(/\D/g, '')}` : undefined;
      const name = customerName.trim() || 'Salon Guest';

      await session.start({
        roomName: 'sunrise-salon-room',
        identity,
        name,
      });
      setIsMuted(false);
    } catch (err) {
      console.error('Start call error:', err);
      setStatus('error');
      setErrorMessage(err.message || 'Microphone access denied or LiveKit unavailable.');
    }
  };

  // End Call Handler
  const handleEndCall = async () => {
    if (sessionRef.current) {
      await sessionRef.current.stop();
      sessionRef.current = null;
    }
    setStatus('disconnected');
    setCallDuration(0);
    setIsAgentSpeaking(false);
    setIsUserSpeaking(false);
  };

  // Toggle Mute Handler
  const handleToggleMute = async () => {
    if (!sessionRef.current) return;
    const nextMuted = !isMuted;
    await sessionRef.current.setMuted(nextMuted);
    setIsMuted(nextMuted);
  };

  // Check bookings for customer phone
  const handleCheckMyBookings = async () => {
    if (!customerPhone.trim()) {
      alert('Please enter your phone number to check bookings.');
      return;
    }
    setIsLoadingBookings(true);
    setMyBookings(null);
    try {
      const res = await axios.get(`${BACKEND_URL}/api/bookings/customer`, {
        params: {
          business_slug: 'sunrise-salon',
          customer_phone: customerPhone.trim(),
        },
      });
      setMyBookings(res.data?.bookings || []);
    } catch (err) {
      console.warn('Failed to load bookings from API:', err);
      setMyBookings([]);
    } finally {
      setIsLoadingBookings(false);
    }
  };

  // Format call duration MM:SS
  const formatDuration = (totalSeconds) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="salon-app-wrapper">
      {/* Top Navbar */}
      <header className="salon-header">
        <div className="salon-brand">
          <div className="brand-icon-wrapper">
            <Scissors className="w-6 h-6 text-amber-500" />
            <Sparkles className="w-3.5 h-3.5 text-amber-400 absolute -top-1 -right-1" />
          </div>
          <div>
            <h1 className="brand-title">Sunrise Salon</h1>
            <p className="brand-tagline">Indiranagar, Bengaluru • Open 09:00 AM - 08:00 PM</p>
          </div>
        </div>

        <div className="header-badges">
          <span className="badge-feature">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" /> AI Voice Receptionist
          </span>
          <span className="badge-feature">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" /> Instant Confirmation
          </span>
        </div>
      </header>

      {/* Main Grid: Call Hero + Salon Details */}
      <main className="salon-main-layout">
        {/* Left Column: Voice Receptionist Experience */}
        <section className="voice-experience-card">
          <div className="voice-card-header">
            <span className="voice-live-badge">
              <span className={`pulse-dot ${status === 'connected' ? 'connected' : ''}`} />
              {status === 'connected' ? `LIVE (${formatDuration(callDuration)})` : 'AI RECEPTIONIST'}
            </span>
            <span className="voice-subtitle">Talk naturally to book, reschedule, or inquire</span>
          </div>

          {/* Animated AI Voice Avatar / Orb */}
          <div className="voice-orb-container">
            <div
              className={`voice-orb ${
                status === 'connected'
                  ? isAgentSpeaking
                    ? 'orb-agent-speaking'
                    : isUserSpeaking
                    ? 'orb-user-speaking'
                    : 'orb-idle-connected'
                  : status === 'connecting'
                  ? 'orb-connecting'
                  : 'orb-idle'
              }`}
            >
              <div className="orb-inner">
                <Scissors className="w-10 h-10 text-white opacity-90" />
              </div>
              <div className="orb-ripple ripple-1" />
              <div className="orb-ripple ripple-2" />
              <div className="orb-ripple ripple-3" />
            </div>
          </div>

          {/* Live Status and Audio Wave Indicator */}
          <CallStatus
            status={status}
            isAgentSpeaking={isAgentSpeaking}
            isUserSpeaking={isUserSpeaking}
            isMuted={isMuted}
            errorMessage={errorMessage}
          />

          {/* Caller Identity Form (Optional Pre-fill) */}
          <div className="caller-input-group">
            <div className="input-field-wrapper">
              <User className="input-icon" />
              <input
                type="text"
                placeholder="Your Name (e.g. John)"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                disabled={status === 'connected'}
                className="caller-input"
              />
            </div>
            <div className="input-field-wrapper">
              <Phone className="input-icon" />
              <input
                type="tel"
                placeholder="Phone (e.g. 9876543210)"
                value={customerPhone}
                onChange={(e) => setCustomerPhone(e.target.value)}
                disabled={status === 'connected'}
                className="caller-input"
              />
            </div>
          </div>

          {/* Primary Call Controls */}
          <CallButton
            status={status}
            onStartCall={handleStartCall}
            onEndCall={handleEndCall}
            onToggleMute={handleToggleMute}
            isMuted={isMuted}
            disabled={status === 'connecting'}
          />

          {/* Helpful Tips Accordion */}
          <div className="voice-features-grid">
            <div className="feature-item">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Real-time slot availability</span>
            </div>
            <div className="feature-item">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Double-confirmation on booking</span>
            </div>
            <div className="feature-item">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>Free cancellation up to 2 hrs before</span>
            </div>
          </div>
        </section>

        {/* Right Column: Salon Services, Stylists, and Booking Lookup */}
        <section className="salon-info-column">
          {/* Services Menu */}
          <div className="info-card">
            <div className="info-card-header">
              <Scissors className="w-5 h-5 text-amber-500" />
              <h3>Services & Pricing</h3>
            </div>
            <div className="services-list">
              {services.map((svc) => (
                <div key={svc.id} className="service-row">
                  <div>
                    <h4 className="service-name">{svc.name}</h4>
                    <span className="service-duration">
                      <Clock className="w-3.5 h-3.5 inline mr-1" />
                      {svc.duration_minutes} mins
                    </span>
                  </div>
                  <div className="service-price">₹{svc.price}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Stylists & Timings */}
          <div className="info-card-grid">
            <div className="info-card">
              <div className="info-card-header">
                <User className="w-5 h-5 text-indigo-400" />
                <h3>Our Stylists</h3>
              </div>
              <div className="stylists-list">
                {stylists.map((st) => (
                  <div key={st.id} className="stylist-badge">
                    <span className="stylist-avatar">{st.name.charAt(0)}</span>
                    <div>
                      <div className="stylist-name">{st.name}</div>
                      <div className="stylist-title">{st.title}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="info-card">
              <div className="info-card-header">
                <Clock className="w-5 h-5 text-teal-400" />
                <h3>Hours & Location</h3>
              </div>
              <div className="hours-block">
                <p className="hours-text">
                  <strong>Tuesday – Sunday:</strong> 09:00 AM – 08:00 PM
                </p>
                <p className="hours-text text-rose-400">
                  <strong>Monday:</strong> Closed (Weekly Holiday)
                </p>
                <div className="location-text">
                  <MapPin className="w-4 h-4 text-amber-500 inline mr-1" />
                  104 Park Avenue, Indiranagar, Bengaluru
                </div>
              </div>
            </div>
          </div>

          {/* Check Existing Bookings Card */}
          <div className="info-card">
            <div className="info-card-header">
              <CalendarCheck className="w-5 h-5 text-emerald-500" />
              <h3>My Existing Appointments</h3>
            </div>
            <p className="text-sm text-neutral-400 mb-3">
              Enter your phone number above or speak to the voice assistant to check your appointments.
            </p>
            <button
              type="button"
              className="btn-check-bookings"
              onClick={handleCheckMyBookings}
              disabled={isLoadingBookings}
            >
              {isLoadingBookings ? 'Checking...' : 'Check My Bookings Online'}
            </button>

            {myBookings && (
              <div className="bookings-result-list">
                {myBookings.length === 0 ? (
                  <p className="no-bookings-text">No active appointments found for this number.</p>
                ) : (
                  myBookings.map((b) => (
                    <div key={b.id} className="booking-card-item">
                      <div className="booking-id">Booking #{b.id} • {b.status?.toUpperCase()}</div>
                      <div className="booking-time">
                        <Calendar className="w-4 h-4 inline mr-1" />
                        {new Date(b.start_time).toLocaleString('en-IN', {
                          timeZone: 'Asia/Kolkata',
                          dateStyle: 'medium',
                          timeStyle: 'short',
                        })}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="salon-footer">
        <p>© 2026 Sunrise Salon • Powered by LiveKit, Groq & Kokoro Voice AI</p>
      </footer>
    </div>
  );
}
