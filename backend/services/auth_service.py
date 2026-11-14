"""Knows how to log in and identify the user's role."""

from backend.services.college_client import CollegeClient


class AuthService:
    def __init__(self):
        self.college = CollegeClient()

    async def login(self, login_id: str, password: str):
        """
        Authenticate the user and identify their role.

        The frontend should use the returned user information
        to display the appropriate experience.
        """

        # Step 1: Authenticate with the college API
        login_result = await self.college.login(login_id, password)

        # Step 2: Extract the token and user profile
        token = login_result["access_token"]
        user = login_result["user"]

        # Step 3: Validate the role
        role = user.get("role")

        if role not in ("student", "teacher"):
            raise ValueError("Unsupported user role")

        # Step 4: Return authenticated session information
        return {
            "access_token": token,
            "user": user,
            "role": role,
        }
