import os
import sys
import json
from fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bi_agent_api.settings")
import django
django.setup()

from agents.bi_agent.agent import BIAgent
from agents.config import (
    MISTRAL_MODEL,
    MISTRAL_API_KEY,
    MISTRAL_EMBEDDING_MODEL,
)
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langfuse.langchain import CallbackHandler

mcp = FastMCP("bi_agent")

_bi_agent = None


def get_bi_agent():
    global _bi_agent
    if _bi_agent is None:
        _bi_agent = BIAgent(
            llm_model=ChatMistralAI(model=MISTRAL_MODEL, api_key=MISTRAL_API_KEY),
            embedder=MistralAIEmbeddings(model=MISTRAL_EMBEDDING_MODEL, api_key=MISTRAL_API_KEY),
        )
    return _bi_agent


@mcp.tool()
def bi_agent(instruction: str, tenant_id: str, contexto_id: str, thread_id: str = "default_session") -> str:
    """
    Utilize esta ferramenta estritamente para buscar dados quantitativos, financeiros e comerciais
    de vendas ESX: receita, produtos, clientes, canais, vendedores, regiões, lucro, descontos,
    margem, rankings e estatísticas do banco de dados relacional ORACULO-ESX.
    Esta ferramenta NÃO responde sobre regras de negócio textuais ou o conteúdo de PDFs.
    """
    print(f"[BI Agent MCP] tenant={tenant_id!r} | instrução={instruction[:80]!r}")

    langfuse_handler = CallbackHandler()

    result = get_bi_agent().ask(
        question=instruction,
        tenant_id=tenant_id,
        contexto_id=contexto_id,
        thread_id=thread_id,
        callbacks=[langfuse_handler],
        execute=True,
    )
    data_rows = result.get("data", [])
    text_resp = result.get("text", result.get("explanation", ""))
    is_valid = bool(result.get("valid"))

    if is_valid and isinstance(data_rows, list) and len(data_rows) == 0:
        text_resp = "A consulta foi executada com sucesso, mas nenhum registro correspondeu ao filtro aplicado."

    data_preview = ""
    if data_rows:
        preview = data_rows[:5]
        data_preview = f"\nDados Retornados (resumo):\n{json.dumps(preview, default=str)}"

    final_content = f"{text_resp}\n{data_preview}"

    payload = {
        "final_content":      final_content,
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
    print(f"[BI Agent MCP] Resultado → type={payload['type']!r} | rows={len(payload['data_rows'] or [])} | field_formats={payload['field_formats']} | text={payload['text_response'][:80]!r}")
    return json.dumps(payload, default=str)


if __name__ == "__main__":
    mcp.run(transport="http", port=8005, host="0.0.0.0")
