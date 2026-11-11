from core.rich_logging import log_node_end, log_node_start, log_warning

from ..state import BiAgentState


def response_formatter(state: BiAgentState) -> dict[str, str]:
    log_node_start("formatter")
    if state["validation_result"]["valid"]:
        log_node_end("formatter", "resposta final válida")
        return {"final_response": state.get("final_response", "SQL gerado com sucesso.")}
    log_warning("bi", f"Finalizando com SQL inválido: {state['validation_result'].get('error')}")
    log_node_end("formatter", "resposta final inválida")
    return {"final_response": "Não foi possível gerar uma query válida após as tentativas."}
