import asyncio

from langchain_core.messages import HumanMessage

from backend.services.auth_service import AuthService
from backend.agents.graph import build_student_agent


def test_student_agent():

    async def run_test():

        auth = AuthService()

        session = await auth.login("arjun", "Kit@2026")

        assert session["role"] == "student"

        agent = build_student_agent(
            access_token=session["access_token"],
            session_id="test-session-arjun",
            request_drafts={},
        )

        result = await agent.ainvoke({
            "messages": [
                HumanMessage(
                    content="I need OD tomorrow to attend a hackathon."
                )
            ]
        })

        print("\nAgent response:")
        print(result["messages"][-1].content)

        assert result["messages"][-1].content

    asyncio.run(run_test())