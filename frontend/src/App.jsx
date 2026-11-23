import { useEffect, useRef, useState, useCallback } from "react";
import axios from "axios";
import LiveKitService from "./services/livekit";
import Navbar from "./components/Navbar";
import VoiceHero from "./components/VoiceHero";
import TranscriptFeed from "./components/TranscriptFeed";
import ServicesSection from "./components/ServicesSection";
import AppointmentsSection from "./components/AppointmentsSection";
import StylistsAndHours from "./components/StylistsAndHours";
import "./App.css";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export default function App() {
  // Voice Call State
  const [agentState, setAgentState] = useState("disconnected"); // 'connecting' | 'listening' | 'thinking' | 'speaking' | 'disconnected'
  const [isMuted, setIsMuted] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [callDuration, setCallDuration] = useState(0);
  const [transcripts, setTranscripts] = useState([]);
  const [showTranscripts, setShowTranscripts] = useState(true);

  // Salon Catalog Data from Backend
  const [business, setBusiness] = useState(null);
  const [services, setServices] = useState([]);
  const [stylists, setStylists] = useState([]);
  const [isLoadingCatalog, setIsLoadingCatalog] = useState(true);

  // Customer Appointments Data
  const [customerPhone, setCustomerPhone] = useState("");
  const [searchedPhone, setSearchedPhone] = useState("");
  const [customerBookings, setCustomerBookings] = useState(null);
  const [isLoadingBookings, setIsLoadingBookings] = useState(false);

  const timerRef = useRef(null);

  // Initialize LiveKitService instance once via state initializer
  const [liveKitService] = useState(
    () =>
      new LiveKitService({
        onStateChange: (state) => {
          setAgentState(state);
          if (state === "disconnected") {
            setCallDuration(0);
          }
        },
        onMuteChange: (muted) => {
          setIsMuted(muted);
        },
        onSpeakerChange: () => {
          // Voice activity tracked directly by LiveKitService
        },
        onTranscription: (updatedTranscripts) => {
          setTranscripts(updatedTranscripts);
        },
        onError: (err) => {
          console.error("LiveKit service error:", err);
          setErrorMessage(
            err.message || "Failed to establish voice call. Please check your microphone permissions."
          );
        },
      })
  );

  // Load real salon business info, services, and stylists from FastAPI backend
  useEffect(() => {
    let isMounted = true;

    async function fetchSalonData() {
      setIsLoadingCatalog(true);
      try {
        const [bizRes, svcRes, styRes] = await Promise.allSettled([
          axios.get(`${BACKEND_URL}/api/business`),
          axios.get(`${BACKEND_URL}/api/services`),
          axios.get(`${BACKEND_URL}/api/stylists`),
        ]);

        if (!isMounted) return;

        if (bizRes.status === "fulfilled" && bizRes.value.data) {
          setBusiness(bizRes.value.data);
        }
        if (svcRes.status === "fulfilled" && Array.isArray(svcRes.value.data)) {
          setServices(svcRes.value.data);
        }
        if (styRes.status === "fulfilled" && Array.isArray(styRes.value.data)) {
          setStylists(styRes.value.data);
        }
      } catch (err) {
        console.error("Failed to load salon catalog from backend:", err);
      } finally {
        if (isMounted) {
          setIsLoadingCatalog(false);
        }
      }
    }

    fetchSalonData();

    return () => {
      isMounted = false;
    };
  }, []);

  // Call timer effect
  useEffect(() => {
    if (agentState !== "disconnected" && agentState !== "connecting") {
      timerRef.current = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [agentState]);

  // Clean up on component unmount
  useEffect(() => {
    return () => {
      liveKitService.stop();
    };
  }, [liveKitService]);

  // Start voice conversation
  const handleStartCall = async () => {
    setErrorMessage(null);
    setCallDuration(0);
    try {
      const normalizedDigits = customerPhone.replace(/\D/g, "");
      const identity = normalizedDigits.length >= 10 ? `customer-${normalizedDigits.slice(-10)}` : undefined;

      await liveKitService.start({
        identity,
        name: "Salon Guest",
      });
    } catch (err) {
      console.error("Failed to start voice call:", err);
      setErrorMessage(
        err.message || "Could not connect to the voice assistant. Please check microphone access."
      );
    }
  };

  // End voice conversation
  const handleEndCall = async () => {
    try {
      await liveKitService.stop();
    } catch (err) {
      console.warn("Error ending call:", err);
    }
    setAgentState("disconnected");
    setIsMuted(false);
    setCallDuration(0);
  };

  // Toggle microphone
  const handleToggleMute = async () => {
    try {
      await liveKitService.toggleMute();
    } catch (err) {
      console.error("Failed to toggle mute:", err);
    }
  };

  // Clear live transcripts
  const handleClearTranscripts = () => {
    liveKitService.clearTranscripts();
    setTranscripts([]);
  };

  // Fetch verified customer bookings from backend
  const handleCheckBookings = useCallback(async () => {
    const rawDigits = customerPhone.replace(/\D/g, "");
    if (rawDigits.length < 10) {
      setErrorMessage("Please enter a valid 10-digit phone number to check appointments.");
      return;
    }

    const tenDigitPhone = rawDigits.slice(-10);
    setIsLoadingBookings(true);
    setSearchedPhone(tenDigitPhone);
    setErrorMessage(null);

    try {
      const res = await axios.get(`${BACKEND_URL}/api/bookings/customer`, {
        params: {
          business_slug: "sunrise-salon",
          customer_phone: tenDigitPhone,
        },
      });

      setCustomerBookings(res.data?.bookings || []);
    } catch (err) {
      if (err.response?.status === 404) {
        // Customer or business has no bookings registered
        setCustomerBookings([]);
      } else {
        console.error("Error querying customer bookings:", err);
        setErrorMessage("Unable to fetch bookings from the salon system. Please try again.");
      }
    } finally {
      setIsLoadingBookings(false);
    }
  }, [customerPhone]);

  return (
    <div className="salon-app-root">
      {/* Top Luxury Navbar */}
      <Navbar agentState={agentState} />

      {/* Main Dashboard Layout */}
      <main className="salon-main-container">
        {/* Left Column: Voice Experience & Real-time Transcripts */}
        <div className="salon-voice-column">
          <VoiceHero
            agentState={agentState}
            isMuted={isMuted}
            callDuration={callDuration}
            errorMessage={errorMessage}
            onStartCall={handleStartCall}
            onEndCall={handleEndCall}
            onToggleMute={handleToggleMute}
            onToggleTranscripts={() => setShowTranscripts(!showTranscripts)}
            showTranscripts={showTranscripts}
            transcriptCount={transcripts.length}
          />

          {showTranscripts && (
            <TranscriptFeed
              transcripts={transcripts}
              onClearTranscripts={handleClearTranscripts}
              isLive={agentState !== "disconnected"}
            />
          )}
        </div>

        {/* Right Column: Salon Services, Live Appointments, and Stylists */}
        <div className="salon-info-column">
          <ServicesSection
            services={services}
            isLoading={isLoadingCatalog}
          />

          <AppointmentsSection
            phoneInput={customerPhone}
            onPhoneChange={setCustomerPhone}
            onCheckBookings={handleCheckBookings}
            bookings={customerBookings}
            isLoading={isLoadingBookings}
            searchedPhone={searchedPhone}
          />

          <StylistsAndHours
            stylists={stylists}
            business={business}
          />
        </div>
      </main>

      {/* Modern Salon Footer */}
      <footer className="salon-footer">
        <div className="footer-inner">
          <p className="footer-brand">Sunrise Salon • Indiranagar, Bengaluru</p>
          <p className="footer-meta">
            Powered by LiveKit Voice AI • Real-time Backend Synchronization
          </p>
        </div>
      </footer>
    </div>
  );
}
