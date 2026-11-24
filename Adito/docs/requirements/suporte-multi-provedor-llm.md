# Requirements — Suporte Multi-Provedor de IA (BYOK) no Adito

**Status:** REQUIREMENTS_READY
**Discovery de origem:** `Adito/docs/discovery/suporte-multi-provedor-llm.md` (`PROBLEM_READY`)
**Classificacao de Processo:** NORMAL PROCESS
**Data:** 2026-11-24
**Branch:** `feat/multi-provedor-llm`

## Intent Summary
Permitir que usuários do Adito configurem e utilizem o chat analítico com a chave de API do provedor de IA a que já possuem acesso (Gemini, OpenAI, Z.AI/GLM, OpenRouter, Groq, DeepSeek, Ollama local ou qualquer endpoint OpenAI-compatível), mantendo UX simples, armazenamento seguro no cofre do SO por provedor, fallback inteligente quando não houver embeddings e 100% de retrocompatibilidade para quem já usa Gemini na v0.1.0.

## Functional Requirements
- **FR01** — **Catálogo declarativo de provedores e presets:** manter um registro centralizado de provedores suportados (`gemini`, `openai`, `zai`, `openrouter`, `groq`, `deepseek`, `ollama`, `custom`), especificando para cada um: `id`, `label`, protocolo (`gemini` | `openai_compatible`), `base_url` padrão, `default_model`, `supports_embeddings`, `default_embedding_model` (quando aplicável) e `requires_key`.
- **FR02** — **Fábrica multi-provedor de Chat LLM e Embeddings:** refatorar `Adito/app/backend/nucleo/agents/config.py` para instanciar sob demanda `ChatGoogleGenerativeAI` (quando `gemini`) ou `ChatOpenAI` (quando `openai` ou qualquer provedor `openai_compatible`, passando `base_url`, `api_key` e `model`), além do embedder correspondente (`GoogleGenerativeAIEmbeddings` ou `OpenAIEmbeddings`) quando o provedor suportar embeddings.
- **FR03** — **Cofre do SO por provedor + persistência de configuração não-sensível (Tauri/Rust):** evoluir `Adito/app/src-tauri/src/lib.rs` para armazenar chaves separadamente por provedor no `keyring` (ex.: `llm-key-<provider>`), gravar metadados não-sensíveis (`provider`, `model`, `base_url`) em arquivo JSON na `data_dir` (ex.: `llm_config.json`) e injetar as variáveis `ADITO_LLM_PROVIDER`, `ADITO_LLM_MODEL`, `ADITO_LLM_BASE_URL` e `ADITO_LLM_API_KEY` (além de `GEMINI_API_KEY` quando provedor = `gemini`) ao subir/reiniciar o núcleo Python.
- **FR04** — **Validação real antes de salvar (`config.test_llm_key`):** estender o método RPC `config.test_llm_key` para aceitar `{provider, key, model, base_url}` (mantendo compatibilidade com chamada legada `{key}` assumindo `gemini`), validando a conectividade, autenticação e disponibilidade do modelo antes de gravar no cofre:
  - `gemini`: `GET /v1beta/models/{model}` com header `x-goog-api-key` (comportamento atual);
  - `openai` e `openai_compatible`: validação via `GET {base_url}/models` (ou chamada mínima `POST {base_url}/chat/completions` com `max_tokens=1` quando `GET /models` não validar modelo/autenticação adequadamente), devolvendo `{ok: bool, reason?: string}` claro em português.
- **FR05** — **Estratégia híbrida inteligente de Embeddings, RAG e Busca Semântica:**
  - Quando o provedor suportar embeddings: manter RAG vetorial e `analytics_text_embedding` normalmente, protegendo `core/vectors.py` contra vetores de dimensões incompatíveis (ignorando vetores cuja dimensão difere do `query_embedding` em vez de quebrar `np.vstack`/`np.linalg.norm`) e registrando metadado do provedor/modelo de embedding ativo para detectar necessidade de reindexação.
  - Quando o provedor **não** suportar embeddings (ou o embedder estiver indisponível): operar o chat automaticamente em **modo fallback sem vetores** em `query_extractor.py` (carregando `examples[:16]` + itens manuais do contexto do `app.db`, respeitando limite de contexto) e em `semantic_value_resolver.py` (pulando busca vetorial sem erro, preservando `views.json`, `rules.md` e busca local).
