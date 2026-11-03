import psycopg2
import psycopg2.extras
from typing import Optional, List, Any
from langchain_core.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from .graph import build_graph

class BIAgent:
    def __init__(
        self,
        dsn: str,
        llm_model: BaseChatModel,
        embedder: Embeddings,
        dialect: str = "postgres",
        validate_sql: bool = True,
        max_attempts: int = 2,
        system_prompt: str = "",
        checkpointer=None,
        callbacks: List[Any] = None,
    ):
        self.dsn = dsn
        self.system_prompt = system_prompt
        
        workflow = build_graph(dsn, llm_model, embedder, dialect, validate_sql, max_attempts)
        self.app = workflow.compile(checkpointer=checkpointer)
        
        if callbacks:
            self.app = self.app.with_config({"callbacks": callbacks})

    def execute_query(self, sql: str, schema: str = None, max_rows: int = 100) -> List[dict]:
        """Executa a query SQL filtrando pelo schema analítico (Tenant)."""
        try:
            clean_sql = sql.strip().rstrip(';')
            with psycopg2.connect(self.dsn) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    if schema:
                        cur.execute(f"SET search_path TO {schema}")
                    cur.execute(f"SELECT * FROM ({clean_sql}) AS sub LIMIT {max_rows}")
                    rows = [dict(r) for r in cur.fetchall()]
            
            if rows and all(v is None for r in rows for v in r.values()):
                return []
            return rows
        except Exception as e:
            print(f"[x] Erro na execução final: {e}")
            return [{"error": str(e)}]

    def ask(self, question: str, tenant_id: str, db_schema_name: str, thread_id: str, callbacks: Optional[List[Any]] = None, execute: bool = False) -> dict:
        """Processa a pergunta do usuário no contexto de um Tenant específico."""
        config = {
            "configurable": {"thread_id": thread_id}, 
            "callbacks": callbacks,
            "metadata": {
                "langfuse_session_id": thread_id
            }
        }
        
        input_data = {
            "user_input": question,
            "tenant_id": str(tenant_id),
            "db_schema_name": db_schema_name,
            "messages": [HumanMessage(content=question)],
            "system_prompt": self.system_prompt
        }
        
        output = self.app.invoke(input_data, config=config)
        
        sql = output.get("generated_sql")
        valid = output.get("validation_result", {}).get("valid", False)
        
        data = None
        if execute and sql and valid:
            data = self.execute_query(sql, schema=db_schema_name)
                
        return {
            "sql": sql,
            "valid": valid,
            "explanation": output.get("final_response"),
            "data": data,
            "field_formats": output.get("field_formats", {})
        }
