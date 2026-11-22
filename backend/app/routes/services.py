from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.service import Service
from app.schemas.service import ServiceResponse

router = APIRouter(prefix="/api/services", tags=["Services"])


@router.get("", response_model=list[ServiceResponse])
async def get_services(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Service).where(Service.business_id == 1)
    )

    services = result.scalars().all()

    return services