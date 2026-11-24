# User Story: [US-LLM-01] Catálogo de provedores, fábrica multi-provedor e validação RPC

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

**Como** usuário ou desenvolvedor do Adito,
**Eu quero** que o núcleo Python suporte um catálogo declarativo de provedores de IA (Gemini, OpenAI, Z.AI/GLM, OpenRouter, Groq, DeepSeek, Ollama local e Outro OpenAI-compatível) com fábrica multi-provedor e validação real de credenciais/modelo via RPC,
**Para que** o agente analítico funcione com o provedor a que tenho acesso mantendo 100% de retrocompatibilidade com Gemini.

### Contexto Adicional

Origem: `Adito/docs/discovery/suporte-multi-provedor-llm.md` (`PROBLEM_READY`) e `Adito/docs/requirements/suporte-multi-provedor-llm.md` (`REQUIREMENTS_READY`).

Atualmente o núcleo Python (`Adito/app/backend/nucleo/agents/config.py`, `rpc/core_methods.py` e `rpc/errors.py`) está acoplado exclusivamente ao Google Gemini (`ChatGoogleGenerativeAI`, `GEMINI_API_KEY` e mensagens de erro fixas). Esta story desacopla a camada de chat LLM, centraliza os presets de provedores suportados e evolui o contrato RPC de validação e status mantendo apenas uma nova dependência externa (`langchain-openai`) para cobrir OpenAI e todo o ecossistema OpenAI-compatível.

**Requisitos rastreados:** `FR01`, `FR02`, `FR04`, `FR07` (backend), `FR09`, `FR10` (backend), `BR01` (env vars), `BR02`, `BR06`, `NFR01`, `NFR03`, `NFR04`, `NFR05` (backend/contrato), `NFR06`, `A01`, `A02`, `A04`.

### Pontos de Esclarecimento

Nenhum ponto pendente. (Nota de governança — Regra 6: antes de adicionar `langchain-openai` em `Adito/app/backend/requirements.txt`, obter confirmação explícita do usuário na etapa de implementação.)

---

## Criterios de Aceitacao

- [ ] **Criterio 1 (Catálogo declarativo — FR01, A01, A02):** Existe um registro centralizado dos 8 provedores (`gemini`, `openai`, `zai`, `openrouter`, `groq`, `deepseek`, `ollama`, `custom`) com `id`, `label`, `protocol` (`gemini` | `openai_compatible`), `base_url`, `default_model`, `supports_embeddings`, `default_embedding_model` e `requires_key`, usando os modelos/URLs padrão definidos em `A01` e `A02`.
- [ ] **Criterio 2 (Fábrica multi-provedor e lazy imports — FR02, NFR01, NFR06, A04, BR01):** `agents/config.py` lê `ADITO_LLM_PROVIDER`, `ADITO_LLM_MODEL`, `ADITO_LLM_BASE_URL` e `ADITO_LLM_API_KEY` (com fallback automático para `GEMINI_API_KEY`/`GOOGLE_API_KEY` e `GEMINI_MODEL` assumindo `provider = "gemini"`), instancia `ChatGoogleGenerativeAI` para `gemini` e `ChatOpenAI` (`langchain-openai`) para `openai`/`openai_compatible` com lazy imports que preservam o tempo de startup (`ready`) do `desktop_server.py`.
- [ ] **Criterio 3 (Structured output entre provedores — NFR03):** `with_structured_output` em `orchestrator/router.py`, `bi_agent/nodes/question_rewriter.py`, `sql_generator.py` e `sql_corrector.py` seleciona estratégia compatível com `ChatGoogleGenerativeAI` e `ChatOpenAI`, retornando erro amigável em português caso um modelo custom não suporte tool calling/structured output.
- [ ] **Criterio 4 (Validação real `config.test_llm_key` — FR04, FR10, BR02, NFR04):** `config.test_llm_key` aceita `{provider, key, model, base_url}` e mantém retrocompatibilidade com `{key}` (assumindo `gemini`), aplica timeout máximo de 15 s, rejeita chave vazia ou com caracteres inválidos/espaços/quebras em endpoints remotos, aceita chave vazia exclusivamente para hosts loopback (`localhost`, `127.0.0.1`, `::1`), valida conexão/autenticação/modelo (`GET /v1beta/models/{model}` para Gemini; `GET /models` ou `POST /chat/completions` com `max_tokens=1` para OpenAI/OpenAI-compatíveis) e retorna `{ok: bool, reason?: string}` claro em português.
- [ ] **Criterio 5 (Contrato RPC e erros agnósticos — FR07, FR09, BR06):** O método `me` expõe `llm_configured`, `llm_provider`, `llm_provider_label`, `llm_model`, `llm_supports_embeddings` e `llm_is_local` preservando todos os campos existentes; o catálogo de provedores fica disponível via RPC (`config.llm_providers`); `rpc/errors.py` (`llm_error_message`) e `rpc/core_methods.py` citam o provedor ativo em vez de "Gemini" fixo; nenhuma chave de API é retornada em RPC ou escrita em logs.
- [ ] **Criterio 6 (Testes offline e contrato — NFR05):** `Adito/app/backend/nucleo/core/tests.py` e `Adito/app/scripts/teste_contrato.py` (com `Adito/app/scripts/contrato/referencia.json` atualizado) cobrem os novos provedores, validações, erros e retrocompatibilidade passando 100% offline.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 3
- **Justificativa do nivel:** A story altera payloads e comportamento observável de boundaries RPC (`me`, `config.test_llm_key`, `config.llm_providers`, `rpc/errors.py`) e o projeto já possui runner executável de contrato (`Adito/app/scripts/teste_contrato.py` + `referencia.json`).
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** O comportamento técnico detalhado está formalizado em `Adito/docs/requirements/suporte-multi-provedor-llm.md` e coberto pelo contrato executável e testes unitários.
- **Spec prevista:** N/A
- **US exige Contract governado?** Sim
- **Justificativa do Contract:** Estende os métodos RPC `me`, `config.test_llm_key` e introduz `config.llm_providers` no protocolo STDIO consumido pelo frontend Vue e Tauri.
- **Contract previsto:** `Adito/app/scripts/contrato/referencia.json` + `Adito/app/scripts/teste_contrato.py`
- **Padrao de erro aplicavel:** `Adito/app/backend/nucleo/rpc/errors.py` (códigos RPC `LLM_KEY_MISSING`, `KEY_INVALID_CHARS`, mensagens amigáveis por provedor)
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** `test-contract` (`teste_contrato.py`) + `unittest` (`core/tests.py`)
- **Touch List preliminar:**
  - `Adito/app/backend/requirements.txt` (após aprovação explícita da Regra 6)
  - `Adito/app/backend/nucleo/agents/providers.py` (novo — catálogo declarativo)
  - `Adito/app/backend/nucleo/agents/config.py`
  - `Adito/app/backend/nucleo/agents/orchestrator/router.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/question_rewriter.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/sql_generator.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/sql_corrector.py`
  - `Adito/app/backend/nucleo/rpc/core_methods.py`
  - `Adito/app/backend/nucleo/rpc/errors.py`
  - `Adito/app/backend/nucleo/core/tests.py`
  - `Adito/app/scripts/teste_contrato.py`
  - `Adito/app/scripts/contrato/referencia.json`
