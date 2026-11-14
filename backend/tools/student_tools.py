import json

from langchain_core.tools import tool

from backend.services.college_client import CollegeClient, CollegeAPIError


def create_student_tools(
    college: CollegeClient,
    access_token: str,
):
    """
    Create tools for the currently authenticated student.

    The access token is captured here. The LLM cannot provide
    or change the token or choose another student's identity.
    """

    def format_result(data) -> str:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    @tool
    async def get_attendance() -> str:
        """Get the logged-in student's attendance summary."""
        try:
            result = await college.get_attendance(access_token)

            # Only expose the fields needed to answer attendance questions.
            safe_result = {
                "as_of_date": result.get("as_of_date"),
                "overall_percentage": result.get("overall_percentage"),
                "total_classes_held": result.get("total_classes_held"),
                "total_classes_attended": result.get("total_classes_attended"),
            }

            return format_result(safe_result)

        except CollegeAPIError as error:
            return f"Could not retrieve attendance: {error}"
        except Exception:
            return "Attendance service is temporarily unavailable."

    @tool
    async def get_timetable() -> str:
        """Get the logged-in student's weekly class timetable."""
        try:
            result = await college.get_timetable(access_token)
            return format_result(result)

        except CollegeAPIError as error:
            return f"Could not retrieve timetable: {error}"

        except Exception:
            return "Timetable service is temporarily unavailable."

    @tool
    async def get_calendar(
        from_date: str = "",
        to_date: str = "",
    ) -> str:
        """
        Get college calendar events.

        Dates must use YYYY-MM-DD format.
        You can provide a date range or leave both empty.
        """
        try:
            result = await college.get_calendar(
                token=access_token,
                from_date=from_date or None,
                to_date=to_date or None,
            )
            return format_result(result)

        except CollegeAPIError as error:
            return f"Could not retrieve college calendar: {error}"

        except Exception:
            return "College calendar service is temporarily unavailable."

    @tool
    async def get_my_requests() -> str:
        """List the logged-in student's own leave and on-duty requests and their statuses."""
        try:
            result = await college.get_student_requests(access_token)
            return format_result(result)

        except CollegeAPIError as error:
            return f"Could not retrieve your requests: {error}"

        except Exception:
            return "Request history service is temporarily unavailable."

    return [
        get_attendance,
        get_timetable,
        get_calendar,
    ]
