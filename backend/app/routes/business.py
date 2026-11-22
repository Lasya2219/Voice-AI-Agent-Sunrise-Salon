from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.business import Business
from app.schemas.business import BusinessResponse

router = APIRouter(prefix="/api/business", tags=["Business"])


@router.get("", response_model=BusinessResponse)
async def get_business(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Business).where(Business.slug == "sunrise-salon")
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    return business