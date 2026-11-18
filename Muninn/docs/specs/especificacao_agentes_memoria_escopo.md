# Especificação — Agentes: memória, escopo e barreira de prompt injection

Código em `Muninn/app/backend/nucleo/agents/`. Achados e correções detalhados em [`resultados/revisao-agentes-2026-11-18.md`](../resultados/revisao-agentes-2026-11-18.md).

## Fluxo de uma pergunta

```
pergunta ─► detect_injection ──sim──► guard_node (resposta fixa "bloqueada")
               │não
               ▼
            roteador (LLM) ─► intents:
               ├─ blocked / out_of_scope ─► guard_node (resposta fixa, sem LLM)
               ├─ bi_agent ─► uma execução por ferramenta (instruções numeradas) ─► resposta escrita com as linhas
               └─ conversational ─► agente de conversa (histórico limitado)
```

`blocked` tem prioridade sobre qualquer outra intent da mesma pergunta.

## Memória

- Toda resposta (conversa, dados e barreira) entra no histórico como `AIMessage`, no checkpointer SQLite por `thread_id`.
- O agente de conversa recebe só as últimas `MAX_HISTORY_MESSAGES` = 12 mensagens, cada uma cortada em `MAX_MESSAGE_CHARS` = 1500 caracteres.
- O `bi_agent` não recebe o histórico, só a instrução do roteador.

## Escopo

- Dentro: dados de pesquisa e extensão do IFES (qualquer campus ou instituição presente nos dados), saudações e perguntas sobre o próprio Muninn.
- Fora (`out_of_scope`): conhecimento geral, código, tarefas pessoais, uso como chatbot genérico.
- O escopo é o tema, não o campus.

## Barreira de prompt injection

1. `orchestrator/guard.py::detect_injection`: regex sem LLM, sobre o texto sem acento e em minúsculas. Pega pedidos para ignorar instruções, revelar o prompt, trocar de papel ("modo desenvolvedor", "finja", "a partir de agora você é") e marcações como `<system>`.
2. O roteador classifica o resto como `blocked` (regras SECURITY no prompt).
3. A proteção dos dados continua no SQL: só `SELECT`, só as 6 views do contexto, sem `*`, sem referência à linha inteira, sem colunas sensíveis, com `mode=ro` e authorizer no SQLite.

## Resposta de dados

- A SQL roda primeiro; depois um LLM escreve a resposta com a pergunta e até `llm_row_limit` linhas do contexto (`views.json`: 50 em `pesquisa-extensao-ifes`; 20 se não definido).
- Erro de execução vira `fallback`, não tabela.
- O corretor de SQL recebe a pergunta, o esquema e as regras do contexto.

## Removido

- Demonstração de vendas: contexto `exemplo-vendas`, `scripts/gerar_dados_demo.py`, `backend/training/`, `mudanças/`.
- Código morto do orquestrador: `orchestrator/nodes/`, `reflection_agent.py`, `report_agent.py`, `orchestrator/config.py`. Os prompts que valem estão em `agents/config.py`.

## Testes

`core/tests.py`: `AgentesMemoriaEscopoTests` e `AgentesRevisaoTests` (LLM simulado, sem rede).