- **FR06** — **Tela de Configurações (`ConfiguracoesView.vue`):** oferecer fluxo simples com opção avançada:
  - seletor de **Provedor** (Gemini, OpenAI, Z.AI/GLM, OpenRouter, Groq, DeepSeek, Ollama local, Outro OpenAI-compatível);
  - campo **Modelo** pré-preenchido com o padrão recomendado do provedor e editável pelo usuário;
  - campo **Base URL** visível quando escolher "Outro (OpenAI-compatível)" ou editável em opção avançada para Ollama/Z.AI (ex.: `open.bigmodel.cn`);
  - campo **Chave API** (`type="password"`) com indicação clara quando já há chave salva para o provedor selecionado (permitindo trocar de provedor ou alterar só o modelo reutilizando a chave já guardada no cofre);
  - ações **Testar e salvar** e **Remover** (remove a chave do provedor selecionado).
- **FR07** — **Privacidade e erros adaptados ao provedor ativo:** atualizar a seção *"O que sai do seu computador"* em `ConfiguracoesView.vue` e as mensagens de erro em `rpc/errors.py` (`llm_error_message`), `rpc/core_methods.py` (`LLM_KEY_MISSING`, `KEY_INVALID_CHARS`) e `analytics_index/embedder.py` para referenciarem o provedor ativo em vez de "Gemini" fixo — indicando explicitamente quando os dados permanecem 100% locais (servidor em `localhost`/`127.0.0.1`).
- **FR08** — **Feedback na aba Administração → Base de conhecimento (`AdminView.vue`):** exibir aviso claro quando:
  - o provedor ativo não suporta embeddings (explicando que o chat funciona via modo fallback textual e que "Wipe & Retrain" vetorial requer provedor com embeddings); ou
  - existem itens/vetores no `app.db` gerados por dimensão/provedor diferente do ativo (orientando o usuário a executar "Wipe & Retrain").
- **FR09** — **Contrato RPC e estado do provedor (`me`, `llm_key_status`, `config.llm_providers`):** expor no `me` (e/ou em método dedicado de metadados de provedores) os campos `llm_configured`, `llm_provider`, `llm_provider_label`, `llm_model`, `llm_supports_embeddings` e `llm_is_local`, mantendo retrocompatibilidade com todos os campos atuais de `me` e do contrato RPC.
- **FR10** — **Suporte a servidor local sem chave (Ollama):** permitir testar, salvar e usar o chat com chave vazia exclusivamente quando o host da `base_url` for loopback (`localhost`, `127.0.0.1`, `::1`), validando a acessibilidade do servidor local antes de salvar.

## Business / Domain Rules
- **BR01** — **Retrocompatibilidade absoluta com v0.1.0:** se não houver `llm_config.json` salvo, uma chave já existente em `gemini-api-key` no cofre do SO ou `GEMINI_API_KEY` / `GOOGLE_API_KEY` no ambiente deve ativar automaticamente o provedor `gemini` com o modelo padrão, sem exigir reconfiguração.
- **BR02** — **Política de chave obrigatória vs. servidor local:** chave vazia só é aceita quando a `base_url` aponta para host loopback (`localhost`, `127.0.0.1`, `::1`). Para qualquer endpoint remoto, a chave é obrigatória e deve conter apenas caracteres ASCII imprimíveis sem espaços ou quebras de linha.
- **BR03** — **Preservação de chaves por provedor:** trocar o provedor ativo no Adito nunca apaga chaves já guardadas no cofre do SO para outros provedores; a ação "Remover" remove apenas a chave do provedor selecionado (e `gemini-api-key` legado se o provedor for `gemini`).
- **BR04** — **Chat nunca bloqueado por falta de embeddings:** a ausência de suporte a embeddings em um provedor (ex.: Groq, DeepSeek) nunca pode impedir o usuário de fazer perguntas no chat; o fallback textual é acionado de forma transparente.
- **BR05** — **Proteção contra mistura de vetores:** vetores persistidos no `app.db` com dimensão incompatível com o embedder ativo nunca podem causar falha na consulta (`ValueError` no `numpy`); devem ser filtrados com segurança até nova indexação.
- **BR06** — **Segurança e LGPD:** nenhuma chave de API pode ser escrita em arquivo texto, exposta em respostas RPC ou logada em `backend.log`; colunas marcadas como sensíveis no contexto continuam estritamente bloqueadas para todos os provedores.

