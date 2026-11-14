from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Stores the conversation messages.
    # add_messages appends new messages instead of replacing old ones.
    messages: Annotated[list[AnyMessage], add_messages]
