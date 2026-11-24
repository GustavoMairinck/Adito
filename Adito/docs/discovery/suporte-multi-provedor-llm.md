# Discovery — Suporte Multi-Provedor de IA (BYOK) no Adito

**Status:** PROBLEM_READY
**Classificacao de Processo:** NORMAL PROCESS
**Origem:** hibrido (usuario + codigo)
**Data:** 2026-11-24
**Branch:** `feat/multi-provedor-llm`

## Intent
Permitir que qualquer usuário do Adito utilize o chat analítico com a chave de API do provedor de IA a que já tem acesso (Gemini, OpenAI, Z.AI/GLM, OpenRouter, Groq, DeepSeek, Ollama local ou qualquer endpoint OpenAI-compatível), eliminando a dependência exclusiva da API do Google Gemini e viabilizando continuidade de uso mesmo quando a cota gratuita do Gemini se esgota ou quando o usuário prefere outro provedor/modelo local.

## Problem
Hoje o Adito está acoplado de ponta a ponta ao Google Gemini (instanciação de LLM e embeddings em `agents/config.py`, validação HTTP em `rpc/core_methods.py`, mensagens de erro em `rpc/errors.py`, cofre do SO com entrada única `gemini-api-key` em `src-tauri/src/lib.rs`, tela de Configurações em `ConfiguracoesView.vue` e empacotamento PyInstaller em `adito-backend.spec`). Usuários que já possuem crédito/chave em outros provedores (OpenAI, Z.AI/GLM, OpenRouter, Groq, DeepSeek) ou que desejam rodar um modelo local (Ollama) ficam impedidos de usar o chat do Adito.

## Users / Stakeholders relevantes
- **Gestores, coordenadores e servidores do IFES Campus Serra (usuários finais):** precisam consultar dados de pesquisa e extensão em linguagem natural sem ficar bloqueados pela cota gratuita do Gemini ou obrigados a criar conta no Google AI Studio.
- **Usuários técnicos / pesquisadores com API própria ou IA local:** possuem chaves da OpenAI, Z.AI/GLM, OpenRouter, Groq, DeepSeek ou servidor Ollama local e querem conectá-los ao Adito sem alterar código.
- **Equipe de desenvolvimento e manutenção do Adito:** precisa manter o instalador desktop enxuto (PyInstaller + Tauri), os testes automatizados/contrato verdes e 100% de retrocompatibilidade para quem já instalou a v0.1.0 com Gemini.

## Current Situation
- O núcleo Python depende apenas de `langchain-google-genai` e instancia `ChatGoogleGenerativeAI` e `GoogleGenerativeAIEmbeddings` (1024 dimensões) lendo `GEMINI_API_KEY` / `GOOGLE_API_KEY` e `GEMINI_MODEL`.
- O Tauri guarda uma única chave no cofre do SO (`KEYRING_USER = "gemini-api-key"`) e a injeta via ambiente ao iniciar/reiniciar o núcleo.
- A tela **Configurações** exibe somente "Chave do Gemini" e um aviso de privacidade citando "Gemini" fixo.
- O `query_extractor.py` já possui fallback de RAG sem vetores (`examples[:16]` cobrindo as 6 views + `rules.md` + `views.json`), e o `semantic_value_resolver.py` já pula a busca vetorial quando não há valores indexados (`_has_indexed_values`).
- Porém, `core/vectors.py` calcula distância L2 assumindo dimensões homogêneas (misturar vetores de dimensões diferentes quebra com erro de broadcast no `numpy`), e `agents/orchestrator/router.py` usa `with_structured_output(..., method="function_calling")`.

## Desired Outcome
Qualquer usuário consegue abrir **Configurações**, escolher seu provedor de IA (ou um endpoint OpenAI-compatível / Ollama local), manter ou editar o modelo recomendado, informar a chave (quando exigida), validar a conexão na hora com feedback claro em português e usar o chat do Adito normalmente — preservando o funcionamento automático do Gemini para quem já o utiliza na v0.1.0.

