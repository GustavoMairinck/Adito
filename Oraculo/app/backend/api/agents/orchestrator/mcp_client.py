from langchain_mcp_adapters.client import MultiServerMCPClient
from contextlib import asynccontextmanager
from datetime import timedelta
from agents.config import ORACULO_MCP_URL
import os


@asynccontextmanager
async def get_mcp_client(timeout: int = None):
    """
    Get MCP client with timeout and error handling.
    
    timeout: seconds to wait for MCP server connection (default: 60)
    """
    if timeout is None:
        timeout = int(os.getenv("MCP_CLIENT_TIMEOUT_SECONDS", "60"))
    
    try:
        client = MultiServerMCPClient(
            {
                "bi_agent": {
                    "url": ORACULO_MCP_URL,
                    "transport": "streamable_http",
                    "timeout": timedelta(seconds=timeout),
                }
            },
        )
        yield client
    except Exception as e:
        print(f"[MCP Client] Erro ao conectar ao servidor MCP ({ORACULO_MCP_URL}): {e}")
        # Return a dummy client that won't crash the chat
        class DummyMCPClient:
            async def get_tools(self):
                return []
        yield DummyMCPClient()
