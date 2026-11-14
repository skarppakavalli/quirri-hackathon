import asyncio

from backend.services.college_client import CollegeClient
from backend.services.auth_service import AuthService
from backend.tools.student_tools import create_student_tools


def test_get_attendance():
    async def run_test():
        auth = AuthService()

        session = await auth.login("arjun", "Kit@2026")

        assert session["role"] == "student"

        college = CollegeClient()

        tools = create_student_tools(
            college,
            session["access_token"]
        )

        attendance_tool = next(
            tool for tool in tools
            if tool.name == "get_attendance"
        )

        result = await attendance_tool.ainvoke({})

        assert result
        print(result)

    asyncio.run(run_test())