import { Users, Clock, ShieldCheck } from "lucide-react";

export default function StylistsAndHours({ stylists, business }) {
  const activeStylists = stylists.filter((s) => s.is_active);

  return (
    <div className="salon-secondary-grid">
      {/* Stylists Card */}
      <section className="salon-card stylists-card">
        <div className="card-header">
          <div className="card-title-group">
            <div className="card-icon-pill">
              <Users className="card-header-icon" />
            </div>
            <div>
              <h3 className="card-heading">Master Stylists</h3>
              <p className="card-subheading">Select a preferred stylist or choose any available slot</p>
            </div>
          </div>
        </div>

        <div className="stylists-pills-list">
          {activeStylists.length === 0 ? (
            <p className="no-stylists-text">Stylist information loading...</p>
          ) : (
            activeStylists.map((st) => (
              <div key={st.id} className="stylist-badge-pill">
                <div className="stylist-initial-avatar">
                  {st.name.charAt(0)}
                </div>
                <div className="stylist-meta">
                  <span className="stylist-name">{st.name}</span>
                  <span className="stylist-role">Expert Stylist</span>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Salon Policies & Schedule */}
      <section className="salon-card policy-card">
        <div className="card-header">
          <div className="card-title-group">
            <div className="card-icon-pill">
              <Clock className="card-header-icon" />
            </div>
            <div>
              <h3 className="card-heading">Salon Timings & Policy</h3>
              <p className="card-subheading">
                {business?.address || "Indiranagar, Bengaluru"}
              </p>
            </div>
          </div>
        </div>

        <div className="policy-content-list">
          <div className="policy-row">
            <span className="policy-day">Tuesday – Sunday</span>
            <span className="policy-time">09:00 AM – 08:00 PM</span>
          </div>
          <div className="policy-row closed">
            <span className="policy-day">Monday</span>
            <span className="policy-time closed-tag">Closed (Weekly Holiday)</span>
          </div>

          <div className="policy-alert-box">
            <ShieldCheck className="alert-icon" />
            <div>
              <strong>Cancellation Policy:</strong> Free cancellations up to{" "}
              {business?.cancellation_window_minutes
                ? Math.round(business.cancellation_window_minutes / 60)
                : 2}{" "}
              hours before appointment.
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
