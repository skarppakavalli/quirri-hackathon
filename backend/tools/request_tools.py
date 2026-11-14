
import json
from uuid import uuid4

from langchain_core.tools import tool

from backend.services.request_service import (
    RequestService,
    RequestValidationError,
)


def create_request_tools(
    request_service: RequestService,
    session_id: str,
    request_drafts: dict,
):
    """
    Creates tools for preparing leave and OD requests.

    Drafts are stored per session so information can be collected
    across multiple chat messages.
    """

    def get_or_create_draft():
        # Reuse an existing draft for this session.
        for draft_id, draft in reversed(list(request_drafts.items())):
            if (
                draft["session_id"] == session_id
                and draft["status"] in (
                    "collecting_details",
                    "pending_confirmation",
                )
            ):
                return draft_id, draft

        # No active draft exists. Create one.
        draft_id = str(uuid4())

        draft = {
            "session_id": session_id,
            "payload": {},
            "idempotency_key": str(uuid4()),
            "status": "collecting_details",
            "result": None,
        }

        request_drafts[draft_id] = draft

        return draft_id, draft

    @tool
    async def prepare_leave_od_request(
        request_type: str = "",
        from_date: str = "",
        to_date: str = "",
        reason: str = "",
        half_day: bool | None = None,
        event_name: str = "",
    ) -> str:
        """
        Prepare a leave or on-duty request draft.

        IMPORTANT:
        Always call this tool when the student expresses leave or OD intent.

        Extract details from the ENTIRE conversation, not just the latest message.

        For example:
        - "I need OD tomorrow to attend a hackathon"
          means:
          request_type = "on_duty"
          reason = "Attend a hackathon"

        - "I need leave because I have fever"
          means:
          request_type = "medical_leave"
          reason = "I have fever"

        - "I need personal leave for a family function"
          means:
          request_type = "personal_leave"
          reason = "Attend a family function"

        Do not ask the student for a reason if their original message
        already explains why they need leave or OD.

        Allowed request types:
        personal_leave, medical_leave, on_duty

        Dates must use YYYY-MM-DD format.
        OD requires event_name.

        Call this tool with all known details from conversation history.
        Never submit a request. Only prepare a draft.
        """

        # Get the existing draft or create a new one.
        draft_id, draft = get_or_create_draft()

        # If a draft is already ready for confirmation,
        # do not create another one.
        if draft["status"] == "pending_confirmation":
            return json.dumps({
                "status": "pending_confirmation",
                "draft_id": draft_id,
                "request": draft["payload"],
                "message": "A draft already exists. Ask the student to review and confirm it.",
            })

        # Start with details collected in earlier messages.
        payload = draft["payload"]

        # Merge only fields that have actually been provided.
        # Empty strings and None must not erase previous values.
        incoming_fields = {
            "type": request_type,
            "from_date": from_date,
            "to_date": to_date,
            "reason": reason,
            "event_name": event_name,
        }

        for field, value in incoming_fields.items():
            if value and value.strip():
                payload[field] = value.strip()

        # half_day is optional. None means the model did not
        # explicitly provide a value.
        if half_day is not None:
            payload["half_day"] = half_day

        # Check required fields using accumulated information.
        missing = []

        if not payload.get("type"):
            missing.append("request_type")

        if not payload.get("from_date"):
            missing.append("from_date")

        if not payload.get("to_date"):
            missing.append("to_date")

        if not payload.get("reason"):
            missing.append("reason")

        if (
            payload.get("type") == "on_duty"
            and not payload.get("event_name")
        ):
            missing.append("event_name")

        # Keep incomplete details for the next conversation turn.
        if missing:
            draft["status"] = "collecting_details"
            draft["payload"] = payload

            return json.dumps({
                "status": "needs_clarification",
                "draft_id": draft_id,
                "missing_fields": missing,
                "collected_details": payload,
                "message": "Ask the student only for the missing details.",
            }, default=str)

        try:
            # Backend validation is authoritative.
            safe_payload = request_service.validate_request(payload)

        except (RequestValidationError, ValueError) as error:
            return json.dumps({
                "status": "invalid_request",
                "draft_id": draft_id,
                "message": str(error),
            })

        # All details are valid. Mark the draft ready for confirmation.
        draft["payload"] = safe_payload
        draft["status"] = "pending_confirmation"

        return json.dumps({
            "status": "pending_confirmation",
            "draft_id": draft_id,
            "request": safe_payload,
            "message": (
                "Draft created. The student must explicitly confirm "
                "before the request can be submitted."
            ),
        }, default=str)

    return [prepare_leave_od_request]
