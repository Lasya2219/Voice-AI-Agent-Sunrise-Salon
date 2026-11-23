import {
  CalendarCheck,
  Search,
  RotateCw,
  Calendar,
  User,
  Scissors,
  CheckCircle2,
  XCircle,
  HelpCircle,
} from "lucide-react";

export default function AppointmentsSection({
  phoneInput,
  onPhoneChange,
  onCheckBookings,
  bookings,
  isLoading,
  searchedPhone,
}) {
  const formatDateTime = (isoString) => {
    if (!isoString) return "";
    try {
      const dt = new Date(isoString);
      return dt.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
    } catch {
      return isoString;
    }
  };

  const getStatusBadge = (status) => {
    const clean = (status || "").toLowerCase();
    if (clean === "confirmed") {
      return (
        <span className="booking-status-tag status-confirmed">
          <CheckCircle2 className="tag-icon" /> Confirmed
        </span>
      );
    }
    if (clean === "cancelled") {
      return (
        <span className="booking-status-tag status-cancelled">
          <XCircle className="tag-icon" /> Cancelled
        </span>
      );
    }
    return (
      <span className="booking-status-tag status-done">
        <HelpCircle className="tag-icon" /> {status}
      </span>
    );
  };

  return (
    <section className="salon-card appointments-card">
      <div className="card-header">
        <div className="card-title-group">
          <div className="card-icon-pill">
            <CalendarCheck className="card-header-icon" />
          </div>
          <div>
            <h3 className="card-heading">My Appointments</h3>
            <p className="card-subheading">View or verify bookings made with our receptionist</p>
          </div>
        </div>

        {searchedPhone && (
          <button
            type="button"
            className="refresh-bookings-btn"
            onClick={onCheckBookings}
            disabled={isLoading}
            title="Refresh bookings from server"
          >
            <RotateCw className={`btn-icon ${isLoading ? "spin" : ""}`} />
            <span>Sync</span>
          </button>
        )}
      </div>

      {/* Phone lookup form */}
      <form
        className="phone-lookup-form"
        onSubmit={(e) => {
          e.preventDefault();
          onCheckBookings();
        }}
      >
        <div className="phone-input-field">
          <span className="country-code">+91</span>
          <input
            type="tel"
            placeholder="Enter 10-digit phone number"
            value={phoneInput}
            onChange={(e) => onPhoneChange(e.target.value)}
            maxLength={14}
            className="lookup-input"
          />
        </div>
        <button
          type="submit"
          className="lookup-submit-btn"
          disabled={isLoading || !phoneInput.trim()}
        >
          {isLoading ? (
            <RotateCw className="btn-icon spin" />
          ) : (
            <Search className="btn-icon" />
          )}
          <span>{isLoading ? "Checking..." : "Look Up"}</span>
        </button>
      </form>

      {/* Bookings Result Display */}
      <div className="bookings-result-container">
        {isLoading && !bookings && (
          <div className="bookings-loading-state">
            <RotateCw className="spin" />
            <span>Searching appointments...</span>
          </div>
        )}

        {bookings && (
          <>
            {bookings.length === 0 ? (
              <div className="no-bookings-card">
                <p className="no-bookings-title">No appointments found</p>
                <p className="no-bookings-desc">
                  We found no appointments registered under <strong>{searchedPhone}</strong>. You can ask our voice
                  receptionist right now to book your next slot!
                </p>
              </div>
            ) : (
              <div className="bookings-list">
                <div className="bookings-summary-bar">
                  <span>Found {bookings.length} appointment(s)</span>
                  <span className="synced-hint">Updated from salon database</span>
                </div>

                {bookings.map((item) => (
                  <div key={item.booking_id} className="booking-card">
                    <div className="booking-card-top">
                      <div className="booking-reference">
                        <span className="ref-hash">#</span>
                        <span className="ref-num">{item.booking_id}</span>
                        <span className="customer-name-sub">• {item.customer_name}</span>
                      </div>
                      {getStatusBadge(item.status)}
                    </div>

                    <div className="booking-card-body">
                      <div className="booking-detail-row">
                        <Scissors className="detail-icon" />
                        <span className="detail-value bold">{item.service_name}</span>
                      </div>

                      <div className="booking-detail-row">
                        <User className="detail-icon" />
                        <span className="detail-value">Stylist: {item.stylist_name}</span>
                      </div>

                      <div className="booking-detail-row time-row">
                        <Calendar className="detail-icon" />
                        <span className="detail-value">{formatDateTime(item.start_time)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
