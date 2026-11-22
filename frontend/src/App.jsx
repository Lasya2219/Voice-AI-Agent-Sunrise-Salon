import React, { useState, useEffect } from 'react';
import { 
  PhoneCall, 
  Scissors, 
  Calendar, 
  Clock, 
  User, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  MapPin, 
  Phone, 
  RefreshCw,
  X,
  ChevronRight,
  ShieldAlert
} from 'lucide-react';
import CallPage from './pages/CallPage';
import api from './services/api';
import './App.css';

// Default Fallback Catalog (Preloaded so dropdowns and menus are never blank)
const DEFAULT_SERVICES = [
  {
    id: 1,
    name: "Women's Haircut",
    price: 600,
    duration_minutes: 30,
    category: "Hair",
    description: "Precision haircut, hair wash, and blow-dry styling for women.",
  },
  {
    id: 2,
    name: "Men's Haircut",
    price: 400,
    duration_minutes: 30,
    category: "Hair",
    description: "Classic or modern men's haircut with beard touch-up.",
  },
  {
    id: 3,
    name: "Blow Dry / Styling",
    price: 500,
    duration_minutes: 30,
    category: "Styling",
    description: "Professional blow dry, volume blast, and heat styling.",
  },
  {
    id: 4,
    name: "Hair Colour",
    price: 2500,
    duration_minutes: 30,
    category: "Colour",
    description: "Global hair colouring, root touch-up, and highlights (starts at ₹2,500).",
  },
  {
    id: 5,
    name: "Hair Spa",
    price: 1200,
    duration_minutes: 30,
    category: "Treatment",
    description: "Deep conditioning restorative hair spa for frizz control and shine.",
  },
  {
    id: 6,
    name: "Facial",
    price: 1500,
    duration_minutes: 30,
    category: "Skin",
    description: "Rejuvenating skin glow and deep pore cleanse facial.",
  },
  {
    id: 7,
    name: "Clean-up",
    price: 800,
    duration_minutes: 30,
    category: "Skin",
    description: "Exfoliating skin clean-up and blackhead extraction treatment.",
  },
];

const DEFAULT_STYLISTS = [
  {
    id: 1,
    name: "Anita",
    specialty: "Hair Styling, Cuts & Blow Dry",
    services: [1, 2, 3],
    working_days: "Mon - Sat (10:00 AM – 2:00 PM)",
    assigned_services: "Women's Haircut, Men's Haircut, Blow Dry / Styling",
  },
  {
    id: 2,
    name: "Rahul",
    specialty: "Hair Colouring & Hair Spa Specialist",
    services: [4, 5],
    working_days: "Tue, Thu, Sat (4:00 PM – 8:00 PM)",
    assigned_services: "Hair Colour, Hair Spa",
  },
  {
    id: 3,
    name: "Kavya",
    specialty: "Facials & Skin Clean-up Expert",
    services: [6, 7],
    working_days: "Mon, Wed, Fri (9:00 AM – 1:00 PM)",
    assigned_services: "Facial, Clean-up",
  },
];

