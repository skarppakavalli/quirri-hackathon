
import json

from langchain_core.tools import tool

from backend.services.college_client import CollegeClient


def create_student_tools(
    college: CollegeClient,
    access_token: str
):
    """
    Create tools for the currently authenticated student.

    The token is captured by the function, not exposed
    as an argument that the LLM can choose or modify.
    """

    @tool
    async def get_attendance() -> str:
        """Get the attendance details of the currently logged-in student."""

        try:
            result = await college.get_attendance(access_token)

            return json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )

        except Exception as error:
            return f"Unable to retrieve attendance: {str(error)}"

    return [get_attendance]
