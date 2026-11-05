from typing import Optional, List, Any
from langchain_core.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from core.contexts import build_system_prompt, get_contexto, read_policy_for
from core.datastore import connect_dados

from .graph import build_graph

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
        """Executa a query no dados.db (só leitura) com a política do contexto. Sem max_rows, devolve todas as linhas."""
        try:
            clean_sql = sql.strip().rstrip(';')
            if max_rows is not None:
                clean_sql = f"SELECT * FROM ({clean_sql}) AS sub LIMIT {int(max_rows)}"
            with connect_dados(read_policy_for(contexto_id), self.dados_path) as conn:
                rows = [dict(r) for r in conn.execute(clean_sql).fetchall()]

            if rows and all(v is None for r in rows for v in r.values()):
                return []
            return rows
        except Exception as e:
            print(f"[x] Erro na execução final: {e}")
            return [{"error": str(e)}]

    def ask(self, question: str, tenant_id: str, contexto_id: str, thread_id: str, callbacks: Optional[List[Any]] = None, execute: bool = False) -> dict:
        """Processa a pergunta do usuário dentro de um contexto (views, regras e RAG do contexto)."""
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

        output = self.app.invoke(input_data, config=config)

        sql = output.get("generated_sql")
        valid = output.get("validation_result", {}).get("valid", False)

        data = None
        if execute and sql and valid:
            data = self.execute_query(sql, contexto_id=str(contexto.id))

        return {
            "sql": sql,
            "valid": valid,
            "explanation": output.get("final_response"),
            "data": data,
            "field_formats": output.get("field_formats", {})
        }
