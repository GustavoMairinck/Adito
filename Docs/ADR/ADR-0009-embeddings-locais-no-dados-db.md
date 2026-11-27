# ADR 0009: Embeddings Locais Gerados na Publicação do `dados.db`

**Status:** Proposto (em teste no fork; modelo escolhido em 27/11/2026, falta a segunda rodada do teste de busca)  
**Data:** 27/11/2026

## Contexto/Problema
O RAG do Adito gerava embeddings pela API do provedor de IA ativo (Gemini, OpenAI, Mistral...). A análise de 27/11/2026 (`/mnt/project-files/embeddings/analise-fluxo-resposta-embeddings.md`) apontou quatro problemas:

1. **Custo e cota:** cada usuário embedava na própria máquina todos os valores distintos das `embed_columns` (milhares de títulos), o que gastava a cota diária do Gemini antes da primeira pergunta.
2. **Vetores incompatíveis:** trocar de provedor ou de modelo invalidava o índice (dimensão ou espaço vetorial diferentes) e pedia "Wipe & Retrain".
3. **Vetores sem uso:** o DDL e as regras eram buscados por similaridade e cortados, mas o `system_prompt` já levava os dois inteiros. O resolvedor de valores era um agente ReAct que decidia sozinho se buscava.
4. **Instabilidade:** a mesma pergunta feita duas vezes dava respostas muito diferentes. Contribuíam a cadeia de 5 a 7 chamadas de LLM, o rewriter que reescrevia a pergunta e o resolvedor ReAct.

## Decisão Tomada
1. **Um modelo de embedding local e único**, rodando em CPU pelo `fastembed` (ONNX, int8). O app não troca de modelo e não tem tela para isso. O modelo é o `e5-small-int8` (`intfloat/multilingual-e5-small`, 384 dimensões), escolhido pela comparação no `dados.db` real (US-EMB-05). A chave fica em `analytics_index/modelo_local.py` (`MODELO_PADRAO`).
2. **Os vetores dos valores vão prontos dentro do `dados.db`.** O `publicar_dados.sh` roda `scripts/gerar_embeddings_dados.py` numa cópia do banco antes de cifrar. O script faz `SELECT DISTINCT` por coluna das `embed_columns`, quebra as `multi_valor_columns` em `; ` e grava `adito_valor_embedding` (float16, normalizado) e `adito_embedding_meta` (modelo, dimensão, data). Essas tabelas ficam fora das `exposed_views`, então o validador de SQL não deixa a LLM ler delas.
3. **O modelo é baixado como o `dados.db`, mas sem criptografia**, da mesma release `dados`: `modelo.json` (chave, tamanho e SHA-256) mais `modelo-<chave>-<sha12>.tar.gz`. O app confere o hash, extrai em `data_dir()/models/<chave>/` e carrega em segundo plano na abertura. Quem publica os dados também publica o modelo, e só quando a chave muda.
4. **Modelo diferente nos vetores desliga a busca semântica.** O app não tenta reaproveitar nem converter vetores. O painel admin avisa ("Busca semântica de valores desligada"). Sinônimos e valores idênticos continuam funcionando.
5. **Sai toda chamada de embedding por API.** Os exemplos do `examples.json` e os itens manuais são embedados na máquina, com cache em memória. DDL e regras não passam por busca.
6. **O resolvedor ReAct e o rewriter saem do grafo.** No lugar deles entra `value_resolver`, um código determinístico: n-gramas da pergunta, depois `sinonimos.json` do contexto, depois valor idêntico do catálogo, depois similaridade no índice local de pelo menos 0,90, e o valor ainda precisa ter letras em comum com o termo (`parecido_em_letras` de pelo menos 0,75), o que corta falsos positivos como "futebol" virando um título. Os valores achados vão num bloco à parte do prompt, e a pergunta original do usuário viaja junto com a instrução do orquestrador até o gerador.
7. **O validador recusa filtro com valor que não existe** nas colunas indexadas, sugere o valor mais próximo e manda para o corretor uma vez.

## Justificativa
1. **Custo zero de API para busca:** nenhum token é gasto em embeddings, nem na publicação nem no uso.
2. **Vetores iguais para todo mundo:** todos usam o mesmo modelo e os mesmos vetores, gerados uma vez por carga, então não existe mais índice incompatível por usuário.
3. **Menos variação:** duas chamadas de LLM saem do caminho (rewriter e ReAct), e a busca de valores passa a ser determinística. A mesma pergunta acha os mesmos valores.
4. **O modelo de LLM não afeta os vetores:** a busca não depende do provedor que o usuário escolhe para o chat.

## Alternativas Consideradas
* **Continuar com embeddings por API, com cache e cota:** descartada. Mantém o custo e a dependência do provedor e não resolve a incompatibilidade entre provedores.
* **Gerar os vetores na máquina do usuário na primeira abertura:** descartada. Leva minutos de CPU em máquinas fracas e cada usuário poderia ficar com um índice diferente.
* **Busca só lexical (sem vetores):** fica como piso (sinônimos e valores idênticos), mas não cobre erro de digitação nem variações de títulos.
* **Vários modelos com seletor na tela:** descartada a pedido do Gustavo. Um modelo só, escolhido pela comparação.
* **Embutir o modelo no instalador:** descartada. Aumenta o instalador em 100 MB a 600 MB e obriga a republicar o app para trocar o modelo.

## Consequências
* **Positivas:** sem gasto de tokens com busca; vetores consistentes; o grafo perde duas chamadas de LLM; o painel mostra se a busca semântica está ligada e por quê.
* **Negativas:** o `dados.db` cresce, cerca de 0,8 KB por valor com 384 dimensões em float16. Há mais um download na primeira abertura (o modelo) e mais uma etapa na publicação. O núcleo empacotado passa a levar `onnxruntime` e `tokenizers`.
* **Riscos:**
  - *Limite de similaridade mal calibrado:* aceita valor errado ou perde o certo. **Mitigação:** `scripts/teste_busca_valores.py` mede acerto e falso positivo por limite. O valor fica em `ADITO_VALOR_SIMILARIDADE_MIN` até a calibração.
  - *Modelo do app diferente do modelo dos vetores:* a busca semântica desliga e o painel avisa. **Mitigação:** o `publicar_dados.sh` usa a chave do próprio app.
  - *Download do modelo bloqueado (rede institucional):* o chat segue com sinônimos, valores idênticos e os primeiros exemplos.

## Referências
* [ADR 0006: Empacotamento Desktop sem Privilégio de Admin e Auto-Update Assistido](./ADR-0006-empacotamento-e-auto-update-desktop.md)
* [ADR 0007: Distribuição e Atualização Criptografada do Banco `dados.db`](./ADR-0007-distribuicao-criptografada-dados-db.md)
* Histórias `US-EMB-01` a `US-EMB-05` em `Adito/docs/stories/`
* [`Adito/docs/DISTRIBUICAO.md`](../../Adito/docs/DISTRIBUICAO.md), seção "Modelo de embedding e vetores de busca"
