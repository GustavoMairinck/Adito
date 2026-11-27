import logging
import threading
from typing import Any, Callable, List, Optional
from langchain_core.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

from core.contexts import build_system_prompt, get_contexto, read_policy_for
from core.datastore import connect_dados

from .cancellation import (
    BIAgentCancelled,
    check_cancelled,
    get_cancel_event,
    reset_cancel_event,
    set_cancel_event,
)
from .graph import build_graph

def execute_query(sql: str, contexto_id: str | None, max_rows: int | None = None, dados_path=None) -> List[dict]:
    """Executa a query no dados.db (só leitura) com a política do contexto. Sem max_rows, devolve todas as linhas.

    Não depende do LLM: widgets e histórico do chat reexecutam SQL sem instanciar o agente.
    """
    try:
        clean_sql = sql.strip().rstrip(';')
        with connect_dados(read_policy_for(contexto_id), dados_path) as conn:
            cur = conn.execute(clean_sql)
            fetched = cur.fetchmany(int(max_rows)) if max_rows is not None else cur.fetchall()
            rows = [dict(r) for r in fetched]

        if rows and all(v is None for r in rows for v in r.values()):
            return []
        return rows
    except Exception as e:
        print(f"[x] Erro na execução final: {e}")
        return [{"error": str(e)}]


class BIAgent:
    def __init__(
        self,
        llm_model: BaseChatModel,
        embedder: Embeddings,
        dados_path: str | None = None,
        dialect: str = "sqlite",
        validate_sql: bool = True,
        max_attempts: int = 2,
        system_prompt: str = "",
        checkpointer=None,
        callbacks: List[Any] = None,
    ):
        self.dados_path = dados_path
        # Instruções extras, somadas ao prompt montado a partir do contexto.
        self.system_prompt = system_prompt

        workflow = build_graph(dados_path, llm_model, embedder, dialect, validate_sql, max_attempts)
        self.app = workflow.compile(checkpointer=checkpointer)

        if callbacks:
            self.app = self.app.with_config({"callbacks": callbacks})

    def execute_query(self, sql: str, contexto_id: str | None, max_rows: int | None = None) -> List[dict]:
        return execute_query(sql, contexto_id, max_rows, self.dados_path)

    def ask(
        self,
        question: str,
        tenant_id: str,
        contexto_id: str,
        thread_id: str,
        callbacks: Optional[List[Any]] = None,
        execute: bool = False,
        cancel_event: threading.Event | None = None,
        on_progress: Optional[Callable[[str, dict], None]] = None,
    ) -> dict:
        """Processa a pergunta do usuário dentro de um contexto (views, regras e RAG do contexto)."""
        token = set_cancel_event(cancel_event) if cancel_event is not None else None
        try:
            check_cancelled()
            contexto = get_contexto(contexto_id)
            if contexto is None:
                return {
                    "sql": None,
                    "valid": False,
                    "explanation": "Nenhum contexto de dados selecionado. Escolha um contexto para esta conversa.",
                    "data": None,
                    "field_formats": {},
                }

            config = {
                "configurable": {"thread_id": thread_id},
                "callbacks": callbacks,
                "metadata": {
                    "langfuse_session_id": thread_id
                }
            }

            system_prompt = build_system_prompt(contexto, self.dados_path)
            if self.system_prompt:
                system_prompt = f"{system_prompt}\n\n{self.system_prompt}"

            input_data = {
                "user_input": question,
                "tenant_id": str(tenant_id),
                "contexto_id": str(contexto.id),
                "allowed_views": contexto.view_names(),
                "messages": [HumanMessage(content=question)],
                "system_prompt": system_prompt,
            }

            check_cancelled()
            if on_progress is not None:
                output: dict[str, Any] = dict(input_data)
                for chunk in self.app.stream(input_data, config=config, stream_mode="updates"):
                    check_cancelled()
                    if not isinstance(chunk, dict):
                        continue
                    for node_name, node_update in chunk.items():
                        if isinstance(node_update, dict):
                            output.update(node_update)
                            try:
                                on_progress(node_name, node_update)
                            except Exception as exc:
                                logger.debug("Falha ao emitir progresso do bi_agent (%s): %s", node_name, exc)
            else:
                output = self.app.invoke(input_data, config=config)
            check_cancelled()

            sql = output.get("generated_sql")
            valid = output.get("validation_result", {}).get("valid", False)

            data = None
            if execute and sql and valid:
                check_cancelled()
                if on_progress is not None:
                    try:
                        on_progress("execute_start", {"sql": sql})
                    except Exception as exc:
                        logger.debug("Falha ao emitir execute_start do bi_agent: %s", exc)
                data = self.execute_query(sql, contexto_id=str(contexto.id))

            return {
                "sql": sql,
                "valid": valid,
                "explanation": output.get("final_response"),
                "data": data,
                "field_formats": output.get("field_formats", {})
            }
        finally:
            if token is not None:
                reset_cancel_event(token)
