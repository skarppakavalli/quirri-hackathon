import asyncio

from backend.services.college_client import CollegeClient
from backend.agent.tools.student_tools import create_student_tools


async def main():
    college = CollegeClient()

    # Authenticate the student
    login_data = await college.login(
        login_id="arjun",
        password="Kit@2026"
    )

    access_token = login_data["access_token"]

    # Create tools for this authenticated student
    tools = create_student_tools(
        college=college,
        access_token=access_token
    )

    # Call the attendance tool directly
    attendance_tool = tools[0]

    result = await attendance_tool.ainvoke({})

    print("Attendance tool result:")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