## Success Criteria
- Usuário consegue configurar e fazer perguntas válidas no chat usando **Gemini**, **OpenAI** ou qualquer provedor **OpenAI-compatível** (presets Z.AI/GLM, OpenRouter, Groq, DeepSeek, Ollama local e Outro custom), com chave testada antes de salvar.
- Instalações existentes da v0.1.0 com `gemini-api-key` no cofre do SO ou `GEMINI_API_KEY` no ambiente continuam funcionando sem nenhuma reconfiguração manual.
- Provedores sem API de embeddings (ex.: Groq, DeepSeek ou endpoints só-chat) funcionam no chat sem erro (via fallback nativo sem vetores) e exibem aviso claro na aba **Admin → Base de conhecimento**.
- Trocar para um provedor/modelo de embedding de dimensão diferente nunca quebra a busca vetorial (`numpy`), orientando claramente o usuário a reindexar ("Wipe & Retrain").
- Chaves de API nunca são gravadas em arquivo texto (apenas no cofre do SO, isoladas por provedor), permitindo alternar de provedor e voltar ao anterior sem perder a chave salva.
- Todas as suítes automatizadas (núcleo `unittest`, contrato RPC, STDIO, Tauri `cargo test`, frontend Vitest e Playwright E2E) passam sem regressões, e o empacotamento PyInstaller (`adito-backend.spec`) inclui o novo adaptador.

## Scope

### IN
- **Provedores suportados:** Gemini (padrão), OpenAI e protocolo OpenAI-compatível com presets pré-preenchidos (**Z.AI / GLM**, **OpenRouter**, **Groq**, **DeepSeek**, **Ollama local**) + opção **"Outro (OpenAI-compatível)"** com `Base URL` editável.
- **Dependência externa mínima:** adição de apenas **1 pacote novo** (`langchain-openai`) no `Adito/app/backend/requirements.txt` e no `Adito/app/backend/adito-backend.spec` (sujeito à aprovação explícita da Regra 6 do `AGENTS.md`).
- **Estratégia híbrida de embeddings/RAG:**
  - Provedores com embeddings (Gemini, OpenAI, OpenAI-compatíveis com modelo de embedding suportado/configurado, ex.: Z.AI `embedding-3`, Ollama) usam RAG vetorial + busca semântica de valores, com proteção de dimensão/modelo em `core/vectors.py` e aviso para reindexar ao trocar.
  - Provedores só-chat operam em modo fallback sem vetores (`views.json` + `rules.md` + `examples[:16]` + busca local, avaliando incluir itens manuais do `app.db` no fallback textual), com aviso claro em **Admin → Base de conhecimento**.
- **Tela de Configurações (simples com opção avançada):** seletor de provedor, campo de modelo pré-preenchido e editável, campo `Base URL` para custom/Ollama, campo de chave API (opcional apenas para servidor local `localhost`/`127.0.0.1`), validação real antes de salvar e textos/avisos de privacidade ("O que sai do seu computador") adaptados ao provedor ativo (incluindo cenário 100% local com Ollama).
- **Armazenamento no Tauri (Rust) + retrocompatibilidade v0.1.0:** 1 provedor ativo por vez na UI; chaves guardadas por provedor no cofre do SO (`keyring`, ex.: `llm-key-<provedor>`); metadados não-sensíveis (provedor, modelo, `base_url`) salvos em arquivo de configuração na pasta de dados; leitura retrocompatível da entrada antiga `gemini-api-key` e `GEMINI_API_KEY`.
- **Validação e mensagens de erro por provedor:** `config.test_llm_key` adaptado por provedor (Gemini via `GET` modelo; OpenAI/OpenAI-compatíveis via `GET /models` ou chamada mínima de 1 token) e `rpc/errors.py` (`llm_error_message`) generalizado para mensagens claras em português sem citar "Gemini" fixo.
- **Compatibilidade dos agentes:** validar/adaptar `with_structured_output` (em `router.py`, `question_rewriter.py`, `sql_generator.py`, `sql_corrector.py`) para operar de forma confiável tanto em `ChatGoogleGenerativeAI` quanto em `ChatOpenAI` (incluindo provedores OpenAI-compatíveis).
- **Testes e contrato:** cobertura unitária (Python, Rust e Vitest), atualização do contrato RPC (`teste_contrato.py` / `referencia.json`) e mock E2E (`tauriMock.ts`).

