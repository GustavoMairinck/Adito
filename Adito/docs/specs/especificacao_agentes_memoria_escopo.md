# Especificação — Agentes: memória, escopo e barreira de prompt injection

Código em `Adito/app/backend/nucleo/agents/`. Achados e correções detalhados em [`resultados/revisao-agentes-2026-11-18.md`](../resultados/revisao-agentes-2026-11-18.md).

## Fluxo de uma pergunta

```
pergunta ─► detect_injection ──sim──► guard_node (resposta fixa "bloqueada")
               │não
               ▼
            roteador (LLM) ─► intents:
               ├─ blocked / out_of_scope ─► guard_node (resposta fixa, sem LLM)
               ├─ bi_agent ─► uma execução por ferramenta (instruções numeradas) ─► resposta escrita com as linhas
               │                └─► agente de painéis (rpc/chat.py) ─► tipo de gráfico da resposta
               └─ conversational ─► agente de conversa (histórico limitado)
```

`blocked` tem prioridade sobre qualquer outra intent da mesma pergunta.

## Memória

- Toda resposta (conversa, dados e barreira) entra no histórico como `AIMessage`, no checkpointer SQLite por `thread_id`.
- O agente de conversa recebe só as últimas `MAX_HISTORY_MESSAGES` = 12 mensagens; o roteador, as últimas 8 mais a pergunta atual. Em ambos, cada mensagem anterior (do usuário ou do assistente) é cortada em `MAX_MESSAGE_CHARS` = 1500 caracteres.
- O `bi_agent` não recebe o histórico, só a instrução do roteador.

## Escopo

- Dentro: dados de pesquisa e extensão do IFES (qualquer campus ou instituição presente nos dados), saudações e perguntas sobre o próprio Adito.
- Fora (`out_of_scope`): conhecimento geral, código, tarefas pessoais, uso como chatbot genérico.
- O escopo é o tema, não o campus.

## Barreira de prompt injection

1. `orchestrator/guard.py::detect_injection`: regex sem LLM, sobre o texto sem acento e em minúsculas. Pega pedidos para ignorar instruções, revelar o prompt, trocar de papel ("modo desenvolvedor", "finja", "a partir de agora você é") e marcações como `<system>`.
   - "Orientação" e "regra" são termos do domínio. Só bloqueiam quando apontam para o assistente: com possessivo ("suas regras") ou com qualificador ("do sistema", "anteriores", "acima"). "Ignore as orientações de 2020" passa.
   - "Atue como" e "aja como" não entram, porque aparecem em filtros ("em que o docente atue como coordenador").
2. O roteador classifica o resto como `blocked` (regras SECURITY no prompt).
3. A proteção dos dados continua no SQL: só `SELECT`, só as 6 views do contexto, sem `*`, sem referência à linha inteira, sem colunas sensíveis, com `mode=ro` e authorizer no SQLite.

## Resposta de dados

- A SQL roda primeiro; depois um LLM escreve a resposta (registrada no Langfuse como `bi_answer_from_rows`) com a pergunta e até `llm_row_limit` linhas do contexto (`views.json`: 50 em `pesquisa-extensao-ifes`; 20 se não definido).
- Erro de execução vira `fallback`, não tabela.
- O corretor de SQL recebe a pergunta, o esquema e as regras do contexto.

## Gráfico da resposta (agente de painéis)

Código em `agents/dashboard_agent/`, chamado por `rpc/chat.py` antes de gravar a resposta. O tipo vai no evento `result` e nos metadados da mensagem (`chart_type`, `chart_source`), então reabrir a conversa mantém o gráfico. Os tipos são os do Meu painel: `bar`, `horizontal_bar`, `line`, `area` e `pie`.

1. **pedido**: a pergunta diz o tipo ("em pizza", "gráfico de linhas", "barras horizontais"). Regex sem LLM, que ignora "grande área" e "linha de pesquisa".
2. **regra**: o formato dos dados decide, sem LLM. Série no tempo com 3 linhas ou mais vira linhas; rótulo com mais de 20 caracteres ou mais de 12 categorias deita as barras; o resto vira barras.
3. **agente**: só quando há uma categoria (que não é tempo) e uma série sem negativos, com 3 a 8 linhas. Nesse caso barras, barras deitadas e pizza fazem sentido e a intenção da pergunta decide. É uma chamada curta ao LLM (Langfuse: `dashboard_chart_type`), com a pergunta e um resumo (nomes das colunas, número de categorias, tamanho do maior rótulo e fatia da maior categoria), nunca as linhas. Se falhar ou devolver um tipo inválido, vale a regra.

No front, a escolha do usuário vence a sugestão, e a sugestão vence a regra do próprio front. A pizza sugerida para dados que não cabem em pizza abre em barras. Ao fixar no Meu painel, o widget nasce com o tipo que está na tela.

## Removido

- Demonstração de vendas: contexto `exemplo-vendas`, `scripts/gerar_dados_demo.py`, `backend/training/`, `mudanças/`.
- Código morto do orquestrador: `orchestrator/nodes/`, `reflection_agent.py`, `report_agent.py`, `orchestrator/config.py`. Os prompts que valem estão em `agents/config.py`.

## Testes

`core/tests.py`: `AgentesMemoriaEscopoTests` e `AgentesRevisaoTests` (LLM simulado, sem rede).
