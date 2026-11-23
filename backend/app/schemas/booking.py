import re
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
)

from app.schemas.availability import AvailableSlot

BookingStatus = Literal["confirmed", "cancelled", "done"]

BookingFailureReason = Literal[
    "not_found",
    "slot_taken",
    "customer_overlap",
    "stylist_not_working",
    "outside_working_hours",
    "invalid_slot",
    "past_time",
    "service_not_offered_by_stylist",
]

CustomerName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class BookingCreateRequest(BaseModel):
    business_slug: str
    customer_name: CustomerName
    customer_phone: str
    service_id: int = Field(gt=0)
    stylist_id: int = Field(gt=0)
    start_time: AwareDatetime

    @field_validator("customer_phone")
    @classmethod
    def normalise_phone(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if len(digits) < 10:
            raise ValueError("Phone number must have at least 10 digits.")
        # MVP assumption: Indian numbers. Keep the last 10 digits so
        # "+91 98765 43210" and "98765 43210" match as the same customer.
        return digits[-10:]


class BookingResponse(BaseModel):
    success: Literal[True] = True
    booking_id: int
    customer_name: str
    service_name: str
    stylist_name: str
    start_time: AwareDatetime
    end_time: AwareDatetime
    status: BookingStatus


class BookingFailure(BaseModel):
    success: Literal[False] = False
    reason: BookingFailureReason
    message: str
    alternative_slots: list[AvailableSlot] = Field(default_factory=list)


class BookingListResponse(BaseModel):
    bookings: list[BookingResponse]
    total: int = Field(ge=0)


class RescheduleRequest(BaseModel):
    business_slug: str
    booking_id: int = Field(gt=0)
    customer_phone: str
    new_start_time: AwareDatetime


class CancelBookingRequest(BaseModel):
    business_slug: str
    booking_id: int = Field(gt=0)
    customer_phone: str


BookingResult = BookingResponse | BookingFailure
