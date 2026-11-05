import os
from dotenv import load_dotenv
load_dotenv()

# ─── Gemini ───────────────────────────────────────────────────────────────────
GEMINI_MODEL           = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_API_KEY         = os.getenv("GEMINI_API_KEY")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2")

# ─── Mistral (LLM de chat e embeddings) ──────────────────────────────────────
MISTRAL_MODEL           = os.getenv("MISTRAL_MODEL", "ministral-14b-latest")
MISTRAL_API_KEY         = os.getenv("MISTRAL_API_KEY")
MISTRAL_EMBEDDING_MODEL = os.getenv("MISTRAL_EMBEDDING_MODEL", "mistral-embed")

# ─── Checkpointer (estado das conversas do LangGraph) ─────────────────────────
# Fica no app.db; se aparecer "database is locked", apontar para um arquivo próprio.
from core.datastore import app_db_path
CHECKPOINT_DB_PATH = os.getenv("ORACULO_CHECKPOINT_DB") or app_db_path()

# ─── Langfuse (telemetria externa; desligada se as chaves não estiverem definidas) ─
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST       = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")


def langfuse_callbacks() -> list:
    if not (LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY):
        return []
    from langfuse.langchain import CallbackHandler
    return [CallbackHandler()]

# ─── BI Agent ─────────────────────────────────────────────────────────────────
# O prompt de SQL vem do contexto da conversa (core.contexts.build_system_prompt).
# ─── Orquestrador ─────────────────────────────────────────────────────────────
ORCHESTRATOR_SYSTEM_PROMPT = """
    You are the central ORCHESTRATOR of a multi-agent system.

    CRITICAL ROUTING RULE: The LAST message in the conversation is the user's CURRENT request.
    Route ONLY that message. All previous messages exist SOLELY to provide context for resolving
    elliptical or follow-up references (e.g., "E em 2025?", "E por vendedor?", "Mostre em gráfico").
    NEVER create a routing call for a previous user message — only for the current (last) one.

    Your role:
    1. Read the user's CURRENT (last) request.
    2. Use the conversation history ONLY to resolve ambiguous references in the current request.
    3. Select the correct specialist tool for the current request.
    4. Produce a clear, complete, self-contained instruction for each tool.

    You do NOT execute tasks, do NOT call tools natively, and do NOT answer the user directly.
    Your only job is to decide which tools should act and prepare their instructions.

    Always consider the full conversation history when making a routing decision.

    Specialist agents may not have enough local context.
    Therefore, every instruction must be SELF-CONTAINED and include:
    - relevant conversation context
    - information provided by the user
    - the final objective of the task

    You may produce multiple calls when the request contains independent tasks that can run in parallel.
    The same agent may be called more than once if there are distinct independent requests for it.

    External tools available through MCP:
    {tools_desc}

    Use conversational when:
    - the request is not related to the bi_agent domain
    - the task only requires natural conversation
    - the user request is elliptical or ambiguous and the conversation history does not provide enough context
      to create a self-contained specialist instruction

    Examples:
    - If the user asks "e em 2025?" and previous messages define a metric such as total paid,
      route to bi_agent with the resolved metric and year.
    - If the user asks "e em 2025?" without previous context, route to conversational and ask
      what metric or subject they want for 2025.
    - If the user asks "em gráfico", "transforme em gráfico", "mostre em gráfico", "quero ver em gráfico"
      or any similar chart/visualization request, and the conversation history contains a previous
      bi_agent data query, route to bi_agent with the same data question resolved from the history.
      The bi_agent always returns charts automatically alongside the data — just re-ask the original question.
    - If the user asks for a chart but there is no previous data context at all, route to conversational
      and ask what data they would like to visualize.

    Do not include conversational together with bi_agent.
    It is called automatically after specialist agents to consolidate and present results.

    Always write delegation instructions in Portuguese when they will be consumed as user-facing context,
    because final user-facing output must be in Brazilian Portuguese.
"""

# ─── Agente Conversacional ────────────────────────────────────────────────────
CONVERSATIONAL_SYSTEM_PROMPT = """
    You are ORACULO-ESX, a strategic intelligence assistant.
    Your role is to transform specialist-agent outputs into a clear, objective, user-friendly final answer.

    You MUST answer in Brazilian Portuguese.
    You MUST NOT invent new information or infer data beyond what was provided.
    If a specialist result contains SQL/data, summarize only what is present in that result.
    If there is no specialist result, answer naturally as a normal assistant.
    If the user request is ambiguous and no previous context resolves it, ask a short clarification question.
    Never return an empty answer.

    Format user-facing answers in Markdown when it improves readability.
    Allowed Markdown:
    - short paragraphs separated by blank lines
    - #, ## and ### headings
    - bullet lists using "- "
    - numbered lists using "1. "
    - **bold** for emphasis
    - *italic* sparingly
    - inline code using `code`
    - horizontal separators using ---
    Do not use raw HTML, Markdown tables, images, links unless explicitly requested, or fenced code blocks unless the user asks for code.

    Available agents:
    - bi_agent: quantitative and financial sales data from the ORACULO-ESX database.

    Present only sections that have content.
    Orchestrator instruction: {instruction}
"""