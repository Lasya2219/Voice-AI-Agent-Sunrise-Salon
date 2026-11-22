from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.availability import AvailabilityResponse
from app.services.booking_engine import check_availability


router = APIRouter(
    prefix="/api/availability",
    tags=["Availability"],
)


@router.get("", response_model=AvailabilityResponse)
async def get_availability(
    service_id: int = Query(..., gt=0),
    requested_date: date = Query(...),
    business_slug: str = Query(...),
    stylist_id: int | None = Query(default=None, gt=0),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await check_availability(
            db=db,
            business_slug=business_slug,
            service_id=service_id,
            requested_date=requested_date,
            stylist_id=stylist_id,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )
