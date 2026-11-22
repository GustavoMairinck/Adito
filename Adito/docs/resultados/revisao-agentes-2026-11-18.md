# Revisão dos agentes do Adito — 2026-11-18

Escopo: `Adito/app/backend/nucleo/agents/` (orquestrador e `bi_agent`) e a integração em `rpc/chat.py`, na branch `feat/agentes-memoria-escopo` (commit `1bd928f`). Revisão de código com verificação: testes com LLM simulado e consultas só leitura numa cópia do `app.db` e no `dados.duckdb` local.

Legenda: **Confirmado** = reproduzido; **Por código** = deduzido da leitura, não reproduzido.

> **Status:** todos os achados (1 a 9) foram corrigidos na mesma branch, com testes em `core/tests.py::AgentesRevisaoTests`:
> - 1: chamadas à mesma ferramenta viram uma, com as instruções numeradas;
> - 2: o estado da busca passa a ser por execução (`ContextVar`);
> - 3 e 8: a resposta é escrita depois da execução, com até `llm_row_limit` linhas;
> - 4: o validador bloqueia referência à linha inteira;
> - 5: o prompt do resolvedor foi reescrito para pesquisa e extensão;
> - 6: erro de execução vira `fallback`;
> - 7: o corretor recebe a pergunta e o contexto;
> - 9: o código parado foi removido.
>
> O item 3 acrescenta uma chamada ao LLM por pergunta de dados.
>
> **Depois do PR #63 (banco em SQLite):** a revisão foi feita com o `dados.duckdb`. No SQLite, o achado 4 não se reproduz (`SELECT p FROM … p` dá "no such column"); o bloqueio no validador fica como defesa caso o motor mude. Os demais achados não dependem do motor.

## Achados

### 1. Alta — Com duas chamadas ao `bi_agent`, o usuário recebe só uma resposta (Confirmado)
O roteador pode gerar várias chamadas ("You may produce multiple calls…"), que rodam em paralelo. Mas os campos de resultado do estado (`final_response`, `graph`, `sql_used`) usam o redutor `prefer_new` (`orchestrator/state.py`), então a última escrita apaga as outras. Além disso, `rpc/chat.py` emite só o primeiro resultado (`has_emitted_result`).

Reprodução (roteador simulado com "contar projetos" e "contar grupos"): o estado final ficou só com `Resposta contar grupos`, `SELECT 7` e `[{'total': 7}]`. O resultado de projetos sumiu da resposta, embora as duas mensagens estejam no histórico.

Caminho: ou limitar o roteador a uma chamada de dados por pergunta, ou acumular os resultados (lista) e mostrar todos.

### 2. Alta — Condição de corrida na busca de valores com chamadas paralelas (Por código)
`bi_agent/tools/vector_search.py` guarda o contexto, o embedder e os candidatos em variáveis globais do módulo. `configure_vector_search()` zera essas listas a cada execução. Duas execuções do `bi_agent` em threads paralelas (o caso do achado 1) podem apagar ou misturar os candidatos uma da outra, o que leva a reescritas e filtros errados.

Caminho: passar o estado da busca por execução (closure ou objeto por chamada), sem globais.

### 3. Média — O texto da resposta de dados é escrito antes de a SQL rodar (Confirmado no código)
`sql_generator` pede ao LLM a SQL e uma `explanation` na mesma chamada. Essa explicação vira `final_response` e é o texto exibido ao usuário (`tool.py` → `mcp_tool_node` → `build_final_result`). O LLM nunca vê o resultado da consulta. Por isso:
- as respostas descrevem a consulta ("Aqui está o levantamento…") em vez de responder;
- números citados no texto vêm do contexto da conversa, não do resultado, e podem não bater;
- em `build_final_result`, o `final_response` vem antes da `scalar_answer` (o valor calculado a partir dos dados), então a resposta numérica correta fica escondida.

O prompt do roteador diz que o conversacional "is called automatically after specialist agents to consolidate", mas o grafo não faz isso: quando há `bi_agent`, o conversacional não roda.