## Non-Functional Requirements
- **NFR01** — **Dependência externa mínima (Regra 6):** introduzir apenas `langchain-openai` em `Adito/app/backend/requirements.txt` (aprovação explícita do usuário antes de adicionar).
- **NFR02** — **Empacotamento PyInstaller:** atualizar `Adito/app/backend/adito-backend.spec` para coletar `langchain_openai` (e submódulos/dependências necessárias de runtime) sem quebrar o empacotamento desktop em Linux/Windows.
- **NFR03** — **Compatibilidade de structured output entre provedores:** `with_structured_output` em `orchestrator/router.py`, `bi_agent/nodes/question_rewriter.py`, `sql_generator.py` e `sql_corrector.py` deve funcionar de forma consistente com `ChatGoogleGenerativeAI` e `ChatOpenAI` (testando e definindo o método adequado — `function_calling` / padrão — por provedor, com erro amigável caso um modelo custom não suporte tool calling/structured output).
- **NFR04** — **Resiliência de timeout e rate limit:** a validação de chave/conexão deve respeitar timeout máximo de 15 s; `EmbedderComEspera` deve continuar tratando HTTP 429/rate limit de forma genérica (mantendo espera inteligente para Gemini e outros provedores).
- **NFR05** — **Cobertura de testes 100% offline:** atualizar e expandir `core/tests.py`, `teste_contrato.py` + `referencia.json`, `src-tauri/src/lib.rs` (`cargo test`), Vitest (`llmKey.spec.ts` e testes da tela) e `tauriMock.ts` sem depender de rede real.
- **NFR06** — **Startup rápido do núcleo:** manter lazy imports para `langchain_google_genai` e `langchain_openai` dentro de `agents/config.py`, evitando regressão no tempo de inicialização (`ready`) do `desktop_server.py`.

## User Scenarios

### Main flow
1. Usuário abre **Configurações**, seleciona um provedor (ex.: **Z.AI / GLM** ou **OpenAI**), vê o modelo padrão recomendado já preenchido (podendo editá-lo se quiser), cola sua chave API e clica em **Testar e salvar**.
2. O front chama `config.test_llm_key` com `{provider, key, model, base_url}`; o núcleo valida a chave/modelo diretamente no endpoint do provedor e retorna `{ok: true}`.
3. O Tauri salva a chave no cofre do SO sob `llm-key-<provider>`, grava `{provider, model, base_url}` em `llm_config.json` na `data_dir` e reinicia o núcleo com as novas variáveis de ambiente.
4. Usuário vai para o **Chat** e faz perguntas normalmente; o agente responde usando o provedor escolhido (com RAG vetorial se suportado, ou fallback textual automático se o provedor for só-chat).
5. Mais tarde, o usuário volta a **Configurações**, seleciona **Gemini** (que já tinha chave salva) e clica em **Ativar / Testar e salvar** sem precisar digitar a chave antiga novamente.

### Alternative / Error / Edge cases
- **Upgrade de v0.1.0:** usuário atualiza o Adito já tendo `gemini-api-key` no cofre do SO (sem `llm_config.json`). Ao abrir, o app detecta a chave legada e inicia em modo `gemini` transparentemente.
- **Chave com acento, espaço ou inválida (401/403):** validação bloqueia antes de salvar e exibe erro claro em português com o nome do provedor escolhido.
- **Modelo inexistente (404) ou sem permissão:** validação falha antes de salvar informando que o modelo não está disponível na conta/provedor.
- **Provedor sem embeddings (ex.: Groq / DeepSeek):** chat funciona sem erro usando fallback textual; na aba **Admin → Base de conhecimento**, um banner informa que o provedor ativo não gera embeddings e o botão "Wipe & Retrain" não tenta gerar vetores sem suporte.
- **Troca de dimensão de embedding (ex.: Gemini 1024 → OpenAI 1536):** busca vetorial em `core/vectors.py` ignora vetores de dimensão diferente sem lançar exceção, cai para fallback se nenhum vetor compatível restar e a aba **Base de conhecimento** sinaliza necessidade de "Wipe & Retrain".
- **Ollama local desligado ou sem modelo baixado:** validação permite chave vazia (por ser `localhost`), tenta conectar na URL local e retorna erro amigável (*"Não consegui conectar ao servidor local em http://localhost:11434/v1. Verifique se o Ollama está rodando."*).
- **Endpoint remoto sem chave:** validação rejeita antes da rede informando que a chave API é obrigatória para provedores remotos.
- **Troca apenas do modelo mantendo a mesma chave salva no cofre:** o Tauri resolve a chave já guardada do provedor (ou o usuário cola uma nova) e testa o novo modelo antes de aplicar — **sem** jamais enviar a chave de volta para o frontend!

