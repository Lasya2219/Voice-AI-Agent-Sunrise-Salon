
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.booking import (
    BookingCreateRequest,
    BookingResponse,
    BookingFailure,
)
from app.services.booking_engine import create_booking


router = APIRouter(
    prefix="/api/bookings",
    tags=["Bookings"],
)


@router.post(
    "",
    response_model=BookingResponse | BookingFailure,
)
async def book_appointment(
    request: BookingCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await create_booking(
            db=db,
            request=request,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )


from fastapi import Query

from app.schemas.booking import (
    BookingListResponse,
    RescheduleRequest,
    CancelBookingRequest,
)

from app.services.booking_engine import (
    get_customer_bookings,
    reschedule_booking,
    cancel_booking,
)


@router.get("/customer", response_model=BookingListResponse)
async def get_bookings(
    business_slug: str,
    customer_phone: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        bookings = await get_customer_bookings(
            db, business_slug, customer_phone
        )
        return BookingListResponse(
            bookings=bookings,
            total=len(bookings),
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.put("/reschedule", response_model=BookingResponse | BookingFailure)
async def reschedule(
    request: RescheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await reschedule_booking(
            db=db,
            business_slug=request.business_slug,
            booking_id=request.booking_id,
            customer_phone=request.customer_phone,
            new_start_time=request.new_start_time,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.put("/cancel", response_model=BookingResponse)
async def cancel(
    request: CancelBookingRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await cancel_booking(
            db=db,
            business_slug=request.business_slug,
            booking_id=request.booking_id,
            customer_phone=request.customer_phone,
        )
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error))
