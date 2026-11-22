import logging
import os
import re
import textwrap
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
    TurnHandlingOptions,
    cli,
    function_tool,
)
from livekit.plugins import groq, openai, silero

logger = logging.getLogger("agent")

load_dotenv(".env.local")
load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BUSINESS_SLUG = os.getenv("BUSINESS_SLUG", "sunrise-salon")
try:
    SALON_TIMEZONE = ZoneInfo("Asia/Kolkata")
except Exception:
    from datetime import timezone
    SALON_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")


def normalise_phone(value: str) -> str:
    """Normalise phone to the last 10 digits, matching backend validation."""
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10:
        raise ValueError("Phone number must have at least 10 digits.")
    return digits[-10:]


def parse_date_str(date_str: str, tz: ZoneInfo = SALON_TIMEZONE) -> date:
    """Parse various natural and formatted date strings into a date object."""
    clean = date_str.strip().lower()
    now_local = datetime.now(tz)

    if clean in ("today", "current"):
        return now_local.date()
    if clean in ("tomorrow", "tmrw"):
        return (now_local + timedelta(days=1)).date()
    if clean in ("day after tomorrow",):
        return (now_local + timedelta(days=2)).date()

    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d",
        "%b %d",
    ):
        try:
            parsed = datetime.strptime(clean, fmt)
            if "%Y" not in fmt and "%y" not in fmt:
                parsed = parsed.replace(year=now_local.year)
                if parsed.date() < now_local.date():
                    parsed = parsed.replace(year=now_local.year + 1)
            return parsed.date()
        except ValueError:
            pass

    try:
        return datetime.fromisoformat(clean).date()
    except Exception:
        pass

    raise ValueError(f"Could not parse date '{date_str}'. Please use YYYY-MM-DD format.")


def parse_time_str(time_str: str) -> tuple[int, int]:
    """Parse 12-hour or 24-hour time string into (hour, minute)."""
    clean = time_str.strip().lower()
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", clean)
    if not match:
        raise ValueError(
            f"Could not parse time '{time_str}'. Please use format like '10:00 AM' or '14:30'."
        )
    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    meridiem = match.group(3)

    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time in '{time_str}'.")

    return hour, minute


def format_slot_time(dt: datetime, tz: ZoneInfo = SALON_TIMEZONE) -> str:
    """Format slot time in 12-hour AM/PM format."""
    local = dt.astimezone(tz)
    return local.strftime("%I:%M %p").lstrip("0")


def format_datetime_readable(dt: datetime, tz: ZoneInfo = SALON_TIMEZONE) -> str:
    """Format datetime into a voice-friendly string (e.g. Monday, November 23 at 10:00 AM)."""
    local = dt.astimezone(tz)
    return local.strftime("%A, %B %d at %I:%M %p").replace(" 0", " ")


