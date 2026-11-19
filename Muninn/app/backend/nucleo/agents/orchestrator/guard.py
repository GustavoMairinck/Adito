"""Barreira de escopo e de prompt injection do Muninn.

Duas camadas antes de qualquer agente com acesso a dados:
1. `detect_injection`: filtro determinístico (sem LLM) para tentativas óbvias de sobrescrever
   instruções ou extrair o prompt. É barato e não depende do modelo que está sendo atacado.
2. O roteador classifica o restante (intents `out_of_scope` e `blocked`, ver ORCHESTRATOR_SYSTEM_PROMPT).

Nos dois casos a resposta é fixa (`guard_node`), sem chamar o LLM. A proteção dos dados em si
continua na camada de SQL (agents/bi_agent/sql_security.py + ReadPolicy): só leitura, só as views
expostas, sem `SELECT *` e sem colunas sensíveis. Esta barreira é a primeira linha, não a única.
"""
from __future__ import annotations

import re
import unicodedata

from langchain_core.messages import AIMessage

INTENT_OUT_OF_SCOPE = "out_of_scope"
INTENT_BLOCKED = "blocked"
GUARD_INTENTS = frozenset({INTENT_OUT_OF_SCOPE, INTENT_BLOCKED})

RESPOSTA_FORA_DO_ESCOPO = (
    "Sou o **Muninn** e respondo apenas sobre os dados de pesquisa e extensão do IFES: "
    "projetos e ações, grupos de pesquisa, pesquisadores, orientações, bolsas e produção.\n\n"
    "Quer consultar algo sobre esses temas?"
)

RESPOSTA_BLOQUEADA = (
    "Não posso atender a esse pedido.\n\n"
    "Posso ajudar com consultas sobre os dados de pesquisa e extensão do IFES."
)

# Texto comparado já sem acentos e em minúsculas (ver _normalizar).
#
# "orientação" e "regra" são termos do domínio (orientações de mestrado, regras do edital) e
# "atue/aja como" aparece em filtros ("em que o docente atue como coordenador"). Por isso esses
# termos só contam quando apontam para o próprio assistente: possessivo ("suas regras") ou
# qualificador ("do sistema", "anteriores", "acima"). O roteador (intent `blocked`) cobre o resto.
_VERBO_DESCARTE = r"\b(?:ignor|esquec|desconsider|descart)\w*\s+"
_PALAVRAS = r"(?:\w+\s+){0,3}"
_POSSESSIVO = r"(?:suas?|seus?|teus?|tuas?)\s+"
_QUALIFICADOR = (
    r"\s+(?:do\s+sistema|de\s+sistema|iniciais|originais|previas|acima|"
    r"anteriores(?!\s+(?:a|ao|aos|as|de|do|da|dos|das)\b))"
)
_PADROES_INJECAO = [
    # sobrescrever instruções (pt)
    _VERBO_DESCARTE + _PALAVRAS + r"(?:instruc(?!\w*\s+normativ)|prompt|diretriz)\w*",
    _VERBO_DESCARTE + _PALAVRAS + _POSSESSIVO + r"(?:\w+\s+)?(?:regra|orientac)\w*",
    _VERBO_DESCARTE + _PALAVRAS + r"(?:regra|orientac)\w*" + _QUALIFICADOR,
    # sobrescrever instruções (en)
    r"\b(?:ignore|disregard|forget|override)\s+(?:\w+\s+){0,3}(?:instructions?|prompt)",
    r"\b(?:ignore|disregard|forget|override)\s+(?:\w+\s+){0,2}(?:your|previous|prior|above|system)\s+rules",
    # extrair o prompt
    r"\b(?:system\s*prompt|prompt\s+(?:do\s+)?sistema|instrucoes\s+(?:do\s+)?sistema)",
    r"\b(?:mostr|revel|exib|imprim|repit|repet|copi|reveal|show|print|repeat)\w*\s+"
    r"(?:\w+\s+){0,4}(?:(?:seu|seus|sua|suas|teu|tuas|your)\s+(?:instruc\w*|instructions?|regras|rules)|prompt)",
    # trocar de papel
    r"\b(?:modo|mode)\s+(?:desenvolvedor|developer|dan|jailbreak|deus|god|irrestrito|sem\s+restric\w*)\b",
    r"\bjailbreak\b",
    r"\ba\s+partir\s+de\s+agora\s+(?:voce\s+)?(?:e|sera|vai\s+ser|age|atua|responde)\b",
    r"\b(?:finja|finge|pretend|act\s+as)\b",
    # marcação imitando mensagens de sistema
    r"</?\s*(?:system|instructions?|prompt)\s*>",
    r"\[\s*(?:system|sistema)\s*\]",
]
_RE_INJECAO = re.compile("|".join(_PADROES_INJECAO))


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sem_acento.lower())


def detect_injection(texto: str | None) -> bool:
    """True quando o texto tenta sobrescrever as instruções, trocar o papel do agente ou extrair o prompt."""
    if not texto:
        return False
    return bool(_RE_INJECAO.search(_normalizar(texto)))


async def guard_node(state: dict) -> dict:
    """Resposta fixa para pedidos fora do escopo ou bloqueados; fica registrada no histórico."""
    bloqueado = state.get("tool_name") == INTENT_BLOCKED
    texto = RESPOSTA_BLOQUEADA if bloqueado else RESPOSTA_FORA_DO_ESCOPO
    print(f"[Guard] {'bloqueado' if bloqueado else 'fora do escopo'}: {str(state.get('user_input', ''))[:80]!r}")
    return {
        "messages": [AIMessage(content=texto)],
        "final_response": texto,
        "text_response": texto,
        "analysis_explanation": None,
        "sql_used": None,
        "graph": None,
        "type": "chat",
        "score": None,
        "message": None,
        "suggestions": [],
        "related_attributes": [],
    }
