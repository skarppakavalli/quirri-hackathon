# KIT AI Campus Assistant

An AI-powered campus assistant for **Knotopian Institute of Technology (KIT)** that helps students interact with college services through natural language and voice.

The assistant is designed to support students with everyday campus queries and administrative requests, reducing the effort required to navigate multiple college services.

## Features

### Implemented

- **AI-powered conversations:** Students can ask questions in natural language.
- **Voice interaction:** Students can speak to the assistant instead of typing.
- **Speech-to-text:** Converts voice input into text using Deepgram.
- **Text-to-speech:** Reads assistant responses aloud using ElevenLabs.
- **Attendance lookup:** Retrieves the student's attendance information.
- **Timetable lookup:** Retrieves the student's timetable.
- **Leave and On-Duty (OD) requests:** Students can describe their requirements conversationally.
- **Request preparation:** The assistant collects missing details such as dates, reason, and event name.
- **Explicit confirmation:** A request is submitted only after the student confirms it.
- **Chat history:** Conversation history is maintained during the active application session.
- **Text fallback:** Students can continue using text if voice interaction is unavailable.

## Technology Stack

| Component | Technology |
|---|---|
| Backend API | FastAPI |
| Frontend | Streamlit |
| Agent orchestration | LangGraph |
| LLM integration | LangChain |
| Language model | Groq-hosted LLM |
| Speech-to-text | Deepgram |
| Text-to-speech | ElevenLabs |
| HTTP communication | HTTPX / Requests |
| College data | KIT-provided APIs |
| Configuration | Environment variables |

## Architecture

```text
                  Student
                     |
             Streamlit Frontend
                     |
          Text Input / Voice Input
                     |
             FastAPI Backend
                     |
          +----------+----------+
          |                     |
     Voice Services         AI Agent
          |                     |
       Deepgram             LangGraph
       (STT)                    |
          |                  Groq LLM
          |                     |
          |              Student Tools
          |                     |
          |              College API Client
          |                     |
          |              KIT REST APIs
          |                     |
          +---------------------+
                     |
              Assistant Response
                     |
                ElevenLabs
                   (TTS)
                     |
                Student
```

### Request flow

1. The student logs in through the Streamlit interface.
2. The frontend sends credentials to the FastAPI backend.
3. The backend authenticates the student using the KIT authentication API.
4. The backend stores the returned access token server-side and gives the frontend an opaque session ID.
5. The student asks a question using text or voice.
6. For voice input, Deepgram converts the audio into text.
7. The LangGraph agent processes the request using the Groq LLM.
8. When college information is required, the agent invokes the appropriate student tool.
9. The tool calls the KIT API through the college API client.
10. The assistant formats the result and returns it to the frontend.
11. ElevenLabs converts the response into speech when audio output is requested.

## KIT API Integration

The application integrates with the college-provided REST API:

**Base URL:** `https://ht.knowvally.com`

All requests use the participant key. Authenticated endpoints additionally use the student's bearer access token.

### Authentication

| API | Method | Purpose |
|---|---|---|
| `/v1/auth/login` | POST | Authenticate a student and obtain an access token |
| `/v1/me` | GET | Retrieve the authenticated user's profile |

The backend keeps the access token on the server. The frontend receives an opaque session ID instead of the college API token.

### Student services

| API | Method | Purpose |
|---|---|---|
| `/v1/me/attendance` | GET | Retrieve student attendance |
| `/v1/me/timetable` | GET | Retrieve the student's timetable |
| `/v1/calendar` | GET | Retrieve calendar information |
| `/v1/me/requests` | GET | Retrieve submitted student requests |
| `/v1/me/requests` | POST | Submit a leave or OD request |
| `/v1/me/requests/{id}` | GET | Retrieve an individual request |
| `/v1/me/requests/{id}/cancel` | POST | Cancel a student request |

The assistant currently uses the profile, attendance, timetable, and request-related integrations in its implemented student workflows.

### Request submission

The application supports these request types:

- Personal leave
- Medical leave
- On-duty requests

For an On-Duty request, the event name is also collected.

Example request:

```json
{
  "type": "on_duty",
  "from_date": "2026-11-15",
  "to_date": "2026-11-15",
  "reason": "Attend a hackathon",
  "half_day": false,
  "event_name": "Knotopia Hackathon 2026"
}
```

The assistant does not directly submit a request as soon as it understands the student's message.

Instead:

1. It extracts the request details.
2. It asks follow-up questions if required information is missing.
3. It validates the collected details.
4. It prepares a request draft.
5. It asks the student for explicit confirmation.
6. Only after confirmation does the backend call the KIT request-submission API.

This prevents accidental submissions.

## Safety and Reliability

Some important implementation decisions:

- **Server-side token handling:** College access tokens are not exposed to the frontend or passed to the LLM.
- **Role validation:** The backend validates the authenticated user's role before allowing student workflows.
- **Explicit write confirmation:** Leave and OD requests require confirmation before submission.
- **Input validation:** Request types, dates, reasons, and OD event names are validated before submission.
- **Idempotency:** An idempotency key is used for request submission to reduce duplicate submissions during retries.
- **API-authoritative status:** The assistant reports the status returned by the college API rather than assuming that a request is approved.
- **Voice fallback:** Students can use text interaction if voice services are unavailable.

## Project Structure

```text
quirri-hackathon/
│
├── backend/
│   ├── main.py
│   ├── config.py
│   │
│   ├── services/
│   │   ├── college_client.py
│   │   ├── auth_service.py
│   │   └── request_service.py
│   │
│   ├── tools/
│   │   ├── student_tools.py
│   │   └── request_tools.py
│   │
│   └── ...
│
├── frontend/
│   └── app.py
│
├── tests/
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Configuration

Create a `.env` file in the project root.

```env
COLLEGE_API_BASE_URL=https://ht.knowvally.com
COLLEGE_PARTICIPANT_KEY=your_participant_key

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=your_groq_model

DEEPGRAM_API_KEY=your_deepgram_api_key

ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_voice_id
```

Never commit `.env` or API keys to GitHub.

## Running Locally

### 1. Install dependencies

```bash
uv sync
```

Or install from the exported requirements:

```bash
pip install -r requirements.txt
```

### 2. Start the backend

```bash
uv run uvicorn backend.main:app --reload
```

Backend API documentation:

```text
http://127.0.0.1:8000/docs
```

### 3. Start the frontend

Open another terminal:

```bash
uv run streamlit run frontend/app.py
```

The Streamlit application will be available at:

```text
http://localhost:8501
```

## Current Scope and Limitations

- Chat history and session data are maintained in application memory. They are not yet persisted in PostgreSQL.
- Sessions and in-memory data may be lost when the backend restarts.
- Voice features depend on the availability and API limits of Deepgram and ElevenLabs.
- College data and request statuses are retrieved from the KIT APIs.
- The application is a student-facing assistant prototype and does not replace the college's official systems or approval process.

## Future Improvements

- Persistent chat history and session storage using PostgreSQL.
- More student services, including placement-drive information and registration.
- Improved handling of temporary failures in external AI and college services.
- Additional automated tests for voice, API failures, and agent workflows.

---

**Built for the Quirri Hackathon**

*An AI-powered assistant to make campus interactions simpler, more accessible, and conversational.*