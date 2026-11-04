from typing import Any, TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    user_input: str
    tenant_id: str
    contexto_id: str
    allowed_views: list[str]
    messages: Annotated[Sequence[BaseMessage], operator.add]
    system_prompt: str
    retrieved_schema: str
    # rewrite pipeline
    rewrite_candidates: list[dict[str, Any]]
    value_search_queries: list[str]
    value_search_calls: list[dict[str, Any]]
    rewritten_user_input: str
    rewrite_reason: str
    # SQL generation
    generated_sql: str
    field_formats: dict[str, str]
    validation_result: dict
    correction_attempts: int
    final_response: str

BiAgentState = AgentState