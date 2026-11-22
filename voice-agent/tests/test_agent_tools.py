import asyncio
import os
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock

import httpx
import pytest
from dotenv import load_dotenv

# Ensure both backend and voice-agent/src are in python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))
sys.path.insert(0, os.path.join(ROOT_DIR, "voice-agent", "src"))

# Load backend environment variables (DATABASE_URL, etc.)
load_dotenv(os.path.join(ROOT_DIR, "backend", ".env"))
load_dotenv(os.path.join(ROOT_DIR, "voice-agent", ".env.local"))

# Load backend app for in-process ASGI testing
from app.main import app
from app.database import engine
from agent import Assistant, SALON_TIMEZONE, normalise_phone, parse_date_str, parse_time_str


@pytest.fixture(autouse=True)
async def reset_db_pool():
    """Ensure database connection pool is disposed between test event loops."""
    yield
    await engine.dispose()


@pytest.fixture
def mock_run_context():
    """Mock RunContext for LiveKit tools."""
    ctx = MagicMock()
    return ctx


@pytest.fixture
def agent():
    """Create Assistant instance using ASGITransport against the FastAPI app."""
    transport = httpx.ASGITransport(app=app)
    return Assistant(transport=transport)


def get_next_weekday(weekday_int: int) -> date:
    """Find the next future date with the specified weekday (0=Mon, 1=Tue, ..., 6=Sun)."""
    now = datetime.now(SALON_TIMEZONE)
    days_ahead = (weekday_int - now.weekday()) % 7
    if days_ahead <= 0:
        days_ahead += 7
    return (now + timedelta(days=days_ahead)).date()


@pytest.mark.asyncio
async def test_get_business_info(agent, mock_run_context):
    """Test 1: get_business_info returns salon info, services, and stylists."""
    result = await agent.get_business_info(mock_run_context)
    assert "Business: Sunrise Salon" in result
    assert "Address: 12 Lake Road, Indiranagar, Bengaluru" in result
    assert "Timezone: Asia/Kolkata" in result
    assert "Appointment slot duration: 30 minutes" in result
    assert "Cancellation window: 120 minutes" in result
    assert "Women's Haircut" in result
    assert "Anita" in result


@pytest.mark.asyncio
async def test_check_availability_success(agent, mock_run_context):
    """Test 2a: check_availability on a valid future working day."""
    next_monday = get_next_weekday(0)  # Anita works Monday 10:00 - 14:00
    result = await agent.check_availability(
        mock_run_context,
        service="Women's Haircut",
        requested_date=next_monday.isoformat(),
        stylist="Anita",
    )
    assert "Women's Haircut" in result
    assert "Anita" in result
    assert "available slots" in result or "slots" in result


@pytest.mark.asyncio
async def test_check_availability_past_date(agent, mock_run_context):
    """Test 2b: check_availability on a past date returns past_date explanation."""
    result = await agent.check_availability(
        mock_run_context,
        service="Women's Haircut",
        requested_date="2020-01-01",
    )
    assert "in the past" in result


@pytest.mark.asyncio
async def test_check_availability_business_closed(agent, mock_run_context):
    """Test 2c: check_availability on Sunday (salon is closed)."""
    next_sunday = get_next_weekday(6)
    result = await agent.check_availability(
        mock_run_context,
        service="Women's Haircut",
        requested_date=next_sunday.isoformat(),
    )
    assert "closed" in result or "No slots are available" in result


@pytest.mark.asyncio
async def test_check_availability_ambiguous_service(agent, mock_run_context):
    """Test 2d: Ambiguous service ('Haircut') prompts caller to choose Women's vs Men's."""
    next_monday = get_next_weekday(0)
    result = await agent.check_availability(
        mock_run_context,
        service="Haircut",
        requested_date=next_monday.isoformat(),
    )
    assert "Women's Haircut" in result
    assert "Men's Haircut" in result
    assert "specify" in result.lower()


@pytest.mark.asyncio
async def test_check_availability_unknown_service(agent, mock_run_context):
    """Test 2e: Unknown service returns error with available options."""
    next_monday = get_next_weekday(0)
    result = await agent.check_availability(
        mock_run_context,
        service="Acrobatics",
        requested_date=next_monday.isoformat(),
    )
    assert "not found" in result
    assert "Women's Haircut" in result


@pytest.mark.asyncio
async def test_identify_caller_existing_customer(agent, mock_run_context):
    """Test 3a: identify_caller with an existing customer phone."""
    result = await agent.identify_caller(mock_run_context, phone_number="9876543210")
    assert agent.identified_phone == "9876543210"
    assert "Caller identified as" in result
    assert agent.customer_name is not None


@pytest.mark.asyncio
async def test_identify_caller_new_customer(agent, mock_run_context):
    """Test 3b: identify_caller with a new phone number."""
    result = await agent.identify_caller(mock_run_context, phone_number="9111222333")
    assert agent.identified_phone == "9111222333"
    assert "Caller phone number recorded as 9111222333" in result
    assert "backend has no dedicated customer lookup endpoint" in result


@pytest.mark.asyncio
async def test_identify_caller_invalid_phone(agent, mock_run_context):
    """Test 3c: identify_caller with an invalid phone number."""
    result = await agent.identify_caller(mock_run_context, phone_number="12345")
    assert "at least 10 digits" in result


