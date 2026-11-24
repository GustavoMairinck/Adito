# User Story: [US-LLM-02] Embeddings híbridos, proteção de dimensão vetorial e fallback textual automático

**Epic:** EPIC-11: Suporte Multi-Provedor de IA (BYOK)
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** Alta (Vertical Slice 1)
**Story Points:** 5
**Sprint:** A definir
**Status:** Done
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário que utiliza um provedor só-chat (ex.: Groq, DeepSeek ou endpoint custom sem embeddings) ou alterna entre provedores com dimensões de embeddings diferentes (ex.: Gemini ↔ OpenAI),
**Eu quero** que o chat continue respondendo automaticamente sem erros de vetorização ou dimensão e que a Base de conhecimento sinalize quando é necessário reindexar,
**Para que** a ausência ou troca de embeddings nunca bloqueie minhas perguntas analíticas.

### Contexto Adicional

Origem: `Adito/docs/discovery/suporte-multi-provedor-llm.md` (`PROBLEM_READY`) e `Adito/docs/requirements/suporte-multi-provedor-llm.md` (`REQUIREMENTS_READY`).

Hoje o Adito assume sempre embeddings Gemini de 1024 dimensões (`analytics_index/embedder.py` e `core/vectors.py`), onde `np.vstack` + `np.linalg.norm` lança `ValueError` caso vetores com dimensões diferentes coexistam no `app.db`. Além disso, provedores populares só-chat (como Groq e DeepSeek) não oferecem API de embeddings. Esta story implementa a estratégia híbrida inteligente: RAG vetorial seguro com proteção de dimensão quando suportado, e fallback textual transparente quando não há embedder disponível.

**Requisitos rastreados:** `FR05`, `FR07` (`embedder.py`), `FR08` (sinalização e guarda no backend), `BR04`, `BR05`, `NFR04`, `NFR05` (backend), `A02`.

### Pontos de Esclarecimento

Nenhum ponto pendente. (Decisão confirmada no Review & Adjust: o modo fallback textual inclui até um teto seguro de 10 itens manuais do contexto do `app.db` além de `examples[:16]`.)

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Proteção de dimensão e provedor em `core/vectors.py` — FR05, BR05):** A busca em `core/vectors.py`, `query_extractor.py` e `analytics_index/services.py` ignora vetores de dimensão ou provedor/modelo divergentes (inclusive mesma dimensão 1024 entre Gemini/Mistral/Together e itens legados v0.1.0 sem tag quando o provedor ativo não for Gemini), sem lançar `ValueError` no `numpy`.
- [x] **Criterio 2 (Embedder multi-provedor e rastreamento em `analytics_text_embedding` — FR02, FR05, FR08, A02):** Migração v2 → v3 adiciona `embedding_provider` e `embedding_model` em `analytics_text_embedding`; `embedding_diagnostics` inspeciona `knowledge_knowledgeitem` e `analytics_text_embedding` e sinaliza `needs_retrain` em `admin.system_status`; `index_contexto` re-embeda manuais incompatíveis em lote antes da transação e limpa `analytics_text_embedding` de outro provedor/modelo/dimensão.
- [x] **Criterio 3 (Fallback textual defensivo no chat — FR05, BR04):** Quando o embedder estiver indisponível (ex.: Ollama sem `nomic-embed-text`) ou não houver vetores compatíveis, `query_extractor.py` opera em fallback textual (`examples[:16]` + até 10 itens manuais do `app.db`) e `semantic_value_resolver.py` pula busca vetorial sem erro.
- [x] **Criterio 4 (Guarda em operações vetoriais do Admin — FR08):** Ações de indexação e "Wipe & Retrain" em `rpc/admin.py` verificam suporte a embeddings antes de chamar o provedor e retornam mensagem clara em português se indisponível.
- [x] **Criterio 5 (Rate limit e erros agnósticos em `EmbedderComEspera` — FR07, NFR04):** `analytics_index/embedder.py` trata HTTP 429/rate limit de forma agnóstica ao provedor.
- [x] **Criterio 6 (Testes unitários e contrato offline — NFR05):** `core/tests.py` e `teste_contrato.py` validam troca de provedor de mesma dimensão (1024 ↔ 1024), mistura de dimensões (1024 vs. 1536), migração v3, fallback com manuais e detecção de reindexação 100% offline.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 3
- **Justificativa do nivel:** Altera comportamento observável do RAG/chat e expõe indicadores de suporte/compatibilidade de embeddings nos endpoints RPC da Base de conhecimento, validados por `teste_contrato.py` e `core/tests.py`.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** Regras de fallback e proteção vetorial estão especificadas em `Adito/docs/requirements/suporte-multi-provedor-llm.md` (`FR05`, `FR08`, `BR04`, `BR05`).
- **Spec prevista:** N/A
- **US exige Contract governado?** Sim
- **Justificativa do Contract:** Adiciona campos de diagnóstico de embeddings (suporte ativo + indicação de vetores com dimensão divergente) consumidos por `AdminView.vue` (`US-LLM-04`).
- **Contract previsto:** `Adito/app/scripts/contrato/referencia.json` + `Adito/app/scripts/teste_contrato.py`
- **Padrao de erro aplicavel:** `Adito/app/backend/nucleo/rpc/errors.py`
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** `test-contract` (`teste_contrato.py`) + `unittest` (`core/tests.py`)
- **Touch List preliminar:**
  - `Adito/app/backend/nucleo/core/vectors.py`
  - `Adito/app/backend/nucleo/agents/config.py`
  - `Adito/app/backend/nucleo/analytics_index/embedder.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/query_extractor.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/semantic_value_resolver.py`
  - `Adito/app/backend/nucleo/rpc/admin.py`
  - `Adito/app/backend/nucleo/core/tests.py`
  - `Adito/app/scripts/teste_contrato.py`
  - `Adito/app/scripts/contrato/referencia.json`