### OUT
- SDK nativo direto da Anthropic/Claude (`langchain-anthropic`) — usuários que queiram Claude podem usar via preset OpenRouter.
- Múltiplos perfis nomeados ou troca de provedor/modelo dentro da tela de chat.
- Configuração de 2 provedores simultâneos (ex.: 1 chave para chat + 1 chave diferente exclusiva para embeddings).
- Embeddings locais embutidos via ONNX/fastembed dentro do instalador.
- Consulta dinâmica da lista completa de modelos da conta via API para popular dropdown.

### LATER
- Suporte a provedor dedicado de embeddings independente do provedor de chat (caso usuários de Groq/DeepSeek peçam busca vetorial combinada com outra chave).
- Perfis nomeados / troca rápida de modelo diretamente na barra do chat.
- Suporte nativo à API da Anthropic caso haja demanda institucional direta fora do OpenRouter.
- Execução automatizada da suíte `eval_acuracia.py` comparando matriz de modelos (Gemini vs. OpenAI vs. GLM vs. DeepSeek) para atualizar recomendações de modelos padrão.

## Constraints / Feasibility
- **Regra 6 (`AGENTS.md`):** adição de `langchain-openai` exige proposta e aprovação explícita do usuário antes da edição de `requirements.txt`.
- **Segurança / LGPD:** chaves de API nunca podem ser salvas em texto claro, nem logadas no `backend.log` ou retornadas ao frontend; dados pessoais sensíveis continuam bloqueados pela política de views do contexto.
- **Empacotamento desktop (PyInstaller + Tauri):** o sidecar `adito-backend` precisa incluir `langchain_openai`, `openai` e `tiktoken` (ou submódulos necessários) no `adito-backend.spec` sem quebrar o build Linux/Windows.
- **Compatibilidade de structured output / tool calling:** modelos escolhidos pelo usuário precisam suportar structured output/function calling (comportamento varia entre provedores OpenAI-compatíveis como DeepSeek, Groq, GLM e Ollama — pode exigir fallback ou ajuste no método de `with_structured_output`).
- **Banco `app.db` existente:** não quebrar instalações com vetores 1024-dim já gravados pelo Gemini ao trocar para um modelo de dimensão diferente (ex.: 1536 da OpenAI ou 2048 do Z.AI).

## Assumptions
- `[ASSUMPTION]` Os presets iniciais terão modelos padrão recomendados com suporte comprovado a structured output / tool calling e custo acessível (ex.: Gemini `gemini-3.5-flash-lite`, OpenAI `gpt-4o-mini`, Z.AI/GLM `glm-4.5-flash` ou `glm-4.5`, OpenRouter `google/gemini-2.5-flash` ou configurável, Groq `llama-3.3-70b-versatile`, DeepSeek `deepseek-chat`, Ollama `qwen2.5:7b`), todos editáveis pelo usuário.
- `[ASSUMPTION]` A configuração não-sensível (provedor ativo, modelo de chat, `base_url` opcional e metadado do modelo/dimensão de embedding usado na última indexação) será persistida em arquivo JSON simples na pasta `data_dir` (lido pelo Tauri ao montar o ambiente do núcleo e/ou pelo núcleo), mantendo segredos exclusivamente no `keyring`.
- `[ASSUMPTION]` Em desenvolvimento sem Tauri (CLI / scripts / testes), variáveis de ambiente (`ADITO_LLM_PROVIDER`, `ADITO_LLM_MODEL`, `ADITO_LLM_BASE_URL`, `ADITO_LLM_API_KEY`, mantendo fallback para `GEMINI_API_KEY`/`GOOGLE_API_KEY` e `GEMINI_MODEL`) permitem testar qualquer provedor sem depender do cofre do SO.
- `[ASSUMPTION]` Permitir chave vazia ficará restrito a URLs locais explícitas (`localhost`, `127.0.0.1`, `::1`), evitando envio acidental sem autenticação para endpoints remotos.

