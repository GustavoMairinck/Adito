from typing import Optional, List, Any, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

def prefer_new(_old, new):
    return new


class MultiAgentState(TypedDict):
    # o state aqui guarda a conversa toda e controla pra onde vai rotear a requisição
    messages: Annotated[List[BaseMessage], add_messages]
    # o texto que o usuario digitou 
    user_input: str
    # chamadas 
    calls: List[dict]
    # resposta final
    final_response: Annotated[Optional[str], prefer_new]
    # dados tragos da api do BI (oraculo)
    graph: Annotated[Optional[Any], prefer_new]
    sql_used: Annotated[Optional[str], prefer_new]
    text_response: Annotated[Optional[str], prefer_new]
    analysis_explanation: Annotated[Optional[str], prefer_new]
    # campos para delegacao MCP
    delegation_instruction: Optional[str]
    tool_name: Optional[str]
    
    # controle de multi-tenancy
    tenant_id: Optional[str]
    db_schema_name: Optional[str]
    thread_id: Optional[str]
    
    # campos visuais do frontend (fallback, suggestions, etc)
    type: Annotated[Optional[str], prefer_new]
    score: Annotated[Optional[float], prefer_new]
    message: Annotated[Optional[str], prefer_new]
    suggestions: Annotated[Optional[List[str]], prefer_new]
    related_attributes: Annotated[Optional[List[Any]], prefer_new]
    field_formats: Annotated[Optional[dict], prefer_new]
