import os
from app.routes import bookings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from sqlalchemy import text
from app.routes.business import router as business_router
from app.routes.services import router as services_router
from app.routes.stylists import router as stylists_router
from app.routes import availability

app = FastAPI(title='Sunrise Salon API', description='Sunrise Salon Voice Agent Backend API')

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*" if "*" in origins else None,
    allow_origins=origins if "*" not in origins else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(business_router)
app.include_router(services_router)
app.include_router(stylists_router)
app.include_router(availability.router)
app.include_router(bookings.router)

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
