
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

