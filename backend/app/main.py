from app.routes import bookings
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from sqlalchemy import text
from pydantic import BaseModel, Field
from livekit.api import AccessToken, VideoGrants
from livekit.protocol.agent_dispatch import RoomAgentDispatch
from livekit.protocol.room import RoomConfiguration
from app.config import settings
from app.routes.business import router as business_router
from app.routes.services import router as services_router
from app.routes.stylists import router as stylists_router
from app.routes import availability

app = FastAPI(title='PorsAI Voice Agent', description='PorsAI Voice Agent API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(business_router)
app.include_router(services_router)
app.include_router(stylists_router)
app.include_router(availability.router)
app.include_router(bookings.router)


class LiveKitTokenRequest(BaseModel):
    room_name: str = Field(min_length=1, max_length=128)
    identity: str = Field(min_length=1, max_length=128)
    name: str = Field(default='Salon Guest', max_length=128)


@app.post("/api/livekit/token")
async def create_livekit_token(request: LiveKitTokenRequest):
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=503,
            detail="LiveKit is not configured on the server",
        )

    token = (
        AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(request.identity)
        .with_name(request.name)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=request.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
        .with_room_config(
            RoomConfiguration(
                name=request.room_name,
                agents=[RoomAgentDispatch(agent_name="sunrise-salon")],
            )
        )
    )
    return {
        "token": token.to_jwt(),
        "url": settings.LIVEKIT_URL,
    }

@app.get("/")
def home():
    return {"message": "Backend Running"}

@app.get("/health")
async def health():
    try:
        async with engine.connect() as connection:
            await connection.execute(text('SELECT 1'))
            return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
