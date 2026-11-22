import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const BUSINESS_SLUG = import.meta.env.VITE_BUSINESS_SLUG || 'sunrise-salon';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

export const api = {
  // Business Info
  getBusiness: async () => {
    const res = await client.get('/business');
    return res.data;
  },

  // Services
  getServices: async () => {
    const res = await client.get('/services');
    return res.data;
  },

  // Stylists
  getStylists: async () => {
    const res = await client.get('/stylists');
    return res.data;
  },

  // Availability
  getAvailability: async (serviceId, requestedDate, stylistId = null) => {
    const params = {
      business_slug: BUSINESS_SLUG,
      service_id: serviceId,
      requested_date: requestedDate,
    };
    if (stylistId) {
      params.stylist_id = stylistId;
    }
    const res = await client.get('/availability', { params });
    return res.data;
  },

  // Bookings
  createBooking: async ({ customerName, customerPhone, serviceId, stylistId, startTime }) => {
    const res = await client.post('/bookings', {
      business_slug: BUSINESS_SLUG,
      customer_name: customerName,
      customer_phone: customerPhone,
      service_id: serviceId,
      stylist_id: stylistId,
      start_time: startTime,
    });
    return res.data;
  },

  getCustomerBookings: async (customerPhone) => {
    const res = await client.get('/bookings/customer', {
      params: {
        business_slug: BUSINESS_SLUG,
        customer_phone: customerPhone,
      },
    });
    return res.data;
  },

  rescheduleBooking: async (bookingId, newStartTime) => {
    const res = await client.put('/bookings/reschedule', {
      business_slug: BUSINESS_SLUG,
      booking_id: bookingId,
      new_start_time: newStartTime,
    });
    return res.data;
  },

  cancelBooking: async (bookingId, reason = 'Customer requested cancellation') => {
    const res = await client.put('/bookings/cancel', {
      business_slug: BUSINESS_SLUG,
      booking_id: bookingId,
      reason,
    });
    return res.data;
  },
};

export default api;
