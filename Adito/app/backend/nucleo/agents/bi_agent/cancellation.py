"""Sinalização cooperativa de cancelamento por execução do agente de BI.

Usa `ContextVar` para isolar o `threading.Event` de cada requisição concorrente
(propagado automaticamente para threads via `asyncio.to_thread`) sem poluir o
estado serializado pelo checkpointer SQLite do LangGraph.
"""
from __future__ import annotations

from contextvars import ContextVar, Token
import threading


class BIAgentCancelled(Exception):
    """Sinaliza cancelamento cooperativo de uma execução do agente de BI."""


_cancel_event_var: ContextVar[threading.Event | None] = ContextVar("bi_agent_cancel_event", default=None)


def set_cancel_event(event: threading.Event | None) -> Token[threading.Event | None]:
    return _cancel_event_var.set(event)


def reset_cancel_event(token: Token[threading.Event | None]) -> None:
    _cancel_event_var.reset(token)


def get_cancel_event() -> threading.Event | None:
    return _cancel_event_var.get()


def check_cancelled(event: threading.Event | None = None) -> None:
    active = event if event is not None else _cancel_event_var.get()
    if active is not None and active.is_set():
        raise BIAgentCancelled("Execução cancelada pelo usuário.")
