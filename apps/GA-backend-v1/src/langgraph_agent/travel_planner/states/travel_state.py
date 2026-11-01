from typing import Annotated, TypedDict, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class UserInfo(TypedDict):
    username: Optional[str]
    phone: Optional[str]
    id_card: Optional[str]
    job_level: Optional[str]
    departure: Optional[str]
    destination: Optional[str]
    departuature_date: Optional[str]
    destination_date: Optional[str]
    flight_ticket_standard: Optional[str]
    rail_ticket_standard: Optional[str]
    hotel_standard: Optional[str]

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    userInfo: Optional[UserInfo]
    todos: list[dict]
    stage: str
    final_planning_result: Optional[str]
    final_planning_confirmed: Optional[bool]
