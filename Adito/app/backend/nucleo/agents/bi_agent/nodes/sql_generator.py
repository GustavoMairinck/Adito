from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agents.config import bind_structured_output
from core.rich_logging import log_node_end, log_node_start, log_panel

from ..config import SQLResponse
from ..state import BiAgentState
from .field_formats import field_formats_as_strings
from .value_resolver import bloco_valores


def pergunta_para_o_modelo(state: BiAgentState) -> str:
    """A instrução do orquestrador e, quando diferente, a pergunta como o usuário escreveu e o SQL anterior."""
    instrucao = state["user_input"].strip()
    original = (state.get("pergunta_original") or "").strip()
    anterior = (state.get("sql_anterior") or "").strip()
    if not original or original == instrucao:
        texto = instrucao
    else:
        texto = (
            f"Pergunta do usuário: {original}\n"
            f"Pedido completo, com o contexto da conversa: {instrucao}\n"
            "Use o pedido completo para saber a quem a pergunta se refere (\"desses\", \"esses\", \"e na Serra?\") e "
            "mantenha os filtros da conversa que ele traz. Não acrescente filtros que não estejam em nenhum dos dois."
        )
    if anterior:
        texto += (
            f"\n\nSQL da resposta anterior:\n{anterior}\n"
            "Se a pergunta se referir ao resultado anterior (\"desses\", \"esses\", \"deles\", \"e na Serra?\"), "
            "reaproveite esse SQL como CTE e parta exatamente do conjunto que ele contou, com os mesmos filtros; "
            "nunca inverta o ponto de partida. Se a pergunta não se referir a ele, ignore-o."
        )
    return texto


def contexto_do_prompt(state: BiAgentState) -> str:
    """Bloco fixo (regras e views) primeiro; exemplos e valores achados por último."""
    partes = [state.get("system_prompt", ""), f"RETRIEVED CONTEXT:\n{state.get('retrieved_schema', '')}"]
    valores = bloco_valores(state.get("valores_reais") or [])
    if valores:
        partes.append(valores)
    return "\n\n".join(p for p in partes if p)


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
    user_input = pergunta_para_o_modelo(state)
    log_node_start("generator", f"pergunta usada={user_input[:120]!r}")
    system_content = (
        f"You are a SQL expert for the {dialect.upper()} database.\n"
        f"Use the CONTEXT below to generate the best possible query.\n\n"
        f"Write the explanation field in Brazilian Portuguese. Keep SQL unchanged in valid {dialect.upper()}.\n\n"
        f"{contexto_do_prompt(state)}"
    )

    messages = [SystemMessage(content=system_content)]
    messages.extend(_messages_with_current_question(state["messages"], user_input))

    structured_llm = bind_structured_output(llm_model, SQLResponse)
    response = structured_llm.invoke(messages)
    sql = response.sql.strip()
    log_panel("bi", "SQL gerado", sql)
    log_node_end("generator", f"explicação={response.explanation[:120]!r}")
    return {
        "generated_sql": sql,
        "final_response": response.explanation,
        "field_formats": field_formats_as_strings(response.field_formats),
    }