## Business / Domain Context
- O Adito é um aplicativo desktop local (Tauri v2 + Vue 3 + sidecar Python via STDIO) usado por servidores e gestores do IFES Campus Serra para consultas analíticas sobre pesquisa e extensão.
- A equipe não mantém servidor backend próprio; cada usuário traz sua própria credencial de IA (BYOK).
- O uso exclusivo do Gemini gera bloqueio operacional quando a cota gratuita acaba ou quando o usuário já tem acesso pago/institucional a OpenAI, Z.AI/GLM, OpenRouter, Groq, DeepSeek ou um servidor Ollama local.

## Technical Context & Constraints
- **Backend Python (`Adito/app/backend/nucleo/`):**
  - `agents/config.py`: ponto único de fábrica (`get_chat_llm`, `get_embeddings`).
  - `agents/orchestrator/router.py`, `bi_agent/nodes/{question_rewriter,sql_generator,sql_corrector}.py`: consumidores de `with_structured_output`.
  - `agents/bi_agent/nodes/query_extractor.py`, `semantic_value_resolver.py`, `core/vectors.py`, `analytics_index/embedder.py`: camada RAG/vetorial.
  - `rpc/core_methods.py`, `rpc/errors.py`, `rpc/admin.py`, `rpc/chat.py`: endpoints RPC e mensagens de erro.
  - `Adito/app/backend/requirements.txt` e `Adito/app/backend/adito-backend.spec`.
- **Desktop Rust (`Adito/app/src-tauri/src/lib.rs`):** gerenciamento do `keyring`, leitura/gravação de `llm_config.json`, migração/retrocompatibilidade de `gemini-api-key`, comandos Tauri e reinício do processo núcleo.
- **Frontend Vue (`Adito/app/frontend-vue/`):** `src/common/api/llmKey.ts`, `src/modules/settings/views/ConfiguracoesView.vue`, `src/modules/admin/views/AdminView.vue`, `tests/unit/llmKey.spec.ts` e `tests/e2e/helpers/tauriMock.ts`.
- **Testes e Contrato:** `Adito/app/backend/nucleo/core/tests.py`, `Adito/app/scripts/teste_contrato.py`, `Adito/app/scripts/contrato/referencia.json`.

## Quality Attributes
- **Segurança:** segredos isolados no cofre do SO por provedor; chave nunca trafega do cofre para o frontend (revalidação de modelo com chave já salva deve ocorrer entre Rust e núcleo Python, sem expor o segredo à WebView).
- **Retrocompatibilidade:** upgrade sem fricção a partir da v0.1.0 (chave Gemini legada e variáveis `GEMINI_API_KEY`/`GOOGLE_API_KEY`).
- **Resiliência:** falha em embeddings ou divergência de dimensão nunca derruba o chat.
- **Manutenibilidade:** adicionar um novo provedor OpenAI-compatível no futuro deve exigir apenas 1 nova entrada declarativa no catálogo de presets.

