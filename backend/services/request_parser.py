
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal

from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from backend.config import settings


# The LLM must return data in this structure.
class RequestExtraction(BaseModel):

    is_request: bool = Field(
        description="Whether the student is asking to create a leave or OD request."
    )

    request_type: Literal[
        "personal_leave",
        "medical_leave",
        "on_duty"
    ] | None = None

    from_date: str | None = Field(
        default=None,
        description="Start date in YYYY-MM-DD format."
    )

    to_date: str | None = Field(
        default=None,
        description="End date in YYYY-MM-DD format."
    )

    reason: str | None = None

    half_day: bool | None = None

    event_name: str | None = None

    missing_fields: list[str] = Field(default_factory=list)

    clarification_question: str | None = None


class RequestParser:

    def __init__(self):

        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is missing.")

        if not settings.GROQ_MODEL:
            raise ValueError("GROQ_MODEL is missing.")

        self.llm = ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0,
        )

        # Force the model to return our Pydantic structure.
        self.structured_llm = self.llm.with_structured_output(
            RequestExtraction
        )

    async def parse_request(self, message: str) -> RequestExtraction:

        # Use Indian local date to understand words like tomorrow.
        current_date = datetime.now(
            ZoneInfo("Asia/Kolkata")
        ).date()

        prompt = f"""
        You are a college leave and on-duty request assistant.

        Current date: {current_date}
        Date format: YYYY-MM-DD

        Understand the student's message and extract request details.

        Allowed request types:
        - personal_leave
        - medical_leave
        - on_duty

        Rules:

        1. Do not invent dates, reasons or event names.
        2. Resolve relative dates such as tomorrow and next Monday
           using the current date.
        3. If only one date is specified, use it for both dates.
        4. For on_duty requests, event_name is mandatory.
        5. If required information is missing, add it to missing_fields.
        6. Ask a short clarification question when information is missing.
        7. Preserve the student's stated reason without adding medical details.
        8. If the message is unrelated to leave or OD, set is_request to false.
        9. Do not assume that a request has been submitted or approved.
        10. If the request type is unclear, ask for clarification.

        Student message:
        {message}
        """

        result = await self.structured_llm.ainvoke(prompt)

        return result
