from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.stylist import Stylist
from app.schemas.stylist import StylistResponse

router = APIRouter(prefix="/api/stylists", tags=["Stylists"])


@router.get("", response_model=list[StylistResponse])
async def get_stylists(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Stylist).where(Stylist.business_id == 1)
    )

    return result.scalars().all()

from app.models.business import Business
from app.models.service import Service
from app.models.stylist_service import StylistService
from fastapi import HTTPException
from app.schemas.service import ServiceResponse


@router.get("/{stylist_id}/services", response_model=list[ServiceResponse])
async def get_stylist_services(
    stylist_id: int,
    db: AsyncSession = Depends(get_db)
):
    # Verify that the stylist exists and is active
    stylist_result = await db.execute(
        select(Stylist).where(
            Stylist.id == stylist_id,
            Stylist.business_id == 1,
            Stylist.is_active == True
        )
    )

    stylist = stylist_result.scalar_one_or_none()

    if not stylist:
        raise HTTPException(status_code=404, detail="Active stylist not found")

    # Retrieve services assigned to this stylist
    result = await db.execute(
        select(Service)
        .join(
            StylistService,
            Service.id == StylistService.service_id
        )
        .where(
            StylistService.stylist_id == stylist_id,
            StylistService.business_id == stylist.business_id
        )
    )

    return result.scalars().all()