- **Task Issues previstas:** N/A

---

## Mockups/Wireframes

N/A (os banners visuais de aviso na aba Base de conhecimento estão em `US-LLM-04`).

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `core/vectors.py`, `agents/config.py`, `analytics_index/embedder.py`, `agents/bi_agent/nodes/query_extractor.py`, `agents/bi_agent/nodes/semantic_value_resolver.py`, `rpc/admin.py`.
- **APIs necessarias:** Endpoints RPC de status/listagem da Base de conhecimento e `admin.wipe_and_retrain` (ou equivalente em `rpc/admin.py`).
- **Database changes:** Sem alteração destrutiva de schema; caso seja necessário registrar metadado de embedding ativo (`provider`, `model`, `dim`) no `app.db`, usar tabela/chave de configuração leve compatível com bancos existentes (ou inspeção direta da dimensão dos vetores armazenados).
- **Referencias do modelo de dados:** `knowledge_knowledgeitem` e `analytics_text_embedding` no `app.db`.
- **Erros observaveis esperados:**
  - Erro amigável em `rpc/admin.py` ao tentar indexar/retrain com provedor sem embeddings.
  - Aviso não-bloqueante em log quando Ollama não possui `nomic-embed-text` instalado, acionando fallback textual transparente.

### Dependencias

- [ ] `US-LLM-01` (catálogo de provedores com `supports_embeddings` e `default_embedding_model`, fábrica em `agents/config.py`).

### Consideracoes de Performance

- Filtragem de dimensão em `core/vectors.py` deve ocorrer em O(N) antes de `np.vstack`, sem copiar matrizes desnecessariamente.
- Limitar itens manuais injetados no fallback textual (`query_extractor.py`) a no máximo 10 itens (e teto de caracteres por item) para evitar estouro da janela de contexto em modelos menores (ex.: Ollama 7B).

---

## Plano de Testes

### Testes Unitarios

- [ ] `core/vectors.py`: matriz homogênea (comportamento preservado), matriz mista 1024 + 1536 (filtra sem `ValueError` e retorna contagem de ignorados), matriz 100% incompatível (retorna lista vazia com flag de divergência).
- [ ] `query_extractor.py`: provedor sem embeddings aciona fallback textual com `examples[:16]` + até 10 itens manuais do `app.db`; provedor com embeddings onde todos os vetores são incompatíveis também cai em fallback sem erro.
- [ ] `semantic_value_resolver.py`: retorna graciosamente quando `get_embeddings()` é `None` ou lança erro de modelo de embedding ausente.
- [ ] `analytics_index/embedder.py`: trata HTTP 429 genérico e não menciona "Gemini" quando provedor ativo é OpenAI/Z.AI/Ollama.
- [ ] `rpc/admin.py`: rejeita com mensagem clara tentativa de "Wipe & Retrain" vetorial quando provedor ativo não suporta embeddings e sinaliza `embeddings_mismatch` quando há vetores incompatíveis.

