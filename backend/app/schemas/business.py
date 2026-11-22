from pydantic import BaseModel, ConfigDict


class BusinessResponse(BaseModel):
    id: int
    name: str
    slug: str
    address: str
    timezone: str
    slot_duration_minutes: int
    cancellation_window_minutes: int

    model_config = ConfigDict(from_attributes=True)