class Assistant(Agent):
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__(
            instructions=textwrap.dedent(
                """
                You are the friendly, polite, and professional voice receptionist for Sunrise Salon.

                Your responsibilities:
                - Welcome callers warmly.
                - Answer questions about salon services, prices, stylists, working hours, and policies.
                - Help callers check availability, book, reschedule, or cancel appointments.
                - Identify repeat callers using their 10-digit phone number.

                Conversation rules:
                - Ask ONLY ONE question at a time.
                - Keep responses short, concise, and natural (1 to 2 sentences) suitable for speech.
                - Never ask for information the caller has already provided.
                - Clarify ambiguous dates, times, or service choices politely.
                - CRITICAL VOICE FORMATTING RULES:
                  * You are speaking on a live phone call. Always output plain conversational English sentences.
                  * NEVER use Markdown, bullet points (- or *), numbered lists, colons, brackets, or tables.
                  * NEVER use line breaks to separate list items.
                  * When listing available slots, times, or services, speak them in a single fluid sentence separated by commas (for example: "Available times with Anita tomorrow are 12:00 PM, 12:30 PM, 1:00 PM, and 1:30 PM. Which time works best for you?").
                  * Keep slot options to at most 4 to 5 times so the caller is not overwhelmed.
                - When cancelling, explain the cancellation policy (free if more than 2 hours in advance; late cancellation if within 2 hours).
                - BEFORE calling create_booking, reschedule_booking, or cancel_booking with customer_confirmed=True:
                  1. Always call the tool first with customer_confirmed=False to verify availability and stage the details.
                  2. Read back the full details to the caller (Service, Stylist, Date, Time, Name, Phone).
                  3. Ask for the customer's explicit confirmation ("Would you like me to confirm this?").
                  4. Only after the caller says 'yes' or explicitly confirms, call the tool with customer_confirmed=True.

                Critical guardrails:
                - NEVER invent service prices, stylist names, slot availability, or business information. Always use your tools.
                - NEVER claim an appointment is booked, rescheduled, or cancelled without receiving confirmation from the tool.
                - Always use Indian Standard Time (Asia/Kolkata).
                """
            ),
        )
        # Optional custom transport (e.g. for in-process testing)
        self.transport = transport
        # Server-side conversation context for the caller
        self.identified_phone: str | None = None
        self.customer_name: str | None = None
        self.pending_booking: dict | None = None
        self.pending_reschedule: dict | None = None
        self.pending_cancel: dict | None = None
        self.confirmed_bookings_cache: dict[tuple[str, str], int] = {}
        self._services_cache: list[dict] | None = None
        self._stylists_cache: list[dict] | None = None
        self._business_cache: dict | None = None

    def _create_http_client(self, timeout: float = 10.0) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout, transport=self.transport)

    async def _get_services(self, client: httpx.AsyncClient) -> list[dict]:
        if self._services_cache is None:
            res = await client.get(f"{BACKEND_URL}/api/services")
            res.raise_for_status()
            self._services_cache = res.json()
        return self._services_cache

    async def _get_stylists(self, client: httpx.AsyncClient) -> list[dict]:
        if self._stylists_cache is None:
            res = await client.get(f"{BACKEND_URL}/api/stylists")
            res.raise_for_status()
            self._stylists_cache = res.json()
        return self._stylists_cache

    async def _get_business(self, client: httpx.AsyncClient) -> dict:
        if self._business_cache is None:
            res = await client.get(f"{BACKEND_URL}/api/business")
            res.raise_for_status()
            self._business_cache = res.json()
        return self._business_cache

    async def _resolve_service(
        self, client: httpx.AsyncClient, query: str
    ) -> tuple[dict | None, str | None]:
        """Resolve a service name or ID to a service dict. Returns (service_dict, error_message)."""
        services = await self._get_services(client)
        query_clean = query.strip().lower()

        # Direct ID match
        if query_clean.isdigit():
            svc_id = int(query_clean)
            for s in services:
                if s["id"] == svc_id:
                    return s, None
            return None, f"Service with ID {svc_id} was not found."

        # Exact name match
        for s in services:
            if s["name"].lower() == query_clean:
                return s, None

        # Partial / Substring matches
        matches = [s for s in services if query_clean in s["name"].lower()]
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            match_names = ", ".join(f"'{m['name']}' (₹{m['price']})" for m in matches)
            return (
                None,
                f"We offer multiple matching services: {match_names}. Please specify which one you prefer.",
            )

        # Keyword aliases
        if "haircut" in query_clean:
            return (
                None,
                "We offer 'Women's Haircut' (₹600) and 'Men's Haircut' (₹400). Please specify which haircut you would like.",
            )
        if "color" in query_clean or "colour" in query_clean:
            for s in services:
                if "colour" in s["name"].lower() or "color" in s["name"].lower():
                    return s, None
        if "spa" in query_clean:
            for s in services:
                if "spa" in s["name"].lower():
                    return s, None
        if "facial" in query_clean:
            for s in services:
                if "facial" in s["name"].lower():
                    return s, None
        if "cleanup" in query_clean or "clean-up" in query_clean or "clean up" in query_clean:
            for s in services:
                if "clean-up" in s["name"].lower():
                    return s, None

        all_names = ", ".join(f"'{s['name']}'" for s in services)
        return (
            None,
            f"Service '{query}' not found. Available services: {all_names}.",
        )

    async def _resolve_stylist(
        self, client: httpx.AsyncClient, query: str
    ) -> tuple[dict | None, str | None]:
        """Resolve a stylist name or ID to a stylist dict."""
        if not query or not query.strip():
            return None, None
        stylists = await self._get_stylists(client)
        query_clean = query.strip().lower()

        if query_clean.isdigit():
            st_id = int(query_clean)
            for st in stylists:
                if st["id"] == st_id:
                    return st, None
            return None, f"Stylist with ID {st_id} was not found."

        for st in stylists:
            if st["name"].lower() == query_clean:
                return st, None

        matches = [st for st in stylists if query_clean in st["name"].lower()]
        if len(matches) == 1:
            return matches[0], None

        available_names = ", ".join(st["name"] for st in stylists if st.get("is_active", True))
        return None, f"Stylist '{query}' not found. Available stylists: {available_names}."

    # 1. get_business_info (Preserved & Enhanced with live service/stylist context)
    @function_tool
    async def get_business_info(self, context: RunContext) -> str:
        """Get official business information, including salon name,
        address, timezone, appointment duration, and cancellation policy."""
        try:
            async with self._create_http_client(timeout=10.0) as client:
                business = await self._get_business(client)
                try:
                    services = await self._get_services(client)
                    stylists = await self._get_stylists(client)
                except Exception:
                    services, stylists = [], []

            services_summary = ", ".join(
                f"{s['name']} (₹{int(s['price']) if s['price'] == int(s['price']) else s['price']}{' onwards' if s.get('is_price_from') else ''}, {s['duration_minutes']} mins)"
                for s in services
            )
            stylists_summary = ", ".join(
                s["name"] for s in stylists if s.get("is_active", True)
            )

            result = (
                f"Business: {business['name']}. "
                f"Address: {business['address']}. "
                f"Timezone: {business['timezone']}. "
                f"Appointment slot duration: "
                f"{business['slot_duration_minutes']} minutes. "
                f"Cancellation window: "
                f"{business['cancellation_window_minutes']} minutes."
            )
            if services_summary:
                result += f" Available services: {services_summary}."
            if stylists_summary:
                result += f" Stylists: {stylists_summary}."
            return result
        except httpx.HTTPError as err:
            logger.error("Failed to fetch business info: %s", err)
            return "Unable to connect to the salon service right now. Please try again shortly."

    # 2. check_availability
    @function_tool
    async def check_availability(
        self,
        context: RunContext,
        service: str,
        requested_date: str,
        stylist: str = "",
    ) -> str:
        """Check available appointment slots for a requested service, date, and optionally a specific stylist.
        Never invent available slots. Always check real-time availability via this tool.

        Args:
            service: Name or ID of the service (e.g. 'Women\'s Haircut', 'Hair Spa', 'Facial').
            requested_date: Date to check in YYYY-MM-DD format (or 'today', 'tomorrow').
            stylist: Optional name or ID of the preferred stylist (e.g. 'Anita', 'Rahul', 'Kavya'). Leave empty for any available stylist.
        """
        try:
            req_date = parse_date_str(requested_date, SALON_TIMEZONE)
        except ValueError as e:
            return str(e)

        try:
            async with self._create_http_client(timeout=10.0) as client:
                svc_dict, err = await self._resolve_service(client, service)
                if err:
                    return err

                stylist_dict, st_err = await self._resolve_stylist(client, stylist)
                if st_err:
                    return st_err

                params = {
                    "business_slug": BUSINESS_SLUG,
                    "service_id": svc_dict["id"],
                    "requested_date": req_date.isoformat(),
                }
                if stylist_dict:
                    params["stylist_id"] = stylist_dict["id"]

                response = await client.get(
                    f"{BACKEND_URL}/api/availability", params=params
                )
                if response.status_code == 404:
                    detail = response.json().get("detail", "Availability check failed.")
                    return f"Availability check: {detail}"
                response.raise_for_status()
                data = response.json()

            available_slots = data.get("available_slots", [])
            svc_name = svc_dict["name"]
            date_readable = req_date.strftime("%A, %B %d, %Y")

            if available_slots:
                # Group slots by stylist if checking all stylists
                slot_strings = []
                for s in available_slots:
                    dt = datetime.fromisoformat(s["start_time"])
                    time_str = format_slot_time(dt, SALON_TIMEZONE)
                    if stylist_dict:
                        slot_strings.append(time_str)
                    else:
                        slot_strings.append(f"{time_str} with {s['stylist_name']}")
                slots_text = ", ".join(slot_strings)
                stylist_note = f" with {stylist_dict['name']}" if stylist_dict else ""
                return (
                    f"On {date_readable}, available slots for {svc_name}{stylist_note} are: {slots_text}. "
                    "Which time would you prefer?"
                )

            # No slots available on requested date
            reason = data.get("reason")
            reason_map = {
                "past_date": f"The date {date_readable} is in the past. Please choose a future date.",
                "business_closed": f"Sunrise Salon is closed on {req_date.strftime('%A')}s.",
                "stylist_not_working": f"The requested stylist does not work on {req_date.strftime('%A')}s.",
                "fully_booked": f"All slots for {svc_name} on {date_readable} are fully booked.",
            }
            explanation = reason_map.get(
                reason, f"No slots are available for {svc_name} on {date_readable}."
            )

            next_date_str = data.get("next_available_date")
            next_slots = data.get("next_available_slots", [])
            if next_date_str and next_slots:
                next_date = date.fromisoformat(next_date_str)
                next_readable = next_date.strftime("%A, %B %d, %Y")
                next_slot_times = [
                    f"{format_slot_time(datetime.fromisoformat(s['start_time']), SALON_TIMEZONE)} ({s['stylist_name']})"
                    for s in next_slots[:6]
                ]
                explanation += (
                    f" However, the next available date is {next_readable} with slots at: "
                    + ", ".join(next_slot_times)
                    + ". Would you like one of these?"
                )

            return explanation

        except httpx.HTTPError as err:
            logger.error("Availability API error: %s", err)
            return "Unable to check availability with the booking server right now. Please try again in a moment."

    # 3. identify_caller
    @function_tool
    async def identify_caller(
        self,
        context: RunContext,
        phone_number: str,
    ) -> str:
        """Identify the customer using their phone number, loading their identity and booking context for the conversation.

        Args:
            phone_number: The customer's 10-digit mobile phone number.
        """
        try:
            norm_phone = normalise_phone(phone_number)
        except ValueError as e:
            return str(e)

        self.identified_phone = norm_phone

        # The backend does not have a dedicated customer profile API (/api/customers).
        # We query the existing customer booking endpoint (/api/bookings/customer) to find existing customer records.
        try:
            async with self._create_http_client(timeout=10.0) as client:
                res = await client.get(
                    f"{BACKEND_URL}/api/bookings/customer",
                    params={
                        "business_slug": BUSINESS_SLUG,
                        "customer_phone": norm_phone,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    bookings = data.get("bookings", [])
                    if bookings:
                        self.customer_name = bookings[0]["customer_name"]
                        total = data.get("total", len(bookings))
                        return (
                            f"Caller identified as {self.customer_name} (phone: {norm_phone}) "
                            f"with {total} confirmed appointment(s) on file. You can now list, "
                            f"reschedule, or cancel their bookings, or book a new appointment."
                        )

            # If no bookings exist for this phone number
            return (
                f"Caller phone number recorded as {norm_phone}. "
                f"(Note: The backend has no dedicated customer lookup endpoint (/api/customers); "
                f"unregistered callers or customers with no prior bookings cannot be retrieved by phone alone). "
                f"Please ask the caller for their name if they would like to book an appointment."
            )
        except httpx.HTTPError as err:
            logger.error("Error identifying caller: %s", err)
            return f"Phone number recorded as {norm_phone}. Please ask for their name to proceed."

    # 4. create_booking
    @function_tool
    async def create_booking(
        self,
        context: RunContext,
        service: str,
        date: str,
        time: str,
        customer_name: str,
        phone_number: str = "",
        stylist: str = "",
        customer_confirmed: bool = False,
    ) -> str:
        """Create a new confirmed appointment.
        SAFETY RULE: Before setting customer_confirmed=True, you MUST first run this tool with customer_confirmed=False to verify availability, read back the complete details to the caller, and ask for their explicit confirmation. ONLY set customer_confirmed=True when the caller explicitly confirms.

        Args:
            service: Service name or ID (e.g. 'Women\'s Haircut', 'Hair Spa', 'Facial').
            date: Appointment date (YYYY-MM-DD, or 'today', 'tomorrow').
            time: Appointment start time (e.g. '10:00 AM', '11:30', or '14:00').
            customer_name: Full name of the customer.
            phone_number: 10-digit phone number. Defaults to current identified caller.
            stylist: Optional preferred stylist name or ID (e.g. 'Anita', 'Rahul', 'Kavya').
            customer_confirmed: Set to False first to check slot availability and stage details. Set to True ONLY after customer explicitly says yes/confirms.
        """
        # Determine phone number
        if phone_number and phone_number.strip():
            try:
                norm_phone = normalise_phone(phone_number)
            except ValueError as e:
                return str(e)
            if self.identified_phone and self.identified_phone != norm_phone:
                return (
                    f"Access restricted: Current session is identified as phone {self.identified_phone}. "
                    f"Cannot create bookings for a different phone number in the same session."
                )
            self.identified_phone = norm_phone
        elif self.identified_phone:
            norm_phone = self.identified_phone
        else:
            return "Customer phone number is required. Please ask the caller for their 10-digit mobile number."

        # Customer name
        name_clean = customer_name.strip() if customer_name else ""
        if not name_clean:
            if self.customer_name:
                name_clean = self.customer_name
            else:
                return "Customer name is required. Please ask the caller for their name."
        self.customer_name = name_clean

        # Parse date and time
        try:
            req_date = parse_date_str(date, SALON_TIMEZONE)
            hour, minute = parse_time_str(time)
            local_start = datetime(
                req_date.year,
                req_date.month,
                req_date.day,
                hour,
                minute,
                tzinfo=SALON_TIMEZONE,
            )
        except ValueError as e:
            return str(e)

        # Ensure future datetime
        if local_start <= datetime.now(SALON_TIMEZONE):
            return "This appointment time has already passed. Please choose a future time."

        # Guard against accidental duplicate tool calls / double-booking in the same session
        cache_key = (norm_phone, local_start.isoformat())
        if cache_key in self.confirmed_bookings_cache:
            existing_id = self.confirmed_bookings_cache[cache_key]
            return f"This appointment has already been confirmed (Booking ID #{existing_id}). No duplicate booking made."

        try:
            async with self._create_http_client(timeout=10.0) as client:
                svc_dict, err = await self._resolve_service(client, service)
                if err:
                    return err

                stylist_dict, st_err = await self._resolve_stylist(client, stylist)
                if st_err:
                    return st_err

                # Check slot availability
                avail_params = {
                    "business_slug": BUSINESS_SLUG,
                    "service_id": svc_dict["id"],
                    "requested_date": req_date.isoformat(),
                }
                if stylist_dict:
                    avail_params["stylist_id"] = stylist_dict["id"]

                avail_res = await client.get(
                    f"{BACKEND_URL}/api/availability", params=avail_params
                )
                if avail_res.status_code != 200:
                    return f"Unable to verify slot availability: {avail_res.text}"

                avail_data = avail_res.json()
                matching_slots = [
                    s
                    for s in avail_data.get("available_slots", [])
                    if datetime.fromisoformat(s["start_time"]).astimezone(
                        SALON_TIMEZONE
                    )
                    == local_start
                ]

                if not matching_slots:
                    # Provide alternative slots
                    alts = [
                        f"{format_slot_time(datetime.fromisoformat(s['start_time']), SALON_TIMEZONE)} ({s['stylist_name']})"
                        for s in avail_data.get("available_slots", [])[:4]
                    ]
                    alt_text = (
                        f" Available slots on this date: {', '.join(alts)}."
                        if alts
                        else " No slots available on this date."
                    )
                    return f"The slot at {time} on {req_date.strftime('%A, %B %d')} is not available.{alt_text}"

                # Choose stylist: either requested stylist or first available stylist
                selected_slot = matching_slots[0]
                stylist_id = selected_slot["stylist_id"]
                stylist_name = selected_slot["stylist_name"]

                formatted_time = format_datetime_readable(local_start, SALON_TIMEZONE)

                # STAGE 1: Unconfirmed — Read back details and request confirmation
                if not customer_confirmed:
                    self.pending_booking = {
                        "business_slug": BUSINESS_SLUG,
                        "customer_name": name_clean,
                        "customer_phone": norm_phone,
                        "service_id": svc_dict["id"],
                        "stylist_id": stylist_id,
                        "start_time": local_start.isoformat(),
                        "service_name": svc_dict["name"],
                        "stylist_name": stylist_name,
                        "formatted_time": formatted_time,
                    }
                    return (
                        f"The slot at {formatted_time} for {svc_dict['name']} with {stylist_name} is available! "
                        f"Please read back these complete details to the caller: "
                        f"Service: {svc_dict['name']}, Stylist: {stylist_name}, Date and Time: {formatted_time}, "
                        f"Name: {name_clean}, Phone: {norm_phone}. "
                        f"Then ask: 'Would you like me to go ahead and book this appointment?' "
                        f"Do NOT call create_booking with customer_confirmed=True until the caller explicitly confirms."
                    )

                # STAGE 2: Confirmed — Guard against duplicate bookings
                cache_key = (norm_phone, local_start.isoformat())
                if cache_key in self.confirmed_bookings_cache:
                    existing_id = self.confirmed_bookings_cache[cache_key]
                    return f"This appointment has already been confirmed (Booking ID #{existing_id}). No duplicate booking made."

                # Send booking request to backend
                booking_payload = {
                    "business_slug": BUSINESS_SLUG,
                    "customer_name": name_clean,
                    "customer_phone": norm_phone,
                    "service_id": svc_dict["id"],
                    "stylist_id": stylist_id,
                    "start_time": local_start.isoformat(),
                }
                res = await client.post(
                    f"{BACKEND_URL}/api/bookings", json=booking_payload
                )

                if res.status_code == 404:
                    detail = res.json().get("detail", "Booking failed.")
                    return f"Booking could not be created: {detail}"

                res.raise_for_status()
                data = res.json()

                if data.get("success") is True:
                    b_id = data["booking_id"]
                    self.confirmed_bookings_cache[cache_key] = b_id
                    self.pending_booking = None
                    return (
                        f"Booking confirmed successfully! Booking ID: #{b_id}. "
                        f"Appointment details: {data['service_name']} with {data['stylist_name']} "
                        f"on {format_datetime_readable(datetime.fromisoformat(data['start_time']), SALON_TIMEZONE)} "
                        f"for {data['customer_name']}. Status: confirmed."
                    )
                else:
                    # BookingFailure
                    msg = data.get("message", "Slot unavailable.")
                    reason = data.get("reason", "")
                    alts = [
                        format_slot_time(
                            datetime.fromisoformat(s["start_time"]), SALON_TIMEZONE
                        )
                        for s in data.get("alternative_slots", [])[:4]
                    ]
                    alt_msg = (
                        f" Alternative slots available: {', '.join(alts)}."
                        if alts
                        else ""
                    )
                    return f"Booking could not be completed: {msg} (Reason: {reason}).{alt_msg}"

        except httpx.HTTPError as err:
            logger.error("Booking creation error: %s", err)
            return "There was an error communicating with the booking system. Please try again."

    # 5. list_my_bookings
    @function_tool
    async def list_my_bookings(
        self,
        context: RunContext,
        phone_number: str = "",
    ) -> str:
        """Retrieve the identified customer's confirmed appointments. Never exposes another customer's bookings.

        Args:
            phone_number: Optional 10-digit phone number. Uses identified caller's phone if already identified.
        """
        if phone_number and phone_number.strip():
            try:
                norm_phone = normalise_phone(phone_number)
            except ValueError as e:
                return str(e)
            if self.identified_phone and self.identified_phone != norm_phone:
                return (
                    f"Access denied: You cannot view bookings for another customer. "
                    f"The current session is identified as {self.identified_phone}."
                )
            self.identified_phone = norm_phone
        elif self.identified_phone:
            norm_phone = self.identified_phone
        else:
            return "Please provide your 10-digit phone number so I can retrieve your appointments."

        try:
            async with self._create_http_client(timeout=10.0) as client:
                res = await client.get(
                    f"{BACKEND_URL}/api/bookings/customer",
                    params={
                        "business_slug": BUSINESS_SLUG,
                        "customer_phone": norm_phone,
                    },
                )
                if res.status_code == 404:
                    return f"No records found for phone number ending in {norm_phone[-4:]}."
                res.raise_for_status()
                data = res.json()

            bookings = data.get("bookings", [])
            if not bookings:
                return f"No confirmed appointments found for phone number ending in {norm_phone[-4:]}."

            lines = []
            for b in bookings:
                start_dt = datetime.fromisoformat(b["start_time"])
                readable = format_datetime_readable(start_dt, SALON_TIMEZONE)
                lines.append(
                    f"Booking #{b['booking_id']} for {b['service_name']} with {b['stylist_name']} on {readable}"
                )

            return f"You have {len(bookings)} confirmed appointment(s): " + "; ".join(lines) + "."

        except httpx.HTTPError as err:
            logger.error("Error listing bookings: %s", err)
            return "Unable to retrieve your bookings from the salon system right now. Please try again in a moment."

    # 6. reschedule_booking
    @function_tool
    async def reschedule_booking(
        self,
        context: RunContext,
        booking_id: int,
        new_date: str,
        new_time: str,
        phone_number: str = "",
        customer_confirmed: bool = False,
    ) -> str:
        """Reschedule an existing confirmed appointment to a new date and time.
        Must check availability, read back details, and obtain customer confirmation before finalizing.

        Args:
            booking_id: The ID of the existing confirmed booking to reschedule.
            new_date: The new date (YYYY-MM-DD, or 'today', 'tomorrow').
            new_time: The new start time (e.g. '11:00 AM', '15:00').
            phone_number: Customer's 10-digit phone number. Defaults to identified phone.
            customer_confirmed: Set to False first to check availability and read back details. Set to True ONLY after customer explicitly confirms the reschedule.
        """
        # Phone validation
        if phone_number and phone_number.strip():
            try:
                norm_phone = normalise_phone(phone_number)
            except ValueError as e:
                return str(e)
            if self.identified_phone and self.identified_phone != norm_phone:
                return "Access denied: You cannot reschedule bookings for another customer."
            self.identified_phone = norm_phone
        elif self.identified_phone:
            norm_phone = self.identified_phone
        else:
            return "Please provide your phone number to verify and reschedule your booking."

        # Parse new datetime
        try:
            req_date = parse_date_str(new_date, SALON_TIMEZONE)
            hour, minute = parse_time_str(new_time)
            new_start_dt = datetime(
                req_date.year,
                req_date.month,
                req_date.day,
                hour,
                minute,
                tzinfo=SALON_TIMEZONE,
            )
        except ValueError as e:
            return str(e)

        if new_start_dt <= datetime.now(SALON_TIMEZONE):
            return "The new appointment time must be in the future."

        try:
            async with self._create_http_client(timeout=10.0) as client:
                # 1. Verify this booking belongs to the caller
                res = await client.get(
                    f"{BACKEND_URL}/api/bookings/customer",
                    params={
                        "business_slug": BUSINESS_SLUG,
                        "customer_phone": norm_phone,
                    },
                )
                if res.status_code != 200:
                    return "Could not retrieve your bookings to verify ownership."

                existing_bookings = res.json().get("bookings", [])
                target_booking = next(
                    (b for b in existing_bookings if b["booking_id"] == booking_id),
                    None,
                )
                if not target_booking:
                    return f"Booking #{booking_id} was not found among confirmed appointments for your phone number."

                formatted_new_time = format_datetime_readable(
                    new_start_dt, SALON_TIMEZONE
                )

                # STAGE 1: Check availability and ask for confirmation
                if not customer_confirmed:
                    self.pending_reschedule = {
                        "booking_id": booking_id,
                        "new_start_time": new_start_dt.isoformat(),
                        "service_name": target_booking["service_name"],
                        "stylist_name": target_booking["stylist_name"],
                        "formatted_new_time": formatted_new_time,
                    }
                    return (
                        f"The new time slot on {formatted_new_time} is requested for Booking #{booking_id} "
                        f"({target_booking['service_name']} with {target_booking['stylist_name']}). "
                        f"Please read back the new details to the caller: "
                        f"Booking #{booking_id}, Service: {target_booking['service_name']}, "
                        f"Stylist: {target_booking['stylist_name']}, New Time: {formatted_new_time}. "
                        f"Then ask: 'Would you like me to confirm this reschedule?' "
                        f"Do NOT call reschedule_booking with customer_confirmed=True until the caller explicitly confirms."
                    )

                # STAGE 2: Confirmed — Call backend reschedule API
                payload = {
                    "business_slug": BUSINESS_SLUG,
                    "booking_id": booking_id,
                    "customer_phone": norm_phone,
                    "new_start_time": new_start_dt.isoformat(),
                }
                reschedule_res = await client.put(
                    f"{BACKEND_URL}/api/bookings/reschedule", json=payload
                )

                if reschedule_res.status_code == 404:
                    detail = reschedule_res.json().get("detail", "Reschedule failed.")
                    return f"Reschedule failed: {detail}"

                reschedule_res.raise_for_status()
                data = reschedule_res.json()

                if data.get("success") is True:
                    self.pending_reschedule = None
                    new_start = datetime.fromisoformat(data["start_time"])
                    return (
                        f"Booking #{booking_id} successfully rescheduled to "
                        f"{format_datetime_readable(new_start, SALON_TIMEZONE)} for "
                        f"{data['service_name']} with {data['stylist_name']}. Status: confirmed."
                    )
                else:
                    # BookingFailure
                    msg = data.get("message", "Requested slot unavailable.")
                    reason = data.get("reason", "")
                    alts = [
                        format_slot_time(
                            datetime.fromisoformat(s["start_time"]), SALON_TIMEZONE
                        )
                        for s in data.get("alternative_slots", [])[:4]
                    ]
                    alt_text = (
                        f" Available alternative slots: {', '.join(alts)}."
                        if alts
                        else ""
                    )
                    return f"Could not reschedule booking: {msg} (Reason: {reason}).{alt_text}"

        except httpx.HTTPError as err:
            logger.error("Reschedule API error: %s", err)
            return "Unable to communicate with the reschedule server right now. Please try again."

    # 7. cancel_booking
    @function_tool
    async def cancel_booking(
        self,
        context: RunContext,
        booking_id: int,
        phone_number: str = "",
        customer_confirmed: bool = False,
    ) -> str:
        """Cancel an existing confirmed appointment.
        Explains cancellation policy (free if more than 2 hours in advance, late cancellation if within 2 hours) and requires explicit confirmation before cancelling.

        Args:
            booking_id: The ID of the booking to cancel.
            phone_number: Customer's 10-digit phone number. Defaults to identified phone.
            customer_confirmed: Set to False first to explain policy and ask for confirmation. Set to True ONLY after customer explicitly confirms.
        """
        # Phone validation
        if phone_number and phone_number.strip():
            try:
                norm_phone = normalise_phone(phone_number)
            except ValueError as e:
                return str(e)
            if self.identified_phone and self.identified_phone != norm_phone:
                return "Access denied: You cannot cancel bookings for another customer."
            self.identified_phone = norm_phone
        elif self.identified_phone:
            norm_phone = self.identified_phone
        else:
            return "Please provide your phone number to verify and cancel your booking."

        try:
            async with self._create_http_client(timeout=10.0) as client:
                # 1. Verify this booking belongs to the caller
                res = await client.get(
                    f"{BACKEND_URL}/api/bookings/customer",
                    params={
                        "business_slug": BUSINESS_SLUG,
                        "customer_phone": norm_phone,
                    },
                )
                if res.status_code != 200:
                    return "Could not retrieve your bookings to verify ownership."

                existing_bookings = res.json().get("bookings", [])
                target_booking = next(
                    (b for b in existing_bookings if b["booking_id"] == booking_id),
                    None,
                )
                if not target_booking:
                    return f"Booking #{booking_id} was not found among confirmed appointments for your phone number."

                # Check cancellation window (cancellation_window_minutes = 120 / 2 hours)
                start_dt = datetime.fromisoformat(target_booking["start_time"]).astimezone(
                    SALON_TIMEZONE
                )
                now_dt = datetime.now(SALON_TIMEZONE)
                time_until = start_dt - now_dt
                is_late = time_until < timedelta(minutes=120)

                policy_explanation = (
                    "Notice: Your appointment is in less than 2 hours. According to salon policy, "
                    "cancelling now will be marked as a late cancellation."
                    if is_late
                    else "Notice: Since your appointment is more than 2 hours away, this cancellation is completely free of charge."
                )

                # STAGE 1: Unconfirmed — Explain policy and prompt for confirmation
                if not customer_confirmed:
                    self.pending_cancel = {
                        "booking_id": booking_id,
                        "service_name": target_booking["service_name"],
                        "stylist_name": target_booking["stylist_name"],
                    }
                    readable_time = format_datetime_readable(start_dt, SALON_TIMEZONE)
                    return (
                        f"You have requested to cancel Booking #{booking_id} for {target_booking['service_name']} "
                        f"with {target_booking['stylist_name']} scheduled for {readable_time}. "
                        f"{policy_explanation} "
                        f"Please ask the caller: 'Are you sure you want to cancel this appointment?' "
                        f"Do NOT call cancel_booking with customer_confirmed=True until the caller explicitly confirms."
                    )

                # STAGE 2: Confirmed — Call backend cancel API
                cancel_payload = {
                    "business_slug": BUSINESS_SLUG,
                    "booking_id": booking_id,
                    "customer_phone": norm_phone,
                }
                cancel_res = await client.put(
                    f"{BACKEND_URL}/api/bookings/cancel", json=cancel_payload
                )

                if cancel_res.status_code == 404:
                    detail = cancel_res.json().get("detail", "Cancellation failed.")
                    return f"Cancellation failed: {detail}"

                cancel_res.raise_for_status()
                data = cancel_res.json()
                self.pending_cancel = None

                policy_status = (
                    "Late cancellation (recorded as late cancellation under salon policy)"
                    if is_late
                    else "Free cancellation (no penalty)"
                )
                return (
                    f"Booking #{booking_id} for {data['service_name']} with {data['stylist_name']} "
                    f"has been successfully cancelled. Cancellation status: {policy_status}."
                )

        except httpx.HTTPError as err:
            logger.error("Cancellation API error: %s", err)
            return "Unable to communicate with the salon cancellation server right now. Please try again."


server = AgentServer()


@server.rtc_session(agent_name="sunrise-salon")
async def my_agent(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession(
        stt=groq.STT(
            model="whisper-large-v3-turbo",
            language="en",
        ),
        llm=groq.LLM(
            model="openai/gpt-oss-20b",
        ),
        # tts=openai.TTS(
        #     model="kokoro",
        #     voice="af_alloy",
        #     api_key="not-needed",
        #     base_url="http://localhost:8880/v1",
        #     response_format="pcm",
        # ),
        tts=groq.TTS(
            model="canopylabs/orpheus-v1-english",
            voice="autumn",  # Options: autumn, diana, hannah, austin, daniel, troy
        ),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection="vad",
            preemptive_generation={"enabled": False},
        ),
    )

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
        room=ctx.room,
    )

    # Join the room and connect to the user
    await ctx.connect()

    # Speak first: greet the user before they say anything
    await session.generate_reply(
        instructions="Enthusiastically greet the user and offer to help."
    )


if __name__ == "__main__":
    cli.run_app(server)
