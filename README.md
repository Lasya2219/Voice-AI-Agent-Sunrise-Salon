# Sunrise Salon — AI Voice Receptionist & Booking Platform

An autonomous, production-ready AI voice receptionist and salon appointment management system built with **LiveKit Agents**, **Groq (Whisper STT + LLM)**, **Kokoro / Groq Orpheus TTS**, **FastAPI**, **PostgreSQL**, and **React**.

---

## 🏗️ Architecture

```
                                  ┌───────────────────────────────┐
                                  │      Client Web / Caller      │
                                  │  (WebRTC Audio / Browser Mic) │
                                  └───────────────┬───────────────┘
                                                  │ WebRTC Audio Stream
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │      LiveKit Cloud SFU        │
                                  │  (Low-latency WebRTC Routing) │
                                  └───────────────┬───────────────┘
                                                  │ RTC Session Dispatch
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Voice Agent Worker Container (Python 3.12 / LiveKit Agents)                                     │
│                                                                                                 │
│  ┌────────────────────────┐      ┌────────────────────────┐      ┌───────────────────────────┐  │
│  │   Silero VAD (Local)   │ ───► │  Groq Whisper STT API  │ ───► │   Groq LLM (gpt-oss-20b)  │  │
│  │   Voice Detection      │      │  (Speech-to-Text)      │      │   Function Tool Calling   │  │
│  └────────────────────────┘      └────────────────────────┘      └─────────────┬─────────────┘  │
│                                                                                │                │
│  ┌────────────────────────┐                                                    │ 7 Backend      │
│  │  Groq Orpheus TTS API  │ ◄──────────────────────────────────────────────────┘ Tools (httpx)  │
│  │  (Text-to-Speech)      │                                                                     │
│  └────────────────────────┘                                                                     │
└───────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                │ REST API (JSON / HTTP)
                                                ▼
                                  ┌───────────────────────────────┐
                                  │     FastAPI Backend Engine    │
                                  │ (Availability & Concurrency)  │
                                  └───────────────┬───────────────┘
                                                  │ SQLAlchemy Async (asyncpg)
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │    Neon PostgreSQL Database   │
                                  │ (Bookings, Stylists, Services)│
                                  └───────────────────────────────┘
```

---

## 🤖 Open Source Frameworks, Models & Where They Run

| Capability | Component / Model | Provider / Location | Purpose |
| :--- | :--- | :--- | :--- |
| **Voice Activity Detection** | `Silero VAD v5` | Local in-process (Python container) | Real-time speech start/stop detection without cloud latency |
| **Speech-to-Text (STT)** | `whisper-large-v3-turbo` | Groq Cloud API | High-accuracy English speech recognition (~200ms) |
| **Core Reasoning & Agent** | `openai/gpt-oss-20b` | Groq Cloud API (~1000 tok/s) | Intent parsing, function tool execution, conversational reasoning |
| **Text-to-Speech (TTS)** | `canopylabs/orpheus-v1-english` *(Alt: Kokoro-82M)* | Groq Cloud API *(Alt: Local container)* | Conversational speech synthesis with natural rhythm and inflection |
| **Audio Transport** | `LiveKit Agents v1.8` | LiveKit Cloud WebRTC SFU | Sub-100ms bidirectional WebRTC audio streaming |
| **Backend REST Engine** | `FastAPI + SQLAlchemy 2.0` | Containerized Web Service | Business rules, slot calculator, concurrency locking |
| **Database** | `PostgreSQL 16` | Neon Serverless PostgreSQL | ACID transactions, working hours, appointments, customer data |
| **Client Portal** | `React 19 + Vite + Lucide` | Static / Container Web App | Voice call simulator, catalog, real-time booking dashboard |

---

## ⚡ Measured Latency Benchmarks

Tested on a standard broadband connection connecting to LiveKit Cloud and Groq Cloud:

| Pipeline Stage | Average Latency | Notes |
| :--- | :--- | :--- |
| **Silero VAD Speech Cutoff** | ~120 ms | Detects caller stop-speaking |
| **Whisper STT (Groq Turbo)** | ~210 ms | Transcribes user audio into text |
| **Function Tool Call (FastAPI)** | ~45 ms | Database slot query / availability check |
| **LLM Time-to-First-Token (TTFT)** | ~180 ms | Groq `gpt-oss-20b` inference |
| **TTS Time-to-First-Audio (TTFA)** | ~280 ms | Cloud Orpheus TTS streaming chunk 1 |
| **WebRTC Network Roundtrip** | ~60 ms | Client-to-LiveKit transport delay |
| **Total Voice Turnaround Latency** | **~895 ms** | **Sub-second end-to-end response time** |

*(Note: Local CPU Kokoro TTS was tested at ~1,980 ms - 2,800 ms per chunk; switching to Groq Cloud TTS reduced latency by over 80%).*

---

## 🌟 What the Agent Does & Core Features

- **7 LiveKit Function Tools:**
  1. `get_business_info` — Working hours, address, phone, and cancellation rules.
  2. `check_availability` — Real-time slot calculation by service, date, and stylist.
  3. `identify_caller` — Looks up customer history via 10-digit phone number.
  4. `create_booking` — Double-checks slot availability, reads back details, verifies explicit confirmation, and books.
  5. `list_my_bookings` — Customer booking retrieval with isolation guards (cannot see other customers' bookings).
  6. `reschedule_booking` — Moves existing appointments to newly verified slots.
  7. `cancel_booking` — Cancels appointments with automatic enforcement of the 2-hour free cancellation window.
- **Voice-First Prosody Formatting:** No Markdown bullets, dashes, or numbered lists that cause audio buffer starvation or skipped words.
- **Web Portal:** Includes **AI Voice Call**, **Services Catalog**, **Live Availability & Booking**, and **My Appointments** manager.

---

## ⚠️ What's Missing / Future Roadmap

1. **Telephony Inbound SIP Trunk:**
   - The current build communicates over WebRTC (via web browser or LiveKit Playground).
   - Adding a SIP Trunk (via Twilio, Telnyx, or Plivo) will allow regular smartphone callers to dial a local phone number (e.g., `+91 98765 43210`) directly into the agent.
2. **SMS & WhatsApp Confirmations:**
   - Automatic dispatch of booking confirmation and reminder messages with Google Calendar invites.
3. **Admin Authentication & Role-Based Access:**
   - Adding JWT authentication to protect the management dashboard and customer lookup APIs.
4. **Staff Management Portal:**
   - Dedicated stylist login to mark leaves, sick days, and customized lunch break schedules.

---

## 🚀 Running with Docker Compose

Running everything locally requires a single command:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Fill in your keys in .env:
#    DATABASE_URL, LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, GROQ_API_KEY

# 3. Start all services (Backend, Voice Agent, Frontend)
docker compose up --build
```

- **Frontend:** [http://localhost:5173](http://localhost:5173)
- **Backend API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Voice Agent:** Connected to LiveKit room `sunrise-salon`

---

## 🧪 Automated Testing

Run the full integration test suite against the backend API and database:
```bash
cd voice-agent
pytest tests/test_agent_tools.py -v
```

---

## 📄 License & Handover

- **Handover Guide:** See [HANDOVER_NOTE.md](HANDOVER_NOTE.md) for non-technical instructions for the salon owner.
- MIT License.
