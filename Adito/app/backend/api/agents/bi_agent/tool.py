"""
Ferramenta `bi_agent` rodando no mesmo processo do backend (antes era um servidor MCP na porta 8005).

Mantém o nome, a descrição e o retorno (JSON em string) que o orquestrador já conhecia,
então o router e o nó de ferramenta funcionam sem mudança.
"""
import asyncio
import json

from langchain_core.tools import StructuredTool
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings

from agents.config import MISTRAL_API_KEY, MISTRAL_EMBEDDING_MODEL, MISTRAL_MODEL, langfuse_callbacks

from .agent import BIAgent

# Prévia de linhas que entra na resposta da ferramenta e, portanto, no histórico enviado ao LLM.
PREVIEW_ROWS = 5

_bi_agent = None


def get_bi_agent() -> BIAgent:
    global _bi_agent
    if _bi_agent is None:
        _bi_agent = BIAgent(
            llm_model=ChatMistralAI(model=MISTRAL_MODEL, api_key=MISTRAL_API_KEY),
            embedder=MistralAIEmbeddings(model=MISTRAL_EMBEDDING_MODEL, api_key=MISTRAL_API_KEY),
        )
    return _bi_agent


def run_bi_agent(instruction: str, tenant_id: str, contexto_id: str, thread_id: str = "default_session") -> str:
    print(f"[BI Agent] tenant={tenant_id!r} contexto={contexto_id!r} | instrução={instruction[:80]!r}")

    result = get_bi_agent().ask(
        question=instruction,
        tenant_id=tenant_id,
        contexto_id=contexto_id,
        thread_id=thread_id,
        callbacks=langfuse_callbacks(),
        execute=True,
    )
    data_rows = result.get("data") or []
    text_resp = result.get("text", result.get("explanation", "")) or ""
    is_valid = bool(result.get("valid"))

    if is_valid and isinstance(data_rows, list) and len(data_rows) == 0:
        text_resp = "A consulta foi executada com sucesso, mas nenhum registro correspondeu ao filtro aplicado."

    data_preview = ""
    if data_rows:
        data_preview = f"\nDados Retornados (resumo):\n{json.dumps(data_rows[:PREVIEW_ROWS], default=str)}"

    payload = {
        "final_content":      f"{text_resp}\n{data_preview}",
        "text_response":      text_resp,
        "sql_used":           result.get("sql", ""),
        "data_rows":          data_rows,
        "field_formats":      result.get("field_formats", {}),
        "type":               "analysis" if is_valid else "fallback",
        "score":              result.get("score", 0),
        "message":            result.get("message") or ("" if is_valid else text_resp),
        "suggestions":        result.get("suggestions", []),
        "related_attributes": result.get("related_attributes", []),
    }
    print(f"[BI Agent] Resultado → type={payload['type']!r} | rows={len(data_rows)} | text={text_resp[:80]!r}")
    return json.dumps(payload, default=str)


async def _arun_bi_agent(instruction: str, tenant_id: str, contexto_id: str, thread_id: str = "default_session") -> str:
    # .ask() é síncrono (LLM + sqlite3); fora do loop para não travar o streaming SSE.
    return await asyncio.to_thread(run_bi_agent, instruction, tenant_id, contexto_id, thread_id)


bi_agent_tool = StructuredTool.from_function(
    func=run_bi_agent,
    coroutine=_arun_bi_agent,
    name="bi_agent",
    description=(
        "Utilize esta ferramenta estritamente para buscar dados quantitativos do contexto de dados "
        "selecionado na conversa: totais, contagens, rankings, comparações e estatísticas calculadas "
        "nas views do banco. Esta ferramenta NÃO responde sobre regras de negócio textuais ou o conteúdo de PDFs."
    ),
)


def local_tools() -> list[StructuredTool]:
    return [bi_agent_tool]
