from datetime import date

from backend.services.college_client import CollegeClient


ALLOWED_REQUEST_TYPES = {
    "personal_leave",
    "medical_leave",
    "on_duty",
}


class RequestValidationError(Exception):
    pass


class RequestService:

    def __init__(self, college: CollegeClient):
        self.college = college

    def validate_request(self, payload: dict) -> dict:
        """Validate a request before showing it to the student."""

        required_fields = [
            "type",
            "from_date",
            "to_date",
            "reason",
        ]

        for field in required_fields:
            if not payload.get(field):
                raise RequestValidationError(
                    f"Missing required field: {field}"
                )

        request_type = payload["type"]

        if request_type not in ALLOWED_REQUEST_TYPES:
            raise RequestValidationError(
                "Invalid request type."
            )

        try:
            from_date = date.fromisoformat(payload["from_date"])
            to_date = date.fromisoformat(payload["to_date"])
        except ValueError:
            raise RequestValidationError(
                "Dates must use YYYY-MM-DD format."
            )

        if to_date < from_date:
            raise RequestValidationError(
                "End date cannot be before start date."
            )

        if request_type == "on_duty" and not payload.get("event_name"):
            raise RequestValidationError(
                "Event name is required for an OD request."
            )

        # Construct a clean payload instead of forwarding
        # arbitrary fields supplied by the LLM.
        safe_payload = {
            "type": request_type,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "reason": payload["reason"].strip(),
            "half_day": bool(payload.get("half_day", False)),
        }

        if request_type == "on_duty":
            safe_payload["event_name"] = payload["event_name"].strip()

        return safe_payload

    async def submit_confirmed_request(
        self,
        token: str,
        payload: dict,
        idempotency_key: str,
    ):
        """
        Call this only after explicit student confirmation.

        The same idempotency key must be reused if this
        particular submission is retried.
        """

        if not idempotency_key:
            raise ValueError("Idempotency key is required.")

        safe_payload = self.validate_request(payload)

        return await self.college.create_student_request(
            token=token,
            payload=safe_payload,
            idempotency_key=idempotency_key,
        )
