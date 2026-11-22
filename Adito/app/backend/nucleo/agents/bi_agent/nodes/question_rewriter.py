from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from core.rich_logging import log_error, log_info, log_node_end, log_node_start, log_success

from ..config import BI_REWRITE_SYSTEM_PROMPT, QuestionRewriteResponse
from ..state import BiAgentState


def _no_rewrite(user_input: str, reason: str, candidates: list[dict] | None = None) -> dict[str, object]:
    return {
        "rewritten_user_input": user_input,
        "rewrite_candidates": candidates or [],
        "rewrite_reason": reason,
    }


def question_rewriter(
    state: BiAgentState,
    llm_model: BaseChatModel,
) -> dict[str, object]:
    user_input = state["user_input"]
    log_node_start("question_rewriter", f"pergunta original={user_input[:120]!r}")
    candidates = state.get("rewrite_candidates") or []

    if not candidates:
        log_info("rewrite", "Nenhum candidato semântico encontrado; mantendo pergunta original.")
        log_node_end("question_rewriter", "sem reescrita")
        return _no_rewrite(user_input, "Nenhum candidato semântico encontrado.")

    candidates_prompt = "\n\n".join(
        f"Candidato {index} (distância {candidate['distance']:.4f}):\n"
        f"{candidate['embedding_text']}"
        for index, candidate in enumerate(candidates, 1)
    )
    human_prompt = (
        f"Pergunta original:\n{user_input}\n\n"
        f"Candidatos reais recuperados:\n{candidates_prompt}\n\n"
        "Reescreva a pergunta somente se isso deixar os nomes citados mais fiéis ao banco."
    )

    try:
        structured_llm = llm_model.with_structured_output(QuestionRewriteResponse)
        response = structured_llm.invoke(
            [
                SystemMessage(content=BI_REWRITE_SYSTEM_PROMPT),
                HumanMessage(content=human_prompt),
            ]
        )
    except Exception as exc:
        log_error("rewrite", f"Falha ao reescrever pergunta: {exc}")
        log_node_end("question_rewriter", "sem reescrita; LLM indisponível")
        return _no_rewrite(user_input, "Reescrita indisponível.", candidates)

    rewritten = (response.rewritten_question or user_input).strip() or user_input
    log_success(
        "rewrite",
        f"changed={response.changed} | original={user_input[:100]!r} | reescrita={rewritten[:140]!r}",
    )
    log_node_end("question_rewriter", f"reasoning={response.reasoning[:160]!r}")
    return {
        "rewritten_user_input": rewritten,
        "rewrite_candidates": candidates,
        "rewrite_reason": response.reasoning,
    }
