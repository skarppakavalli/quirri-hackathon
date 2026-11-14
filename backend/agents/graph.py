
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage

from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition

from backend.config import settings
from backend.agents.state import AgentState

from backend.services.college_client import CollegeClient
from backend.services.request_service import RequestService

from backend.tools.student_tools import create_student_tools
from backend.tools.request_tools import create_request_tools


def build_student_agent(
    access_token: str,
    session_id: str,
    request_drafts: dict,
):

    # 1. Create shared college API client.
    college = CollegeClient()

    # 2. Create the request service.
    request_service = RequestService(college)

    # 3. Create read-only student tools.
    student_tools = create_student_tools(
        college=college,
        access_token=access_token,
    )

    # 4. Create request preparation tool.
    # This tool can create drafts, but cannot submit them.
    request_tools = create_request_tools(
        request_service=request_service,
        session_id=session_id,
        request_drafts=request_drafts,
    )

    tools = student_tools + request_tools

    # 5. Initialize Groq.
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,
    )

    llm_with_tools = llm.bind_tools(tools)

    current_date = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).date()

    SYSTEM_PROMPT = f"""
You are KIT, a helpful student assistant for
Knotopian Institute of Technology.

Today's date is {current_date}.
Use this date to understand relative dates such as tomorrow
and next Monday.

You can help students with:
1. Attendance
2. Timetable
3. College calendar
4. Leave and on-duty requests
5. General college enquiries supported by your tools.

TOOL RULES:

- Use attendance, timetable and calendar tools when actual
  student information is required.
- When a student expresses an intent to apply for leave or OD,
call prepare_leave_od_request even if some details are missing.
- Always pass every detail already available from the entire conversation,
not just the latest message.
- If the tool returns needs_clarification, ask only for the missing fields.
- Do not ask again for details already collected.
- Use prepare_leave_od_request when a student wants to
  prepare a leave or OD application.
- Collect all required information before preparing a draft.
- For OD, collect the event name.
- Never invent missing dates, reasons or event names.
- Ask clarification questions when information is missing.
- Never claim a draft is submitted.
- Never claim a request is approved.
- Preparing a draft is NOT submitting a request.
- The student must explicitly confirm through the application
  before the backend submits it.
- Never ask for or reveal passwords or access tokens.
- Never invent API results.
- If a tool fails, explain that the service is unavailable.

REASON EXTRACTION RULES:
- A reason does not need to be a separate sentence.
- Extract the purpose from phrases such as "to attend a hackathon",
  "for a family function", or "because I have fever".
- Do not ask for a reason if the student's original message
  already contains a meaningful purpose.
- For "OD tomorrow to attend a hackathon", use
  reason = "Attend a hackathon".

Keep responses friendly, concise and easy to understand.
"""

    # 6. Agent node.
    async def call_model(state: AgentState):

        messages = [
            SystemMessage(content=SYSTEM_PROMPT)
        ] + state["messages"]

        response = await llm_with_tools.ainvoke(messages)

        return {
            "messages": [response]
        }

    # 7. Tool execution node.
    tool_node = ToolNode(tools)

    # 8. Build LangGraph.
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node("agent", call_model)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_edge(START, "agent")

    graph_builder.add_conditional_edges(
        "agent",
        tools_condition,
    )

    graph_builder.add_edge("tools", "agent")

    return graph_builder.compile()
