from functools import partial

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, StateGraph

from core.rich_logging import log_info

from .nodes import (
    query_extractor,
    question_rewriter,
    response_formatter,
    semantic_value_resolver,
    sql_corrector,
    sql_generator,
    sql_validator,
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


def build_graph(
    dsn: str,
    llm_model: BaseChatModel,
    embedder,
    dialect: str,
    validate_sql: bool,
    max_attempts: int,
):
    workflow = StateGraph(BiAgentState)

    workflow.add_node("extractor", partial(query_extractor, embedder=embedder))
    workflow.add_node(
        "semantic_value_resolver",
        partial(semantic_value_resolver, llm_model=llm_model, embedder=embedder),
    )
    workflow.add_node("question_rewriter", partial(question_rewriter, llm_model=llm_model))
    workflow.add_node("generator", partial(sql_generator, llm_model=llm_model, dialect=dialect))
    workflow.add_node(
        "validator",
        partial(sql_validator, dsn=dsn, dialect=dialect, validate_sql=validate_sql),
    )
    workflow.add_node("corrector", partial(sql_corrector, llm_model=llm_model, dialect=dialect))
    workflow.add_node("formatter", response_formatter)

    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "semantic_value_resolver")
    workflow.add_edge("semantic_value_resolver", "question_rewriter")
    workflow.add_edge("question_rewriter", "generator")
    workflow.add_edge("generator", "validator")

    workflow.add_conditional_edges(
        "validator",
        partial(route_validation, max_attempts=max_attempts),
        {"end": "formatter", "correct": "corrector"}
    )
    workflow.add_edge("corrector", "validator")
    workflow.add_edge("formatter", END)

    return workflow