### Testes de Integracao

- [ ] Consulta analítica simulada com provedor só-chat (Groq mock) e com troca Gemini → OpenAI sobre `app.db` pré-populado com vetores 1024 dims.

### Testes de Contract

- [ ] `Adito/app/scripts/teste_contrato.py` validando os campos adicionais de status de embeddings no RPC da Base de conhecimento.

### Testes Manuais

- [ ] Configurar provedor Groq (sem embeddings), fazer pergunta no chat e confirmar resposta sem erro.
- [ ] Com `app.db` indexado em Gemini (1024 dims), alternar para OpenAI (`text-embedding-3-small`, 1536 dims) e confirmar ausência de crash no chat + sinalização de reindexação.

### BDD / Cenarios de Comportamento

- [ ] N/A (coberto por testes unitários e de contrato).

---

## Tasks (Breakdown)

- [ ] **[TASK-001]** Proteger `core/vectors.py` contra dimensões incompatíveis e expor diagnóstico de vetores ignorados/divergentes
  - GitHub Task Issue: N/A
  - Estimativa: 2h
  - Assignee: A definir
- [ ] **[TASK-002]** Evoluir `agents/config.py` (`get_embeddings`) e `analytics_index/embedder.py` para embeddings multi-provedor e rate-limit agnóstico
  - GitHub Task Issue: N/A
  - Estimativa: 3h
  - Assignee: A definir
- [ ] **[TASK-003]** Implementar fallback textual (com teto de itens manuais) em `query_extractor.py` e degradação graciosa em `semantic_value_resolver.py`
  - GitHub Task Issue: N/A
  - Estimativa: 3h
  - Assignee: A definir
- [ ] **[TASK-004]** Adicionar guarda/sinalização de embeddings em `rpc/admin.py` e cobrir todos os cenários em `core/tests.py` + `teste_contrato.py`
  - GitHub Task Issue: N/A
  - Estimativa: 2h
  - Assignee: A definir

---

## IA Insights

### Sugestoes de Implementacao

- Inspecionar a dimensão real dos vetores já persistidos em `knowledge_knowledgeitem` / `analytics_text_embedding` (comparando com a dimensão esperada do provedor ativo ou armazenando `embedding_provider`/`embedding_dim` em metadado) evita falso alarme quando a base ainda está vazia.
- Para Ollama (`nomic-embed-text`), tentar gerar o embedding sob demanda e, em caso de 404 (modelo de embedding não baixado), degradar automaticamente para fallback textual registrando um aviso único no log.

### Riscos Identificados

- Itens manuais muito longos cadastrados no `app.db` poderiam inflar o prompt no modo fallback — aplicar truncamento controlado por item + limite de 10 itens.

### Alternativas Consideradas

- Bloquear provedores sem embeddings ou embutir modelo ONNX local no instalador: descartadas no Discovery por aumentar muito o instalador ou restringir provedores populares como Groq e DeepSeek.

---

## Notas e Comentarios

- Completa o **Vertical Slice 1** junto com `US-LLM-01`.

---

## Definition of Done Checklist

- [ ] Codigo implementado conforme criterios de aceitacao
- [ ] Decisao sobre Spec governada foi registrada
- [ ] Decisao sobre Contract governado foi registrada
- [ ] Nivel ScrumAIDev foi registrado
- [ ] Spec, Contract e BDD foram atualizados quando aplicavel
- [ ] Gates opcionais executados ou dispensados com justificativa
- [ ] Error handling observavel segue o padrao compartilhado quando aplicavel
- [ ] Code review aprovado
- [ ] Testes unitarios com cobertura adequada
- [ ] Testes de integracao e contract passando
- [ ] Documentacao atualizada
- [ ] Build/CI passando
- [ ] `Behavior change` documentado no PR
- [ ] Aprovacao do Product Owner
