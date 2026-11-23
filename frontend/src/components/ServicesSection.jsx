import { Scissors, Clock, Sparkles } from "lucide-react";

export default function ServicesSection({ services, isLoading }) {
  return (
    <section className="salon-card services-card">
      <div className="card-header">
        <div className="card-title-group">
          <div className="card-icon-pill">
            <Scissors className="card-header-icon" />
          </div>
          <div>
            <h3 className="card-heading">Services & Treatments</h3>
            <p className="card-subheading">Ask our receptionist to check available slots for any service</p>
          </div>
        </div>
      </div>

      <div className="services-grid">
        {isLoading ? (
          <div className="catalog-loading-state">
            <Sparkles className="spin-slow" />
            <span>Loading current salon catalog...</span>
          </div>
        ) : services.length === 0 ? (
          <p className="catalog-empty-state">No services found in salon catalog.</p>
        ) : (
          services.map((svc) => (
            <div key={svc.id} className="service-item-row">
              <div className="service-primary-info">
                <h4 className="service-title">{svc.name}</h4>
                {svc.notes && <p className="service-description">{svc.notes}</p>}
                <div className="service-duration-pill">
                  <Clock className="inline-icon-xs" />
                  <span>{svc.duration_minutes} mins</span>
                </div>
              </div>

              <div className="service-price-block">
                <span className="price-tag">
                  ₹{Number(svc.price).toLocaleString("en-IN")}
                </span>
                {svc.is_price_from && <span className="price-prefix">onwards</span>}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
