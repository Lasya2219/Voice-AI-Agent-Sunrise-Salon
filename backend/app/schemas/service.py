from pydantic import BaseModel, ConfigDict


class ServiceResponse(BaseModel):
    id: int
    name: str
    price: float
    is_price_from: bool
    duration_minutes: int
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)