Caminho: um passo de resposta depois da execução, que recebe a pergunta e a prévia das linhas (respeitando o limite do contexto). Ou, no mínimo, priorizar a `scalar_answer`.

### 4. Média — Referenciar o alias da tabela contorna o bloqueio de `SELECT *` (Confirmado)
`SELECT p FROM vfact_extensao_participacao_resolved p` e `SELECT to_json(p) … p` passam no `validate_read_only_sql` e devolvem a linha inteira, como um `SELECT *`. Testado no `dados.duckdb` local. Hoje não vaza CPF nem e-mail porque as views não têm essas colunas (o ETL já as remove), mas o bloqueio de `*` existe justamente para o caso de uma view ganhar uma coluna sensível não declarada.

Caminho: rejeitar `exp.Column` cujo nome coincide com um alias ou nome de tabela da consulta, e funções que recebem a linha inteira (`to_json`, `struct_pack`, `row`).

### 5. Média — Prompt do resolvedor de valores ainda é de vendas (Confirmado no código)
`BI_VALUE_RESOLVER_SYSTEM_PROMPT` (`bi_agent/config.py`) manda buscar só "product names, client names, sales channels, salesperson names…", com exemplos como "CRM Premium" e "Metalúrgica Vitória". No domínio atual, as entidades são pesquisadores, orientadores, grupos, projetos, áreas e programas. Nomes aproximados de pessoas e grupos podem não ser buscados, e o SQL filtra com o texto errado.

Caminho: trocar os tipos e os exemplos para o domínio de pesquisa e extensão.

### 6. Baixa — Erro na execução vira "dado" com tipo `analysis` (Por código)
`bi_agent/agent.py::execute_query` devolve `[{"error": "…"}]` em caso de exceção. Isso conta como linha de resultado: `type="analysis"` e a tabela mostra a mensagem de erro do banco ao usuário.

### 7. Baixa — O corretor de SQL não recebe a pergunta nem o esquema (Por código)
`sql_corrector` envia só a SQL errada, o erro e os nomes das views. Sem a pergunta e sem as colunas, a correção pode mudar o significado da consulta ou repetir o erro até esgotar as tentativas.

### 8. Baixa — `llm_row_limit` do contexto não é usado (Confirmado no código)
`views.json` aceita `llm_row_limit` e `core/contexts.py::row_limit_for` existe, mas nada chama essa função. A prévia enviada ao LLM é fixa em 5 linhas (`bi_agent/tool.py::PREVIEW_ROWS`).

### 9. Baixa — Código parado no orquestrador (Confirmado)
`orchestrator/nodes/` (roteador ReAct, reflection, relatório, conversacional duplicado), `reflection_agent.py`, `report_agent.py` e `orchestrator/config.py` não estão ligados ao `graph.py`. O fluxo de relatório (`requires_report`) é inalcançável, porque `RouterDecision` em `models.py` nem tem esse campo. `rpc/chat.py` ainda cita `report_agent`. Isso confunde quem edita prompts: os que valem estão em `agents/config.py`.

## Já corrigido nesta branch
- Respostas do conversacional não entravam no histórico, e o agente respondia de novo perguntas anteriores.
- Escopo (`out_of_scope`) e barreira de prompt injection (`blocked` + filtro determinístico).

## O que está bem
- A validação de SQL é sólida e roda duas vezes (no agente e na execução, via `ReadPolicy`). Ela bloqueia:
  - escrita e administração;
  - leitura de arquivos (`read_csv`, `glob` etc.);
  - prefixo de schema e tabelas fora da lista;
  - colunas com `cpf` ou `email`.
- O ETL já entrega as views sem CPF e e-mail.
- O `bi_agent` não recebe o histórico, só a instrução do roteador. Isso reduz a superfície de injeção vinda de mensagens antigas.

## Prioridade sugerida
1. Achados 1 e 2 juntos: mesma causa (chamadas paralelas).
2. Achado 3: maior impacto na qualidade das respostas.
3. Achados 4 e 5.
4. Achados 6 a 9, num PR de limpeza.
