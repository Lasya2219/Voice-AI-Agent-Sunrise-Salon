# Sunrise Salon — AI Voice Receptionist: Owner Handover Note

**Welcome to your new AI Voice Receptionist!**  
This document is a non-technical guide designed for salon management. It explains what your automated voice receptionist can do, the safety guardrails protecting your business, and simple instructions on how to update salon hours, service prices, stylists, and policies.

---

## 1. What the Voice Receptionist Does

Your AI receptionist works 24 hours a day, 7 days a week to handle phone calls and online visitors without taking breaks:

* **Warm Salon Welcome:** Greets callers with a natural, friendly voice and asks how it can help.
* **Answers Inquiries Instantly:** Accurately answers questions about haircut prices, facial packages, stylist specialties, salon address, parking, and opening hours.
* **Checks Real-Time Availability:** Checks your salon calendar live to see which stylists and time slots are open for any date.
* **Books Confirmed Appointments:** Collects the client's name, phone number, desired service, stylist, and time. It reads back the full details and **only reserves the slot once the customer explicitly says yes**.
* **Recognizes Returning Clients:** Automatically recognizes repeat clients by their 10-digit phone number and greets them by name.
* **Reschedules & Cancels:** Lets customers move their appointment to a new date or cancel, while automatically applying your 2-hour cancellation policy.

---

## 2. What the Voice Receptionist Will NOT Do (Safety Guardrails)

We designed the receptionist with strict guardrails so your calendar stays organized and protected:

* **No Double Bookings:** It will **never** book two clients with the same stylist at the same time.
* **No Invented Slots or Prices:** It never guesses or makes up prices. It strictly quotes the prices and times recorded in your database.
* **No Bookings Outside Working Hours:** It will refuse appointments before opening time, after closing time, or on days when a stylist is off.
* **No Accidental Changes:** It will never finalize a booking, reschedule, or cancel unless the customer explicitly confirms the action.
* **Zero Privacy Leaks:** It will never reveal one customer’s appointment details to another caller.
* **Polite Boundary on Out-of-Scope Requests:** If a caller asks personal questions or has a complex dispute, it politely asks them to speak with salon staff in person.

---

## 3. How to Update Salon Details, Hours & Prices

Your receptionist reads everything live from your central salon database. Whenever you update your records, the receptionist learns the changes **immediately without needing any reprogramming**.

### A. How to Update Service Prices & Durations
* **Database Table:** `services`
* **Fields:** `price` (e.g., change `800` to `900`), `duration_minutes` (e.g., change `45` to `60`).
* **Effect:** The very next caller asking for haircut prices will hear the updated price and the scheduling engine will allocate the new duration.

### B. How to Change Working Hours
* **Database Table:** `working_hours`
* **Fields:** `open_time` (e.g., `10:00:00`), `close_time` (e.g., `20:00:00`), and `is_closed` (`true` or `false`).
* **Example:** If you decide to open on Sundays for holiday season, set Sunday’s `is_closed` to `false`. The receptionist will immediately offer Sunday slots to callers.

### C. How to Add or Change Stylists
* **Database Table:** `stylists` & `stylist_services`
* **Adding a Stylist:** Add the stylist's name and specialty (e.g., *"Priya Nair — Senior Colorist"*).
* **Assigning Services:** Link which service IDs they can perform in `stylist_services`.
* **Effect:** Callers can immediately ask for that stylist by name.

### D. How to Update Policies & Salon Information
* **Database Table:** `businesses`
* **Fields:**
  * `phone`: Contact number displayed to clients.
  * `address`: Indiranagar address provided to callers asking for directions.
  * `cancellation_window_hours`: Set to `2` (clients cancelling more than 2 hours in advance receive a free cancellation; cancellations within 2 hours are recorded as late).

---

## 4. Daily Manager Checklist

1. **Check Bookings Every Morning:** Open your salon web dashboard tab (**My Bookings**) to view the day's confirmed appointments, assigned stylists, and client contact numbers.
2. **Review Cancellations:** View cancelled appointments to open slots for walk-in clients.
3. **Emergency Support:** If salon internet or backend servers go down, callers are politely informed to call back shortly, preventing lost bookings or errors.

---
*Sunrise Salon Operations Team — AI Automation & Receptionist Handover*