- **Task Issues previstas:** N/A

---

## Mockups/Wireframes

N/A (story de núcleo backend e contrato RPC; interface visual está em `US-LLM-04`).

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `agents/providers.py` (catálogo), `agents/config.py` (fábrica), `agents/orchestrator/router.py`, `agents/bi_agent/nodes/{question_rewriter,sql_generator,sql_corrector}.py`, `rpc/core_methods.py`, `rpc/errors.py`.
- **APIs necessarias:** Métodos RPC STDIO `me`, `config.test_llm_key` e `config.llm_providers`.
- **Database changes:** Nenhuma migração de banco nesta story.
- **Referencias do modelo de dados:** N/A
- **Erros observaveis esperados:**
  - `LLM_KEY_MISSING`: provedor remoto sem credencial configurada.
  - `KEY_INVALID_CHARS`: caracteres não-ASCII, espaços ou quebras de linha na chave.
  - `config.test_llm_key` retornando `{ok: false, reason}` para: chave inválida (401/403), modelo não encontrado (404), cota/rate limit (429), timeout (15 s), erro de conexão em servidor local (`localhost`/`127.0.0.1`), URL inválida ou chave vazia em endpoint remoto.
  - Erro amigável em português quando modelo custom não suporta structured output / tool calling.

### Dependencias

- [ ] Aprovação explícita do usuário (Regra 6) para adicionar `langchain-openai` em `Adito/app/backend/requirements.txt`.

### Consideracoes de Performance

- Manter imports de `langchain_google_genai` e `langchain_openai` preguiçosos (dentro de `get_chat_llm`/`get_embeddings`) para não aumentar o tempo de inicialização até o sinal `ready` do `desktop_server.py`.
- Timeout estrito de 15 s nas chamadas HTTP de validação em `config.test_llm_key`.

---

## Plano de Testes

### Testes Unitarios

