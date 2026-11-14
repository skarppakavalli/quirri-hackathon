import json
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, ToolMessage
from backend.agents.graph import build_student_agent

from backend.services.auth_service import AuthService
from backend.services.college_client import CollegeClient, CollegeAPIError
from backend.services.request_parser import RequestParser
from backend.services.request_service import (
    RequestService,
    RequestValidationError,
)

app = FastAPI(
    title="KIT Student Assistant",
    description="AI-powered college assistant",
    version="1.0.0",
)


# Temporary session store for the hackathon MVP.
# The college access token stays on the backend.
# Replace this with persistent session storage before production.
# Temporary in-memory storage
sessions = {}
request_drafts = {}
chat_histories = {} # Temporary conversation history, isolated by session.

college = CollegeClient()

request_service = RequestService(college)
auth_service = AuthService()
request_parser = RequestParser()


# -------------------------
# Request models
# -------------------------

class LoginRequest(BaseModel):
    login_id: str
    password: str

# -------------------------
# RequestDraftCreate
# -------------------------
class RequestDraftCreate(BaseModel):
    type: str
    from_date: str
    to_date: str
    reason: str
    half_day: bool = False
    event_name: str | None = None

# -------------------------
# ChatMessageRequest
# -------------------------
class ChatMessageRequest(BaseModel):
    message: str

# -------------------------
# Health check
# -------------------------

@app.get("/health")
async def health():
    return {"status": "healthy"}


# -------------------------
# Login
# -------------------------

@app.post("/auth/login")
async def login(request: LoginRequest):

    try:
        session = await auth_service.login(
            request.login_id,
            request.password,
        )

        # Create an opaque session ID.
        session_id = str(uuid4())

        # Keep sensitive information on the backend.
        sessions[session_id] = {
            "access_token": session["access_token"],
            "role": session["role"],
            "user": session["user"],
        }

        # Never return the college access token.
        return {
            "session_id": session_id,
            "user": {
                "full_name": session["user"]["full_name"],
                "role": session["role"],
            },
            "message": "Login successful",
        }

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Login failed. Check your credentials.",
        )


# -------------------------
# Session helper
# -------------------------

def get_session(session_id: str):

    session = sessions.get(session_id)

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session.",
        )

    return session


# -------------------------
# Example authenticated route
# -------------------------

@app.get("/me")
async def get_current_user(
    x_session_id: str = Header(...)
):

    session = get_session(x_session_id)

    return {
        "role": session["role"],
        "full_name": session["user"]["full_name"],
    }

@app.post("/requests/draft")
async def create_request_draft(
    request: RequestDraftCreate,
    x_session_id: str = Header(...),
):
    session = get_session(x_session_id)

    # Only students can create leave/OD requests.
    if session["role"] != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can create these requests."
        )

    try:
        # Validate and clean the request.
        safe_payload = request_service.validate_request(
            request.model_dump()
        )

        # Generate an ID and idempotency key once per draft.
        draft_id = str(uuid4())
        idempotency_key = str(uuid4())

        request_drafts[draft_id] = {
            "session_id": x_session_id,
            "payload": safe_payload,
            "idempotency_key": idempotency_key,
            "status": "pending_confirmation",
            "result": None,
        }

        return {
            "draft_id": draft_id,
            "status": "pending_confirmation",
            "request": safe_payload,
            "message": "Please review and confirm this request."
        }

    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

@app.post("/requests/{draft_id}/confirm")
async def confirm_request(
    draft_id: str,
    x_session_id: str = Header(...),
):
    session = get_session(x_session_id)

    if session["role"] != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can submit these requests."
        )

    draft = request_drafts.get(draft_id)

    if not draft:
        raise HTTPException(
            status_code=404,
            detail="Request draft not found."
        )

    # Prevent another student's session from confirming this draft.
    if draft["session_id"] != x_session_id:
        raise HTTPException(
            status_code=403,
            detail="You cannot confirm another student's request."
        )

    # Make retries safe after a successful submission.
    if draft["status"] == "submitted":
        return draft["result"]

    if draft["status"] != "pending_confirmation":
        raise HTTPException(
            status_code=409,
            detail="This request cannot be submitted right now."
        )

    try:
        result = await request_service.submit_confirmed_request(
            token=session["access_token"],
            payload=draft["payload"],
            idempotency_key=draft["idempotency_key"],
        )

        # Return only the necessary response fields.
        status = result.get("status", "submitted")

        safe_result = {
            "id": result.get("id"),
            "type": result.get("type"),
            "from_date": result.get("from_date"),
            "to_date": result.get("to_date"),
            "status": status,
            "message": f"Your request was submitted. Current status: {status}."
        }

        draft["status"] = "submitted"
        draft["result"] = safe_result

        return safe_result

    except CollegeAPIError:
        # Keep the draft and its original idempotency key.
        # A retry can safely reuse the same key.
        raise HTTPException(
            status_code=502,
            detail="The college service could not process your request. Please retry."
        )


