
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.stylist import Stylist
from app.models.service import Service
from app.models.stylist_service import StylistService
from app.models.working_hours import WorkingHours
from app.models.booking import Booking

from app.schemas.availability import (
    AvailableSlot,
    AvailabilityResponse,
)

from app.models.customer import Customer
from app.schemas.booking import (
    BookingCreateRequest,
    BookingResponse,
    BookingFailure,
    BookingResult,
)

from sqlalchemy.exc import IntegrityError


async def _get_slots_for_date(
    db: AsyncSession,
    business_id: int,
    service_id: int,
    requested_date: date,
    timezone_info: ZoneInfo,
    slot_duration: int,
    service_duration: int,
    stylist_id: int | None = None,
    exclude_booking_id: int | None = None,
):
    weekday = requested_date.weekday()

    # Find active stylists assigned to the requested service.
    stylist_query = (
        select(Stylist)
        .join(
            StylistService,
            (Stylist.id == StylistService.stylist_id)
            & (Stylist.business_id == StylistService.business_id),
        )
        .where(
            Stylist.business_id == business_id,
            StylistService.business_id == business_id,
            StylistService.service_id == service_id,
            Stylist.is_active.is_(True),
        )
    )

    if stylist_id is not None:
        stylist_query = stylist_query.where(
            Stylist.id == stylist_id
        )

    result = await db.execute(stylist_query)
    stylists = result.scalars().unique().all()

    if not stylists:
        raise ValueError(
            "No active stylist is assigned to this service."
        )

    stylist_ids = [stylist.id for stylist in stylists]

    stylist_names = {
        stylist.id: stylist.name
        for stylist in stylists
    }

    # Get working hours for eligible stylists.
    hours_result = await db.execute(
        select(WorkingHours).where(
            WorkingHours.business_id == business_id,
            WorkingHours.stylist_id.in_(stylist_ids),
            WorkingHours.weekday == weekday,
        )
    )

    working_hours = hours_result.scalars().all()

    if not working_hours:

        # Check whether any stylist at the business works that day.
        business_hours_result = await db.execute(
            select(WorkingHours.id).where(
                WorkingHours.business_id == business_id,
                WorkingHours.weekday == weekday,
            ).limit(1)
        )

        business_is_closed = (
            business_hours_result.scalar_one_or_none() is None
        )

        if business_is_closed:
            return [], "business_closed"

        return [], "stylist_not_working"

    # Determine the overall working-time range.
    local_starts = [
        datetime.combine(
            requested_date,
            hours.start_time,
            tzinfo=timezone_info,
        )
        for hours in working_hours
    ]

    local_ends = [
        datetime.combine(
            requested_date,
            hours.end_time,
            tzinfo=timezone_info,
        )
        for hours in working_hours
    ]

    earliest_start = min(local_starts).astimezone(timezone.utc)
    latest_end = max(local_ends).astimezone(timezone.utc)

    # Fetch confirmed bookings that overlap the working-time range.
    bookings_query = select(Booking).where(
        Booking.business_id == business_id,
        Booking.stylist_id.in_(stylist_ids),
        Booking.status == "confirmed",
        Booking.start_time < latest_end,
        Booking.end_time > earliest_start,
    )

    if exclude_booking_id is not None:
        bookings_query = bookings_query.where(
            Booking.id != exclude_booking_id
        )

    bookings_result = await db.execute(bookings_query)

    bookings = bookings_result.scalars().all()

    booked_intervals = {}

    for booking in bookings:
        booked_intervals.setdefault(
            booking.stylist_id, []
        ).append((
            booking.start_time.astimezone(timezone.utc),
            booking.end_time.astimezone(timezone.utc),
        ))

    available_slots = []
    now_local = datetime.now(timezone_info)

    # Generate candidate slots for each eligible stylist.
    for hours in working_hours:

        work_start = datetime.combine(
            requested_date,
            hours.start_time,
            tzinfo=timezone_info,
        )

        work_end = datetime.combine(
            requested_date,
            hours.end_time,
            tzinfo=timezone_info,
        )

        stylist_bookings = booked_intervals.get(
            hours.stylist_id, []
        )

        slot_start = work_start

        while True:

            slot_end = slot_start + timedelta(
                minutes=service_duration
            )

            # The appointment must finish within working hours.
            if slot_end > work_end:
                break

            # Do not offer past or already-started slots.
            if (
                requested_date == now_local.date()
                and slot_start <= now_local
            ):
                slot_start += timedelta(minutes=slot_duration)
                continue

            start_utc = slot_start.astimezone(timezone.utc)
            end_utc = slot_end.astimezone(timezone.utc)

            # Check interval overlap with existing bookings.
            overlaps = any(
                start_utc < booked_end
                and end_utc > booked_start
                for booked_start, booked_end in stylist_bookings
            )

            if not overlaps:
                available_slots.append(
                    AvailableSlot(
                        stylist_id=hours.stylist_id,
                        stylist_name=stylist_names[hours.stylist_id],
                        start_time=slot_start,
                        end_time=slot_end,
                    )
                )

            slot_start += timedelta(minutes=slot_duration)

    available_slots.sort(key=lambda slot: slot.start_time)

    return (
        available_slots,
        None if available_slots else "fully_booked",
    )