- [ ] Resolução de catálogo e defaults para todos os 8 provedores (`A01`, `A02`).
- [ ] Precedência de env vars (`ADITO_LLM_*` vs. fallback legado `GEMINI_API_KEY`/`GOOGLE_API_KEY` e `GEMINI_MODEL`).
- [ ] Fábrica `get_chat_llm` instanciando `ChatGoogleGenerativeAI` para `gemini` e `ChatOpenAI` com `base_url`/`api_key`/`model` para `openai` e presets OpenAI-compatíveis (incluindo chave dummy/vazia segura para loopback).
- [ ] Validação `config.test_llm_key` com mocks HTTP: sucesso Gemini, sucesso OpenAI-compatível, chamada legada `{key}`, 401/403, 404 modelo inexistente, 429 cota, timeout, loopback sem chave (sucesso e servidor desligado), remoto sem chave (bloqueado antes da rede).
- [ ] Mensagens de `llm_error_message` adaptadas ao provedor ativo sem vazar chave nem citar "Gemini" quando outro provedor está ativo.
- [ ] Helper de `with_structured_output` compatível com Gemini e OpenAI-compatíveis.

### Testes de Integracao

- [ ] Execução do fluxo RPC `me` e `config.llm_providers` via `desktop_server.py` em memória/subprocesso sem rede.

### Testes de Contract

- [ ] `Adito/app/scripts/teste_contrato.py` atualizado e passando contra `Adito/app/scripts/contrato/referencia.json` verificando retrocompatibilidade dos campos existentes de `me` e formato dos novos campos.

### Testes Manuais

- [ ] Subir o núcleo com `GEMINI_API_KEY` legado e confirmar que `me` reporta `llm_provider = "gemini"`, `llm_configured = true`.
- [ ] Subir o núcleo com `ADITO_LLM_PROVIDER=ollama` e `ADITO_LLM_BASE_URL=http://localhost:11434/v1` sem chave e verificar `llm_is_local = true`.

### BDD / Cenarios de Comportamento

- [ ] N/A (coberto por testes unitários e contrato executável).

---

## Tasks (Breakdown)

- [ ] **[TASK-001]** Criar módulo `agents/providers.py` com catálogo declarativo, validação de URL/loopback e resolução de configuração via env vars
  - GitHub Task Issue: N/A
  - Estimativa: 2h
  - Assignee: A definir
- [ ] **[TASK-002]** Refatorar `agents/config.py` (com `langchain-openai` após aprovação Regra 6) e compatibilizar `with_structured_output` nos nós do agente
  - GitHub Task Issue: N/A
  - Estimativa: 3h
  - Assignee: A definir
- [ ] **[TASK-003]** Estender `rpc/core_methods.py` (`me`, `config.test_llm_key`, `config.llm_providers`) e `rpc/errors.py` (erros por provedor)
  - GitHub Task Issue: N/A
  - Estimativa: 3h
  - Assignee: A definir
- [ ] **[TASK-004]** Atualizar `core/tests.py`, `teste_contrato.py` e `referencia.json` 100% offline
  - GitHub Task Issue: N/A
  - Estimativa: 2h
  - Assignee: A definir

---

## IA Insights

### Sugestoes de Implementacao

- Centralizar a lógica de `is_loopback_url(url)` em `agents/providers.py` usando `urllib.parse.urlparse` (validando `hostname in {"localhost", "127.0.0.1", "::1"}` e esquema `http`/`https`) para evitar bypass por substrings malformadas.
- Para `ChatOpenAI` apontando para Ollama sem chave, passar um placeholder inerte no cliente SDK (ex.: `"ollama"`), nunca exigindo segredo do usuário.
- Em `config.test_llm_key` para `openai_compatible`: tentar `POST {base_url}/chat/completions` mínimo (`max_tokens=1`, `messages=[{"role":"user","content":"ok"}]`) ou fallback de `GET {base_url}/models` conforme resposta, garantindo que erros de modelo inexistente (404) e cota (429) sejam detectados antes de salvar.

### Riscos Identificados

- Alguns endpoints OpenAI-compatíveis (ex.: proxies locais ou Z.AI/OpenRouter) diferem no suporte a `response_format` vs. `function_calling` no `with_structured_output` — criar um helper único (`bind_structured_output(llm, schema)`) facilita ajuste pontual e fallback de erro claro.
- `teste_contrato.py` compara estrutura exata de respostas RPC contra `referencia.json`; atualizar ambos na mesma mudança evita falso positivo de regressão.

### Alternativas Consideradas

- Usar `litellm` como camada única: descartada por trazer árvore pesada de dependências e alto risco de quebrar o empacotamento PyInstaller (`NFR01`/`NFR02`).

---

## Notas e Comentarios

- Faz parte do **Vertical Slice 1** junto com `US-LLM-02`.
- **Ajuste final consolidado na implementação (24/11/2026):** o catálogo final reúne 8 provedores com suporte completo a Chat + Embeddings (`gemini`, `openai`, `openrouter`, `mistral` com padrão `ministral-8b-latest`, `zai`, `together`, `fireworks` e `ollama`), removendo provedores só-chat (`groq`, `deepseek`, `custom`). Validação `config.test_llm_key` e `rpc/errors.py` exibem o motivo exato de erros HTTP 429 (diferenciando capacidade do plano vs. cota).

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
