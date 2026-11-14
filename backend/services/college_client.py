"""Knows how to communicate with the external API."""

import uuid
import httpx

from backend.config import settings


class CollegeAPIError(Exception):
    """Represents an error returned by the college system."""

    def __init__(self, status_code: int, message: str, code=None, field=None):
        self.status_code = status_code
        self.code = code
        self.field = field
        super().__init__(message)


class CollegeClient:

    def __init__(self):
        self.base_url = settings.COLLEGE_API_BASE_URL.rstrip("/")

    async def request(
        self,
        method: str,
        endpoint: str,
        token: str | None = None,
        params: dict | None = None,
        payload: dict | None = None,
        idempotency_key: str | None = None
    ):

        # Every request needs the participant key.
        headers = {
            "X-Participant-Key": settings.COLLEGE_PARTICIPANT_KEY,
            "Accept": "application/json"
        }

        # Only authenticated student/teacher requests need a token.
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Protect write operations from accidental duplicate submissions.
        if method.upper() in ["POST", "PUT", "PATCH"]:
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key
            else:
                headers["Idempotency-Key"] = (
                    idempotency_key or str(uuid.uuid4())
                )

        async with httpx.AsyncClient(timeout=20.0) as client:

            response = await client.request(
                method=method,
                url=f"{self.base_url}{endpoint}",
                headers=headers,
                params=params,
                json=payload
            )

        # Parse API errors instead of exposing raw HTTP errors.

        if not response.is_success:
            try:
                body = response.json()
                error_data = body.get("error", {})
                message = error_data.get(
                    "message",
                    str(body)
                )
                code = error_data.get("code")
                field = error_data.get("field")

            except ValueError:
                message = response.text
                code = None
                field = None

            print(f"\nCollege API Error")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")

            raise CollegeAPIError(
                status_code=response.status_code,
                message=message,
                code=code,
                field=field
            )

        if response.status_code == 204 or not response.content:
            return None

        print("\n--- API DEBUG ---")
        print("Requested URL:", response.request.url)
        print("Status:", response.status_code)
        print("Final URL:", response.url)
        print("Content-Type:", response.headers.get("content-type"))
        print("Redirect history:", response.history)
        print("Response preview:", response.text[:500])
        print("-----------------\n")
        return response.json()

    # -------------------------
    # AUTHENTICATION
    # -------------------------

    async def login(self, login_id: str, password: str):

        return await self.request(
            method="POST",
            endpoint="/v1/auth/login",
            payload={
                "login_id": login_id,
                "password": password
            }
        )

    # -------------------------
    # PUBLIC ENDPOINTS
    # -------------------------

    async def get_college(self):
        return await self.request("GET", "/v1/college")

    async def get_courses(self):
        return await self.request("GET", "/v1/courses")

    async def get_today(self):
        return await self.request("GET", "/v1/today")

    async def get_documents(self):
        return await self.request("GET", "/v1/documents")

    async def get_placement_drives(self):
        return await self.request("GET", "/v1/placements/drives")

    # -------------------------
    # STUDENT ENDPOINTS
    # -------------------------

    async def get_attendance(self, token: str):
        return await self.request(
            method="GET",
            endpoint="/v1/me/attendance",
            token=token
        )


    # -------------------------------
    # STUDENT READ OPERATIONS
    # -------------------------------

    async def get_student_profile(self, token: str):
        return await self.request(
            "GET", "/v1/me", token=token
        )

    async def get_student_timetable(self, token: str):
        return await self.request(
            "GET", "/v1/me/timetable", token=token
        )

    async def get_calendar(
        self,
        token: str,
        from_date: str | None = None,
        to_date: str | None = None
    ):
        params = {}

        if from_date:
            params["from"] = from_date

        if to_date:
            params["to"] = to_date

        return await self.request(
            "GET",
            "/v1/calendar",
            token=token,
            params=params
        )

    async def get_student_requests(self, token: str):
        return await self.request(
            "GET", "/v1/me/requests", token=token
        )

    async def get_student_request(
        self, token: str, request_id: int
    ):
        return await self.request(
            "GET",
            f"/v1/me/requests/{request_id}",
            token=token
        )

    # -------------------------------
    # TEACHER OPERATIONS
    # -------------------------------

    async def get_teacher_requests(
        self,
        token: str,
        status: str | None = "pending"
    ):
        params = {}

        if status:
            params["status"] = status

        return await self.request(
            "GET",
            "/v1/teacher/requests",
            token=token,
            params=params
        )

    async def approve_request(
        self,
        token: str,
        request_id: int,
        payload: dict | None = None
    ):
        return await self.request(
            "POST",
            f"/v1/teacher/requests/{request_id}/approve",
            token=token,
            payload=payload
        )

    async def reject_request(
        self,
        token: str,
        request_id: int,
        payload: dict
    ):
        return await self.request(
            "POST",
            f"/v1/teacher/requests/{request_id}/reject",
            token=token,
            payload=payload
        )

    # ---------- STUDENT: PROFILE AND ACADEMICS ----------

    async def get_profile(self, token: str):
        """Get the currently authenticated user's profile."""
        return await self.request("GET", "/v1/me", token=token)

    async def get_timetable(self, token: str):
        return await self.request("GET", "/v1/me/timetable", token=token)

    async def get_calendar(
        self,
        token: str,
        from_date: str | None = None,
        to_date: str | None = None,
    ):
        params = {}

        if from_date:
            params["from"] = from_date

        if to_date:
            params["to"] = to_date

        return await self.request(
            "GET",
            "/v1/calendar",
            token=token,
            params=params,
        )

    # ---------- STUDENT: LEAVE / ON-DUTY REQUESTS ----------

    async def get_student_requests(self, token: str):
        """List requests belonging to the logged-in student."""
        return await self.request(
            "GET",
            "/v1/me/requests",
            token=token,
        )

    async def get_student_request(self, token: str, request_id: int):
        return await self.request(
            "GET",
            f"/v1/me/requests/{request_id}",
            token=token,
        )

    async def create_student_request(
        self,
        token: str,
        payload: dict,
        idempotency_key: str,
    ):
        """
        Submit a leave or on-duty request.

        The caller must create one idempotency key per logical submission
        and reuse that same key if retrying the request.
        """
        return await self.request(
            "POST",
            "/v1/me/requests",
            token=token,
            payload=payload,
            idempotency_key=idempotency_key,
        )

    # ---------- TEACHER: REQUEST MANAGEMENT ----------

    async def get_teacher_requests(
        self,
        token: str,
        status: str | None = "pending",
    ):
        params = {}

        if status:
            params["status"] = status

        return await self.request(
            "GET",
            "/v1/teacher/requests",
            token=token,
            params=params,
        )

    async def approve_request(
        self,
        token: str,
        request_id: int,
        comment: str | None = None,
    ):
        payload = {"comment": comment} if comment else None

        return await self.request(
            "POST",
            f"/v1/teacher/requests/{request_id}/approve",
            token=token,
            payload=payload,
        )

    async def reject_request(
        self,
        token: str,
        request_id: int,
        reason: str,
    ):
        payload = {"reason": reason}

        return await self.request(
            "POST",
            f"/v1/teacher/requests/{request_id}/reject",
            token=token,
            payload=payload,
        )