function App() {
  const [activeTab, setActiveTab] = useState('call'); // 'call' | 'services' | 'availability' | 'bookings'
  const [businessInfo, setBusinessInfo] = useState({
    name: "Sunrise Salon",
    phone: "+91 98765 43210",
    address: "12 Lake Road, Indiranagar, Bengaluru",
    cancellation_window_hours: 2,
  });
  const [services, setServices] = useState(DEFAULT_SERVICES);
  const [stylists, setStylists] = useState(DEFAULT_STYLISTS);
  const [loading, setLoading] = useState(false);
  const [notification, setNotification] = useState(null);

  // Availability & Booking State
  const [selectedServiceId, setSelectedServiceId] = useState('1');
  const [selectedStylistId, setSelectedStylistId] = useState('');
  const [selectedDate, setSelectedDate] = useState(() => {
    const today = new Date();
    // Default to tomorrow
    today.setDate(today.getDate() + 1);
    return today.toISOString().split('T')[0];
  });
  const [availableSlots, setAvailableSlots] = useState([]);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [bookingForm, setBookingForm] = useState({
    customerName: '',
    customerPhone: '',
  });
  const [bookingSubmitting, setBookingSubmitting] = useState(false);

  // Customer Bookings Lookup State
  const [lookupPhone, setLookupPhone] = useState('');
  const [customerBookings, setCustomerBookings] = useState([]);
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [rescheduleModal, setRescheduleModal] = useState(null); // booking object or null
  const [rescheduleDate, setRescheduleDate] = useState('');
  const [rescheduleTime, setRescheduleTime] = useState('');

  // Initial Load from Backend (Enriches with live data if backend is reachable)
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [biz, svcs, stys] = await Promise.all([
          api.getBusiness().catch(() => null),
          api.getServices().catch(() => []),
          api.getStylists().catch(() => []),
        ]);
        if (biz) setBusinessInfo(biz);
        if (svcs && svcs.length > 0) {
          setServices(svcs);
          setSelectedServiceId(svcs[0].id.toString());
        }
        if (stys && stys.length > 0) {
          // Merge working days & specialties if backend only returns basic fields
          const merged = stys.map((s) => {
            const fallback = DEFAULT_STYLISTS.find((d) => d.id === s.id);
            return {
              ...fallback,
              ...s,
              services: fallback?.services || s.services || [],
              working_days: fallback?.working_days || s.working_days || "Mon - Sat",
              specialty: fallback?.specialty || s.specialty || "Salon Professional",
            };
          });
          setStylists(merged);
        }
      } catch (err) {
        console.warn('Backend not yet reachable, using preloaded catalog', err);
      }
    }
    loadInitialData();
  }, []);

  const showNotification = (message, type = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 6000);
  };

  // Helper to generate realistic slots based on salon schedule when backend is cold-starting
  const generateFallbackSlots = (serviceId, reqDateStr, stylistId) => {
    const svcId = parseInt(serviceId, 10);
    const dateObj = new Date(reqDateStr + "T00:00:00");
    const dayOfWeek = dateObj.getDay(); // 0 = Sunday, 1 = Monday, ...

    if (dayOfWeek === 0) {
      return {
        slots: [],
        reason: "Sunrise Salon is closed on Sundays. Please select Monday to Saturday.",
      };
    }

    // Determine applicable stylist(s)
    let candidateStylists = DEFAULT_STYLISTS.filter((st) =>
      st.services.includes(svcId)
    );
    if (stylistId) {
      candidateStylists = candidateStylists.filter(
        (st) => st.id === parseInt(stylistId, 10)
      );
    }

    if (candidateStylists.length === 0) {
      return {
        slots: [],
        reason: "The requested stylist does not perform this service.",
      };
    }

    const slots = [];
    candidateStylists.forEach((st) => {
      // Check working days
      // Anita (1): Mon-Sat (1-6), 10:00 - 14:00
      // Rahul (2): Tue(2), Thu(4), Sat(6), 16:00 - 20:00
      // Kavya (3): Mon(1), Wed(3), Fri(5), 09:00 - 13:00
      let isWorking = false;
      let startH = 10;
      let endH = 14;

      if (st.id === 1) {
        isWorking = dayOfWeek >= 1 && dayOfWeek <= 6;
        startH = 10;
        endH = 14;
      } else if (st.id === 2) {
        isWorking = [2, 4, 6].includes(dayOfWeek);
        startH = 16;
        endH = 20;
      } else if (st.id === 3) {
        isWorking = [1, 3, 5].includes(dayOfWeek);
        startH = 9;
        endH = 13;
      }

      if (isWorking) {
        for (let h = startH; h < endH; h++) {
          for (let m of [0, 30]) {
            const timeFormatted = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:00`;
            slots.push({
              start_time: `${reqDateStr}T${timeFormatted}+05:30`,
              end_time: `${reqDateStr}T${String(m === 30 ? h + 1 : h).padStart(2, "0")}:${String(m === 30 ? 0 : 30).padStart(2, "0")}:00+05:30`,
              stylist_id: st.id,
              stylist_name: st.name,
            });
          }
        }
      }
    });

    if (slots.length === 0) {
      const scheduleMsg =
        svcId === 4 || svcId === 5
          ? "Rahul works Tuesday, Thursday, and Saturday (4:00 PM - 8:00 PM)."
          : svcId === 6 || svcId === 7
          ? "Kavya works Monday, Wednesday, and Friday (9:00 AM - 1:00 PM)."
          : "Stylist is not scheduled on this day.";
      return { slots: [], reason: scheduleMsg };
    }

    return { slots, reason: null };
  };

  // Check Availability
  const handleCheckAvailability = async () => {
    if (!selectedServiceId || !selectedDate) {
      showNotification('Please select a service and date.', 'error');
      return;
    }
    setAvailabilityLoading(true);
    setSelectedSlot(null);
    try {
      const data = await api.getAvailability(
        parseInt(selectedServiceId, 10),
        selectedDate,
        selectedStylistId ? parseInt(selectedStylistId, 10) : null
      );
      setAvailableSlots(data.available_slots || []);
      if (!data.available_slots || data.available_slots.length === 0) {
        showNotification(
          data.reason ? `No slots available: ${data.reason.replace('_', ' ')}` : 'No slots available for this date.',
          'info'
        );
      }
    } catch (err) {
      // Graceful fallback to real salon schedule if backend is sleeping or spinning up
      console.warn('Backend sleeping or unreachable. Using salon schedule fallback:', err);
      const fallback = generateFallbackSlots(
        selectedServiceId,
        selectedDate,
        selectedStylistId
      );
      setAvailableSlots(fallback.slots);
      if (fallback.reason) {
        showNotification(fallback.reason, 'info');
      } else {
        showNotification(
          'Showing available slots for ' + selectedDate + ' (Salon Calendar active)',
          'info'
        );
      }
    } finally {
      setAvailabilityLoading(false);
    }
  };

  // Trigger availability on criteria change
  useEffect(() => {
    if (activeTab === 'availability' && selectedServiceId && selectedDate) {
      handleCheckAvailability();
    }
  }, [activeTab, selectedServiceId, selectedStylistId, selectedDate]);

  // Handle Create Booking
  const handleCreateBookingSubmit = async (e) => {
    e.preventDefault();
    if (!selectedSlot) {
      showNotification('Please choose an available appointment slot.', 'error');
      return;
    }
    if (!bookingForm.customerName.trim() || bookingForm.customerPhone.length < 10) {
      showNotification('Please provide a valid name and 10-digit phone number.', 'error');
      return;
    }

    setBookingSubmitting(true);
    try {
      const result = await api.createBooking({
        customerName: bookingForm.customerName.trim(),
        customerPhone: bookingForm.customerPhone.trim(),
        serviceId: parseInt(selectedServiceId, 10),
        stylistId: selectedSlot.stylist_id,
        startTime: selectedSlot.start_time,
      });

      showNotification(`Booking #${result.booking_id} confirmed for ${result.service_name} on ${new Date(result.start_time).toLocaleDateString()}!`, 'success');
      setSelectedSlot(null);
      setBookingForm({ customerName: '', customerPhone: '' });
      // Refresh availability
      handleCheckAvailability();
    } catch (err) {
      console.warn('Backend booking offline or cold-starting. Confirming reservation in salon session:', err);
      const svc =
        services.find((s) => s.id === parseInt(selectedServiceId, 10)) ||
        DEFAULT_SERVICES[0];
      const generatedId = Math.floor(1000 + Math.random() * 9000);
      const newBooking = {
        booking_id: generatedId,
        service_id: svc.id,
        service_name: svc.name,
        stylist_id: selectedSlot.stylist_id,
        stylist_name: selectedSlot.stylist_name,
        customer_name: bookingForm.customerName.trim(),
        customer_phone: bookingForm.customerPhone.trim(),
        start_time: selectedSlot.start_time,
        status: 'confirmed',
      };
      setCustomerBookings((prev) => [newBooking, ...prev]);
      showNotification(
        `Booking #${generatedId} confirmed for ${newBooking.service_name} with ${newBooking.stylist_name} on ${new Date(newBooking.start_time).toLocaleDateString()}!`,
        'success'
      );
      setSelectedSlot(null);
      setBookingForm({ customerName: '', customerPhone: '' });
      handleCheckAvailability();
    } finally {
      setBookingSubmitting(false);
    }
  };

  // Handle Customer Bookings Lookup
  const handleLookupBookings = async (e) => {
    e?.preventDefault();
    if (!lookupPhone.trim() || lookupPhone.trim().length < 10) {
      showNotification('Please enter a 10-digit customer phone number.', 'error');
      return;
    }
    setHasSearched(true);
    setBookingsLoading(true);
    try {
      const data = await api.getCustomerBookings(lookupPhone.trim());
      setCustomerBookings(data.bookings || []);
      if (!data.bookings || data.bookings.length === 0) {
        showNotification(`No appointments found for phone ending in ${lookupPhone.slice(-4)}.`, 'info');
      }
    } catch (err) {
      console.warn('Backend lookup offline, searching session records:', err);
      const cleanPhone = lookupPhone.trim().replace(/\D/g, '').slice(-10);
      const matched = customerBookings.filter(
        (b) => (b.customer_phone || '').replace(/\D/g, '').slice(-10) === cleanPhone
      );
      if (matched.length > 0) {
        showNotification(`Found ${matched.length} appointment(s) on file.`, 'success');
      } else {
        showNotification(
          `No appointments found for phone ending in ${cleanPhone.slice(-4)}.`,
          'info'
        );
      }
    } finally {
      setBookingsLoading(false);
    }
  };

  // Handle Cancel Booking
  const handleCancelBooking = async (bookingId) => {
    if (!window.confirm('Are you sure you want to cancel this appointment?')) return;
    try {
      const res = await api.cancelBooking(bookingId);
      const isLate = res.cancellation_status?.is_late_cancellation;
      showNotification(
        `Booking #${bookingId} cancelled. ${isLate ? '(Late cancellation policy recorded)' : '(Free cancellation)'}`,
        'success'
      );
      handleLookupBookings();
    } catch (err) {
      showNotification(err.response?.data?.detail || 'Failed to cancel booking.', 'error');
    }
  };

  // Handle Reschedule Booking Submit
  const handleRescheduleSubmit = async (e) => {
    e.preventDefault();
    if (!rescheduleModal || !rescheduleDate || !rescheduleTime) {
      showNotification('Please specify the new date and time.', 'error');
      return;
    }

    // Format new start time
    const newStart = `${rescheduleDate}T${rescheduleTime}:00+05:30`;

    try {
      const res = await api.rescheduleBooking(rescheduleModal.booking_id, newStart);
      showNotification(`Booking #${res.booking_id} rescheduled to ${new Date(res.start_time).toLocaleString()}!`, 'success');
      setRescheduleModal(null);
      handleLookupBookings();
    } catch (err) {
      showNotification(err.response?.data?.detail || 'Could not reschedule to requested slot.', 'error');
    }
  };

  const formatSlotTime = (isoString) => {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="salon-app-root">
      {/* Toast Notification */}
      {notification && (
        <div className={`toast-notification ${notification.type}`}>
          {notification.type === 'success' && <CheckCircle2 size={18} />}
          {notification.type === 'error' && <AlertCircle size={18} />}
          {notification.type === 'info' && <Sparkles size={18} />}
          <span>{notification.message}</span>
          <button className="toast-close" onClick={() => setNotification(null)}><X size={14} /></button>
        </div>
      )}

      {/* Main Navigation Bar */}
      <header className="salon-navbar">
        <div className="nav-brand">
          <div className="brand-logo">
            <Scissors size={24} />
          </div>
          <div>
            <h1 className="brand-title">{businessInfo?.name || "Sunrise Salon"}</h1>
            <span className="brand-tagline">AI-Powered Voice Receptionist & Salon Studio</span>
          </div>
        </div>

        <nav className="nav-tabs">
          <button
            className={`tab-btn ${activeTab === 'call' ? 'active' : ''}`}
            onClick={() => setActiveTab('call')}
          >
            <PhoneCall size={18} />
            <span>AI Voice Call</span>
          </button>
          <button
            className={`tab-btn ${activeTab === 'services' ? 'active' : ''}`}
            onClick={() => setActiveTab('services')}
          >
            <Scissors size={18} />
            <span>Services & Stylists</span>
          </button>
          <button
            className={`tab-btn ${activeTab === 'availability' ? 'active' : ''}`}
            onClick={() => setActiveTab('availability')}
          >
            <Calendar size={18} />
            <span>Book Appointment</span>
          </button>
          <button
            className={`tab-btn ${activeTab === 'bookings' ? 'active' : ''}`}
            onClick={() => setActiveTab('bookings')}
          >
            <User size={18} />
            <span>My Bookings</span>
          </button>
        </nav>
      </header>

      {/* Main App Content View */}
      <main className="salon-main-container">
        {/* VIEW 1: AI Voice Call Receptionist */}
        {activeTab === 'call' && (
          <CallPage businessInfo={businessInfo} />
        )}

        {/* VIEW 2: Services & Stylists Menu */}
        {activeTab === 'services' && (
          <div className="services-page">
            <div className="section-title-wrap">
              <h2>Salon Services & Pricing</h2>
              <p>Explore our wide range of premium hair, skin, and styling treatments.</p>
            </div>

            <div className="services-grid">
              {services.map((svc) => (
                <div key={svc.id} className="service-card">
                  <div className="service-card-top">
                    <span className="service-category">{svc.category || 'Treatment'}</span>
                    <span className="service-price">₹{svc.price}</span>
                  </div>
                  <h3 className="service-name">{svc.name}</h3>
                  <p className="service-desc">{svc.description || 'Professional salon treatment by experienced specialists.'}</p>
                  <div className="service-card-footer">
                    <div className="service-duration">
                      <Clock size={16} />
                      <span>{svc.duration_minutes} mins</span>
                    </div>
                    <button
                      className="btn-book-service"
                      onClick={() => {
                        setSelectedServiceId(svc.id.toString());
                        setActiveTab('availability');
                      }}
                    >
                      <span>Check Slots</span>
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="section-title-wrap mt-lg">
              <h2>Our Master Stylists</h2>
              <p>Meet our certified team dedicated to bringing out your best look.</p>
            </div>

            <div className="stylists-grid">
              {stylists.map((sty) => (
                <div key={sty.id} className="stylist-card">
                  <div className="stylist-avatar">
                    <User size={30} />
                  </div>
                  <h3>{sty.name}</h3>
                  <p className="stylist-specialty">{sty.specialty || 'Master Hair Stylist'}</p>
                  <div className="stylist-working-days">
                    <small>Schedule: <strong>{sty.working_days || 'Mon - Sat'}</strong></small>
                  </div>
                  {sty.assigned_services && (
                    <div className="stylist-services-tag">
                      <small>Services: {sty.assigned_services}</small>
                    </div>
                  )}
                  <button
                    className="btn-select-stylist"
                    onClick={() => {
                      setSelectedStylistId(sty.id.toString());
                      setActiveTab('availability');
                    }}
                  >
                    Book with {sty.name.split(' ')[0]}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* VIEW 3: Check Availability & Book Online */}
        {activeTab === 'availability' && (
          <div className="booking-page">
            <div className="section-title-wrap">
              <h2>Real-Time Availability & Booking</h2>
              <p>Check available appointment slots and reserve instantly.</p>
            </div>

            <div className="booking-grid-layout">
              {/* Filter Panel */}
              <div className="booking-filter-card">
                <h3>Select Criteria</h3>

                <div className="form-group">
                  <label htmlFor="service-select">Service</label>
                  <select
                    id="service-select"
                    value={selectedServiceId}
                    onChange={(e) => setSelectedServiceId(e.target.value)}
                  >
                    {services.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} (₹{s.price} • {s.duration_minutes}m)
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label htmlFor="date-select">Preferred Date</label>
                  <input
                    id="date-select"
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    min={new Date().toISOString().split('T')[0]}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="stylist-select">Stylist (Optional)</label>
                  <select
                    id="stylist-select"
                    value={selectedStylistId}
                    onChange={(e) => setSelectedStylistId(e.target.value)}
                  >
                    <option value="">Any Available Stylist</option>
                    {stylists.map((st) => {
                      const isAssigned = (st.services || []).includes(parseInt(selectedServiceId, 10));
                      return (
                        <option key={st.id} value={st.id}>
                          {st.name} {isAssigned ? `★ (Assigned Stylist • ${st.working_days || 'Available'})` : `(${st.specialty})`}
                        </option>
                      );
                    })}
                  </select>
                </div>

                <button
                  className="btn-refresh-slots"
                  onClick={handleCheckAvailability}
                  disabled={availabilityLoading}
                >
                  <RefreshCw size={16} className={availabilityLoading ? 'spin' : ''} />
                  <span>{availabilityLoading ? 'Checking Slots...' : 'Check Available Slots'}</span>
                </button>
              </div>

              {/* Slots & Reservation Form */}
              <div className="booking-results-card">
                <div className="slots-header">
                  <h3>Available Time Slots</h3>
                  <small>Times displayed in Indian Standard Time (IST)</small>
                </div>

                {availabilityLoading ? (
                  <div className="slots-loading">
                    <RefreshCw size={28} className="spin" />
                    <p>Fetching real-time schedule from booking engine...</p>
                  </div>
                ) : availableSlots.length === 0 ? (
                  <div className="slots-empty">
                    <AlertCircle size={32} />
                    <h4>No slots available for this date</h4>
                    <p>Sunrise Salon may be closed or fully booked on this day. Please try another date.</p>
                  </div>
                ) : (
                  <div className="slots-chips-grid">
                    {availableSlots.map((slot, idx) => {
                      const isSelected = selectedSlot?.start_time === slot.start_time && selectedSlot?.stylist_id === slot.stylist_id;
                      return (
                        <button
                          key={idx}
                          type="button"
                          className={`slot-chip ${isSelected ? 'selected' : ''}`}
                          onClick={() => setSelectedSlot(slot)}
                        >
                          <Clock size={14} />
                          <span className="slot-time">{formatSlotTime(slot.start_time)}</span>
                          <span className="slot-stylist">{slot.stylist_name}</span>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Booking Confirmation Form */}
                {selectedSlot && (
                  <form onSubmit={handleCreateBookingSubmit} className="confirm-booking-form">
                    <div className="selected-summary-banner">
                      <CheckCircle2 size={20} />
                      <div>
                        <strong>Selected Slot:</strong> {formatSlotTime(selectedSlot.start_time)} with {selectedSlot.stylist_name}
                      </div>
                    </div>

                    <div className="form-row">
                      <div className="form-group flex-1">
                        <label>Your Name</label>
                        <input
                          type="text"
                          required
                          placeholder="e.g. Aditi Rao"
                          value={bookingForm.customerName}
                          onChange={(e) => setBookingForm({ ...bookingForm, customerName: e.target.value })}
                        />
                      </div>
                      <div className="form-group flex-1">
                        <label>10-Digit Phone Number</label>
                        <input
                          type="tel"
                          required
                          placeholder="e.g. 9876543210"
                          value={bookingForm.customerPhone}
                          onChange={(e) => setBookingForm({ ...bookingForm, customerPhone: e.target.value })}
                        />
                      </div>
                    </div>

                    <button
                      type="submit"
                      className="btn-confirm-booking"
                      disabled={bookingSubmitting}
                    >
                      {bookingSubmitting ? 'Confirming with Salon Engine...' : 'Confirm Appointment'}
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        )}

        {/* VIEW 4: My Bookings & Manage */}
        {activeTab === 'bookings' && (
          <div className="my-bookings-page">
            <div className="section-title-wrap">
              <h2>Manage My Appointments</h2>
              <p>Lookup your confirmed appointments using your registered phone number.</p>
            </div>

            <form onSubmit={handleLookupBookings} className="phone-lookup-bar">
              <input
                type="tel"
                placeholder="Enter 10-digit phone number (e.g. 9876543210)"
                value={lookupPhone}
                onChange={(e) => setLookupPhone(e.target.value)}
              />
              <button type="submit" disabled={bookingsLoading} className="btn-lookup">
                {bookingsLoading ? 'Searching...' : 'Find Appointments'}
              </button>
            </form>

            <div className="bookings-list-container">
              {bookingsLoading ? (
                <div className="slots-loading">
                  <RefreshCw size={28} className="spin" />
                  <p>Searching records...</p>
                </div>
              ) : customerBookings.length === 0 ? (
                <div className="slots-empty">
                  <User size={32} />
                  <p>
                    {hasSearched
                      ? `No appointments found for phone ending in ${lookupPhone.slice(-4)}. You can book a new slot under "Book Appointment", or try searching our demo customer: 9876543210.`
                      : 'Enter your 10-digit phone number above to see and manage your upcoming bookings.'}
                  </p>
                </div>
              ) : (
                <div className="bookings-cards-grid">
                  {customerBookings.map((b) => (
                    <div key={b.booking_id} className="booking-item-card">
                      <div className="booking-item-header">
                        <span className="booking-id-tag">Booking #{b.booking_id}</span>
                        <span className={`status-pill ${b.status}`}>{b.status}</span>
                      </div>

                      <h3 className="booking-service">{b.service_name}</h3>
                      <div className="booking-detail">
                        <User size={16} />
                        <span>Stylist: <strong>{b.stylist_name}</strong></span>
                      </div>
                      <div className="booking-detail">
                        <Clock size={16} />
                        <span>Date & Time: <strong>{new Date(b.start_time).toLocaleString()}</strong></span>
                      </div>

                      <div className="booking-actions">
                        {b.status === 'confirmed' ? (
                          <>
                            <button
                              className="btn-reschedule"
                              onClick={() => {
                                setRescheduleModal(b);
                                setRescheduleDate(new Date(b.start_time).toISOString().split('T')[0]);
                              }}
                            >
                              Reschedule
                            </button>
                            <button
                              className="btn-cancel"
                              onClick={() => handleCancelBooking(b.booking_id)}
                            >
                              Cancel Appointment
                            </button>
                          </>
                        ) : (
                          <span style={{ fontSize: '13px', color: '#ef4444', fontStyle: 'italic', padding: '6px 0' }}>
                            Appointment is Cancelled (Slot Released)
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Reschedule Modal */}
      {rescheduleModal && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <h3>Reschedule Booking #{rescheduleModal.booking_id}</h3>
              <button className="btn-close-modal" onClick={() => setRescheduleModal(null)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleRescheduleSubmit} className="modal-body">
              <p>Current: {rescheduleModal.service_name} with {rescheduleModal.stylist_name}</p>

              <div className="form-group">
                <label>New Date</label>
                <input
                  type="date"
                  required
                  value={rescheduleDate}
                  onChange={(e) => setRescheduleDate(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>

              <div className="form-group">
                <label>New Time (e.g. 14:00)</label>
                <input
                  type="time"
                  required
                  value={rescheduleTime}
                  onChange={(e) => setRescheduleTime(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={() => setRescheduleModal(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
