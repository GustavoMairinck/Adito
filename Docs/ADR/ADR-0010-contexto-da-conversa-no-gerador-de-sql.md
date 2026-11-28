# ADR 0010: Contexto da Conversa até o Gerador de SQL

**Status:** Proposto (em teste no fork; falta o reteste numa conversa nova)  
**Data:** 28/11/2026

## Contexto/Problema
O orquestrador reescreve cada pergunta como uma instrução para o BI Agent. O gerador de SQL só via essa instrução em texto. O SQL da resposta anterior ficava no estado do grafo (`sql_used`) e não chegava ao BI Agent. Em perguntas que dependem da anterior ("desses", "esses", "e na Serra?"), o gerador precisava reconstruir o grupo a partir de uma frase.

O teste de 27 e 28/11/2026 no `dados.db` real, com três perguntas na mesma conversa, mostrou três falhas:

1. **"quantos pesquisadores tem no campus serra"** deu 111, que está certo.
2. **"quantos desses participaram de extensões?"** deu 5.160 na primeira versão, porque o filtro de pesquisadores se perdeu. O certo é 60, ou 69 contando quem coordenou ação de extensão.
3. **"Todos esses já foram pesquisadores?"** levou 6 min 50 s e depois deu uma resposta invertida:
   - **A demora:** o SQL cruzava as pessoas com `LIKE '%' || coluna || '%'`, que no Adito roda numa função Python e não usa índice.
   - **A resposta invertida:** o orquestrador citou "os 69", mas o gerador partiu das 5.178 pessoas de extensão do Serra e contou quantas eram pesquisadoras (70). A resposta certa era "sim, todos os 69".

## Decisão Tomada
1. **A pergunta do usuário viaja junto com a instrução do orquestrador** até o gerador. O pedido ao modelo diz para usar a instrução para saber a quem a pergunta se refere e manter os filtros da conversa, sem acrescentar filtros que não estejam em nenhuma das duas (commit `629fe1c`).
2. **O gerador recebe o SQL da resposta anterior.** O orquestrador manda o `sql_used` do turno anterior como `sql_anterior` para o `bi_agent`. Ele passa pelo estado do BI Agent até `pergunta_para_o_modelo` (`sql_generator.py`), que o anexa ao pedido com esta orientação:
   - se a pergunta se refere ao resultado anterior, reaproveite esse SQL como CTE e parta do mesmo conjunto, sem inverter o ponto de partida;
   - se a pergunta for de outro assunto, ignore-o.
   - O corretor usa a mesma função e recebe o mesmo bloco. Depois de uma resposta conversacional ou bloqueada, o `sql_used` volta a `None` e nada é anexado (commit `22f515c`).
3. **Cruzar pessoas entre views compara o nome exato normalizado.** Uma regra no `rules.md` do contexto `pesquisa-extensao-ifes` manda montar CTEs com `DISTINCT LOWER(TRIM(nome))` e comparar com `IN`, nunca com `LIKE '%' || coluna || '%'`. A regra de busca por nome com `LIKE` vale só para o nome digitado na pergunta (commit `629fe1c`).

## Justificativa
1. **O problema era falta de contexto, não de regra.** Sem o SQL anterior, o gerador não tem como saber quais filtros definiram "os 69". Uma regra a mais no `rules.md` não entrega essa informação.
2. **O `rules.md` já está grande.** São cerca de 1.650 palavras (uns 4 mil tokens), que vão inteiras em toda chamada ao gerador. O texto mais que dobrou desde 13/11/2026, quase sempre com remendos. Passar o SQL anterior não acrescenta nenhuma palavra ao `rules.md`.
3. **Mudança pequena e no padrão existente:** o `sql_anterior` segue o mesmo caminho do `pergunta_original` (orquestrador → ferramenta → estado do BI Agent → pedido ao modelo).
4. **Nome exato é rápido e correto:** a versão com `IN` sobre nomes normalizados volta em segundos. Ela deu 109 onde o `LIKE` com coluna dava 110, com um nome parcial casado por engano.

## Alternativas Consideradas
* **Só uma regra no `rules.md` para "esses/desses" (cerca de 40 a 70 palavras):** descartada a pedido do Gustavo. Depende de o orquestrador descrever bem o grupo e aumenta um arquivo que já está grande.
* **Validador recusar `LIKE` com coluna e limite de tempo de 30 s no SQL:** descartada pelo Gustavo. A regra de nome exato resolveu a demora sem bloquear consultas.
* **Reexecutar o SQL anterior e passar o resultado (linhas) ao gerador:** descartada. Custa uma consulta a mais por pergunta e aumenta muito o prompt quando o resultado é grande. O SQL já descreve o grupo.
* **Guardar o histórico de todos os SQLs da conversa:** descartada por ora. O caso que falhou só precisa do turno anterior.

## Consequências
* **Positivas:** perguntas encadeadas partem do mesmo grupo da resposta anterior; o `rules.md` não cresce; cruzamento de pessoas volta em segundos.
* **Negativas:** o pedido ao gerador fica maior em toda pergunta que vem depois de uma consulta, porque leva o SQL anterior inteiro. Os testes automáticos conferem que o SQL chega ao gerador, mas não chamam LLM. Que a resposta fica certa só se confere no app.
* **Riscos:**
  - *SQL anterior errado contamina a pergunta seguinte:* se a resposta anterior estava errada, o gerador continua a partir dela. Isso aconteceu no teste das 12:25 de 28/11/2026, feito na mesma conversa que já tinha o SQL invertido. **Mitigação:** testar numa conversa nova; o usuário pode refazer a pergunta anterior para corrigir a base.
  - *Pergunta de outro assunto herdando filtros:* o modelo pode usar o SQL anterior quando não devia. **Mitigação:** o pedido diz para ignorá-lo quando a pergunta não se refere ao resultado anterior.
  - *Conclusão sobre "todos" a partir de uma amostra:* quem escreve a resposta (`answer_from_rows` em `tool.py`) vê só as primeiras linhas do resultado. Num resultado longo e ordenado, pode generalizar errado, como no "Sim, todos" das 12:25, em que só 70 das 5.178 linhas eram "Sim". Isso já acontecia antes desta decisão e fica para uma mudança separada, se aprovada.

## Referências
* [ADR 0009: Embeddings Locais Gerados na Publicação do `dados.db`](./ADR-0009-embeddings-locais-no-dados-db.md) (decisão 6: pergunta original até o gerador)
* Commits `629fe1c` e `22f515c` no branch `feat/embeddings-locais` do fork
* `Adito/app/backend/nucleo/agents/bi_agent/nodes/sql_generator.py` (`pergunta_para_o_modelo`)
* `Adito/app/backend/nucleo/agents/orchestrator/graph.py` (`sql_anterior` a partir de `sql_used`)
* `Adito/app/contexts/pesquisa-extensao-ifes/rules.md`, seção 3, "Cruzar pessoas entre views"
