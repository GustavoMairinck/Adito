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
    # pergunta como o usuário escreveu (user_input é a instrução resolvida pelo orquestrador)
    pergunta_original: str
    # valores reais do banco achados na pergunta (nodes/value_resolver.py)
    valores_reais: list[dict[str, Any]]
    # SQL generation
    generated_sql: str
    field_formats: dict[str, str]
    validation_result: dict
    correction_attempts: int
    final_response: str

BiAgentState = AgentState