@app.post("/requests/interpret")
async def interpret_request(
    request: ChatMessageRequest,
    x_session_id: str = Header(...),
):
    session = get_session(x_session_id)

    if session["role"] != "student":
        raise HTTPException(
            status_code=403,
            detail="Only students can create these requests."
        )

    message = request.message.strip()

    if not message or len(message) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Message must contain between 1 and 2000 characters."
        )

    try:
        # Step 1: Understand the student's message.
        extracted = await request_parser.parse_request(message)

        if not extracted.is_request:
            return {
                "status": "not_a_request",
                "message": "Please describe the leave or OD request you want to make."
            }

        # Step 2: Check required fields ourselves.
        # Do not rely solely on the LLM's missing_fields output.
        payload = extracted.model_dump()

        required_fields = [
            "request_type",
            "from_date",
            "to_date",
            "reason",
        ]

        missing = [
            field for field in required_fields
            if not payload.get(field)
        ]

        if payload.get("request_type") == "on_duty" and not payload.get("event_name"):
            missing.append("event_name")

        if missing:
            return {
                "status": "needs_clarification",
                "missing_fields": missing,
                "question": extracted.clarification_question
                    or "Could you provide the missing request details?"
            }

        # Step 3: Convert LLM output into the college API format.
        college_payload = {
            "type": payload["request_type"],
            "from_date": payload["from_date"],
            "to_date": payload["to_date"],
            "reason": payload["reason"],
            "half_day": payload.get("half_day") or False,
            "event_name": payload.get("event_name"),
        }

        # Step 4: Apply backend validation.
        try:
            safe_payload = request_service.validate_request(
                college_payload
            )
        except RequestValidationError as error:
            return {
                "status": "needs_clarification",
                "question": str(error)
            }

        # Step 5: Create a draft, but DO NOT submit it.
        draft_id = str(uuid4())
        idempotency_key = str(uuid4())

        request_drafts[draft_id] = {
            "session_id": x_session_id,
            "payload": safe_payload,
            "idempotency_key": idempotency_key,
            "status": "pending_confirmation",
            "result": None,
        }

        return {
            "status": "pending_confirmation",
            "draft_id": draft_id,
            "request": safe_payload,
            "message": "Please review your request before confirming."
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to understand your request right now. Please try again."
        )


@app.post("/chat")
async def chat(
    request: ChatMessageRequest,
    x_session_id: str = Header(...),
):
    session = get_session(x_session_id)

    if session["role"] != "student":
        raise HTTPException(
            status_code=403,
            detail="Student assistant access only."
        )

    message = request.message.strip()

    if not message or len(message) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Message must contain between 1 and 2000 characters."
        )

    try:
        # Retrieve this student's previous conversation.
        history = chat_histories.get(x_session_id, [])

        # Add the new message.
        messages = history + [
            HumanMessage(content=message)
        ]

        # Build an agent using this student's server-side token.
        agent = build_student_agent(
            access_token=session["access_token"],
            session_id=x_session_id, #This is how the request tool receives the correct student's session context.
            request_drafts=request_drafts,
        )

        # Run the LangGraph agent.
        result = await agent.ainvoke({
            "messages": messages
        })

        # Look for a draft created by the request tool.
        pending_confirmation = None

        for msg in result["messages"]:

            if isinstance(msg, ToolMessage) and isinstance(msg.content, str):

                try:
                    tool_result = json.loads(msg.content)

                    if tool_result.get("status") == "pending_confirmation":
                        pending_confirmation = {
                            "draft_id": tool_result["draft_id"],
                            "request": tool_result["request"],
                            "status": tool_result["status"],
                        }

                except (json.JSONDecodeError, KeyError):
                    continue

        # Save the complete conversation, including tool calls.
        chat_histories[x_session_id] = result["messages"]

        # Return the final assistant response.
        final_message = result["messages"][-1]

        return {
            "reply": final_message.content,
            "pending_confirmation": pending_confirmation,
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="The assistant is temporarily unavailable. Please try again."
        )