@pytest.mark.asyncio
async def test_booking_full_flow_and_duplicate_protection(agent, mock_run_context):
    """Test 4: Full create_booking flow: unconfirmed check -> read-back -> confirmed booking -> duplicate prevention."""
    import time
    import re
    test_phone = f"98{int(time.time()) % 100000000:08d}"
    next_mon = get_next_weekday(0)

    # Dynamically find an available slot for Anita
    avail_res = await agent.check_availability(
        mock_run_context,
        service="Women's Haircut",
        requested_date=next_mon.isoformat(),
        stylist="Anita",
    )
    match = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))", avail_res)
    assert match is not None, f"No slots found in availability response: {avail_res}"
    target_time = match.group(1)

    # 1. Unconfirmed stage: Should verify availability, stage details, and ask for confirmation
    unconfirmed_res = await agent.create_booking(
        mock_run_context,
        service="Women's Haircut",
        date=next_mon.isoformat(),
        time=target_time,
        customer_name="Test Customer Flow",
        phone_number=test_phone,
        stylist="Anita",
        customer_confirmed=False,
    )
    assert "available!" in unconfirmed_res
    assert "Please read back these complete details" in unconfirmed_res
    assert "Would you like me to go ahead and book" in unconfirmed_res
    assert agent.pending_booking is not None

    # 2. Confirmed stage: Execute booking
    confirmed_res = await agent.create_booking(
        mock_run_context,
        service="Women's Haircut",
        date=next_mon.isoformat(),
        time=target_time,
        customer_name="Test Customer Flow",
        phone_number=test_phone,
        stylist="Anita",
        customer_confirmed=True,
    )
    assert "Booking confirmed successfully!" in confirmed_res or "Booking ID" in confirmed_res

    # 3. Duplicate check: Trying to confirm the exact same booking again in same session should be prevented
    dup_res = await agent.create_booking(
        mock_run_context,
        service="Women's Haircut",
        date=next_mon.isoformat(),
        time=target_time,
        customer_name="Test Customer Flow",
        phone_number=test_phone,
        stylist="Anita",
        customer_confirmed=True,
    )
    assert "already been confirmed" in dup_res or "No duplicate booking made" in dup_res


@pytest.mark.asyncio
async def test_list_my_bookings_and_isolation(agent, mock_run_context):
    """Test 5: list_my_bookings retrieves appointments and enforces customer isolation."""
    # Identify customer A
    await agent.identify_caller(mock_run_context, phone_number="9876543210")

    # List bookings for Customer A
    my_bookings = await agent.list_my_bookings(mock_run_context)
    assert "Booking #" in my_bookings or "appointment" in my_bookings

    # Customer isolation test: Attempting to list Customer B's bookings from Customer A's session
    spoofed = await agent.list_my_bookings(mock_run_context, phone_number="9123456780")
    assert "Access denied" in spoofed


@pytest.mark.asyncio
async def test_reschedule_and_cancellation_flow(agent, mock_run_context):
    """Test 6 & 7: Booking, rescheduling with confirmation, and cancelling with policy explanation."""
    import time
    test_phone = f"97{int(time.time()) % 100000000:08d}"
    next_tue = get_next_weekday(1)  # Rahul works Tue 16:00 - 20:00 (Hair Spa)

    # 1. Create a booking for Hair Spa with Rahul at 6:00 PM
    book_res = await agent.create_booking(
        mock_run_context,
        service="Hair Spa",
        date=next_tue.isoformat(),
        time="6:00 PM",
        customer_name="Reschedule Test",
        phone_number=test_phone,
        stylist="Rahul",
        customer_confirmed=True,
    )
    assert "Booking confirmed successfully!" in book_res

    # Extract booking ID from response
    import re
    match = re.search(r"Booking ID: #?(\d+)", book_res)
    assert match is not None
    booking_id = int(match.group(1))

    # 2. Reschedule - Stage 1 (customer_confirmed=False)
    resched_stage1 = await agent.reschedule_booking(
        mock_run_context,
        booking_id=booking_id,
        new_date=next_tue.isoformat(),
        new_time="6:30 PM",
        phone_number=test_phone,
        customer_confirmed=False,
    )
    assert "is requested for Booking" in resched_stage1
    assert "Would you like me to confirm this reschedule?" in resched_stage1

    # 3. Reschedule - Stage 2 (customer_confirmed=True)
    resched_stage2 = await agent.reschedule_booking(
        mock_run_context,
        booking_id=booking_id,
        new_date=next_tue.isoformat(),
        new_time="6:30 PM",
        phone_number=test_phone,
        customer_confirmed=True,
    )
    assert "successfully rescheduled" in resched_stage2

    # 4. Isolation test for reschedule: Customer B tries to reschedule Customer A's booking
    isolation_resched = await agent.reschedule_booking(
        mock_run_context,
        booking_id=booking_id,
        new_date=next_tue.isoformat(),
        new_time="6:00 PM",
        phone_number="9998887776",  # different phone
        customer_confirmed=True,
    )
    assert "Access denied" in isolation_resched or "not found" in isolation_resched

    # 5. Cancel - Stage 1 (customer_confirmed=False): Should explain cancellation policy
    cancel_stage1 = await agent.cancel_booking(
        mock_run_context,
        booking_id=booking_id,
        phone_number=test_phone,
        customer_confirmed=False,
    )
    assert "cancellation is completely free" in cancel_stage1 or "late cancellation" in cancel_stage1
    assert "Are you sure you want to cancel" in cancel_stage1

    # 6. Cancel - Stage 2 (customer_confirmed=True)
    cancel_stage2 = await agent.cancel_booking(
        mock_run_context,
        booking_id=booking_id,
        phone_number=test_phone,
        customer_confirmed=True,
    )
    assert "successfully cancelled" in cancel_stage2
    assert "Free cancellation" in cancel_stage2 or "Late cancellation" in cancel_stage2

    # 7. Isolation test for cancel: Another phone tries to cancel
    isolation_cancel = await agent.cancel_booking(
        mock_run_context,
        booking_id=booking_id,
        phone_number="9998887776",
        customer_confirmed=True,
    )
    assert "Access denied" in isolation_cancel or "not found" in isolation_cancel