## Risks
- **Divergência de `with_structured_output` entre provedores OpenAI-compatíveis:** alguns endpoints (ex.: DeepSeek, Ollama ou Z.AI) podem rejeitar `method="function_calling"` ou `json_schema` estrito em `ChatOpenAI`, exigindo estratégia resiliente (ex.: `function_calling` com fallback ou `json_mode` testado por provedor).
- **Mistura de dimensões de vetor no `app.db`:** vetores antigos do Gemini (1024 dims) misturados com vetores novos de outro provedor (ex.: 1536 dims) quebram `np.vstack` / `np.linalg.norm` em `core/vectors.py`; mitigado filtrando/validando dimensão em `core/vectors.py` e registrando assinatura do embedder ativo.
- **Aumento de tamanho do sidecar PyInstaller:** `langchain-openai` traz `openai` e `tiktoken`; é necessário validar o empacotamento em `adito-backend.spec` (e conferir impacto no tamanho do binário).
- **Qualidade NL-to-SQL em modelos menores/locais:** o `rules.md` foi calibrado para o `flash-lite`; modelos muito pequenos locais (ex.: 3B) podem gerar SQL inferior — mitigado deixando claro na UI que a qualidade depende do modelo escolhido.
- **Validação de chave em provedores que não expõem `GET /models` ou bloqueiam `GET` sem auth:** mitigado fazendo fallback para uma chamada mínima (`max_tokens=1`) quando `GET /models` não validar autenticação/modelo adequadamente.

## Open Questions
- `[BLOCKING? nao]` No modo sem embeddings (ex.: Groq, DeepSeek), devemos incluir automaticamente no fallback de texto do `query_extractor.py` também os itens manuais criados pelo admin em `knowledge_knowledgeitem` (além de `examples[:16]`), ou manter apenas `examples[:16]` na v1? (Assumimos incluir itens manuais do contexto se houver, limitado para não estourar tokens.)
- `[BLOCKING? nao]` Para `Z.AI / GLM`, qual endpoint oficial usar como preset padrão: o internacional (`https://api.z.ai/api/paas/v4`) ou permitir alternar/editar caso o usuário tenha conta na URL chinesa (`open.bigmodel.cn`)? (Assumimos `https://api.z.ai/api/paas/v4` como padrão e campo `Base URL` editável em opção avançada.)

## Review & Adjust

- [x] Usuario revisou a proposta completa
- [x] Alteracoes solicitadas foram incorporadas
- [x] Decisoes relevantes foram confirmadas
- [x] Nao existem perguntas bloqueantes abertas

### User adjustments
- Proposta aprovada integralmente pelo usuario sem alteracoes adicionais (2026-11-24).
- **Refinamento posterior de escopo durante a implementacao/revisao do PR:** o catalogo de provedores foi ajustado para incluir apenas provedores com suporte nativo a embeddings (`gemini`, `openai`, `openrouter`, `mistral` com padrao `ministral-8b-latest`, `zai`, `together`, `fireworks`, `ollama`), removendo `groq`, `deepseek` e o preset `custom` sem embeddings (ver requisitos atualizados em `Adito/docs/requirements/suporte-multi-provedor-llm.md`).

## Gate G0 — PROBLEM READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
