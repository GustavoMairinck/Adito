from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from core.rich_logging import log_node_end, log_node_start, log_panel

from ..config import SQLResponse
from ..state import BiAgentState
from .field_formats import field_formats_as_strings


def _messages_with_current_question(messages, question: str):
    updated = list(messages)
    for index in range(len(updated) - 1, -1, -1):
        if isinstance(updated[index], HumanMessage):
            updated[index] = HumanMessage(content=question)
            return updated
    return [HumanMessage(content=question)]


def sql_generator(
    state: BiAgentState,
    llm_model: BaseChatModel,
    dialect: str,
) -> dict[str, str]:
    user_input = state.get("rewritten_user_input") or state["user_input"]
    log_node_start("generator", f"pergunta usada={user_input[:120]!r}")
    system_content = (
        f"You are a SQL expert for the {dialect.upper()} database.\n"
        f"Use the CONTEXT below to generate the best possible query.\n\n"
        f"Write the explanation field in Brazilian Portuguese. Keep SQL unchanged in valid PostgreSQL.\n\n"
        f"RETRIEVED CONTEXT:\n{state['retrieved_schema']}\n\n"
        f"{state.get('system_prompt', '')}"
    )

    messages = [SystemMessage(content=system_content)]
    messages.extend(_messages_with_current_question(state["messages"], user_input))

    structured_llm = llm_model.with_structured_output(SQLResponse)
    response = structured_llm.invoke(messages)
    sql = response.sql.strip()
    log_panel("bi", "SQL gerado", sql)
    log_node_end("generator", f"explicação={response.explanation[:120]!r}")
    return {
        "generated_sql": sql,
        "final_response": response.explanation,
        "field_formats": field_formats_as_strings(response.field_formats),
    }