async def check_availability(
    db: AsyncSession,
    business_slug: str,
    service_id: int,
    requested_date: date,
    stylist_id: int | None = None,
) -> AvailabilityResponse:

    # Find the business using its slug.
    business_result = await db.execute(
        select(Business).where(
            Business.slug == business_slug
        )
    )

    business = business_result.scalar_one_or_none()

    if business is None:
        raise ValueError("Business not found.")

    timezone_info = ZoneInfo(business.timezone)

    # Verify that the service belongs to this business.
    service_result = await db.execute(
        select(Service).where(
            Service.id == service_id,
            Service.business_id == business.id,
        )
    )

    service = service_result.scalar_one_or_none()

    if service is None:
        raise ValueError("Service not found for this business.")

    # Handle past dates as a structured response.
    if requested_date < datetime.now(timezone_info).date():
        return AvailabilityResponse(
            service_id=service.id,
            requested_date=requested_date,
            available_slots=[],
            reason="past_date",
        )

    # Check availability for the requested date.
    slots, reason = await _get_slots_for_date(
        db=db,
        business_id=business.id,
        service_id=service.id,
        requested_date=requested_date,
        timezone_info=timezone_info,
        slot_duration=business.slot_duration_minutes,
        service_duration=service.duration_minutes,
        stylist_id=stylist_id,
    )

    next_date = None
    next_slots = []

    # Search the next 30 days if no slots are available.
    if not slots:

        for days_ahead in range(1, 31):

            candidate_date = requested_date + timedelta(
                days=days_ahead
            )

            candidate_slots, _ = await _get_slots_for_date(
                db=db,
                business_id=business.id,
                service_id=service.id,
                requested_date=candidate_date,
                timezone_info=timezone_info,
                slot_duration=business.slot_duration_minutes,
                service_duration=service.duration_minutes,
                stylist_id=stylist_id,
            )

            if candidate_slots:
                next_date = candidate_date
                next_slots = candidate_slots
                break

    return AvailabilityResponse(
        service_id=service.id,
        requested_date=requested_date,
        available_slots=slots,
        reason=reason,
        next_available_date=next_date,
        next_available_slots=next_slots,
    )

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession




from app.models.booking import Booking
from app.models.business import Business
from app.models.customer import Customer
from app.models.service import Service
from app.models.stylist import Stylist
from app.models.stylist_service import StylistService
from app.models.working_hours import WorkingHours
from app.schemas.availability import AvailableSlot
from app.schemas.booking import (
    BookingCreateRequest,
    BookingFailure,
    BookingResponse,
    BookingResult,
)

STATUS_CONFIRMED = "confirmed"  # better: define once next to the Booking model

# Must match the constraint names used in the Alembic migration.
CUSTOMER_OVERLAP_CONSTRAINT = "no_customer_overlap"


async def _drop_customer_conflicts(
    db: AsyncSession,
    business_id: int,
    customer_id: int,
    slots: list[AvailableSlot],
) -> list[AvailableSlot]:
    """Remove slots that overlap the customer's own confirmed bookings."""
    if not slots:
        return []

    window_start = min(s.start_time for s in slots).astimezone(timezone.utc)
    window_end = max(s.end_time for s in slots).astimezone(timezone.utc)

    result = await db.execute(
        select(Booking.start_time, Booking.end_time).where(
            Booking.business_id == business_id,
            Booking.customer_id == customer_id,
            Booking.status == STATUS_CONFIRMED,
            Booking.start_time < window_end,
            Booking.end_time > window_start,
        )
    )
    intervals = [
        (start.astimezone(timezone.utc), end.astimezone(timezone.utc))
        for start, end in result.all()
    ]

    return [
        slot
        for slot in slots
        if not any(
            slot.start_time.astimezone(timezone.utc) < booked_end
            and slot.end_time.astimezone(timezone.utc) > booked_start
            for booked_start, booked_end in intervals
        )
    ]


