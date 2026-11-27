from functools import partial

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph

from core.rich_logging import log_info

from .cancellation import check_cancelled
from .nodes import (
    query_extractor,
    response_formatter,
    sql_corrector,
    sql_generator,
    sql_validator,
    value_resolver,
)
from .state import BiAgentState


def route_validation(state: BiAgentState, max_attempts: int) -> str:
    if state["validation_result"]["valid"] or state.get("correction_attempts", 0) >= max_attempts:
        log_info(
            "bi",
            (
                "roteador validator -> formatter "
                f"valid={state['validation_result']['valid']} "
                f"tentativas={state.get('correction_attempts', 0)}/{max_attempts}"
            ),
        )
        return "end"
    log_info(
        "bi",
        (
            "roteador validator -> corrector "
            f"erro={state['validation_result'].get('error', '')[:160]!r} "
            f"tentativas={state.get('correction_attempts', 0)}/{max_attempts}"
        ),
    )
    return "correct"


def _cancellable(node_fn):
    def wrapped(state: BiAgentState):
        check_cancelled()
        result = node_fn(state)
        check_cancelled()
        return result

    return wrapped


def build_graph(
    dados_path: str | None,
    llm_model: BaseChatModel,
    embedder,
    dialect: str,
    validate_sql: bool,
    max_attempts: int,
):
    workflow = StateGraph(BiAgentState)

    workflow.add_node("extractor", _cancellable(partial(query_extractor, embedder=embedder)))
    workflow.add_node("value_resolver", _cancellable(partial(value_resolver, embedder=embedder)))
    workflow.add_node("generator", _cancellable(partial(sql_generator, llm_model=llm_model, dialect=dialect)))
    workflow.add_node(
        "validator",
        _cancellable(partial(sql_validator, dados_path=dados_path, dialect=dialect, validate_sql=validate_sql)),
    )
    workflow.add_node("corrector", _cancellable(partial(sql_corrector, llm_model=llm_model, dialect=dialect)))
    workflow.add_node("formatter", _cancellable(response_formatter))

    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "value_resolver")
    workflow.add_edge("value_resolver", "generator")
    workflow.add_edge("generator", "validator")

    workflow.add_conditional_edges(
        "validator",
        partial(route_validation, max_attempts=max_attempts),
        {"end": "formatter", "correct": "corrector"}
    )
    workflow.add_edge("corrector", "validator")
    workflow.add_edge("formatter", END)

    return workflow
