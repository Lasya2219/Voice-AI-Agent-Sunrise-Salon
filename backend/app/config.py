
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
project_root = Path(__file__).resolve().parents[2]
load_dotenv(project_root / "voice-agent" / ".env.local", override=True)

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET")

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL is missing in .env")

settings = Settings()
