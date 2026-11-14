
import asyncio

from backend.services.college_client import CollegeClient


async def main():

    college = CollegeClient()

    # Test 1: Public endpoint (no login)
    print("\nTesting public college endpoint...")

    college_data = await college.get_college()
    print(college_data)

    # Test 2: Student login
    print("\nTesting student login...")

    login_data = await college.login(
        login_id="arjun",
        password="Kit@2026"
    )

    print("Login successful!")
    print(login_data)

    # IMPORTANT:
    # Inspect the actual response and identify the token field.
    token = login_data["access_token"]

    # Test 3: Authenticated student endpoint
    print("\nTesting attendance...")

    attendance = await college.get_attendance(token)

    print("Attendance:")
    print(attendance)


if __name__ == "__main__":
    asyncio.run(main())