async def create_booking(
    db: AsyncSession,
    request: BookingCreateRequest,
) -> BookingResult:

    # 1. Business and timezone.
    business = (
        await db.execute(
            select(Business).where(Business.slug == request.business_slug)
        )
    ).scalar_one_or_none()

    if business is None:
        return BookingFailure(
            reason="not_found", message="Business not found."
        )

    # Copy plain values now. ORM objects expire after commit or rollback
    # and cannot be read safely in async code afterwards.
    business_id = business.id
    slot_minutes = business.slot_duration_minutes
    timezone_info = ZoneInfo(business.timezone)

    local_start = request.start_time.astimezone(timezone_info)

    if local_start <= datetime.now(timezone_info):
        return BookingFailure(
            reason="past_time",
            message="This appointment time has already passed.",
        )

    # 2. Service.
    service = (
        await db.execute(
            select(Service).where(
                Service.id == request.service_id,
                Service.business_id == business_id,
            )
        )
    ).scalar_one_or_none()

    if service is None:
        return BookingFailure(
            reason="not_found", message="Service not found."
        )

    service_id = service.id
    service_name = service.name
    service_minutes = service.duration_minutes

    # 3. Stylist.
    stylist = (
        await db.execute(
            select(Stylist).where(
                Stylist.id == request.stylist_id,
                Stylist.business_id == business_id,
                Stylist.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()

    if stylist is None:
        return BookingFailure(
            reason="not_found", message="Stylist not found or inactive."
        )

    stylist_id = stylist.id
    stylist_name = stylist.name

    # 4. Does this stylist offer this service?
    assignment = (
        await db.execute(
            select(StylistService).where(
                StylistService.business_id == business_id,
                StylistService.stylist_id == stylist_id,
                StylistService.service_id == service_id,
            )
        )
    ).scalar_one_or_none()

    if assignment is None:
        return BookingFailure(
            reason="service_not_offered_by_stylist",
            message=f"{stylist_name} does not offer {service_name}.",
        )

    # 5. Working hours for that weekday.
    working_hours = (
        await db.execute(
            select(WorkingHours).where(
                WorkingHours.business_id == business_id,
                WorkingHours.stylist_id == stylist_id,
                WorkingHours.weekday == local_start.weekday(),
            )
        )
    ).scalars().all()

    if not working_hours:
        return BookingFailure(
            reason="stylist_not_working",
            message=f"{stylist_name} does not work on this day.",
        )

    # 6. Must fit inside one working window and sit on the slot grid.
    local_end = local_start + timedelta(minutes=service_minutes)
    local_date = local_start.date()

    window_start = None
    for hours in working_hours:
        start_of_window = datetime.combine(
            local_date, hours.start_time, tzinfo=timezone_info
        )
        end_of_window = datetime.combine(
            local_date, hours.end_time, tzinfo=timezone_info
        )
        if local_start >= start_of_window and local_end <= end_of_window:
            window_start = start_of_window
            break

    if window_start is None:
        return BookingFailure(
            reason="outside_working_hours",
            message="The appointment is outside the stylist's working hours.",
        )

    minutes_from_open = (local_start - window_start).total_seconds() / 60
    if minutes_from_open % slot_minutes != 0:
        return BookingFailure(
            reason="invalid_slot",
            message="This is not a valid appointment start time.",
        )

    # 7. Recheck real availability right before booking.
    slots, _ = await _get_slots_for_date(
        db=db,
        business_id=business_id,
        service_id=service_id,
        requested_date=local_date,
        timezone_info=timezone_info,
        slot_duration=slot_minutes,
        service_duration=service_minutes,
        stylist_id=stylist_id,
    )

    requested_utc = local_start.astimezone(timezone.utc)
    end_utc = local_end.astimezone(timezone.utc)

    if not any(
        slot.start_time.astimezone(timezone.utc) == requested_utc
        for slot in slots
    ):
        # On the grid and inside working hours, so someone else has it.
        return BookingFailure(
            reason="slot_taken",
            message="This time slot is already booked.",
            alternative_slots=slots,
        )

    # 8. Find or create the customer, safe against two simultaneous callers.
    await db.execute(
        pg_insert(Customer)
        .values(
            business_id=business_id,
            name=request.customer_name,
            phone=request.customer_phone,
        )
        .on_conflict_do_nothing(index_elements=["business_id", "phone"])
    )
    customer = (
        await db.execute(
            select(Customer).where(
                Customer.business_id == business_id,
                Customer.phone == request.customer_phone,
            )
        )
    ).scalar_one()

    customer_id = customer.id
    customer_name = customer.name  # stored name wins for an existing phone

    # 9. Reject if the customer already has an overlapping appointment.
    overlap = (
        await db.execute(
            select(Booking.id).where(
                Booking.business_id == business_id,
                Booking.customer_id == customer_id,
                Booking.status == STATUS_CONFIRMED,
                Booking.start_time < end_utc,
                Booking.end_time > requested_utc,
            ).limit(1)
        )
    ).scalar_one_or_none()

    if overlap is not None:
        alternatives = await _drop_customer_conflicts(
            db, business_id, customer_id, slots
        )
        await db.rollback()
        return BookingFailure(
            reason="customer_overlap",
            message="You already have another appointment during this time.",
            alternative_slots=alternatives,
        )

    # 10. Create the booking. The database constraints are the final guard.
    booking = Booking(
        business_id=business_id,
        customer_id=customer_id,
        stylist_id=stylist_id,
        service_id=service_id,
        start_time=requested_utc,
        end_time=end_utc,
        status=STATUS_CONFIRMED,
    )

    try:
        db.add(booking)
        await db.flush()
        booking_id = booking.id  # read before commit expires the object
        await db.commit()

    except IntegrityError as exc:
        await db.rollback()

        cause = getattr(exc.orig, "__cause__", None)
        constraint = getattr(cause, "constraint_name", None) or str(exc.orig)

        refreshed_slots, _ = await _get_slots_for_date(
            db=db,
            business_id=business_id,
            service_id=service_id,
            requested_date=local_date,
            timezone_info=timezone_info,
            slot_duration=slot_minutes,
            service_duration=service_minutes,
            stylist_id=stylist_id,
        )
        remaining = [
            slot
            for slot in refreshed_slots
            if slot.start_time.astimezone(timezone.utc) != requested_utc
        ]

        if CUSTOMER_OVERLAP_CONSTRAINT in constraint:
            return BookingFailure(
                reason="customer_overlap",
                message="You already have another appointment during this time.",
                alternative_slots=await _drop_customer_conflicts(
                    db, business_id, customer_id, remaining
                ),
            )

        return BookingFailure(
            reason="slot_taken",
            message="This slot was just booked. Please choose another time.",
            alternative_slots=remaining,
        )

    # 11. Build the response from local values only.
    return BookingResponse(
        booking_id=booking_id,
        customer_name=customer_name,
        service_name=service_name,
        stylist_name=stylist_name,
        start_time=local_start,
        end_time=local_end,
        status=STATUS_CONFIRMED,
    )



def _clean_phone(phone_str: str | None) -> str:
    if not phone_str:
        return ""
    digits = re.sub(r"\D", "", phone_str)
    return digits[-10:] if len(digits) >= 10 else digits


async def get_customer_bookings(
    db: AsyncSession,
    business_slug: str,
    customer_phone: str,
) -> list[BookingResponse]:

    business_result = await db.execute(
        select(Business).where(Business.slug == business_slug)
    )
    business = business_result.scalar_one_or_none()

    if business is None:
        raise ValueError("Business not found.")

    clean = _clean_phone(customer_phone)
    phone_filter = (
        or_(
            Customer.phone == customer_phone,
            Customer.phone == clean,
            Customer.phone.endswith(clean),
        )
        if clean
        else (Customer.phone == customer_phone)
    )

    customer_result = await db.execute(
        select(Customer).where(
            Customer.business_id == business.id,
            phone_filter,
        )
    )
    customers = customer_result.scalars().all()

    if not customers:
        return []

    customer_ids = [c.id for c in customers]
    customer_name_map = {c.id: c.name for c in customers}

    result = await db.execute(
        select(Booking, Service, Stylist)
        .join(Service, Booking.service_id == Service.id)
        .join(Stylist, Booking.stylist_id == Stylist.id)
        .where(
            Booking.business_id == business.id,
            Booking.customer_id.in_(customer_ids),
            Booking.status.in_(["confirmed", "cancelled"]),
        )
        .order_by(Booking.start_time.desc())
    )

    timezone_info = ZoneInfo(business.timezone)

    return [
        BookingResponse(
            booking_id=booking.id,
            customer_name=customer_name_map.get(booking.customer_id, "Customer"),
            service_name=service.name,
            stylist_name=stylist.name,
            start_time=booking.start_time.astimezone(timezone_info),
            end_time=booking.end_time.astimezone(timezone_info),
            status=booking.status,
        )
        for booking, service, stylist in result.all()
    ]



async def reschedule_booking(
    db: AsyncSession,
    business_slug: str,
    booking_id: int,
    customer_phone: str,
    new_start_time: datetime,
) -> BookingResult:

    business_result = await db.execute(
        select(Business).where(Business.slug == business_slug)
    )
    business = business_result.scalar_one_or_none()

    if business is None:
        raise ValueError("Business not found.")

    timezone_info = ZoneInfo(business.timezone)

    clean = _clean_phone(customer_phone)
    query = (
        select(Booking)
        .join(Customer, Booking.customer_id == Customer.id)
        .where(
            Booking.id == booking_id,
            Booking.business_id == business.id,
            Booking.status == "confirmed",
        )
    )
    if clean:
        query = query.where(
            or_(
                Customer.phone == customer_phone,
                Customer.phone == clean,
                Customer.phone.endswith(clean),
            )
        )

    booking_result = await db.execute(query)
    booking = booking_result.scalar_one_or_none()

    if booking is None:
        raise ValueError(
            "Confirmed booking not found for this customer."
        )

    local_start = new_start_time.astimezone(timezone_info)

    if local_start <= datetime.now(timezone_info):
        return BookingFailure(
            reason="past_time",
            message="The new appointment time must be in the future.",
        )

    service_result = await db.execute(
        select(Service).where(
            Service.id == booking.service_id,
            Service.business_id == business.id,
        )
    )
    service = service_result.scalar_one()

    stylist_result = await db.execute(
        select(Stylist).where(
            Stylist.id == booking.stylist_id,
            Stylist.business_id == business.id,
            Stylist.is_active.is_(True),
        )
    )
    stylist = stylist_result.scalar_one_or_none()

    if stylist is None:
        raise ValueError("The assigned stylist is inactive.")

    local_end = local_start + timedelta(
        minutes=service.duration_minutes
    )

    hours_result = await db.execute(
        select(WorkingHours).where(
            WorkingHours.business_id == business.id,
            WorkingHours.stylist_id == stylist.id,
            WorkingHours.weekday == local_start.weekday(),
        )
    )
    working_hours = hours_result.scalars().all()

    if not working_hours:
        return BookingFailure(
            reason="stylist_not_working",
            message=f"{stylist.name} does not work on this day.",
        )

    inside_hours = any(
        local_start >= datetime.combine(
            local_start.date(), hours.start_time,
            tzinfo=timezone_info,
        )
        and local_end <= datetime.combine(
            local_start.date(), hours.end_time,
            tzinfo=timezone_info,
        )
        for hours in working_hours
    )

    if not inside_hours:
        return BookingFailure(
            reason="outside_working_hours",
            message="The new time is outside working hours.",
        )

    slots, availability_reason = await _get_slots_for_date(
        db=db,
        business_id=business.id,
        service_id=service.id,
        requested_date=local_start.date(),
        timezone_info=timezone_info,
        slot_duration=business.slot_duration_minutes,
        service_duration=service.duration_minutes,
        stylist_id=stylist.id,
        exclude_booking_id=booking.id,
    )


    # Fetch the customer's other confirmed bookings.
    customer_bookings_result = await db.execute(
        select(Booking).where(
            Booking.business_id == business.id,
            Booking.customer_id == booking.customer_id,
            Booking.id != booking.id,
            Booking.status == "confirmed",
        )
    )

    customer_bookings = customer_bookings_result.scalars().all()

    # Remove alternative slots that overlap another customer booking.
    slots = [
        slot for slot in slots
        if not any(
            slot.start_time.astimezone(timezone.utc)
            < other_booking.end_time.astimezone(timezone.utc)
            and
            slot.end_time.astimezone(timezone.utc)
            > other_booking.start_time.astimezone(timezone.utc)
            for other_booking in customer_bookings
        )
    ]


    new_start_utc = local_start.astimezone(timezone.utc)
    new_end_utc = local_end.astimezone(timezone.utc)

    # Check for a customer conflict before validating the requested slot.
    overlap_result = await db.execute(
        select(Booking.id).where(
            Booking.business_id == business.id,
            Booking.customer_id == booking.customer_id,
            Booking.id != booking.id,
            Booking.status == "confirmed",
            Booking.start_time < new_end_utc,
            Booking.end_time > new_start_utc,
        ).limit(1)
    )

    if overlap_result.scalar_one_or_none() is not None:
        return BookingFailure(
            reason="customer_overlap",
            message="You already have an appointment during this time.",
            alternative_slots=slots,
        )

    matching_slot = any(
        slot.start_time.astimezone(timezone.utc) == new_start_utc
        for slot in slots
    )

    if not matching_slot:
        return BookingFailure(
            reason=(
                "slot_taken"
                if availability_reason == "fully_booked"
                else "invalid_slot"
            ),
            message="The requested new slot is unavailable.",
            alternative_slots=slots,
        )

    # Update the existing booking, not create a new one.
    booking.start_time = new_start_utc
    booking.end_time = new_end_utc

    try:
        await db.commit()
        await db.refresh(booking)
    except IntegrityError:
        await db.rollback()
        return BookingFailure(
            reason="slot_taken",
            message="This slot was booked by another request. Please choose another time.",
        )

    customer_result = await db.execute(
        select(Customer).where(Customer.id == booking.customer_id)
    )
    customer = customer_result.scalar_one()

    return BookingResponse(
        booking_id=booking.id,
        customer_name=customer.name,
        service_name=service.name,
        stylist_name=stylist.name,
        start_time=booking.start_time.astimezone(timezone_info),
        end_time=booking.end_time.astimezone(timezone_info),
        status=booking.status,
    )


async def cancel_booking(
    db: AsyncSession,
    business_slug: str,
    booking_id: int,
    customer_phone: str,
) -> BookingResponse:

    business_result = await db.execute(
        select(Business).where(Business.slug == business_slug)
    )
    business = business_result.scalar_one_or_none()

    if business is None:
        raise ValueError("Business not found.")

    timezone_info = ZoneInfo(business.timezone)

    clean = _clean_phone(customer_phone)
    query = (
        select(Booking)
        .join(Customer, Booking.customer_id == Customer.id)
        .where(
            Booking.id == booking_id,
            Booking.business_id == business.id,
            Booking.status == "confirmed",
        )
    )
    if clean:
        query = query.where(
            or_(
                Customer.phone == customer_phone,
                Customer.phone == clean,
                Customer.phone.endswith(clean),
            )
        )

    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if booking is None:
        raise ValueError(
            "Confirmed booking not found for this customer."
        )

    now_utc = datetime.now(timezone.utc)
    cancellation_deadline = (
        booking.start_time
        - timedelta(minutes=business.cancellation_window_minutes)
    )

    # Mark cancellations within the 2-hour window as late.
    booking.late_cancel = now_utc > cancellation_deadline
    booking.status = "cancelled"
    booking.cancelled_at = now_utc

    await db.commit()
    await db.refresh(booking)

    customer_result = await db.execute(
        select(Customer).where(Customer.id == booking.customer_id)
    )
    customer = customer_result.scalar_one()

    service_result = await db.execute(
        select(Service).where(Service.id == booking.service_id)
    )
    service = service_result.scalar_one()

    stylist_result = await db.execute(
        select(Stylist).where(Stylist.id == booking.stylist_id)
    )
    stylist = stylist_result.scalar_one()

    return BookingResponse(
        booking_id=booking.id,
        customer_name=customer.name,
        service_name=service.name,
        stylist_name=stylist.name,
        start_time=booking.start_time.astimezone(timezone_info),
        end_time=booking.end_time.astimezone(timezone_info),
        status=booking.status,
    )
