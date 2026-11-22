# Sunrise Salon — AI Voice Receptionist & Booking Platform

An autonomous, end-to-end voice receptionist and salon management system built with **LiveKit Agents**, **Groq (Whisper STT + LLM)**, **Kokoro / Groq Orpheus TTS**, **FastAPI**, **PostgreSQL**, and **React**.

---

## 🌟 Features

- **Autonomous Voice Receptionist:** Handles incoming voice calls, answers questions about salon services, stylists, business hours, and policies.
- **Availability & Booking Engine:** Real-time slot calculation, concurrency locking, and duplicate booking prevention.
- **Appointment Management:** Live caller identification via 10-digit phone number, appointment lookup, reschedule, and cancellation with policy enforcement.
- **Human-Like Speech Flow:** Conversational, spoken-style responses without awkward pauses or robotic bullet formatting.
- **Interactive Salon Web Portal:** High-end React dashboard to browse services, meet stylists, check real-time slots, book appointments, and place voice calls.

---

## 🏗️ Architecture

```
┌─────────────────┐       WebRTC Audio       ┌───────────────────────┐
│  Client Caller  │ ◄──────────────────────► │ LiveKit Cloud Server  │
└─────────────────┘                          └──────────┬────────────┘
                                                        │ Job Dispatch
                                                        ▼
                                             ┌───────────────────────┐
                                             │  Voice Agent Worker   │
                                             │  (LiveKit + Groq)     │
                                             └──────────┬────────────┘
                                                        │ REST API (httpx)
                                                        ▼
┌─────────────────┐       HTTP / JSON        ┌───────────────────────┐
│ React Frontend  │ ◄──────────────────────► │    FastAPI Backend    │
│ (Vite + Lucide) │                          └──────────┬────────────┘
└─────────────────┘                                     │ SQLAlchemy Async
                                                        ▼
                                             ┌───────────────────────┐
                                             │ PostgreSQL (Neon)     │
                                             └───────────────────────┘
```

---

## 📁 Repository Structure

```
├── backend/              # FastAPI application & PostgreSQL booking engine
│   ├── app/
│   │   ├── models/       # SQLAlchemy models (Business, Service, Stylist, Booking)
│   │   ├── routes/       # API endpoints (availability, bookings, services, etc.)
│   │   ├── services/     # Core booking engine with concurrency guards
│   │   └── main.py       # FastAPI application entrypoint
│   ├── Dockerfile        # Production container specification
│   └── requirements.txt  # Python dependencies
├── voice-agent/          # LiveKit voice assistant worker
│   ├── src/
│   │   └── agent.py      # LiveKit Agent with 7 backend function tools
│   ├── tests/            # Automated integration tests for all function tools
│   ├── Dockerfile        # Production container specification
│   └── pyproject.toml    # Python package & dependency manifest
└── frontend/             # React + Vite client dashboard
    ├── src/
    │   ├── components/   # CallButton, CallStatus visualizer
    │   ├── pages/        # CallPage with Web Speech API & transcript
    │   ├── services/     # Axios API client
    │   └── App.jsx       # Salon portal with 4 interactive tabs
    └── package.json      # Node dependencies
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL database (or [Neon](https://neon.tech))
- [LiveKit Cloud](https://cloud.livekit.io) account
- [Groq Cloud](https://console.groq.com) account

---

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

---

### 3. Voice Agent Setup
```bash
cd voice-agent
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

pip install -e .
cp .env.example .env.local
# Edit .env.local with LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and GROQ_API_KEY

# Run in development mode:
python src/agent.py dev
```

---

### 4. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🧪 Testing

Run the automated test suite against the FastAPI endpoints:
```bash
cd voice-agent
pytest tests/test_agent_tools.py -v
```

---

## 📄 License
MIT License.
