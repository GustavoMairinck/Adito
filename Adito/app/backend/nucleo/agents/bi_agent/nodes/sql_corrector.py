from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agents.config import bind_structured_output
from core.rich_logging import log_node_end, log_node_start, log_panel

from ..config import SQLResponse
from ..state import BiAgentState
from .field_formats import field_formats_as_strings
from .sql_generator import contexto_do_prompt, pergunta_para_o_modelo


def sql_corrector(
    state: BiAgentState,
    llm_model: BaseChatModel,
    dialect: str,
) -> dict[str, object]:
    error = state["validation_result"]["error"]
    sql = state["generated_sql"]
    attempt = state.get("correction_attempts", 0) + 1
    log_node_start("corrector", f"tentativa={attempt} erro={error[:160]!r}")

    question = pergunta_para_o_modelo(state)
    # Mesmo contexto do gerador: sem a pergunta e o esquema, a correção podia mudar o sentido da consulta.
    system_content = (
        f"You are a SQL expert for the {dialect.upper()} database. Fix the query so it answers the question.\n\n"
        f"Write the explanation field in Brazilian Portuguese.\n\n"
        f"{contexto_do_prompt(state)}"
    )
    prompt = (
        f"Question: {question}\n"
        f"The {dialect} query failed.\n"
        f"Wrong Query: {sql}\nError: {error}\n"
        f"Correct it using ONLY these views: {', '.join(state.get('allowed_views', []))}, "
        f"with lowercase columns, no schema prefix, and {dialect.upper()} syntax. "
        f"Keep the meaning of the question. Maintain the same structured output format."
    )
    structured_llm = bind_structured_output(llm_model, SQLResponse)
    response = structured_llm.invoke([SystemMessage(content=system_content), HumanMessage(content=prompt)])
    corrected_sql = response.sql.strip()
    log_panel("bi", f"SQL corrigido tentativa {attempt}", corrected_sql)
    log_node_end("corrector", f"tentativa={attempt}")

    return {
        "generated_sql": corrected_sql,
        "final_response": response.explanation,
        "field_formats": field_formats_as_strings(response.field_formats),
        "correction_attempts": attempt,
    }