## Assumptions
- **A01** — Os modelos padrão iniciais dos presets serão: Gemini (`gemini-3.5-flash-lite`), OpenAI (`gpt-4o-mini`), Z.AI/GLM (`glm-4.5-flash` em `https://api.z.ai/api/paas/v4`), OpenRouter (`google/gemini-2.5-flash` em `https://openrouter.ai/api/v1`), Groq (`llama-3.3-70b-versatile` em `https://api.groq.com/openai/v1`), DeepSeek (`deepseek-chat` em `https://api.deepseek.com/v1`) e Ollama (`qwen2.5:7b` em `http://localhost:11434/v1`) — todos editáveis na UI.
- **A02** — Os embeddings padrão para provedores que os suportam serão: Gemini (`gemini-embedding-2`, 1024 dims), OpenAI (`text-embedding-3-small`), Z.AI (`embedding-3`) e Ollama (`nomic-embed-text`, opcional/graceful fallback caso não instalado).
- **A03** — Quando o usuário alterar apenas o modelo ou alternar para um provedor que já possui chave salva no cofre do SO (sem redigitar a chave), o Tauri fará a leitura da chave no cofre e a enviará diretamente ao teste ou ao núcleo sem nunca expor o valor da chave para o frontend Vue.
- **A04** — Em modo de desenvolvimento sem Tauri (CLI / `teste_contrato.py` / `unittest`), as variáveis `ADITO_LLM_PROVIDER`, `ADITO_LLM_MODEL`, `ADITO_LLM_BASE_URL`, `ADITO_LLM_API_KEY` (com fallback para `GEMINI_API_KEY`/`GOOGLE_API_KEY` e `GEMINI_MODEL`) governam o provedor ativo.

## Out of Scope
- SDK nativo da Anthropic/Claude (`langchain-anthropic`) — uso de Claude segue possível via OpenRouter.
- Múltiplos perfis nomeados ou seletor de modelo dentro da tela de chat.
- Configuração de 2 provedores simultâneos (chat em um provedor + embeddings em outro).
- Embeddings locais embutidos via ONNX/fastembed no instalador.
- Consulta dinâmica de modelos via API para popular dropdown.

## Open Questions
- `[BLOCKING? nao]` No modo fallback sem embeddings (`query_extractor.py`), incluir até um teto (ex.: 10) de itens manuais do contexto criados no `app.db` junto com `examples[:16]`, ou usar apenas `examples[:16]`? (Padrão proposto: incluir itens manuais do contexto até um limite seguro, preservando o valor do que o admin cadastrou na Base de conhecimento.)

## Key Decisions Proposed
1. **Apenas 1 nova dependência (`langchain-openai`):** cobre OpenAI + Z.AI/GLM + OpenRouter + Groq + DeepSeek + Ollama + qualquer endpoint OpenAI-compatível via catálogo declarativo.
2. **Segurança no reuso de chave salva (`A03`):** o frontend nunca recebe a chave de volta do cofre do SO; ao reativar um provedor já salvo ou mudar só o modelo, o comando Tauri busca a chave no cofre e aciona a validação/reinício diretamente pelo lado Rust → núcleo.
3. **Configuração não-sensível em `llm_config.json` na `data_dir` + segredos no `keyring` por provedor:** evita guardar metadados em entradas misturadas no cofre e facilita migração/retrocompatibilidade com `gemini-api-key`.
4. **Proteção defensiva de dimensão em `core/vectors.py` + fallback automático sem embeddings:** elimina qualquer crash de `numpy` ao alternar provedores e garante que provedores só-chat funcionem de imediato.
5. **Validação inteligente em `config.test_llm_key`:** usa `GET` quando o endpoint valida chave+modelo (Gemini) e `POST /chat/completions` mínimo (`max_tokens=1`) ou `GET /models` autenticado nos OpenAI-compatíveis para garantir que tanto a chave quanto o nome do modelo digitado realmente funcionam.

## Review & Adjust

O usuario pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes do gate.

- [x] Proposta completa apresentada ao usuario
- [x] Ajustes solicitados incorporados
- [x] IDs estabilizados depois da revisao
- [x] Nenhuma pergunta bloqueante aberta

### User adjustments
- Aprovado sem alteracoes adicionais em 2026-11-24 (`prossiga.`).
- Ajuste pós-validação funcional em 2026-11-24: removidos provedores sem suporte a embeddings (`groq`, `deepseek`, `custom`), promovido `openrouter` (com `/api/v1/embeddings`), adicionados `mistral` (padrão `ministral-8b-latest` + `mistral-embed`), `together` (`intfloat/multilingual-e5-large-instruct`) e `fireworks` (`nomic-ai/nomic-embed-text-v1.5`), mantendo fallback defensivo, dropdown customizado (`ProviderSelect.vue`) com indicador "Em uso" e diagnóstico detalhado de erros HTTP 429.

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
